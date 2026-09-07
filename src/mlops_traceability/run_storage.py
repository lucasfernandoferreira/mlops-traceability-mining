"""Armazenamento imutável e ponteiros para execuções locais do pipeline."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from mlops_traceability.config import load_config
from mlops_traceability.manifest import sha256_file

StageName = Literal[
    "phase1_search_candidates",
    "phase2_screen_sample",
    "phase3_clone_repos",
    "phase4_mine_commits",
    "phase5_compute_metrics",
    "study_index",
    "phase6_validate_taxonomy",
    "phase7_select_qualitative",
    "phase8_report",
    "phase9_finalize_study",
]
RunStatus = Literal["SUCCESS", "FAILED"]


class LatestRunPointer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    stage: StageName
    status: RunStatus
    run_id: str = Field(min_length=1)
    source_run_id: str | None = None
    run_directory: str = Field(min_length=1)
    artifacts: dict[str, str]
    manifest_path: str | None = None


def run_directory(interim_directory: Path, run_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", run_id) or run_id in {".", ".."}:
        raise ValueError("Invalid run ID")
    return interim_directory / "runs" / run_id


def portable_path(root: Path, path: str) -> Path:
    """New paths are root-relative; legacy absolute paths use their /data/ suffix."""
    candidate = Path(path)
    if candidate.is_absolute() and not candidate.is_relative_to(root.resolve()):
        if "/data/" not in candidate.as_posix():
            raise ValueError("Unsupported legacy artifact path")
        candidate = Path("data") / candidate.as_posix().split("/data/", 1)[1]
    target = (root / candidate).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError("Artifact path escapes project")
    return target


def verified_run(
    root: Path,
    run_id: str,
    stage: StageName | None = None,
    *,
    expected_hash: str | None = None,
    scientific: bool = False,
    seen: frozenset[str] = frozenset(),
) -> tuple[dict[str, Any], dict[str, Path], dict[str, Any]]:
    """Verify all bytes and recursively bind the source chain, independent of latest."""
    config = load_config(root / "config/config.yaml")
    run_directory(root / config.paths.interim, run_id)
    path = root / config.paths.manifests / f"{run_id}.json"
    if run_id in seen:
        raise ValueError("Cyclic source chain")
    if expected_hash is not None and sha256_file(path) != expected_hash:
        raise ValueError("Source manifest hash mismatch")
    manifest = json.loads(path.read_text())
    if manifest["run_id"] != run_id or (stage and manifest["stage"] != stage):
        raise ValueError("Source run/stage mismatch")
    if manifest["status"] != "SUCCESS":
        raise ValueError("Missing successful source stage")
    if manifest["protocol_version"] != config.protocol.version:
        raise ValueError("Source protocol mismatch")
    for field, relative in (
        ("config_sha256", "config/config.yaml"),
        ("taxonomy_sha256", "config/file_taxonomy.yaml"),
        ("requirements_sha256", "requirements.txt"),
    ):
        if manifest[field] != sha256_file(root / relative):
            raise ValueError(f"Source instrument mismatch: {relative}")
    if not re.fullmatch(r"[a-f0-9]{40}", manifest["code_commit_sha"]):
        raise ValueError("Missing code identity")
    artifacts = {}
    for artifact in manifest["artifacts"]:
        target = portable_path(root, artifact["path"])
        if sha256_file(target) != artifact["sha256"]:
            raise ValueError("Source artifact hash mismatch")
        if target.name in artifacts:
            raise ValueError("Duplicate artifact filename")
        artifacts[target.name] = target
    execution = json.loads(artifacts["execution.json"].read_text())
    if execution.get("contract_version") != "2.1.0":
        raise ValueError("Undeclared source code compatibility")
    if execution["run_id"] != run_id or execution["status"] != "SUCCESS":
        raise ValueError("Source execution mismatch")
    if scientific and (manifest["dirty_worktree"] or not execution["scientific_eligible"]):
        raise ValueError("Development source is not scientifically eligible")
    for source in execution.get("sources", []):
        verified_run(
            root,
            source["run_id"],
            expected_hash=source["manifest_sha256"],
            scientific=scientific,
            seen=seen | {run_id},
        )
    return manifest, artifacts, execution


def latest_pointer_path(interim_directory: Path, stage: StageName) -> Path:
    return interim_directory / "latest" / f"{stage}.json"


def _relative_to_interim(path: Path, interim_directory: Path) -> str:
    resolved_interim = interim_directory.resolve()
    resolved_path = path.resolve()
    if not resolved_path.is_relative_to(resolved_interim):
        raise ValueError(f"Artefato fora de data/interim: {path}")
    return resolved_path.relative_to(resolved_interim).as_posix()


def build_run_pointer(
    *,
    interim_directory: Path,
    stage: StageName,
    status: RunStatus,
    run_id: str,
    artifacts: dict[str, Path],
    source_run_id: str | None = None,
    manifest_path: Path | None = None,
) -> LatestRunPointer:
    directory = run_directory(interim_directory, run_id)
    return LatestRunPointer(
        stage=stage,
        status=status,
        run_id=run_id,
        source_run_id=source_run_id,
        run_directory=_relative_to_interim(directory, interim_directory),
        artifacts={
            name: _relative_to_interim(path, interim_directory) for name, path in artifacts.items()
        },
        manifest_path=None if manifest_path is None else manifest_path.resolve().as_posix(),
    )


def write_latest_pointer(interim_directory: Path, pointer: LatestRunPointer) -> Path:
    output = latest_pointer_path(interim_directory, pointer.stage)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        json.dump(pointer.model_dump(mode="json"), handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(temp_path, output)
    return output


def load_latest_pointer(
    interim_directory: Path,
    stage: StageName,
) -> LatestRunPointer | None:
    path = latest_pointer_path(interim_directory, stage)
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return LatestRunPointer.model_validate(json.load(handle))


def resolve_artifact(
    interim_directory: Path,
    pointer: LatestRunPointer,
    artifact_name: str,
) -> Path:
    relative_path = pointer.artifacts.get(artifact_name)
    if relative_path is None:
        raise KeyError(f"Artefato {artifact_name!r} ausente no ponteiro {pointer.stage}")
    target = (interim_directory / relative_path).resolve()
    if not target.is_relative_to(interim_directory.resolve()):
        raise ValueError(f"Ponteiro de artefato fora de data/interim: {relative_path}")
    return target


def preserve_legacy_run(
    *,
    interim_directory: Path,
    stage: StageName,
    status: RunStatus,
    run_id: str,
    legacy_artifacts: dict[str, Path],
    source_run_id: str | None = None,
    manifest_path: Path | None = None,
) -> LatestRunPointer:
    destination = run_directory(interim_directory, run_id)
    destination.mkdir(parents=True, exist_ok=True)
    archived: dict[str, Path] = {}
    for name, source in legacy_artifacts.items():
        if not source.is_file():
            raise FileNotFoundError(f"Artefato legado não encontrado: {source}")
        target = destination / source.name
        if not target.exists():
            shutil.copy2(source, target)
        archived[name] = target

    pointer = build_run_pointer(
        interim_directory=interim_directory,
        stage=stage,
        status=status,
        run_id=run_id,
        source_run_id=source_run_id,
        artifacts=archived,
        manifest_path=manifest_path,
    )
    write_latest_pointer(interim_directory, pointer)
    return pointer
