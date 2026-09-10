"""Synthetic end-to-end source verification; fixtures never authorize empirical acceptance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from test_reviews import imported_sources as imported_sources
from test_reviews import project as project
from test_selection_oracle import preserve_collection
from test_study_pipeline import latest_study

from mlops_traceability.manifest import sha256_file
from mlops_traceability.pilot import write_csv, write_json
from mlops_traceability.study import run_study
from mlops_traceability.verification.runner import main, verify_study


def test_runner_compares_sources_and_keeps_unexecuted_gates_blocked(
    imported_sources: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, index, reviews = imported_sources
    config = yaml.safe_load((root / "config/amostra_final.yaml").read_text())
    shortlist = (
        root / "data/interim/runs" / config["source_runs"]["phase2_screen_sample"] / "shortlist.csv"
    )
    shortlist.parent.mkdir(parents=True, exist_ok=True)
    write_csv(shortlist, [{"repository_id": "test/case", "stars_count": "100"}])
    monkeypatch.setattr(
        "mlops_traceability.verification.runner.audit_collection", lambda *_: {"verified": True}
    )
    template = json.loads((index.parent / "pr_map_template.json").read_text())
    collection = preserve_collection(
        root / "pr_collection", index, [r["commit_sha"] for r in template["test/case"]]
    )
    assert (
        run_study(
            "phase7_select_qualitative",
            [
                "--study-index",
                str(index),
                "--pr-map",
                str(collection.parent / "mapa_prs.json"),
                "--allow-dirty",
            ],
            root,
        )
        == 0
    )
    qualitative = latest_study(root, "phase7_select_qualitative")
    assert run_study("phase8_report", ["--study-index", str(index), "--allow-dirty"], root) == 0
    origins_path = reviews / "origens.json"
    origins = json.loads(origins_path.read_text())
    origins["qualitative_run_id"] = qualitative.name
    origins["pr_collection"] = str(collection.relative_to(root))
    coding = qualitative / "codificacao_qualitativa.csv"
    origins["originals"]["codificacao_revisada.csv"] = {
        "path": str(coding.relative_to(root)),
        "sha256": sha256_file(coding),
    }
    origins["report_run_id"] = latest_study(root, "phase8_report").name
    write_json(origins_path, origins)
    output = root / "verification"
    assert verify_study(root, index, reviews, output, scope="synthetic") == 1
    receipt = json.loads((output / "verification_receipt.json").read_text())
    assert receipt["scope"] == "synthetic" and not receipt["scientific_result_accepted"]
    assert receipt["processing_errors"] == []
    criteria = {r["criterion_id"]: r for r in receipt["criteria"]}
    for key in ("G01", "G03", "G05", "G07", "G08", "G09", "G10"):
        assert criteria[key]["status"] == "PASS", criteria[key]
    assert criteria["G06"]["status"] == "FAIL"  # Five synthetic commits do not meet 300.
    assert criteria["G04"]["status"] == "NOT_RUN"
    assert criteria["G13"]["status"] == "FAIL"
    assert len(receipt["criteria_scope"]) == 14
    assert "test__case/source_commits.json" in receipt["proof_hashes"]
    assert "qualitative/selected.json" in receipt["proof_hashes"]
    assert "pr_collection/batch_0000.json" in receipt["bound_file_hashes"]
    raw_path = collection.parent / "batch_0000.json"
    original_response = raw_path.read_bytes()
    raw_path.write_text("{}")
    assert verify_study(root, index, reviews, root / "bad-pr", scope="synthetic") == 2
    bad_pr = json.loads((root / "bad-pr/verification_receipt.json").read_text())
    assert any("PR evidence hash mismatch" in error for error in bad_pr["processing_errors"])
    assert next(c for c in bad_pr["criteria"] if c["criterion_id"] == "G10")["status"] == "FAIL"
    assert not bad_pr["scientific_result_accepted"]
    raw_path.write_bytes(original_response)
    with pytest.raises(FileExistsError):
        verify_study(root, index, reviews, output, scope="synthetic")
    assert (
        verify_study(root, index, root / "missing-reviews", root / "missing", scope="synthetic")
        == 2
    )
    failed = json.loads((root / "missing/verification_receipt.json").read_text())
    assert failed["processing_errors"] and failed["verification_status"] == "FAIL"
    assert verify_study(root, index, reviews, root / "reject-empirical") == 2
    with pytest.raises(ValueError, match="Invalid scope"):
        verify_study(root, index, reviews, root / "invalid", scope="invalid")
    assert (
        main(
            ["--study-index", str(index), "--review-dir", str(reviews), "--output-dir", str(output)]
        )
        == 2
    )
