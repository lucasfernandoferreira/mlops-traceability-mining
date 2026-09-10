"""Synthetic receipts and deliberate forgeries; never empirical acceptance evidence."""

from __future__ import annotations

import json
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from test_runner import imported_sources as imported_sources
from test_runner import project as project
from test_runner import verification_inputs as verification_inputs

from mlops_traceability.manifest import sha256_file
from mlops_traceability.verification.finalization import (
    CRITERIA,
    REVIEW_NAMES,
    assess_verification,
    check_receipt_bindings,
    checked_path,
    validate_claim,
)
from mlops_traceability.verification.runner import verify_study


def forged_pass(receipt: dict[str, Any]) -> dict[str, Any]:
    data = deepcopy(receipt)
    data.update(
        scope="empirical",
        dirty_worktree=False,
        verification_status="PASS",
        exit_code=0,
        processing_errors=[],
        blocking_reasons=[],
    )
    data["criteria"] = [
        {
            "criterion_id": key,
            "method": "Deliberate synthetic forgery",
            "expected": [],
            "observed": [],
            "status": "PASS",
            "reason": "",
            "proof": ["finalization_contract.json"],
        }
        for key in CRITERIA
    ]
    return data


@pytest.mark.counterexample
@pytest.mark.parametrize(
    "mutation",
    [
        "synthetic",
        "dirty",
        "accepted",
        "scope",
        "missing",
        "duplicate",
        "not_run",
        "fail",
        "error",
        "exit",
        "proof",
    ],
)
def test_incomplete_claim_cannot_authorize_candidate(mutation: str) -> None:
    data = forged_pass(
        {
            "scientific_result_accepted": False,
            "criteria_scope": CRITERIA,
            "proof_hashes": {"finalization_contract.json": "a" * 64},
        }
    )
    validate_claim(data)  # Structural validation alone is deliberately insufficient.
    if mutation == "synthetic":
        data["scope"] = "synthetic"
    elif mutation == "dirty":
        data["dirty_worktree"] = True
    elif mutation == "accepted":
        data["scientific_result_accepted"] = True
    elif mutation == "scope":
        data["criteria_scope"] = ["G13"]
    elif mutation == "missing":
        data["criteria"].pop()
    elif mutation == "duplicate":
        data["criteria"].append(data["criteria"][0])
    elif mutation == "not_run":
        data["criteria"][0].update(status="NOT_RUN", reason="Not executed")
    elif mutation == "fail":
        data["verification_status"] = "FAIL"
    elif mutation == "error":
        data["processing_errors"] = ["failure"]
    elif mutation == "exit":
        data["exit_code"] = 2
    else:
        data["criteria"][0]["proof"] = ["missing.json"]
    with pytest.raises(ValueError):
        validate_claim(data)


@pytest.mark.counterexample
def test_binding_mutations_fail_even_after_declaring_pass(
    verification_inputs: tuple[Path, Path, Path],
) -> None:
    root, index, reviews = verification_inputs
    output = root / "bindings"
    assert verify_study(root, index, reviews, output, scope="synthetic") == 1
    receipt = json.loads((output / "verification_receipt.json").read_text())
    assert check_receipt_bindings(root, index, output, receipt)["reviews"] == 5
    for path in (
        index,
        root / "config/file_taxonomy.yaml",
        root / "config/verification.yaml",
        output / "qualitative/selected.json",
        output / "reviews/original_reviews/casos_revisados.json",
    ):
        original = path.read_bytes()
        path.write_bytes(original + b"\n")
        with pytest.raises(ValueError, match="mismatch"):
            check_receipt_bindings(root, index, output, forged_pass(receipt))
        path.write_bytes(original)
    for key in ("bound_file_hashes", "proof_hashes", "input_manifest_hashes", "review_file_hashes"):
        changed = forged_pass(receipt)
        changed[key] = {}
        with pytest.raises(ValueError):
            check_receipt_bindings(root, index, output, changed)
    for name in ("../outside", str(index), "./config/config.yaml"):
        with pytest.raises(ValueError, match="Unsafe"):
            checked_path(root, name)
    (root / "escape").symlink_to(root.parent)
    with pytest.raises(ValueError, match="escaping"):
        checked_path(root, "escape/missing")


