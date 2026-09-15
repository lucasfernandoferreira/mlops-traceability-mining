"""Closure gates reject changed evidence and keep identity separate from judgment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from mlops_traceability.manifest import sha256_file
from mlops_traceability.verification import closure


def dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def claim_for(path: Path, root: Path) -> dict[str, Any]:
    return dict(
        claim_id="one",
        statement="Observed text",
        method="Read preserved text",
        result={"text": "evidence"},
        limitation="Only text",
        allowed_conclusion="Only text",
        relevance="Text documents a contract, not runtime usage",
        status="sustentada_no_escopo",
        sources=[
            dict(
                evidence_id="one",
                kind="file",
                path=path.relative_to(root).as_posix(),
                sha256=sha256_file(path),
                excerpt="evidence",
                start_line=1,
                end_line=1,
            )
        ],
    )


def test_catalog_identity_does_not_establish_relevance(tmp_path: Path) -> None:
    path = tmp_path / "source.txt"
    path.write_text("evidence\n")
    claim = claim_for(path, tmp_path)
    bound: list[Path] = []
    checked = closure.catalog_check({"claims": [claim]}, tmp_path, bound.append)
    assert not checked["identity_errors"] and bound == [path]
    claim["relevance"] = ""
    checked = closure.catalog_check({"claims": [claim]}, tmp_path, bound.append)
    assert len(checked["identity_results"]) == 1
    assert "one:missing:relevance" in checked["identity_errors"]
    claim["status"] = "accepted"
    path.write_text("changed")
    checked = closure.catalog_check({"claims": [claim]}, tmp_path, bound.append)
    assert "one:invalid_status" in checked["identity_errors"]
    assert any(":source:" in e for e in checked["identity_errors"])
    with pytest.raises(ValueError, match="Empty or duplicate"):
        closure.catalog_check({"claims": [claim, claim]}, tmp_path, bound.append)


def test_catalog_rejects_numeric_forgery(tmp_path: Path) -> None:
    path = tmp_path / "metrics.csv"
    path.write_text(
        "repository_id,metric_id,value,numerator,denominator,status\norg/repo,m,0.5,1,2,observed\n"
    )
    claim = claim_for(path, tmp_path)
    claim.update(
        claim_id="repo:m",
        result=dict(value="0.5", numerator="1", denominator="2", status="observed"),
    )
    claim["sources"][0] = dict(
        evidence_id="metric", kind="file", path="metrics.csv", sha256=sha256_file(path)
    )
    assert not closure.catalog_check({"claims": [claim]}, tmp_path, lambda _: None)[
        "identity_errors"
    ]
    claim["result"]["denominator"] = "3"
    assert closure.catalog_check({"claims": [claim]}, tmp_path, lambda _: None)[
        "identity_errors"
    ] == ["repo:m:numeric_result_mismatch"]


def test_gates_emit_each_proof_and_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index = tmp_path / "index.json"
    index.write_text("{}")
    source = tmp_path / "source.txt"
    source.write_text("evidence\n")
    inventory = tmp_path / "inventory.json"
    dump(
        inventory,
        {
            "files": [
                dict(path="source.txt", size=source.stat().st_size, sha256=sha256_file(source))
            ]
        },
    )
    reviews = tmp_path / "reviews"
    dump(reviews / "claims_catalog.json", {"claims": [claim_for(source, tmp_path)]})
    inputs = dict(
        study_index_sha256=sha256_file(index),
        inventory_path="inventory.json",
        inventory_sha256=sha256_file(inventory),
        alignment_evidence=dict(
            evidence_id="scope", kind="file", path="source.txt", sha256=sha256_file(source)
        ),
    )
    dump(reviews / "closure_inputs.json", inputs)
    academic = dict(
        operational_objective="Read contracts",
        status="accepted",
        mlflow_scope_resolved=True,
        metric_mapping_resolved=True,
        unanswered_questions=[
            "provenance_coverage",
            "data_code_ratio_original",
            "data_code_cochange",
            "cace_index",
            "env_versioning_rate",
            "experiment_redundancy",
        ],
    )
    dump(reviews / "alinhamento_academico.json", academic)
    monkeypatch.setattr(closure, "fixtures", lambda *a: {"differences": []})

    def execute(name: str) -> dict[str, tuple[str, list[Any], list[str]]]:
        output = tmp_path / name
        output.mkdir()
        return closure.run_closure_checks(
            tmp_path, index, reviews, output, {}, "revision", lambda _: None
        )

    result = execute("valid_bytes")
    assert set(result) == {"G00", "G02", "G04", "G11", "G12"}
    assert not result["G00"][1] and not result["G02"][1]
    assert "claims_provenance_missing" in result["G11"][1]
    assert "academic_provenance_missing" in result["G12"][1]
    # A technical alignment status alone never substitutes for attributed review.
    academic.update(unanswered_questions=[], metric_mapping_resolved=1)
    dump(reviews / "alinhamento_academico.json", academic)
    source.write_text("modified\n")
    result = execute("modified")
    assert result["G00"][1] and result["G02"][1] and result["G12"][1]
    dump(reviews / "claims_catalog.json", {"claims": []})
    inputs["study_index_sha256"] = "wrong"
    dump(reviews / "closure_inputs.json", inputs)
    result = execute("invalid")
    assert "Closure index mismatch" in result["G00"][1]
    assert "Empty or duplicate claims" in result["G02"][1]
    assert "Empty or duplicate claims" in result["G11"][1]


def test_required_fixture_executes_and_unknown_scenario_refuses(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    policy = dict(
        required_scenarios=["four_commit_arithmetic"],
        initial_counterexamples=[],
        additional_counterexamples=[],
    )
    result = closure.fixtures(root, tmp_path, policy, "test-revision")
    assert not result["differences"] and result["mapping"][0]["passed"]
    assert result["code_sha"] == "test-revision"
    policy["required_scenarios"] = ["unimplemented"]
    with pytest.raises(ValueError, match="Unmapped"):
        closure.fixtures(root, tmp_path, policy, "test-revision")
