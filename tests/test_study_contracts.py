"""Synthetic contract checks only; these labels are not empirical validation."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from mlops_traceability.config import ResearchConfig, load_config
from mlops_traceability.descriptive_analysis import (
    configuration_sensitivity,
    distribution,
    monthly_series,
)
from mlops_traceability.pilot import write_csv, write_json
from mlops_traceability.qualitative_selection import select_events, systematic
from mlops_traceability.run_storage import portable_path, run_directory
from mlops_traceability.study import acceptance
from mlops_traceability.validation.taxonomy_review import evaluate_review, make_sample, valid_utc


def commit(number: int, **extra: Any) -> dict[str, Any]:
    return {
        "repository_id": "a/b",
        "commit_sha": f"{number:040x}",
        "committed_at_utc": "2026-01-01T00:00:00Z",
        "eligibility_status": "included",
        "C": True,
        "P": True,
        "config_semantic_status": "observed",
        "config_changed_keys": 1,
        **extra,
    }


def inventory_rows(size: int = 3) -> dict[str, Any]:
    return {
        "complete": True,
        "errors": [],
        "taxonomy_version": "1.1.0",
        "expected_unique_paths": size,
        "cases": [{"repository_id": "a/b", "head_commit_sha": "a" * 40}],
        "units": [
            {
                "unit_id": str(i),
                "repository_id": "a/b",
                "head_commit_sha": "a" * 40,
                "file_path": f"f{i}.py",
                "category": "CODE",
                "taxonomy_version": "1.1.0",
                "historical_observations": 1,
                "calibration_used": False,
            }
            for i in range(size)
        ],
    }


def review_fixture(tmp_path: Path, size: int = 3) -> tuple[Path, Path, Path, ResearchConfig]:
    config = load_config("config/config.yaml")
    inventory = inventory_rows(size)
    original, reviewed, inv = (
        tmp_path / name for name in ("original.csv", "reviewed.csv", "inventory.json")
    )
    rows = make_sample(inventory, config)
    write_csv(original, rows)
    for row in rows:
        row.update(
            expected_category="CODE",
            reviewer="synthetic evaluator",
            justification="Synthetic fixture: explicit known CODE role.",
            reviewed_at_utc="2026-09-07T22:00:00Z",
        )
    write_csv(reviewed, rows)
    write_json(inv, inventory)
    return original, reviewed, inv, config


def test_absent_and_rare_categories_and_review_integrity(tmp_path: Path) -> None:
    original, reviewed, inv, config = review_fixture(tmp_path)
    result = evaluate_review(reviewed, config, original=original, inventory_path=inv)
    assert result["accepted"] and result["agreement"] == 1
    coverage = {r["category"]: r for r in result["coverage"]}
    assert coverage["CODE"]["status"] == "exhaustive_small_category"
    assert coverage["DATA_META"]["status"] == "absent_in_validated_universe"
    assert coverage["DATA_META"]["agreement"] is None
    text = reviewed.read_text()
    for before, after in (
        ("synthetic evaluator", ""),
        ("2026-09-07T22:00:00Z", "yesterday"),
        ("2026-09-07T22:00:00Z", "2026-09-07T22:00:00"),
        ("f0.py", "tampered.py"),
        (",CODE,synthetic", ",INVALID,synthetic"),
    ):
        reviewed.write_text(text.replace(before, after))
        assert not evaluate_review(reviewed, config, original=original, inventory_path=inv)[
            "accepted"
        ]
    reviewed.write_text(text)
    inventory = json.loads(inv.read_text())
    inventory["complete"] = False
    write_json(inv, inventory)
    result = evaluate_review(reviewed, config, original=original, inventory_path=inv)
    assert not result["accepted"]
    assert all(r["status"] == "incomplete_inventory" for r in result["coverage"])


def test_inventory_duplicates_calibration_and_low_agreement(tmp_path: Path) -> None:
    original, reviewed, inv, config = review_fixture(tmp_path, 25)
    inventory = json.loads(inv.read_text())
    inventory["units"][0]["file_path"] = inventory["units"][1]["file_path"]
    write_json(inv, inventory)
    assert not evaluate_review(reviewed, config, original=original, inventory_path=inv)["accepted"]
    inventory = inventory_rows(25)
    for row in inventory["units"]:
        row["calibration_used"] = True
    write_json(inv, inventory)
    rows = make_sample(inventory, config)
    write_csv(original, rows)
    for row in rows:
        row.update(
            expected_category="CODE",
            reviewer="synthetic",
            reviewed_at_utc="2026-09-07T00:00:00Z",
            justification="Synthetic fixture: explicit known CODE role.",
        )
    write_csv(reviewed, rows)
    assert not evaluate_review(reviewed, config, original=original, inventory_path=inv)["accepted"]
    original, reviewed, inv, config = review_fixture(tmp_path, 25)
    text = reviewed.read_text().replace(",CODE,synthetic", ",DOC,synthetic", 2)
    reviewed.write_text(text)
    assert not evaluate_review(reviewed, config, original=original, inventory_path=inv)["accepted"]


def test_historical_role_review_and_source_labels_are_required(tmp_path: Path) -> None:
    original, reviewed, inv, config = review_fixture(tmp_path)
    inventory = inventory_rows()
    inventory["units"][0]["historical_observations"] = 2
    rows = make_sample(inventory, config)
    write_json(inv, inventory)
    write_csv(original, rows)
    for row in rows:
        row.update(
            expected_category="CODE",
            reviewer="synthetic",
            reviewed_at_utc="2026-09-07T00:00:00Z",
            justification="Synthetic fixture: explicit known CODE role.",
        )
    write_csv(reviewed, rows)
    assert not evaluate_review(reviewed, config, original=original, inventory_path=inv)["accepted"]
    rows[0]["role_change_review"] = "synthetic role checked"
    write_csv(reviewed, rows)
    assert evaluate_review(reviewed, config, original=original, inventory_path=inv)["accepted"]
    write_csv(original, rows)
    assert not evaluate_review(reviewed, config, original=original, inventory_path=inv)["accepted"]
    assert not valid_utc("2026-01-01T00:00:00-03:00")


def test_systematic_exact_counts_and_deterministic_qualitative_selection() -> None:
    for size in range(31):
        for quota in range(16):
            result = systematic([{"i": i} for i in range(size)], quota)
            assert len(result) == min(size, quota)
            assert len({r["i"] for r in result}) == len(result)
    plan = load_config("config/config.yaml").analysis
    commits = [commit(i, config_changed_keys=i % 4) for i in range(30)]
    changes = [{"commit_sha": r["commit_sha"], "file_path": "logger.py"} for r in commits[:10]]
    first = select_events(commits, changes, "a/b", ["logger.py"], plan)
    assert first == select_events(list(reversed(commits)), changes, "a/b", ["logger.py"], plan)
    assert len(first[1]) == 15 and len({r["event_id"] for r in first[1]}) == 15
    assert first[1][0]["tie_sha"] == commits[0]["commit_sha"]
    assert first[2]["groups"][1]["overlap_already_selected"] == 5
    _, selected, coverage = select_events([commit(1, C=False, P=False)], [], "a/b", [], plan)
    assert selected[0]["selection_group"] == "FILL" and coverage["total_deficit"] == 14
    assert select_events([], [], "a/b", [], plan)[1] == []


def test_pr_grouping_before_sampling_and_lookup_failures() -> None:
    plan = load_config("config/config.yaml").analysis
    commits = [commit(i) for i in range(3)]
    links = [
        {
            "commit_sha": r["commit_sha"],
            "status": "found",
            "pr_url": "https://github.com/a/b/pull/1",
            "source_url": "https://github.com/a/b/pull/1",
            "reviewer": "synthetic",
            "checked_at_utc": "2026-09-07T00:00:00Z",
        }
        for r in commits
    ]
    candidates, selected, coverage = select_events(commits, [], "a/b", [], plan, links)
    assert len(candidates) == 1 and len(selected[0]["commit_shas"].split(";")) == 3
    assert coverage["pr_map_complete"]
    with pytest.raises(ValueError, match="cover exactly"):
        select_events(commits, [], "a/b", [], plan, links[:1])
    for key, value in (
        ("status", "unknown"),
        ("reviewer", ""),
        ("pr_url", "https://github.com/wrong/case/pull/1"),
        ("pr_url", "1"),
    ):
        bad = deepcopy(links)
        bad[0][key] = value
        with pytest.raises(ValueError):
            select_events(commits, [], "a/b", [], plan, bad)
    links[0]["status"] = "error"
    assert select_events(commits, [], "a/b", [], plan, links)[2]["pr_errors"] == 1


def test_monthly_reconciliation_errors_and_configuration_sensitivity() -> None:
    plan = load_config("config/config.yaml").analysis
    rows = [
        commit(1, config_changed_keys=2),
        commit(2, committed_at_utc="2026-03-01T00:00:00Z", config_changed_keys=0),
        commit(3, eligibility_status="merge"),
    ]
    series = monthly_series(rows, "a/b")
    assert series[1]["status"] == "undefined"
    assert sum(r["numerator"] for r in series) == 2
    dist = distribution(rows, "a/b", plan)
    assert dist["mean"] == 1 and dist["median"] == 1 and dist["p95"] == 1.9
    assert dist["semantic_zero_fraction"] == 0.5 and dist["top_fraction_share"] == 1
    changes = [
        {
            "commit_sha": rows[0]["commit_sha"],
            "file_path": name,
            "change_type": action,
            "category": "CONFIG",
            "changed_key_count": 1,
            "changed_keys": ['["str:names", "int:0"]'],
            "before_blob_sha": "same" if action == "D" else None,
            "after_blob_sha": "same" if action == "A" else None,
        }
        for name, action in (("data/old.yaml", "D"), ("new.yaml", "A"))
    ]
    variants = {r["variant"]: r for r in configuration_sensitivity(rows, changes, "a/b", plan)}
    assert variants["principal"]["value"] == 1
    assert variants["identical_blob_moves"]["value"] == 0
    assert variants["class_map_keys"]["value"] == 0
    assert variants["dataset_paths"]["value"] == 0.5
    rows[0]["config_semantic_status"] = "error"
    assert distribution(rows, "a/b", plan)["mean"] is None
    assert all(
        r["status"] == "error" and r["value"] is None
        for r in configuration_sensitivity(rows, changes, "a/b", plan)
    )
    rows[0]["config_semantic_status"] = "not_applicable"
    assert distribution(rows, "a/b", plan)["status"] == "not_applicable"
    assert distribution([], "a/b", plan)["status"] == "undefined"
    assert monthly_series([], "a/b") == []


def test_portable_paths_and_configuration_contracts(tmp_path: Path) -> None:
    assert portable_path(tmp_path, "/old/place/data/interim/a") == tmp_path / "data/interim/a"
    for path in ("../escape", "/unmapped/file", "data/../../escape"):
        with pytest.raises(ValueError):
            portable_path(tmp_path, path)
    for run in ("../escape", "..", "bad/run"):
        with pytest.raises(ValueError):
            run_directory(tmp_path, run)
    config = load_config("config/config.yaml")
    raw = config.model_dump()
    for field, value in (
        ("group_order", ["Q2", "Q1", "Q3"]),
        ("planned_at_utc", "2026-01-01"),
        ("events_per_group", 0),
    ):
        bad = deepcopy(raw)
        bad["analysis"][field] = value
        with pytest.raises(ValidationError):
            ResearchConfig.model_validate(bad)


def test_final_status_never_overrides_scientific_gates() -> None:
    config = load_config("config/config.yaml")
    config = config.model_copy(
        update={
            "selection": config.selection.model_copy(
                update={"final_sample_min": 1, "final_sample_max": 1}
            )
        }
    )
    index = {
        "status": "final",
        "cases": [{"repository_id": "a/b", "head_commit_sha": "a" * 40}],
        "taxonomy_version": "1.1.0",
        "inventory_sha256": "inventory",
        "sample_sha256": "sample",
    }
    receipt: dict[str, Any] = {
        "accepted": True,
        "taxonomy_version": "1.1.0",
        "input_hashes": {"inventory": "inventory", "original": "sample"},
        "cases": index["cases"],
    }
    case = {
        "repository_id": "a/b",
        "head_commit_sha": "a" * 40,
        "decision": "accepted",
        "reviewer": "synthetic",
        "reviewed_at_utc": "2026-09-07T00:00:00Z",
        "integration_evidence_status": "functional_integration_observed",
        "integration_entrypoint": "train.py",
        "integration_component": "logger.py",
        "operation": "log_params",
        "evidence_url": "synthetic",
        "evidence_scope": "synthetic",
        "decision_reason": "synthetic",
        "evidence_sha": "a" * 40,
        "reachable_commit_count": 300,
        "active_identity_count": 5,
        "stars_at_collection": 100,
    }
    academic = {
        "status": "accepted",
        "reviewer": "synthetic",
        "evidence": "synthetic",
        "operational_objective": "synthetic",
        "unanswered_questions": ["runtime"],
        "reviewed_at_utc": "2026-09-07T00:00:00Z",
        "mlflow_scope_resolved": True,
        "metric_mapping_resolved": True,
    }
    row = dict.fromkeys(
        (
            "themes",
            "evidence",
            "interpretation",
            "justification",
            "ambiguity",
            "metric_id",
            "quantitative_pattern",
            "contrary_evidence",
            "conclusion_limit",
            "reviewer",
        ),
        "synthetic",
    )
    row.update(
        repository_id="a/b",
        event_id="event",
        commit_shas="sha",
        reviewed_at_utc="2026-09-07T00:00:00Z",
    )

    def check(**overrides: Any) -> dict[str, Any]:
        flags = {
            "chain_eligible": True,
            "metrics_valid": True,
            "qualitative_valid": True,
            "case_measurements_valid": True,
            "verification_valid": True,
            **overrides,
        }
        return acceptance(index, receipt, [case], academic, [row], [row], config, **flags)

    assert check()["candidate_eligible"]
    assert not check()["scientific_result_accepted"]
    assert check()["blocking_reasons"] == ["G14:NOT_RUN", "G15:NOT_RUN"]
    for flag in (
        "chain_eligible",
        "metrics_valid",
        "qualitative_valid",
        "case_measurements_valid",
        "verification_valid",
    ):
        assert not check(**{flag: False})["candidate_eligible"]
    case["integration_evidence_status"] = "dependency_only"
    assert not check()["candidate_eligible"]
    case["integration_evidence_status"] = "functional_integration_observed"
    receipt["taxonomy_version"] = "other"
    assert not check()["candidate_eligible"]
    receipt["taxonomy_version"] = "1.1.0"
    receipt["input_hashes"]["inventory"] = "other"
    assert not check()["candidate_eligible"]
    receipt["input_hashes"]["inventory"] = "inventory"
    assert not check(unanswered_metric_ids={"provenance_coverage"})["candidate_eligible"]
    academic["status"] = "pending"
    assert not check()["candidate_eligible"]


def test_first_component_introduction_is_mandatory_even_after_caller_history() -> None:
    plan = load_config("config/config.yaml").analysis
    commits = [commit(i) for i in range(20)]
    changes = [
        {"commit_sha": r["commit_sha"], "file_path": "trainer.py", "change_type": "M"}
        for r in commits
    ]
    changes.append(
        {"commit_sha": commits[11]["commit_sha"], "file_path": "mlflow.py", "change_type": "A"}
    )
    _, selected, coverage = select_events(
        commits,
        changes,
        "a/b",
        ["trainer.py", "mlflow.py"],
        plan,
        integration_component="mlflow.py",
    )
    assert selected[0]["commit_shas"] == commits[11]["commit_sha"]
    assert selected[0]["selection_reason"] == "first_component_introduction"
    assert coverage["first_integration_event_id"] == commits[11]["commit_sha"]
    assert len({r["event_id"] for r in selected}) == 15
