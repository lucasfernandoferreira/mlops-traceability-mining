"""Temporary synthetic confirmations exercise gates without attributing real research."""

from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path
from typing import Any

import pytest
from test_closure import dump

from mlops_traceability.manifest import sha256_file
from mlops_traceability.verification import release


def setup_review(root: Path) -> tuple[Path, Path]:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Synthetic",
            "-c",
            "user.email=synthetic@example.invalid",
            "commit",
            "--allow-empty",
            "-qm",
            "fixture",
        ],
        cwd=root,
        check=True,
    )
    root.joinpath("text.md").write_text("Observed 1 of 2. [afirmação:ratio]\n")
    reviews = root / "reviews"
    metadata = dict(
        drafted_by="assistant:synthetic-test",
        review_mode="ai_drafted_pending_confirmation",
        confirmed_by=None,
        confirmed_at_utc=None,
    )
    dump(
        reviews / "claims_catalog.json",
        {"claims": [dict(claim_id="ratio", allowed_conclusion="Observed 1 of 2.", **metadata)]},
    )
    dump(
        reviews / "manuscript_review.json",
        dict(
            manuscript_path="text.md",
            manuscript_sha256=sha256_file(root / "text.md"),
            catalog_sha256=sha256_file(reviews / "claims_catalog.json"),
            claim_ids=["ratio"],
            figures=[],
            opinion="Scope limited to fixture",
            **metadata,
        ),
    )
    (reviews / "labels.csv").write_text("id,label\n1,CODE\n")
    dump(
        reviews / "review_provenance.json",
        dict(
            file_hashes={p.name: sha256_file(p) for p in reviews.iterdir()},
            records=[
                dict(file=name, record_id=name, **metadata)
                for name in ("claims_catalog.json", "manuscript_review.json", "labels.csv")
            ],
        ),
    )
    lock = root / "lock.json"
    dump(
        lock,
        dict(
            code_sha=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip(),
            file_hashes={
                p.relative_to(root).as_posix(): sha256_file(p)
                for p in [*reviews.iterdir(), root / "text.md"]
            },
        ),
    )
    return reviews, lock


@pytest.mark.parametrize(
    "a,b,accepted",
    [
        (1, 2, False),
        (1, 1.0, False),
        (1.0, 1.0 + 1e-13, True),
        (1.0, 1.1, False),
        ([1, 2], [2, 1], False),
        ([1], [1, 2], False),
        ({"a": 1}, {"b": 1}, False),
    ],
)
def test_comparison_preserves_all_differences(a: Any, b: Any, accepted: bool) -> None:
    differences = release.compare_values(a, b)
    assert differences and all(d["within_tolerance"] is accepted for d in differences)
    assert not release.compare_values(a, a)


