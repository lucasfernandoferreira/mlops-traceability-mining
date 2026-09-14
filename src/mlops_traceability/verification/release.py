"""Isolated reproduction, manuscript binding and explicit researcher confirmation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from mlops_traceability.manifest import sha256_file
from mlops_traceability.validation.taxonomy_review import valid_utc
from mlops_traceability.verification.finalization import (
    check_hashes,
    check_receipt_bindings,
    checked_path,
    validate_claim,
)
from mlops_traceability.verification.provenance import assess_provenance


def write_new(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def compare_values(
    expected: Any, observed: Any, tolerance: float = 1e-12, path: str = ""
) -> list[dict[str, Any]]:
    """Report every difference, including accepted floating-point differences."""
    if type(expected) is not type(observed):
        return [dict(path=path, expected=expected, observed=observed, within_tolerance=False)]
    if isinstance(expected, dict):
        if expected.keys() != observed.keys():
            return [
                dict(
                    path=path,
                    expected=sorted(expected),
                    observed=sorted(observed),
                    within_tolerance=False,
                )
            ]
        return [
            d
            for k in expected
            for d in compare_values(expected[k], observed[k], tolerance, f"{path}/{k}")
        ]
    if isinstance(expected, list):
        if len(expected) != len(observed):
            return [
                dict(
                    path=path,
                    expected=len(expected),
                    observed=len(observed),
                    within_tolerance=False,
                )
            ]
        return [
            d
            for i, (a, b) in enumerate(zip(expected, observed, strict=True))
            for d in compare_values(a, b, tolerance, f"{path}/{i}")
        ]
    if expected == observed:
        return []
    numeric = type(expected) is float
    return [
        dict(
            path=path,
            expected=expected,
            observed=observed,
            within_tolerance=numeric and abs(expected - observed) <= tolerance,
        )
    ]


def manuscript_check(root: Path, reviews: Path) -> dict[str, Any]:
    review = json.loads((reviews / "manuscript_review.json").read_text())
    catalog = json.loads((reviews / "claims_catalog.json").read_text())
    path = checked_path(root, review["manuscript_path"])
    text = path.read_text()
    errors = []
    if (
        sha256_file(path) != review["manuscript_sha256"]
        or sha256_file(reviews / "claims_catalog.json") != review["catalog_sha256"]
    ):
        errors.append("manuscript_or_catalog_changed")
    references = re.findall(r"\[afirmação:([^\]]+)\]", text)
    claims = {c["claim_id"]: c for c in catalog["claims"]}
    if references != review["claim_ids"] or set(references) != set(claims):
        errors.append("manuscript_claim_coverage_mismatch")
    for cid, claim in claims.items():
        # Require literal, scoped author-approved wording beside its reference.
        if claim["allowed_conclusion"] + f" [afirmação:{cid}]" not in text:
            errors.append(f"manuscript_statement_mismatch:{cid}")
    for figure in review["figures"]:
        if sha256_file(checked_path(root, figure["path"])) != figure["sha256"]:
            errors.append("manuscript_figure_changed")
    provenance = assess_provenance(reviews, "manuscript_review.json")
    errors += provenance["errors"]
    if provenance["mode"] == "legacy_unspecified":
        errors.append("manuscript_provenance_missing")
    return dict(
        criterion_id="G15",
        status="FAIL" if errors else "PASS",
        manuscript_path=review["manuscript_path"],
        manuscript_sha256=sha256_file(path),
        catalog_sha256=sha256_file(reviews / "claims_catalog.json"),
        numeric_claims_checked=len(claims),
        figures_checked=len(review["figures"]),
        differences=errors,
        opinion=review["opinion"],
        provenance=provenance,
    )


def confirm_reviews(
    root: Path, review_dir: Path, lock_path: Path, name: str, assume_review: bool
) -> Path:
    """Only an explicit researcher CLI invocation records human confirmation."""
    if not assume_review or not name.strip() or name.strip().lower().startswith("assistant:"):
        raise ValueError("Explicit researcher name and --assumo-revisao are required")
    lock = json.loads(lock_path.read_text())
    check_hashes(root, lock["file_hashes"])
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if head != lock["code_sha"]:
        raise ValueError("Confirmation lock uses another verifier revision")
    for file in review_dir.iterdir():
        if file.is_file() and lock["file_hashes"].get(
            file.relative_to(root).as_posix()
        ) != sha256_file(file):
            raise ValueError("Review artifact outside confirmation lock")
    record_path = root / "docs/evidencias/confirmacao_pesquisador.json"
    if record_path.exists():
        old = json.loads(record_path.read_text())
        if old["responsavel"] != name.strip() or old["lock_sha256"] != sha256_file(lock_path):
            raise ValueError("Existing confirmation cannot be overwritten")
        check_hashes(root, old["confirmed_file_hashes"])
        return root / str(old["confirmed_review_dir"])
    at = utc_now()
    destination = review_dir.parent / (
        "confirmadas_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    )
    shutil.copytree(review_dir, destination)

    def promote(value: Any) -> Any:
        if isinstance(value, dict):
            result = {k: promote(v) for k, v in value.items()}
            if result.get("review_mode") == "ai_drafted_pending_confirmation":
                result.update(
                    review_mode="human_confirmed", confirmed_by=name.strip(), confirmed_at_utc=at
                )
            return result
        return [promote(v) for v in value] if isinstance(value, list) else value

    for path in destination.glob("*.json"):
        if path.name != "review_provenance.json":
            data = promote(json.loads(path.read_text()))
            if path.name == "manuscript_review.json":
                continue
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    manuscript = destination / "manuscript_review.json"
    data = promote(json.loads(manuscript.read_text()))
    data["catalog_sha256"] = sha256_file(destination / "claims_catalog.json")
    manuscript.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    path = destination / "review_provenance.json"
    data = promote(json.loads(path.read_text()))
    data["file_hashes"] = {
        p.name: sha256_file(p) for p in destination.iterdir() if p.is_file() and p != path
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    hashes = {
        p.relative_to(root).as_posix(): sha256_file(p) for p in destination.iterdir() if p.is_file()
    }
    for name_, digest in lock["file_hashes"].items():
        if not (root / name_).is_relative_to(review_dir):
            hashes[name_] = digest
    write_new(
        record_path,
        dict(
            responsavel=name.strip(),
            confirmed_at_utc=at,
            declaration=(
                "Revisei o conteúdo listado e assumo os julgamentos e seus limites como "
                "pesquisador, preservando a autoria da redação assistida por IA."
            ),
            lock_sha256=sha256_file(lock_path),
            code_sha=head,
            original_file_hashes=lock["file_hashes"],
            confirmed_file_hashes=hashes,
            confirmed_review_dir=destination.relative_to(root).as_posix(),
        ),
    )
    return destination


def review_package(root: Path, receipt_path: Path, reviews: Path, output: Path) -> Path:
    """Prepare a reproducibility rehearsal while confirmation gates remain closed."""
    receipt = json.loads(receipt_path.read_text())
    paths = {checked_path(root, n) for n in receipt["bound_file_hashes"]}
    paths.update(p for p in reviews.iterdir() if p.is_file())
    path = output / "pacote_revisao.zip"
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(paths):
            archive.write(p, p.relative_to(root).as_posix())
        archive.write(receipt_path, "verification_receipt.json")
        archive.write(receipt_path.parent / "instrument.bundle", "instrument.bundle")
        archive.writestr(
            "PACKAGE_MANIFEST.json",
            json.dumps(
                dict(
                    package_status="review_rehearsal",
                    candidate_eligible=False,
                    scientific_result_accepted=False,
                    files=[
                        dict(path=p.relative_to(root).as_posix(), sha256=sha256_file(p))
                        for p in sorted(paths)
                    ],
                ),
                indent=2,
            ),
        )
    return path


def restore_study(
    root: Path, index_path: Path, receipt_path: Path, package: Path, reviews: Path, output: Path
) -> dict[str, Any]:
    """Copy declared sources to independent storage, run the restored instrument, compare."""
    output.mkdir(parents=True, exist_ok=False)
    receipt = json.loads(receipt_path.read_text())
    check_hashes(root, receipt["bound_file_hashes"])
    check_hashes(receipt_path.parent, receipt["proof_hashes"])
    restored = output / "instrument"
    bundle = receipt_path.parent / "instrument.bundle"
    subprocess.run(
        ["git", "clone", str(bundle.resolve()), str(restored.resolve())],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", "--detach", receipt["verification_code_sha"]],
        cwd=restored,
        check=True,
        capture_output=True,
    )
    recovered_from_zip = []
    with zipfile.ZipFile(package) as archive:
        package_manifest = json.loads(archive.read("PACKAGE_MANIFEST.json"))
        for entry in package_manifest["files"]:
            name = entry["path"]
            relative = PurePosixPath(name)
            if relative.is_absolute() or ".." in relative.parts or relative.as_posix() != name:
                raise ValueError("Unsafe restoration archive path")
            content = archive.read(name)
            if hashlib.sha256(content).hexdigest() != entry["sha256"]:
                raise ValueError("Restoration package entry hash mismatch")
            target = restored / name
            if not target.resolve().is_relative_to(restored.resolve()):
                raise ValueError("Restoration archive escapes root")
            if target.exists() and target.read_bytes() != content:
                raise ValueError("Restoration archive conflicts with instrument")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            recovered_from_zip.append(name)
    baseline = json.loads((root / "docs/evidencias/inventario_insumos.json").read_text())["files"]
    paths = {e["path"]: e["sha256"] for e in baseline}
    paths.update(receipt["bound_file_hashes"])
    paths.update(
        {p.relative_to(root).as_posix(): sha256_file(p) for p in reviews.iterdir() if p.is_file()}
    )
    # Restore proof inputs and baseline literally; clone object files are independent copies.
    for name_, digest in paths.items():
        source = checked_path(root, name_)
        if sha256_file(source) != digest:
            raise ValueError(f"Restoration source changed: {name_}")
        target = restored / name_
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if sha256_file(target) != digest:
                raise ValueError(f"Restored instrument conflicts with source: {name_}")
        else:
            shutil.copy2(source, target)
        if sha256_file(target) != digest:
            raise ValueError(f"Restoration copy mismatch: {name_}")
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=restored)
    if dirty.strip():
        raise ValueError("Restored worktree is dirty")
    destination = restored / "data/interim/restoration_verification"
    command = [
        sys.executable,
        "scripts/verify_study.py",
        "--study-index",
        index_path.relative_to(root).as_posix(),
        "--review-dir",
        reviews.relative_to(root).as_posix(),
        "--output-dir",
        destination.relative_to(restored).as_posix(),
    ]
    env = {**os.environ, "PYTHONPATH": str((restored / "src").resolve())}
    with (output / "restoration.log").open("x") as stream:
        result = subprocess.run(
            command, cwd=restored, env=env, stdout=stream, stderr=subprocess.STDOUT, check=False
        )
    repeated = json.loads((destination / "verification_receipt.json").read_text())
    check_receipt_bindings(restored, restored / index_path.relative_to(root), destination, repeated)
    if repeated["verification_code_sha"] != receipt["verification_code_sha"]:
        raise ValueError("Restored verifier revision mismatch")
    differences = []
    compared = []
    for case in receipt["cases"]:
        prefix = case["repository_id"].replace("/", "__")
        for name_ in ("source_commits.json", "source_changes.json", "crosscheck.json"):
            relative = prefix + "/" + name_
            a = json.loads((receipt_path.parent / relative).read_text())
            b = json.loads((destination / relative).read_text())
            differences += compare_values(a, b, path=relative)
            compared.append(relative)
    for name_ in ("qualitative/selected.json", "qualitative/crosscheck.json"):
        differences += compare_values(
            json.loads((receipt_path.parent / name_).read_text()),
            json.loads((destination / name_).read_text()),
            path=name_,
        )
        compared.append(name_)
    # Required technical recalculations must pass even for an unconfirmed review rehearsal.
    mandatory = {"G00", "G02", "G03", "G04", "G05", "G06", "G08", "G09", "G10", "G13"}
    technical = {c["criterion_id"] for c in repeated["criteria"] if c["status"] == "PASS"}
    failures = sorted(mandatory - technical)
    failed = bool(
        failures
        or repeated["processing_errors"]
        or any(not d["within_tolerance"] for d in differences)
    )
    report = dict(
        criterion_id="G14",
        status="FAIL" if failed else "PASS",
        created_at_utc=utc_now(),
        study_index_sha256=sha256_file(index_path),
        verification_code_sha=receipt["verification_code_sha"],
        empirical_receipt_sha256=sha256_file(receipt_path),
        package_sha256=sha256_file(package),
        restored_root=str(restored),
        restored_receipt=str(destination / "verification_receipt.json"),
        restored_receipt_sha256=sha256_file(destination / "verification_receipt.json"),
        source_hashes=paths,
        recovered_from_package=recovered_from_zip,
        external_sources=sorted(set(paths) - set(recovered_from_zip)),
        recalculated=compared,
        integrity_only=(
            "Original collection, review judgments, static scanner counts and prose; "
            "no case training executed"
        ),
        dependency_recovery=(
            "Independent byte copies of declared bare clones; no hardlinks, "
            "symlinks or network lookup. Interpreter/dependencies shared "
            "and declared in command."
        ),
        command=command,
        subprocess_exit_code=result.returncode,
        absolute_tolerance=1e-12,
        differences=differences,
        technical_failures=failures,
        processing_errors=repeated["processing_errors"],
    )
    write_new(output / "restoration_report.json", report)
    return report


def final_receipt(
    root: Path,
    index_path: Path,
    empirical: Path,
    package: Path,
    restoration: Path,
    reviews: Path,
    output: Path,
) -> dict[str, Any]:
    errors = []
    measured = json.loads(empirical.read_text())
    restored = json.loads(restoration.read_text())
    manuscript = manuscript_check(root, reviews)
    try:
        check_receipt_bindings(root, index_path, empirical.parent, measured)
        validate_claim(measured)
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        if measured["verification_code_sha"] != head:
            raise ValueError("Final acceptance uses another verifier revision")
        repeated_path = Path(restored["restored_receipt"])
        if sha256_file(repeated_path) != restored["restored_receipt_sha256"]:
            raise ValueError("Restored receipt changed")
        repeated = json.loads(repeated_path.read_text())
        restored_root = Path(restored["restored_root"])
        check_receipt_bindings(
            restored_root,
            restored_root / index_path.relative_to(root),
            repeated_path.parent,
            repeated,
        )
        validate_claim(repeated)
        if repeated["verification_code_sha"] != head or restored["verification_code_sha"] != head:
            raise ValueError("Restored evidence uses another verifier revision")
        check_hashes(root, restored["source_hashes"])
        check_hashes(restored_root, restored["source_hashes"])
    except (OSError, ValueError, KeyError) as error:
        errors.append(str(error))
    for key, value in (
        ("study_index_sha256", sha256_file(index_path)),
        ("empirical_receipt_sha256", sha256_file(empirical)),
        ("package_sha256", sha256_file(package)),
    ):
        if restored.get(key) != value:
            errors.append(f"restoration_binding:{key}")
    if (
        restored.get("status") != "PASS"
        or restored.get("processing_errors")
        or restored.get("technical_failures")
        or any(not x["within_tolerance"] for x in restored.get("differences", []))
    ):
        errors.append("restoration_not_passed")
    with zipfile.ZipFile(package) as archive:
        manifest = json.loads(archive.read("PACKAGE_MANIFEST.json"))
        if manifest["package_status"] != "candidate":
            errors.append("package_is_not_scientific_candidate")
        entries = manifest["files"]
        if not entries or len({e["path"] for e in entries}) != len(entries):
            errors.append("invalid_candidate_inventory")
        for entry in entries:
            if hashlib.sha256(archive.read(entry["path"])).hexdigest() != entry["sha256"]:
                errors.append(f"candidate_entry_changed:{entry['path']}")
    if manuscript["status"] != "PASS":
        errors += manuscript["differences"]
    confirmation = root / "docs/evidencias/confirmacao_pesquisador.json"
    confirmation_hash = None
    try:
        confirmation_data = json.loads(confirmation.read_text())
        check_hashes(root, confirmation_data["confirmed_file_hashes"])
        if (
            not confirmation_data["responsavel"].strip()
            or confirmation_data["responsavel"].lower().startswith("assistant:")
            or not valid_utc(confirmation_data["confirmed_at_utc"])
            or confirmation_data["code_sha"] != measured["verification_code_sha"]
            or confirmation_data["confirmed_review_dir"] != reviews.relative_to(root).as_posix()
        ):
            raise ValueError("Researcher confirmation uses another review package")
        confirmation_hash = sha256_file(confirmation)
    except (OSError, ValueError, KeyError) as error:
        errors.append(f"researcher_confirmation:{error}")
    result = dict(
        scientific_result_accepted=not errors,
        created_at_utc=utc_now(),
        study_index_sha256=sha256_file(index_path),
        empirical_receipt_sha256=sha256_file(empirical),
        package_sha256=sha256_file(package),
        restoration_report_sha256=sha256_file(restoration),
        manuscript=manuscript,
        researcher_confirmation_sha256=confirmation_hash,
        blocking_reasons=errors,
    )
    write_new(output, result)
    return result
