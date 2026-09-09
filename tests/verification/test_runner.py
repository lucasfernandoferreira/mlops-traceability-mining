"""Synthetic end-to-end source verification; fixtures never authorize empirical acceptance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from test_reviews import imported_sources as imported_sources
from test_reviews import project as project
from test_study_pipeline import latest_study

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
    assert run_study("phase8_report", ["--study-index", str(index), "--allow-dirty"], root) == 0
    origins_path = reviews / "origens.json"
    origins = json.loads(origins_path.read_text())
    origins["report_run_id"] = latest_study(root, "phase8_report").name
    write_json(origins_path, origins)
    output = root / "verification"
    assert verify_study(root, index, reviews, output, scope="synthetic") == 1
    receipt = json.loads((output / "verification_receipt.json").read_text())
    assert receipt["scope"] == "synthetic" and not receipt["scientific_result_accepted"]
    assert receipt["processing_errors"] == []
    criteria = {r["criterion_id"]: r for r in receipt["criteria"]}
    for key in ("G01", "G03", "G05", "G07", "G08", "G09"):
        assert criteria[key]["status"] == "PASS", criteria[key]
    assert criteria["G06"]["status"] == "FAIL"  # Five synthetic commits do not meet 300.
    assert criteria["G04"]["status"] == "NOT_RUN"
    assert criteria["G13"]["status"] == "FAIL"
    assert len(receipt["criteria_scope"]) == 14
    assert "test__case/source_commits.json" in receipt["proof_hashes"]
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