def test_confirmation_preserves_original_and_updates_manuscript_binding(tmp_path: Path) -> None:
    reviews, lock = setup_review(tmp_path)
    original = {p.name: p.read_bytes() for p in reviews.iterdir()}
    assert release.manuscript_check(tmp_path, reviews)["status"] == "FAIL"
    for name, assume in [("Synthetic reviewer", False), ("assistant:fake", True), ("", True)]:
        with pytest.raises(ValueError, match="Explicit"):
            release.confirm_reviews(tmp_path, reviews, lock, name, assume)
    confirmed = release.confirm_reviews(tmp_path, reviews, lock, "Synthetic test reviewer", True)
    assert confirmed != reviews
    assert original == {p.name: p.read_bytes() for p in reviews.iterdir()}
    assert (confirmed / "labels.csv").read_bytes() == original["labels.csv"]
    assert release.manuscript_check(tmp_path, confirmed)["status"] == "PASS"
    record = json.loads((tmp_path / "docs/evidencias/confirmacao_pesquisador.json").read_text())
    assert record["responsavel"] == "Synthetic test reviewer"
    data = json.loads((confirmed / "claims_catalog.json").read_text())["claims"][0]
    assert data["drafted_by"] == "assistant:synthetic-test"
    assert data["review_mode"] == "human_confirmed" and data["confirmed_at_utc"]
    assert (
        release.confirm_reviews(tmp_path, reviews, lock, "Synthetic test reviewer", True)
        == confirmed
    )
    with pytest.raises(ValueError, match="overwritten"):
        release.confirm_reviews(tmp_path, reviews, lock, "Other synthetic reviewer", True)
    (confirmed / "labels.csv").write_text("changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        release.confirm_reviews(tmp_path, reviews, lock, "Synthetic test reviewer", True)


def test_lock_and_manuscript_mutations_refuse(tmp_path: Path) -> None:
    reviews, lock = setup_review(tmp_path)
    text = tmp_path / "text.md"
    text.write_text("Observed 2 of 2. [afirmação:other]\n")
    result = release.manuscript_check(tmp_path, reviews)
    assert "manuscript_or_catalog_changed" in result["differences"]
    assert "manuscript_claim_coverage_mismatch" in result["differences"]
    assert "manuscript_statement_mismatch:ratio" in result["differences"]
    with pytest.raises(ValueError, match="hash mismatch"):
        release.confirm_reviews(tmp_path, reviews, lock, "Synthetic test reviewer", True)
    with pytest.raises(FileExistsError):
        release.write_new(lock, {})


def test_review_package_cannot_be_promoted_to_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reviews, _ = setup_review(tmp_path)
    evidence = tmp_path / "empirical"
    evidence.mkdir()
    receipt = evidence / "verification_receipt.json"
    dump(
        receipt,
        dict(
            bound_file_hashes={"text.md": sha256_file(tmp_path / "text.md")},
            verification_code_sha="synthetic",
        ),
    )
    (evidence / "instrument.bundle").write_bytes(b"synthetic")
    package = release.review_package(tmp_path, receipt, reviews, evidence)
    with zipfile.ZipFile(package) as archive:
        assert json.loads(archive.read("PACKAGE_MANIFEST.json"))["candidate_eligible"] is False
    restoration = tmp_path / "restoration.json"
    dump(
        restoration,
        dict(
            status="PASS",
            technical_failures=[],
            differences=[],
            study_index_sha256=sha256_file(tmp_path / "text.md"),
            empirical_receipt_sha256=sha256_file(receipt),
            package_sha256=sha256_file(package),
        ),
    )

    def reject(*args: Any) -> None:
        raise ValueError("Synthetic receipt has no empirical evidence")

    monkeypatch.setattr(release, "check_receipt_bindings", reject)
    result = release.final_receipt(
        tmp_path,
        tmp_path / "text.md",
        receipt,
        package,
        restoration,
        reviews,
        tmp_path / "final.json",
    )
    assert result["scientific_result_accepted"] is False
    assert "package_is_not_scientific_candidate" in result["blocking_reasons"]
    assert "ai_review_requires_confirmation" in result["blocking_reasons"]
    assert any(x.startswith("researcher_confirmation:") for x in result["blocking_reasons"])


@pytest.mark.parametrize("mutation", ["none", "count", "float", "technical"])
def test_isolated_restore_copies_sources_and_compares_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    # Only the verifier subprocess is a synthetic stand-in. Git recovery and copies are real.
    root = tmp_path / "original"
    root.mkdir()
    reviews, _ = setup_review(root)
    (root / ".gitignore").write_text("*\n!.gitignore\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Synthetic",
            "-c",
            "user.email=synthetic@example.invalid",
            "commit",
            "-qm",
            "ignore fixture data",
        ],
        cwd=root,
        check=True,
    )
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    index = root / "index.json"
    index.write_text("{}")
    raw = root / "raw.bin"
    raw.write_bytes(b"independent external input")
    inventory = root / "docs/evidencias/inventario_insumos.json"
    dump(inventory, {"files": [dict(path="raw.bin", sha256=sha256_file(raw))]})
    evidence = root / "empirical"
    evidence.mkdir()
    subprocess.run(
        ["git", "bundle", "create", str(evidence / "instrument.bundle"), "HEAD"],
        cwd=root,
        check=True,
    )
    proofs = {}
    for name in (
        "org__repo/source_commits.json",
        "org__repo/source_changes.json",
        "org__repo/crosscheck.json",
        "qualitative/selected.json",
        "qualitative/crosscheck.json",
    ):
        path = evidence / name
        dump(path, {"count": 2, "value": 0.5, "ids": ["first", "second"]})
        proofs[name] = sha256_file(path)
    receipt = evidence / "verification_receipt.json"
    dump(
        receipt,
        dict(
            bound_file_hashes={
                p.relative_to(root).as_posix(): sha256_file(p) for p in [index, inventory]
            },
            proof_hashes=proofs,
            verification_code_sha=head,
            cases=[dict(repository_id="org/repo")],
        ),
    )
    package = release.review_package(root, receipt, reviews, evidence)
    original_run = subprocess.run

    def run(command: list[str], **kwargs: Any) -> Any:
        if len(command) < 2 or command[1] != "scripts/verify_study.py":
            return original_run(command, **kwargs)
        restored = Path(kwargs["cwd"])
        destination = restored / command[-1]
        for name in proofs:
            data = json.loads((evidence / name).read_text())
            if mutation == "count":
                data["count"] = 3
            elif mutation == "float":
                data["value"] += 1e-13
            dump(destination / name, data)
        keys = ("G00", "G02", "G03", "G04", "G05", "G06", "G08", "G09", "G10", "G13")
        dump(
            destination / "verification_receipt.json",
            dict(
                verification_code_sha=head,
                processing_errors=[],
                criteria=[
                    dict(
                        criterion_id=k,
                        status="FAIL" if mutation == "technical" and k == "G08" else "PASS",
                    )
                    for k in keys
                ],
            ),
        )
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(release, "check_receipt_bindings", lambda *args: {})
    output = tmp_path / "isolated"
    report = release.restore_study(root, index, receipt, package, reviews, output)
    assert report["status"] == ("FAIL" if mutation in {"count", "technical"} else "PASS")
    restored_raw = output / "instrument/raw.bin"
    assert raw.read_bytes() == restored_raw.read_bytes()
    assert raw.stat().st_ino != restored_raw.stat().st_ino
    assert "raw.bin" in report["external_sources"]
    assert "index.json" in report["recovered_from_package"]
    if mutation == "float":
        assert report["differences"] and all(d["within_tolerance"] for d in report["differences"])
    elif mutation == "count":
        assert all(not d["within_tolerance"] for d in report["differences"])
    elif mutation == "technical":
        assert report["technical_failures"] == ["G08"]


