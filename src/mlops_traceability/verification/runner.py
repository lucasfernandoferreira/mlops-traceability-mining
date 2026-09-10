"""Offline empirical checks with immutable refusals and explicit incomplete criteria.

This increment executes source, arithmetic and descriptive crosschecks. It does not
issue final scientific acceptance or treat unexecuted G00-G13 criteria as passed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from mlops_traceability.manifest import sha256_file
from mlops_traceability.pilot import audit_collection
from mlops_traceability.run_storage import verified_run
from mlops_traceability.study import load_index
from mlops_traceability.verification.contracts import Criterion, aggregate_criteria
from mlops_traceability.verification.descriptive import describe
from mlops_traceability.verification.git_oracle import (
    classify,
    git,
    object_reader,
    reconcile_rows,
    source_history,
)
from mlops_traceability.verification.oracles import arithmetic, compare_metrics
from mlops_traceability.verification.qualitative import verify_qualitative
from mlops_traceability.verification.reviews import import_reviews
from mlops_traceability.verification.tables import read_table

CRITERIA = [f"G{i:02}" for i in range(14)]
COMMIT_FIELDS = (
    "parent_sha",
    "parent_count",
    "committed_at_utc",
    "is_bot",
    "files_changed_count",
    "large_commit",
    "eligibility_status",
    "C",
    "D",
    "P",
    "config_changed_keys",
    "config_semantic_status",
)
CHANGE_FIELDS = (
    "parent_sha",
    "change_type",
    "category",
    "before_blob_sha",
    "after_blob_sha",
    "semantic_status",
    "changed_keys",
    "changed_key_count",
)


def write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def inventory_check(
    clone: Path,
    head: str,
    repository: str,
    rows: list[dict[str, Any]],
    inventory: dict[str, Any],
    sample: list[dict[str, Any]],
    taxonomy: dict[str, Any],
) -> dict[str, Any]:
    paths = {r["file_path"] for r in rows}
    for record in git(clone, "ls-tree", "-r", "-z", head).split(b"\0"):
        if record:
            metadata, path = record.split(b"\t", 1)
            if metadata.split()[1] == b"blob":
                paths.add(path.decode("utf-8"))
    actual = [r for r in inventory["units"] if r["repository_id"] == repository]
    expected = [
        dict(
            repository_id=repository,
            file_path=p,
            category=classify(p, taxonomy),
            head_commit_sha=head,
        )
        for p in sorted(paths)
    ]
    issues = reconcile_rows(
        expected, actual, ("repository_id", "file_path"), ("category", "head_commit_sha")
    )
    checked = 0
    with object_reader(clone) as read:
        for row in sample:
            if row["repository_id"] != repository:
                continue
            for field in ("blob_revision", "blob_sha", "head_commit_sha"):
                if not re.fullmatch(r"[a-f0-9]{40}", row[field]):
                    raise ValueError("Invalid sample object SHA")
            git(clone, "merge-base", "--is-ancestor", row["blob_revision"], head)
            oid = (
                git(clone, "rev-parse", f"{row['blob_revision']}:{row['file_path']}")
                .decode()
                .strip()
            )
            if row["head_commit_sha"] != head or oid != row["blob_sha"]:
                issues.append(
                    dict(
                        identity=row["unit_id"],
                        field="historical_blob",
                        expected=row["blob_sha"],
                        observed=oid,
                    )
                )
            read(oid, "blob")
            checked += 1
    return dict(
        inventory_paths=len(expected), historical_sample_blobs_checked=checked, differences=issues
    )


def verify_study(
    root: Path, index_path: Path, review_dir: Path, output: Path, *, scope: str = "empirical"
) -> int:
    if scope not in {"empirical", "synthetic"}:
        raise ValueError("Invalid scope")
    root, index_path, review_dir = root.resolve(), index_path.resolve(), review_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    receipt: dict[str, Any] = {
        "verification_schema_version": "1.0.0",
        "verification_policy_version": None,
        "scope": scope,
        "criteria_scope": CRITERIA,
        "scientific_result_accepted": False,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "verification_status": "FAIL",
        "verification_code_sha": None,
        "test_suite_code_sha": None,
        "test_results_hashes": {},
        "study_index_sha256": None,
        "input_manifest_hashes": {},
        "review_file_hashes": {},
        "bound_file_hashes": {},
        "proof_hashes": {},
        "cases": [],
        "processing_errors": [],
        "limitations": [
            "Git, regex, PyYAML and JSON serialization are shared dependencies.",
            "Static MLflow call counts are not recalculated by this increment.",
            "G00-G13 remain incomplete; G14-G15 and final acceptance are outside this receipt.",
            "Record validation does not authenticate reviewers or academic approval.",
        ],
    }
    criteria = {
        key: Criterion(
            criterion_id=key,
            method="Pending implementation or evidence",
            expected="Complete evidence under verification policy",
            observed=None,
            proof=[],
            status="NOT_RUN",
            reason="Not executed in this increment",
        )
        for key in CRITERIA
    }

    def bound(path: Path) -> None:
        receipt["bound_file_hashes"][str(path.relative_to(root))] = sha256_file(path)

    def criterion(key: str, method: str, differences: list[Any], proofs: list[str]) -> None:
        criteria[key] = Criterion(
            criterion_id=key,
            method=method,
            expected="No discrepancies",
            observed=differences,
            proof=proofs,
            status="FAIL" if differences else "PASS",
        )

    try:
        config_path, policy_path = root / "config/config.yaml", root / "config/verification.yaml"
        cfg = yaml.safe_load(config_path.read_text())
        policy = yaml.safe_load(policy_path.read_text())
        if policy["pre_restoration_criteria"] != CRITERIA:
            raise ValueError("Policy must cover exactly G00-G13")
        tolerance = float(policy["absolute_tolerance"])
        if not 0 <= tolerance <= 1e-12:
            raise ValueError("Unsupported verification tolerance")
        tax = yaml.safe_load((root / "config/file_taxonomy.yaml").read_text())
        receipt["verification_policy_version"] = policy["verification_policy_version"]
        receipt["verification_code_sha"] = git(root, "rev-parse", "HEAD").decode().strip()
        receipt["test_suite_code_sha"] = receipt["verification_code_sha"]
        receipt["dirty_worktree"] = bool(git(root, "status", "--porcelain").strip())
        for path in (
            config_path,
            policy_path,
            root / "config/file_taxonomy.yaml",
            root / "requirements.txt",
            root / "requirements-dev.txt",
            root / "config/amostra_final.yaml",
        ):
            bound(path)
        with tarfile.open(output / "verification_source.tar.gz", "w:gz") as archive:
            paths = [
                p
                for base in ("src", "scripts", "tests", "config", "docs")
                for p in (root / base).rglob("*")
                if p.is_file() and "__pycache__" not in p.parts
            ]
            paths += [
                root / p
                for p in ("Makefile", "pyproject.toml", "requirements.txt", "requirements-dev.txt")
                if (root / p).is_file()
            ]
            for path in sorted(paths):
                archive.add(path, arcname=path.relative_to(root), recursive=False)
        git(root, "bundle", "create", str((output / "instrument.bundle").resolve()), "--all")
        receipt["study_index_sha256"] = sha256_file(index_path)
        bound(index_path)
        index, inputs = load_index(root, index_path)
        manifests: dict[str, dict[str, Path]] = {}
        for run_id in [index_path.parent.name, *[r["run_id"] for r in index["sources"]]]:
            _, artifacts, _ = verified_run(root, run_id, scientific=scope == "empirical")
            manifest = root / cfg["paths"]["manifests"] / f"{run_id}.json"
            receipt["input_manifest_hashes"][run_id] = sha256_file(manifest)
            bound(manifest)
            for path in artifacts.values():
                bound(path)
            manifests[run_id] = artifacts
        import_code = import_reviews(root, index_path, review_dir, output / "reviews", scope=scope)
        review_receipt = json.loads((output / "reviews/review_import.json").read_text())
        receipt["review_file_hashes"] = review_receipt["review_file_hashes"]
        criterion(
            "G01",
            "Validate preserved human decision records",
            review_receipt["blocking_reasons"],
            ["reviews/review_import.json"],
        )
        if import_code == 2:
            receipt["processing_errors"].append("Review import has missing/incompatible inputs")
        origins = json.loads((output / "reviews/original_reviews/origens.json").read_text())
        report_files = None
        if origins.get("report_run_id"):
            manifest, report_files, execution = verified_run(
                root, origins["report_run_id"], "phase8_report", scientific=scope == "empirical"
            )
            if not any(
                r["run_id"] == index_path.parent.name
                and r["manifest_sha256"] == receipt["input_manifest_hashes"][index_path.parent.name]
                for r in execution["sources"]
            ):
                raise ValueError("Report belongs to another study index")
            report_manifest = root / cfg["paths"]["manifests"] / f"{manifest['run_id']}.json"
            receipt["input_manifest_hashes"][manifest["run_id"]] = sha256_file(report_manifest)
            bound(report_manifest)
            for path in report_files.values():
                bound(path)
        selection = yaml.safe_load((root / "config/amostra_final.yaml").read_text())
        audit = audit_collection(root, selection)
        write_json(output / "original_collection_audit.json", audit)
        shortlist_path = (
            root
            / "data/interim/runs"
            / selection["source_runs"]["phase2_screen_sample"]
            / "shortlist.csv"
        )
        bound(shortlist_path)
        shortlist_rows = read_table(shortlist_path)
        shortlist = {r["repository_id"]: r for r in shortlist_rows}
        if len(shortlist) != len(shortlist_rows):
            raise ValueError("Duplicate shortlist identity")
        inventory_path = index_path.parent / "taxonomy_inventory.json"
        inventory = json.loads(inventory_path.read_text())
        sample = read_table(index_path.parent / "amostra_validacao_taxonomia.csv")
        all_history, all_maturity, all_metrics, all_inventory, all_descriptive = [], [], [], [], []
        proofs = []
        for case in index["cases"]:
            repository, head = case["repository_id"], case["head_commit_sha"]
            if not re.fullmatch(r"[\w-][\w.-]*/[\w-][\w.-]*", repository):
                raise ValueError("Invalid case repository ID")
            directory = output / repository.replace("/", "__")
            directory.mkdir()
            clone = (
                root / cfg["paths"]["raw_repositories"] / (repository.replace("/", "__") + ".git")
            )
            print(f"Verifying {repository} at {head}", flush=True)
            source, changes, summary = source_history(clone, head, repository, cfg, tax)
            files = inputs[repository]
            history = reconcile_rows(
                source,
                read_table(files["commits.parquet"]),
                ("repository_id", "commit_sha"),
                COMMIT_FIELDS,
            )
            history += reconcile_rows(
                changes,
                read_table(files["changes.parquet"]),
                ("repository_id", "commit_sha", "file_path"),
                CHANGE_FIELDS,
            )
            old_summary = json.loads(files["mining_summary.json"].read_text())
            for field in ("reachable_commits", "funnel", "active_contributors_count"):
                if summary[field] != old_summary[field]:
                    history.append(
                        dict(field=field, expected=summary[field], observed=old_summary[field])
                    )
            maturity = [r for r in history if r.get("field") == "active_contributors_count"]
            if datetime.fromisoformat(old_summary["active_after"]) != datetime.fromisoformat(
                cfg["selection"]["active_after"]
            ):
                maturity.append(
                    dict(
                        field="active_after",
                        expected=cfg["selection"]["active_after"],
                        observed=old_summary["active_after"],
                    )
                )
            for name, observed, minimum in (
                ("commits", summary["reachable_commits"], cfg["selection"]["min_commits"]),
                (
                    "identities",
                    summary["active_contributors_count"],
                    cfg["selection"]["min_contributors"],
                ),
                ("stars", int(shortlist[repository]["stars_count"]), cfg["selection"]["min_stars"]),
            ):
                if observed < minimum:
                    maturity.append(dict(field=name, expected_minimum=minimum, observed=observed))
            expected = arithmetic(source)
            actual = read_table(manifests[case["runs"]["metrics"]["run_id"]]["metrics.csv"])
            if any(
                r["repository_id"] != repository or r["head_commit_sha"] != head for r in actual
            ):
                raise ValueError("Metric case/SHA mismatch")
            metric_issues = compare_metrics(expected, actual, tolerance=tolerance)
            if any(r["P"] and r["config_semantic_status"] != "observed" for r in source):
                metric_issues.append("source_config_semantics_incomplete")
            inv_check = inventory_check(clone, head, repository, changes, inventory, sample, tax)
            descriptive = describe(source, changes, repository, cfg["analysis"])
            descriptive_issues = []
            if report_files:
                for key, file, identity in (
                    ("distribution", "distribuicao_configuracao.csv", ("repository_id",)),
                    ("months", "serie_mensal.csv", ("repository_id", "month_utc")),
                    ("sensitivity", "sensibilidade_configuracao.csv", ("repository_id", "variant")),
                ):
                    measured = [
                        r
                        for r in read_table(report_files[file])
                        if r["repository_id"] == repository
                    ]
                    descriptive_issues += reconcile_rows(
                        descriptive[key],
                        measured,
                        identity,
                        tuple(descriptive[key][0]) if descriptive[key] else (),
                        tolerance=tolerance,
                    )
            result = dict(
                repository_id=repository,
                head_commit_sha=head,
                source_summary=summary,
                arithmetic=expected,
                historical_stars=int(shortlist[repository]["stars_count"]),
                history_differences=history,
                maturity_differences=maturity,
                metric_differences=metric_issues,
                inventory=inv_check,
                descriptive=descriptive,
                descriptive_differences=descriptive_issues,
            )
            write_json(directory / "source_commits.json", source)
            write_json(directory / "source_changes.json", changes)
            write_json(directory / "crosscheck.json", result)
            proof = str((directory / "crosscheck.json").relative_to(output))
            proofs.append(proof)
            receipt["cases"].append(dict(repository_id=repository, proof=proof))
            all_history.extend(history)
            all_maturity.extend(maturity)
            all_metrics.extend(metric_issues)
            all_inventory.extend(inv_check["differences"])
            all_descriptive.extend(descriptive_issues)
        write_json(
            output / "independence.json",
            {
                "source": "Raw Git objects and first-parent file diffs over the full DAG",
                "config": "Paired recursive tree comparison; typed paths; cached blob pairs",
                "arithmetic": "Plain Python integer counts and SQLite human label tally",
                "descriptive": "Python linear quantiles, month buckets and path contributions",
                "qualitative": "GraphQL parsing, sorted event partitions and rational sampling",
                "common_dependencies": [
                    "Git",
                    "Python regex",
                    "PyYAML",
                    "JSON scalar serialization",
                ],
                "source_archive_sha256": sha256_file(output / "verification_source.tar.gz"),
            },
        )
        criterion(
            "G03",
            "Independent implementations and comparable outputs recorded",
            [],
            proofs + ["independence.json"],
        )
        criterion(
            "G05", "Full raw Git objects/diffs versus commit and file tables", all_history, proofs
        )
        criterion(
            "G06",
            "Git activity identities and historical shortlist thresholds",
            all_maturity,
            proofs + ["original_collection_audit.json"],
        )
        criterion(
            "G07",
            "Full inventory and historical sample blobs; preserved human labels",
            all_inventory
            + review_receipt.get("taxonomy", {}).get(
                "blocking_reasons", ["human_labels_not_verified"]
            ),
            proofs + ["reviews/review_import.json"],
        )
        criterion(
            "G08",
            "Git C/P and CONFIG pairs; independent integer ratios; six unavailable metrics",
            all_history + all_metrics,
            proofs,
        )
        if report_files:
            criterion(
                "G09",
                "Independent linear quantiles, concentration, monthly totals and sensitivity",
                all_history + all_descriptive,
                proofs,
            )
        try:
            qualitative, qualitative_inputs = verify_qualitative(
                root, index_path, origins, output, cfg["analysis"], scientific=scope == "empirical"
            )
            for path in qualitative_inputs:
                bound(path)
            receipt["qualitative"] = dict(proof="qualitative/crosscheck.json")
            criterion(
                "G10",
                "Recorded PR associations; independent grouping, quotas, ties and deficit fill",
                all_history + qualitative["differences"],
                proofs + ["qualitative/crosscheck.json"],
            )
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            message = f"qualitative_input:{type(error).__name__}:{error}"
            receipt["processing_errors"].append(message)
            criterion("G10", "Independent PR and event selection", [message], proofs)
        criterion(
            "G13",
            "Verification/finalization integration and clean empirical code",
            ["finalization_integration_not_implemented"]
            + (["dirty_verifier_worktree"] if receipt["dirty_worktree"] else []),
            proofs,
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        yaml.YAMLError,
        subprocess.CalledProcessError,
    ) as error:
        receipt["processing_errors"].append(f"{type(error).__name__}: {error}")
    receipt["criteria"] = [criteria[k].model_dump() for k in CRITERIA]
    status, reasons = aggregate_criteria(list(criteria.values()), CRITERIA)
    receipt["verification_status"] = "FAIL" if receipt["processing_errors"] else status
    receipt["blocking_reasons"] = reasons + receipt["processing_errors"]
    for path in output.rglob("*"):
        if path.is_file():
            receipt["proof_hashes"][str(path.relative_to(output))] = sha256_file(path)
    code = (
        2 if receipt["processing_errors"] else 1 if receipt["verification_status"] != "PASS" else 0
    )
    receipt["exit_code"] = code
    write_json(output / "verification_receipt.json", receipt)
    (output / "verification_report.md").write_text(
        "# Verificação do estudo\n\nEscopo: G00–G13; sem aceite científico final.\n\n"
        + "\n".join(f"- {key}: {criteria[key].status}" for key in CRITERIA)
        + "\n\n"
        + "\n".join(receipt["processing_errors"])
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Verification {receipt['verification_status']}; exit {code}; "
        f"receipt: {output / 'verification_receipt.json'}",
        flush=True,
    )
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-index", required=True, type=Path)
    parser.add_argument("--review-dir", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[3]
    output = args.output_dir or root / "data/interim/verification" / datetime.now(UTC).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )
    try:
        return verify_study(root, args.study_index, args.review_dir, output)
    except OSError as error:
        print(f"Cannot create immutable verification output: {error}")
        return 2
