"""Manifestos que permitem reproduzir cada execução da pesquisa."""

import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from git import Repo
from pydantic import BaseModel, ConfigDict


class RunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    run_id: str
    protocol_id: str
    protocol_version: str
    stage: str
    status: Literal["SUCCESS", "FAILED"]
    started_at_utc: datetime
    finished_at_utc: datetime
    code_commit_sha: str
    dirty_worktree: bool
    config_sha256: str
    taxonomy_sha256: str
    requirements_sha256: str
    python_version: str
    operating_system: str
    error: str | None = None


def sha256_file(path: str | Path) -> str:
    target = Path(path)
    digest = hashlib.sha256()

    with target.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def get_git_state(project_root: Path) -> tuple[str, bool]:
    repository = Repo(project_root, search_parent_directories=True)

    if repository.head.is_detached:
        commit_sha = repository.head.commit.hexsha
    else:
        commit_sha = repository.head.reference.commit.hexsha

    dirty = repository.is_dirty(untracked_files=True)
    return commit_sha, dirty


def write_manifest(
    *,
    project_root: Path,
    manifest_directory: Path,
    config_path: Path,
    taxonomy_path: Path,
    requirements_path: Path,
    protocol_id: str,
    protocol_version: str,
    stage: str,
    status: Literal["SUCCESS", "FAILED"],
    started_at_utc: datetime,
    require_clean_worktree: bool,
    error: str | None = None,
) -> Path:
    commit_sha, dirty = get_git_state(project_root)

    if require_clean_worktree and dirty:
        raise RuntimeError(
            "A execução científica exige um worktree limpo. "
            "Faça commit ou registre explicitamente a alteração antes de executar."
        )

    if started_at_utc.tzinfo is None or started_at_utc.utcoffset() is None:
        raise ValueError("started_at_utc precisa conter fuso horário.")

    started_at_utc = started_at_utc.astimezone(UTC)
    finished_at_utc = datetime.now(UTC)

    if finished_at_utc < started_at_utc:
        raise ValueError("finished_at_utc não pode anteceder started_at_utc.")

    run_id = f"{started_at_utc:%Y%m%dT%H%M%S%fZ}_{commit_sha[:8]}_{stage}"

    manifest = RunManifest(
        schema_version="1.0.0",
        run_id=run_id,
        protocol_id=protocol_id,
        protocol_version=protocol_version,
        stage=stage,
        status=status,
        started_at_utc=started_at_utc,
        finished_at_utc=finished_at_utc,
        code_commit_sha=commit_sha,
        dirty_worktree=dirty,
        config_sha256=sha256_file(config_path),
        taxonomy_sha256=sha256_file(taxonomy_path),
        requirements_sha256=sha256_file(requirements_path),
        python_version=sys.version,
        operating_system=platform.platform(),
        error=error,
    )

    manifest_directory.mkdir(parents=True, exist_ok=True)
    output = manifest_directory / f"{run_id}.json"
    with output.open("x", encoding="utf-8") as stream:
        json.dump(manifest.model_dump(mode="json"), stream, indent=2, ensure_ascii=False)
        stream.write("\n")

    return output