@pytest.mark.parametrize(
    "mutation", ["none", "restored_receipt", "source", "timestamp", "package", "g14"]
)
def test_final_bindings_reject_changed_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    # Synthetic gate outputs isolate final binding checks; this is not study acceptance evidence.
    reviews, lock = setup_review(tmp_path)
    reviews = release.confirm_reviews(tmp_path, reviews, lock, "Synthetic reviewer", True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    index = tmp_path / "text.md"
    empirical = tmp_path / "empirical.json"
    dump(empirical, dict(verification_code_sha=head))
    repeated = tmp_path / "repeated.json"
    dump(repeated, dict(verification_code_sha=head))
    package = tmp_path / "candidate.zip"
    with zipfile.ZipFile(package, "x") as archive:
        archive.writestr("source", index.read_bytes())
        archive.writestr(
            "PACKAGE_MANIFEST.json",
            json.dumps(
                dict(
                    package_status="candidate",
                    files=[
                        dict(
                            path="source",
                            sha256="a" * 64 if mutation == "package" else sha256_file(index),
                        )
                    ],
                )
            ),
        )
    restoration = tmp_path / "restoration.json"
    dump(
        restoration,
        dict(
            status="FAIL" if mutation == "g14" else "PASS",
            technical_failures=[],
            differences=[],
            processing_errors=[],
            study_index_sha256=sha256_file(index),
            empirical_receipt_sha256=sha256_file(empirical),
            package_sha256=sha256_file(package),
            restored_receipt=str(repeated),
            restored_receipt_sha256=sha256_file(repeated),
            restored_root=str(tmp_path),
            verification_code_sha=head,
            source_hashes={"text.md": sha256_file(index)},
        ),
    )
    monkeypatch.setattr(release, "check_receipt_bindings", lambda *args: {})
    monkeypatch.setattr(release, "validate_claim", lambda *args: None)
    if mutation == "restored_receipt":
        repeated.write_text("{}")
    elif mutation == "source":
        index.write_text("changed")
    elif mutation == "timestamp":
        confirmation = tmp_path / "docs/evidencias/confirmacao_pesquisador.json"
        data = json.loads(confirmation.read_text())
        data["confirmed_at_utc"] = "not-a-timestamp"
        dump(confirmation, data)
    result = release.final_receipt(
        tmp_path, index, empirical, package, restoration, reviews, tmp_path / "final.json"
    )
    assert result["scientific_result_accepted"] is (mutation == "none")
    if mutation == "restored_receipt":
        assert "Restored receipt changed" in result["blocking_reasons"]
    elif mutation == "package":
        assert "candidate_entry_changed:source" in result["blocking_reasons"]