@pytest.mark.counterexample
def test_finalizer_replays_claimed_pass_and_preserves_refusal(
    verification_inputs: tuple[Path, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, index, reviews = verification_inputs
    output = root / "supplied"
    assert verify_study(root, index, reviews, output, scope="synthetic") == 1
    path = output / "verification_receipt.json"
    original = json.loads(path.read_text())
    origins = json.loads((reviews / "origens.json").read_text())
    inputs: dict[str, Path | None] = {k: reviews / k for k in REVIEW_NAMES if k != "origens.json"}
    attempt = 0

    def assess(receipt_path: Path | None = path, **overrides: Any) -> tuple[dict[str, Any], Path]:
        nonlocal attempt
        attempt += 1
        directory = root / f"finalize_{attempt}"
        directory.mkdir()
        result = assess_verification(
            root,
            index,
            receipt_path,
            directory,
            overrides.get("inputs", inputs),
            overrides.get("qualitative", origins["qualitative_run_id"]),
            origins["report_run_id"],
        )
        return result, directory

    result, _ = assess(None)
    assert not result["candidate_eligible"] and "Explicit" in result["blocking_reasons"][0]
    result, _ = assess()
    assert not result["candidate_eligible"] and not result["replay_executed"]
    result, _ = assess(qualitative="swapped-run")
    assert "input differs" in result["blocking_reasons"][0]
    result, _ = assess(inputs={})
    assert "all four" in result["blocking_reasons"][0]
    changed_inputs = dict(inputs, **{"casos_revisados.json": index})
    result, _ = assess(inputs=changed_inputs)
    assert "review differs" in result["blocking_reasons"][0]
    data = forged_pass(original)
    path.write_text(json.dumps(dict(data, verification_code_sha="a" * 40)))
    result, _ = assess()
    assert "code revision" in result["blocking_reasons"][0]
    path.write_text(json.dumps(data))
    result, directory = assess()
    # Real verifier rejects the forged empirical claim on the synthetic source chain.
    assert not result["candidate_eligible"] and result["replay_executed"]
    assert "Fresh empirical verification did not pass" in result["blocking_reasons"][0]
    with zipfile.ZipFile(directory / "verification_replay.zip") as archive:
        replay = json.loads(archive.read("verification_receipt.json"))
        assert replay["processing_errors"] and replay["verification_status"] == "FAIL"
    assert not (directory / "verification_evidence.zip").exists()

    # Isolated packaging contract with a simulated future complete verifier.
    def simulated_replay(_root: Path, _index: Path, _reviews: Path, destination: Path) -> int:
        shutil.copytree(output, destination)
        return 0

    monkeypatch.setattr("mlops_traceability.verification.runner.verify_study", simulated_replay)
    result, directory = assess()
    assert result["candidate_eligible"] and result["scientific_result_accepted"] is False
    with zipfile.ZipFile(directory / "verification_evidence.zip") as archive:
        assert "supplied/verification_receipt.json" in archive.namelist()
        assert "recomputed/qualitative/selected.json" in archive.namelist()
        for name, digest in data["bound_file_hashes"].items():
            assert archive.read(f"inputs/{name}") == (root / name).read_bytes()
            assert sha256_file(root / name) == digest

    def discrepant_replay(_root: Path, _index: Path, _reviews: Path, destination: Path) -> int:
        simulated_replay(_root, _index, _reviews, destination)
        changed = deepcopy(data)
        changed["criteria"][0]["observed"] = ["different"]
        (destination / "verification_receipt.json").write_text(json.dumps(changed))
        return 0

    monkeypatch.setattr("mlops_traceability.verification.runner.verify_study", discrepant_replay)
    result, _ = assess()
    assert not result["candidate_eligible"]
    assert "differ from recomputed" in result["blocking_reasons"][0]
