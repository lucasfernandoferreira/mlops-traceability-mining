"""Bind finalization to preserved evidence and recompute any claimed G00–G13 PASS."""

from __future__ import annotations

import json
import re
import subprocess
import zipfile
from pathlib import Path
from typing import Any

import yaml

from mlops_traceability.manifest import sha256_file
from mlops_traceability.run_storage import verified_run
from mlops_traceability.verification.contracts import Criterion, aggregate_criteria

CRITERIA = [f"G{i:02}" for i in range(14)]
REVIEW_NAMES = (
    "taxonomia_revisada.csv",
    "casos_revisados.json",
    "alinhamento_academico.json",
    "codificacao_revisada.csv",
    "origens.json",
)


def checked_path(base: Path, name: str) -> Path:
    """Only canonical relative files inside their declared evidence root are allowed."""
    path = Path(name)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != name:
        raise ValueError(f"Unsafe evidence path: {name}")
    target = (base / path).resolve()
    if not target.is_relative_to(base.resolve()) or not target.is_file():
        raise ValueError(f"Missing or escaping evidence file: {name}")
    return target


def check_hashes(base: Path, hashes: dict[str, str]) -> None:
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("Missing evidence hash inventory")
    for name, digest in hashes.items():
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"Invalid evidence hash: {name}")
        if sha256_file(checked_path(base, name)) != digest:
            raise ValueError(f"Evidence hash mismatch: {name}")


def check_receipt_bindings(
    root: Path, index_path: Path, evidence: Path, receipt: dict[str, Any]
) -> dict[str, int]:
    """Audit bindings even for a refusal; this function alone never grants acceptance."""
    policy = yaml.safe_load((root / "config/verification.yaml").read_text())
    if receipt["verification_schema_version"] != "1.0.0" or (
        receipt["verification_policy_version"] != policy["verification_policy_version"]
    ):
        raise ValueError("Verification schema or policy mismatch")
    if receipt["study_index_sha256"] != sha256_file(index_path):
        raise ValueError("Study index hash mismatch")
    bound, proofs = receipt["bound_file_hashes"], receipt["proof_hashes"]
    required = {
        "config/config.yaml",
        "config/file_taxonomy.yaml",
        "config/verification.yaml",
        "config/amostra_final.yaml",
        "requirements.txt",
        "requirements-dev.txt",
        index_path.resolve().relative_to(root.resolve()).as_posix(),
    }
    if not required <= bound.keys():
        raise ValueError("Incomplete bound input inventory")
    if (
        not {
            "verification_source.tar.gz",
            "instrument.bundle",
            "reviews/review_import.json",
            "reviews/verification_source.tar.gz",
        }
        <= proofs.keys()
    ):
        raise ValueError("Incomplete proof inventory")
    check_hashes(root, bound)
    check_hashes(evidence, proofs)
    imported = json.loads((evidence / "reviews/review_import.json").read_text())
    reviews = receipt["review_file_hashes"]
    if not set(REVIEW_NAMES) <= reviews.keys() or reviews != imported["review_file_hashes"]:
        raise ValueError("Incomplete or incompatible review inventory")
    check_hashes(evidence / "reviews/original_reviews", reviews)
    for name, digest in reviews.items():
        if proofs.get(f"reviews/original_reviews/{name}") != digest:
            raise ValueError("Review missing from proof inventory")
    # Local import avoids the study -> finalization -> reviews -> study cycle.
    from mlops_traceability.verification.reviews import check_import_bindings

    check_import_bindings(
        evidence / "reviews/review_import.json",
        root,
        index_path,
        evidence / "reviews/original_reviews",
    )
    index = json.loads(index_path.read_text())
    origins = json.loads((evidence / "reviews/original_reviews/origens.json").read_text())
    config = yaml.safe_load((root / "config/config.yaml").read_text())
    runs = {index_path.parent.name, *[r["run_id"] for r in index["sources"]]}
    runs.update(origins[k] for k in ("qualitative_run_id", "report_run_id"))
    for run_id in runs:
        _, artifacts, _ = verified_run(root, run_id)
        manifest = root / config["paths"]["manifests"] / f"{run_id}.json"
        digest = sha256_file(manifest)
        if receipt["input_manifest_hashes"].get(run_id) != digest:
            raise ValueError(f"Missing or changed input manifest: {run_id}")
        for path in [manifest, *artifacts.values()]:
            if bound.get(path.relative_to(root).as_posix()) != sha256_file(path):
                raise ValueError(f"Input artifact not bound: {path.name}")
    return {"bound_inputs": len(bound), "proofs": len(proofs), "reviews": len(reviews)}


