"""Distinguish Unconfirmed drafts from confirmed decisions without changing review identities."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from mlops_traceability.manifest import sha256_file
from mlops_traceability.validation.taxonomy_review import valid_utc


def copy_provenance(source: Path, destination: Path) -> None:
    """Carry authorship through input renaming, retaining the declared byte digest."""
    origin = source.parent / "review_provenance.json"
    if not origin.exists():
        return
    data = json.loads(origin.read_text())
    target = destination.parent / "review_provenance.json"
    merged = (
        json.loads(target.read_text()) if target.exists() else {"records": [], "file_hashes": {}}
    )
    if destination.name in merged["file_hashes"]:
        raise ValueError("Duplicate provenance destination")
    merged["file_hashes"][destination.name] = data["file_hashes"].get(source.name)
    for record in data["records"]:
        if record["file"] == source.name:
            copied = {**record, "file": destination.name}
            if record.get("review_mode") == "human_recorded":
                original = source.parent / record["source_record"]
                local = destination.parent / ("human_source_" + record["source_sha256"])
                shutil.copyfile(original, local)
                copied["source_record"] = local.name
            merged["records"].append(copied)
    target.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n")


def assess_provenance(directory: Path, filename: str) -> dict[str, Any]:
    path = directory / "review_provenance.json"
    if not path.exists():
        return {"mode": "legacy_unspecified", "errors": [], "records": 0}
    errors = []
    try:
        data = json.loads(path.read_text())
        records = [r for r in data["records"] if r["file"] == filename]
        if not records:
            errors.append("review_provenance_records_missing")
        if data["file_hashes"].get(filename) != sha256_file(directory / filename):
            errors.append("review_provenance_hash_mismatch")
        ids = [r["record_id"] for r in records]
        if len(ids) != len(set(ids)):
            errors.append("review_provenance_duplicate_identity")
        for record in records:
            mode = record.get("review_mode")
            if not record.get("drafted_by"):
                errors.append("review_provenance_author_missing")
            if mode == "draft_pending_confirmation":
                errors.append("review_requires_confirmation")
            elif mode == "human_recorded":
                source = directory / record["source_record"]
                if sha256_file(source) != record["source_sha256"]:
                    errors.append("human_source_hash_mismatch")
            elif mode == "human_confirmed":
                if not record.get("confirmed_by") or not valid_utc(record.get("confirmed_at_utc")):
                    errors.append("human_confirmation_incomplete")
            else:
                errors.append("review_mode_invalid")
        return {
            "mode": "explicit_provenance",
            "errors": sorted(set(errors)),
            "records": len(records),
        }
    except (OSError, KeyError, ValueError, TypeError) as error:
        return {"mode": "invalid", "errors": [f"review_provenance_invalid:{error}"], "records": 0}
