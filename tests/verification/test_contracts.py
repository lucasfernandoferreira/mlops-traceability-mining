from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from git import Repo
from pydantic import ValidationError
from test_pilot_pipeline import change

from mlops_traceability.verification.contracts import Claim, Criterion, aggregate_criteria
from mlops_traceability.verification.evidence import Evidence, resolve_evidence


def test_criteria_and_claims_fail_closed() -> None:
    passed = Criterion(
        criterion_id="G00",
        method="hash",
        expected=True,
        observed=True,
        proof=["preservation.json"],
        status="PASS",
    )
    assert aggregate_criteria([passed], ["G00"]) == ("PASS", [])
    skipped = passed.model_copy(update={"status": "NOT_APPLICABLE", "reason": "policy"})
    assert aggregate_criteria([skipped], ["G00"])[0] == "FAIL"
    assert (
        aggregate_criteria([skipped], ["G00"], allowed_not_applicable=frozenset({"G00"}))[0]
        == "PASS"
    )
    for criteria, required in (([passed, passed], ["G00"]), ([passed], ["G01"])):
        with pytest.raises(ValueError, match="Duplicate or unexpected"):
            aggregate_criteria(criteria, required)
    updates: list[dict[str, Any]] = [
        {"proof": []},
        {"status": "NOT_RUN"},
        {"status": "NOT_APPLICABLE"},
    ]
    for update in updates:
        with pytest.raises(ValidationError):
            Criterion.model_validate({**passed.model_dump(), **update})
    raw = dict(
        claim_id="CLM-X",
        statement="Within fixture",
        criterion_id="G08",
        source_run_ids=[],
        source_hashes={},
        evidence_ids=[],
        evidence_kind="structural",
        verification_method="arithmetic",
        expected_result=1,
        observed_result=None,
        assertion_status="not_assessed",
        allowed_conclusion="Pending verification",
        limitation="Synthetic",
    )
    assert Claim.model_validate(raw).assertion_status == "not_assessed"
    with pytest.raises(ValidationError, match="Supported claims require"):
        Claim.model_validate({**raw, "assertion_status": "supported_within_scope"})


@pytest.mark.counterexample
def test_force_partial_pass_does_not_cover_missing_criteria() -> None:
    passed = Criterion(
        criterion_id="G00",
        method="test",
        expected=1,
        observed=1,
        proof=["synthetic.json"],
        status="PASS",
    )
    status, reasons = aggregate_criteria([passed], [f"G{i:02}" for i in range(16)])
    assert status == "FAIL" and "G15:NOT_RUN" in reasons and "G01:NOT_RUN" in reasons


def file_evidence() -> Evidence:
    return Evidence(
        evidence_id="E-FILE",
        kind="file",
        path="proof.txt",
        sha256=hashlib.sha256(b"first\nsecond\n").hexdigest(),
        start_line=2,
        end_line=2,
        excerpt="second",
    )


def test_file_evidence_and_symlink_escape(tmp_path: Path) -> None:
    evidence = file_evidence()
    (tmp_path / "proof.txt").write_bytes(b"first\nsecond\n")
    assert resolve_evidence(evidence, tmp_path, {})["status"] == "PASS"
    for update, message in (
        ({"excerpt": "wrong"}, "excerpt"),
        ({"end_line": 3}, "excerpt"),
        ({"sha256": "f" * 64}, "content hash"),
    ):
        with pytest.raises(ValueError, match=message):
            resolve_evidence(evidence.model_copy(update=update), tmp_path, {})
    (tmp_path / "proof.txt").unlink()
    (tmp_path / "proof.txt").symlink_to(tmp_path.parent / "outside.txt")
    with pytest.raises(ValueError, match="escapes root"):
        resolve_evidence(evidence, tmp_path, {})


@pytest.mark.parametrize(
    "update",
    [
        {"path": "../outside"},
        {"path": "/tmp/outside"},
        {"path": "a//b"},
        {"path": ""},
        {"end_line": 1},
        {"start_line": None},
        {"kind": "git_blob"},
    ],
)
def test_evidence_contract_invalid(update: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Evidence.model_validate({**file_evidence().model_dump(), **update})


@pytest.mark.counterexample
def test_historical_deletion_and_swapped_blob(tmp_path: Path) -> None:
    with Repo.init(tmp_path) as repo:
        revision = change(repo, "deleted.py", "x = 1\n")
        blob = (repo.commit(revision).tree / "deleted.py").hexsha
        repo.index.remove(["deleted.py"], working_tree=True)
        head = repo.index.commit("remove").hexsha
        evidence = Evidence(
            evidence_id="E-HISTORY",
            kind="git_blob",
            path="deleted.py",
            sha256=hashlib.sha256(b"x = 1\n").hexdigest(),
            repository_id="a/b",
            head_commit_sha=head,
            blob_revision=revision,
            blob_sha=blob,
            start_line=1,
            end_line=1,
            excerpt="x = 1",
        )
        assert resolve_evidence(evidence, tmp_path, {"a/b": tmp_path})["status"] == "PASS"
        with pytest.raises(ValueError, match="blob SHA mismatch"):
            resolve_evidence(
                evidence.model_copy(update={"blob_sha": "f" * 40}), tmp_path, {"a/b": tmp_path}
            )


def test_initial_catalog_and_criterion_matrix_remain_pending() -> None:
    import json

    catalog = json.loads(Path("docs/evidencias/catalogo_afirmacoes_inicial.json").read_text())
    references = {Evidence.model_validate(r).evidence_id for r in catalog["evidence"]}
    for raw in catalog["claims"]:
        claim = Claim.model_validate(raw)
        assert claim.assertion_status == "not_assessed"
        assert claim.observed_result is None and set(claim.evidence_ids) <= references
    matrix = json.loads(Path("docs/evidencias/matriz_criterios_inicial.json").read_text())
    criteria = [Criterion.model_validate(r) for r in matrix["criteria"]]
    assert aggregate_criteria(criteria, [f"G{i:02}" for i in range(16)])[0] == "FAIL"
    assert matrix["scientific_result_accepted"] is False