def validate_claim(receipt: dict[str, Any]) -> None:
    if receipt["scope"] != "empirical" or receipt["dirty_worktree"] is not False:
        raise ValueError("Receipt must be empirical and produced with a clean worktree")
    if receipt["scientific_result_accepted"] is not False:
        raise ValueError("Pre-restoration receipt cannot declare final acceptance")
    if receipt["criteria_scope"] != CRITERIA:
        raise ValueError("Receipt scope must be exactly G00-G13")
    criteria = [Criterion.model_validate(c) for c in receipt["criteria"]]
    if [c.criterion_id for c in criteria] != CRITERIA:
        raise ValueError("Incomplete or duplicate criteria")
    status, _ = aggregate_criteria(criteria, CRITERIA)
    if (
        status != "PASS"
        or receipt["verification_status"] != status
        or (receipt["processing_errors"] or receipt["exit_code"] != 0)
    ):
        raise ValueError("G00-G13 verification is incomplete or failed")
    for criterion in criteria:
        if any(p not in receipt["proof_hashes"] for p in criterion.proof):
            raise ValueError(f"Unbound criterion proof: {criterion.criterion_id}")


def assess_verification(
    root: Path,
    index_path: Path,
    receipt_path: Path | None,
    directory: Path,
    review_inputs: dict[str, Path | None],
    qualitative_run_id: str | None,
    report_run_id: str | None,
) -> dict[str, Any]:
    """Fail closed; a declared complete PASS must survive a fresh empirical execution."""
    result: dict[str, Any] = {
        "candidate_eligible": False,
        "scientific_result_accepted": False,
        "blocking_reasons": [],
        "replay_executed": False,
    }
    try:
        if receipt_path is None:
            raise ValueError("Explicit --verification-receipt is required")
        receipt_path = receipt_path.resolve()
        result["receipt_sha256"] = sha256_file(receipt_path)
        receipt = json.loads(receipt_path.read_text())
        result["bindings"] = check_receipt_bindings(root, index_path, receipt_path.parent, receipt)
        origins = json.loads(
            (receipt_path.parent / "reviews/original_reviews/origens.json").read_text()
        )
        for key, actual in (
            ("qualitative_run_id", qualitative_run_id),
            ("report_run_id", report_run_id),
        ):
            if not actual or origins[key] != actual:
                raise ValueError(f"Finalization input differs from verification: {key}")
        if set(review_inputs) != set(REVIEW_NAMES) - {"origens.json"}:
            raise ValueError("Finalization requires all four reviewed inputs")
        for name, path in review_inputs.items():
            if path is None or sha256_file(path) != receipt["review_file_hashes"][name]:
                raise ValueError(f"Finalization review differs from verification: {name}")
        validate_claim(receipt)
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip()
        if receipt["verification_code_sha"] != head or receipt["test_suite_code_sha"] != head:
            raise ValueError("Verification code revision differs from current HEAD")
        from mlops_traceability.verification.runner import verify_study

        replay = directory / "verification_replay"
        result["replay_executed"] = True
        code = verify_study(
            root, index_path, receipt_path.parent / "reviews/original_reviews", replay
        )
        replay_path = replay / "verification_receipt.json"
        result["replay_receipt_sha256"] = sha256_file(replay_path)
        repeated = json.loads(replay_path.read_text())
        if code != 0:
            raise ValueError("Fresh empirical verification did not pass G00-G13")
        validate_claim(repeated)
        check_receipt_bindings(root, index_path, replay, repeated)
        check_receipt_bindings(root, index_path, receipt_path.parent, receipt)
        if repeated["criteria"] != receipt["criteria"]:
            raise ValueError("Claimed criteria differ from recomputed evidence")
        for key in ("bound_file_hashes", "review_file_hashes", "input_manifest_hashes"):
            if repeated[key] != receipt[key]:
                raise ValueError(f"Recomputed input inventory differs: {key}")
        if sha256_file(receipt_path) != result["receipt_sha256"]:
            raise ValueError("Supplied receipt changed during finalization")
        # A single direct artifact binds nested evidence without basename collisions
        # in the existing run manifest contract. Never extract an untrusted archive.
        with zipfile.ZipFile(
            directory / "verification_evidence.zip", "x", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for prefix, base, data in (
                ("supplied", receipt_path.parent, receipt),
                ("recomputed", replay, repeated),
            ):
                for name in data["proof_hashes"]:
                    archive.write(checked_path(base, name), f"{prefix}/{name}")
                archive.write(
                    receipt_path if prefix == "supplied" else replay_path,
                    f"{prefix}/verification_receipt.json",
                )
            for name in receipt["bound_file_hashes"]:
                archive.write(checked_path(root, name), f"inputs/{name}")
        result["candidate_eligible"] = True
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        yaml.YAMLError,
        subprocess.CalledProcessError,
    ) as error:
        result["blocking_reasons"].append(f"{type(error).__name__}: {error}")
    finally:
        replay = directory / "verification_replay"
        if replay.is_dir():
            with zipfile.ZipFile(
                directory / "verification_replay.zip", "x", compression=zipfile.ZIP_DEFLATED
            ) as archive:
                for path in sorted(replay.rglob("*")):
                    if path.is_file():
                        archive.write(path, path.relative_to(replay).as_posix())
    return result
