"""Manifestos que permitem reproduzir cada execução da pesquisa."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from git import Repo
from pydantic import BaseModel, ConfigDict, Field


@dataclass(frozen=True)
class RunContext:
    run_id: str
    stage: str
    started_at_utc: datetime
    code_commit_sha: str
    dirty_worktree: bool


class ManifestArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1)
    sha256: str = Field(min_length=1)
    line_count: int = Field(ge=0)


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
    artifacts: list[ManifestArtifact] = Field(default_factory=list)
    error: str | None = None


def sha256_file(path: str | Path) -> str:
    target = Path(path)
    digest = hashlib.sha256()

    with target.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def count_lines(path: str | Path) -> int:
    target = Path(path)
    line_count = 0

    with target.open("r", encoding="utf-8") as stream:
        for _line_count, _line in enumerate(stream, start=1):
            line_count = _line_count

    return line_count


def build_artifact(path: str | Path) -> ManifestArtifact:
    target = Path(path)
    return ManifestArtifact(
        path=str(target.as_posix()),
        sha256=sha256_file(target),
        line_count=count_lines(target),
    )


def get_git_state(project_root: Path) -> tuple[str, bool]:
    repository = Repo(project_root, search_parent_directories=True)

    if repository.head.is_detached:
        commit_sha = repository.head.commit.hexsha
    else:
        commit_sha = repository.head.reference.commit.hexsha

    dirty = repository.is_dirty(untracked_files=True)
    return commit_sha, dirty


def start_run(
    *,
    project_root: Path,
    stage: str,
    started_at_utc: datetime | None = None,
) -> RunContext:
    if started_at_utc is None:
        started_at_utc = datetime.now(UTC)

    if started_at_utc.tzinfo is None or started_at_utc.utcoffset() is None:
        raise ValueError("started_at_utc precisa conter fuso horário.")

    started_at_utc = started_at_utc.astimezone(UTC)
    code_commit_sha, dirty_worktree = get_git_state(project_root)
    run_id = f"{started_at_utc:%Y%m%dT%H%M%S%fZ}_{code_commit_sha[:8]}_{stage}"
    return RunContext(
        run_id=run_id,
        stage=stage,
        started_at_utc=started_at_utc,
        code_commit_sha=code_commit_sha,
        dirty_worktree=dirty_worktree,
    )


def write_manifest(
    *,
    context: RunContext,
    manifest_directory: Path,
    config_path: Path,
    taxonomy_path: Path,
    requirements_path: Path,
    protocol_id: str,
    protocol_version: str,
    status: Literal["SUCCESS", "FAILED"],
    artifacts: list[ManifestArtifact] | None = None,
    error: str | None = None,
) -> Path:
    finished_at_utc = datetime.now(UTC)

    if finished_at_utc < context.started_at_utc:
        raise ValueError("finished_at_utc não pode anteceder started_at_utc.")

    manifest = RunManifest(
        schema_version="1.1.0",
        run_id=context.run_id,
        protocol_id=protocol_id,
        protocol_version=protocol_version,
        stage=context.stage,
        status=status,
        started_at_utc=context.started_at_utc,
        finished_at_utc=finished_at_utc,
        code_commit_sha=context.code_commit_sha,
        dirty_worktree=context.dirty_worktree,
        config_sha256=sha256_file(config_path),
        taxonomy_sha256=sha256_file(taxonomy_path),
        requirements_sha256=sha256_file(requirements_path),
        python_version=sys.version,
        operating_system=platform.platform(),
        artifacts=[] if artifacts is None else artifacts,
        error=error,
    )

    manifest_directory.mkdir(parents=True, exist_ok=True)
    output = manifest_directory / f"{context.run_id}.json"
    with output.open("x", encoding="utf-8") as stream:
        json.dump(manifest.model_dump(mode="json"), stream, indent=2, ensure_ascii=False)
        stream.write("\n")

    return output
