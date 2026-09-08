"""Offline resolution of preserved files and historical Git blobs, never execution."""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str = Field(min_length=1)
    kind: Literal["file", "git_blob"]
    path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    repository_id: str | None = None
    head_commit_sha: str | None = Field(default=None, pattern=r"^[a-f0-9]{40}$")
    blob_revision: str | None = Field(default=None, pattern=r"^[a-f0-9]{40}$")
    blob_sha: str | None = Field(default=None, pattern=r"^[a-f0-9]{40}$")
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    excerpt: str | None = None

    @model_validator(mode="after")
    def coherent(self) -> Evidence:
        path = PurePosixPath(self.path)
        if (
            not self.path
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != self.path
        ):
            raise ValueError("Evidence path must be canonical and relative")
        if self.kind == "git_blob" and not all(
            (
                self.repository_id,
                self.head_commit_sha,
                self.blob_revision,
                self.blob_sha,
                self.excerpt,
            )
        ):
            raise ValueError("Git evidence requires case, frozen SHA, blob identity and excerpt")
        if any(v is not None for v in (self.start_line, self.end_line, self.excerpt)) and (
            self.start_line is None
            or self.end_line is None
            or self.excerpt is None
            or self.end_line < self.start_line
        ):
            raise ValueError("Excerpt requires a valid line range")
        return self


def resolve_evidence(
    evidence: Evidence, root: Path, repositories: dict[str, Path]
) -> dict[str, str]:
    if evidence.kind == "file":
        target = (root / evidence.path).resolve()
        if not target.is_relative_to(root.resolve()):
            raise ValueError("Evidence escapes root")
        content = target.read_bytes()
    else:
        assert evidence.repository_id is not None
        clone = repositories[evidence.repository_id]
        subprocess.run(
            [
                "git",
                "-C",
                str(clone),
                "merge-base",
                "--is-ancestor",
                str(evidence.blob_revision),
                str(evidence.head_commit_sha),
            ],
            check=True,
            capture_output=True,
        )
        oid = subprocess.check_output(
            ["git", "-C", str(clone), "rev-parse", f"{evidence.blob_revision}:{evidence.path}"],
            text=True,
        ).strip()
        if not re.fullmatch(r"[a-f0-9]{40}", oid) or oid != evidence.blob_sha:
            raise ValueError("Evidence blob SHA mismatch")
        content = subprocess.check_output(["git", "-C", str(clone), "cat-file", "blob", oid])
    if hashlib.sha256(content).hexdigest() != evidence.sha256:
        raise ValueError("Evidence content hash mismatch")
    if evidence.excerpt is not None:
        assert evidence.start_line is not None and evidence.end_line is not None
        lines = content.decode("utf-8").splitlines()
        if evidence.end_line > len(lines) or (
            "\n".join(lines[evidence.start_line - 1 : evidence.end_line]) != evidence.excerpt
        ):
            raise ValueError("Evidence excerpt mismatch")
    return {"evidence_id": evidence.evidence_id, "status": "PASS", "sha256": evidence.sha256}
