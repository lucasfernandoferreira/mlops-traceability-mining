"""Draft provenance cannot silently become scientific human acceptance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mlops_traceability.manifest import sha256_file
from mlops_traceability.verification.provenance import assess_provenance


def test_draft_and_confirmation_bind_bytes(tmp_path: Path) -> None:
    review = tmp_path / "taxonomia_revisada.csv"
    review.write_text("unit_id,expected_category\nu,CODE\n")
    record = {
        "file": review.name,
        "record_id": "u",
        "drafted_by": "draft:synthetic",
        "review_mode": "draft_pending_confirmation",
        "confirmed_by": None,
        "confirmed_at_utc": None,
    }
    sidecar = tmp_path / "review_provenance.json"
    data = {"records": [record], "file_hashes": {review.name: sha256_file(review)}}
    sidecar.write_text(json.dumps(data))
    assert "review_requires_confirmation" in assess_provenance(tmp_path, review.name)["errors"]
    record.update(review_mode="human_confirmed", confirmed_by="Synthetic confirmer")
    sidecar.write_text(json.dumps(data))
    assert "human_confirmation_incomplete" in assess_provenance(tmp_path, review.name)["errors"]
    record["confirmed_at_utc"] = "2026-01-01T00:00:00Z"
    sidecar.write_text(json.dumps(data))
    assert not assess_provenance(tmp_path, review.name)["errors"]
    review.write_text("unit_id,expected_category\nu,DOC\n")
    assert "review_provenance_hash_mismatch" in assess_provenance(tmp_path, review.name)["errors"]


def test_invalid_missing_and_duplicate_provenance(tmp_path: Path) -> None:
    review = tmp_path / "r.csv"
    review.write_text("x")
    assert assess_provenance(tmp_path, review.name)["mode"] == "legacy_unspecified"
    sidecar = tmp_path / "review_provenance.json"
    sidecar.write_text("{")
    assert assess_provenance(tmp_path, review.name)["mode"] == "invalid"
    data: dict[str, Any] = {"records": [], "file_hashes": {review.name: sha256_file(review)}}
    sidecar.write_text(json.dumps(data))
    assert "review_provenance_records_missing" in assess_provenance(tmp_path, review.name)["errors"]
    record = {"file": review.name, "record_id": "u", "review_mode": "invalid"}
    data["records"] = [record, record]
    sidecar.write_text(json.dumps(data))
    errors = assess_provenance(tmp_path, review.name)["errors"]
    assert "review_provenance_duplicate_identity" in errors
    assert "review_provenance_author_missing" in errors
    assert "review_mode_invalid" in errors


def test_imported_human_source_is_preserved(tmp_path: Path) -> None:
    review = tmp_path / "r.csv"
    review.write_text("x")
    source = tmp_path / "original.csv"
    source.write_text("original")
    data = {
        "file_hashes": {review.name: sha256_file(review)},
        "records": [
            {
                "file": review.name,
                "record_id": "u",
                "drafted_by": "Synthetic human",
                "review_mode": "human_recorded",
                "source_record": source.name,
                "source_sha256": sha256_file(source),
            }
        ],
    }
    sidecar = tmp_path / "review_provenance.json"
    sidecar.write_text(json.dumps(data))
    assert not assess_provenance(tmp_path, review.name)["errors"]
    source.write_text("changed")
    assert "human_source_hash_mismatch" in assess_provenance(tmp_path, review.name)["errors"]
