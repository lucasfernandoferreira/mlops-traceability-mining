"""Historical sampling and human review; software predictions are never human labels."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any

from git import Repo

from mlops_traceability.config import ResearchConfig
from mlops_traceability.manifest import sha256_file
from mlops_traceability.taxonomy import Category, FileTaxonomy

HUMAN_FIELDS = (
    "expected_category",
    "reviewer",
    "reviewed_at_utc",
    "justification",
    "role_change_review",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def valid_utc(value: str) -> bool:
    try:
        instant = datetime.fromisoformat(value)
        return instant.utcoffset() == timedelta(0)
    except (TypeError, ValueError):
        return False


def build_inventory(
    clone: Path,
    changes: list[dict[str, Any]],
    inspection: dict[str, Any],
    summary: dict[str, Any],
    taxonomy: FileTaxonomy,
    config: ResearchConfig,
) -> dict[str, Any]:
    """One normalized path per case; deleted paths resolve against the first parent."""
    observations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for change in changes:
        observations[change["file_path"]].append(
            {
                "commit_sha": change["commit_sha"],
                "blob_revision": change["parent_sha"]
                if change["change_type"] == "D"
                else change["commit_sha"],
            }
        )
    for row in inspection["files"]:
        observations[row["file_path"]].append(
            {
                "commit_sha": summary["head_commit_sha"],
                "blob_revision": summary["head_commit_sha"],
            }
        )
    units = []
    errors = []
    with Repo(clone) as repo:
        for path, candidates in sorted(observations.items()):
            normalized = PurePosixPath(path).as_posix()
            if normalized != path or ".." in PurePosixPath(path).parts or path.startswith("/"):
                raise ValueError("Noncanonical inventory path")
            representative = min(candidates, key=lambda r: (r["commit_sha"], r["blob_revision"]))
            try:
                blob = repo.commit(representative["blob_revision"]).tree / path
                blob_sha = blob.hexsha
                # Verify recoverability now, including historical deletions.
                blob.data_stream.read()
            except Exception as error:
                errors.append({"file_path": path, "error": str(error)})
                continue
            identity = f"{summary['repository_id']}:{path}"
            units.append(
                {
                    "unit_id": hashlib.sha256(identity.encode()).hexdigest(),
                    "repository_id": summary["repository_id"],
                    "head_commit_sha": summary["head_commit_sha"],
                    "file_path": path,
                    **representative,
                    "blob_sha": blob_sha,
                    "category": taxonomy.classify(path).value,
                    "taxonomy_version": taxonomy.config.version,
                    "historical_observations": len(candidates),
                    "calibration_used": identity in config.taxonomy_validation.calibration_units,
                }
            )
    return {
        "schema_version": "2.1.0",
        "complete": not errors,
        "errors": errors,
        "scope": "eligible historical paths plus frozen tree; renames as A/D",
        "cases": [
            {
                "repository_id": summary["repository_id"],
                "head_commit_sha": summary["head_commit_sha"],
            }
        ],
        "taxonomy_version": taxonomy.config.version,
        "units": units,
        "expected_unique_paths": len(observations),
    }


def make_sample(inventory: dict[str, Any], config: ResearchConfig) -> list[dict[str, Any]]:
    result = []
    quota = config.taxonomy_validation.samples_per_category
    for category in Category:
        candidates = [r for r in inventory["units"] if r["category"] == category.value]
        # Round-robin across cases before taking the quota: deterministic case coverage.
        by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in candidates:
            by_case[row["repository_id"]].append(row)
        ranked = []
        for repository, rows in sorted(by_case.items()):
            for position, row in enumerate(
                sorted(rows, key=lambda r: (r["calibration_used"], r["unit_id"]))
            ):
                ranked.append((row["calibration_used"], position, repository, row))
        for _, _, _, row in sorted(ranked, key=lambda x: x[:3])[:quota]:
            result.append(
                {**row, "source_unit_id": row["unit_id"], **dict.fromkeys(HUMAN_FIELDS, "")}
            )
    return result


def evaluate_review(
    path: Path,
    config: ResearchConfig,
    *,
    original: Path | None = None,
    inventory_path: Path | None = None,
) -> dict[str, Any]:
    rows = read_csv(path)
    categories = {item.value for item in Category}
    problems = []
    inventory = json.loads(inventory_path.read_text()) if inventory_path else None
    if not original or not inventory:
        problems.append("original_and_complete_inventory_required")
        source_rows = []
    else:
        source_rows = read_csv(original)
        expected = make_sample(inventory, config)

        # CSV normalizes scalar values; compare all immutable fields, not just labels.
        def immutable(row: dict[str, Any]) -> dict[str, str]:
            return {
                k: str(v).lower() if isinstance(v, bool) else str(v)
                for k, v in row.items()
                if k not in HUMAN_FIELDS
            }

        if [immutable(r) for r in source_rows] != [immutable(r) for r in expected] or [
            immutable(r) for r in rows
        ] != [immutable(r) for r in source_rows]:
            problems.append("sample_integrity_mismatch")
        if any(row.get(field) for row in source_rows for field in HUMAN_FIELDS):
            problems.append("source_is_not_blank")
        units = inventory["units"]
        identities = {(r["repository_id"], r["file_path"]) for r in units}
        if len(identities) != len(units) or len(units) != inventory["expected_unique_paths"]:
            problems.append("incomplete_or_duplicate_inventory")
        if not inventory["complete"] or inventory["errors"]:
            problems.append("incomplete_inventory")
        if any(
            r["category"] not in categories
            or r["taxonomy_version"] != inventory["taxonomy_version"]
            for r in units
        ):
            problems.append("inventory_taxonomy_mismatch")
    reviewed = [
        r
        for r in rows
        if r.get("expected_category") in categories
        and r.get("reviewer", "").strip()
        and valid_utc(r.get("reviewed_at_utc", ""))
        and (
            str(r.get("historical_observations", "1")).isdigit()
            and int(r.get("historical_observations", "1")) <= 1
            or r.get("role_change_review", "").strip()
        )
    ]
    if len(reviewed) != len(rows) or not rows:
        problems.append("incomplete_human_review")
    if len({(r["repository_id"], r["file_path"]) for r in rows}) != len(rows):
        problems.append("duplicate_sample_units")
    correct = sum(r["category"] == r["expected_category"] for r in reviewed)
    agreement = correct / len(reviewed) if reviewed else None
    if agreement is None or agreement < config.taxonomy_validation.minimum_agreement:
        problems.append("agreement_below_threshold")
    coverage = []
    for category in sorted(categories):
        population = [r for r in (inventory or {}).get("units", []) if r["category"] == category]
        selected = [r for r in reviewed if r["category"] == category]
        size = len(population)
        state = (
            "incomplete_inventory"
            if not inventory or not inventory["complete"]
            else "absent_in_validated_universe"
            if size == 0
            else "exhaustive_small_category"
            if size < config.taxonomy_validation.samples_per_category
            else "sampled_category"
        )
        if state == "sampled_category" and any(r["calibration_used"] == "true" for r in selected):
            problems.append(f"calibration_requires_additional_evaluation:{category}")
        coverage.append(
            {
                "category": category,
                "universe_count": size,
                "reviewed_count": len(selected),
                "required_count": min(size, config.taxonomy_validation.samples_per_category),
                "status": state,
                "agreement": sum(r["category"] == r["expected_category"] for r in selected)
                / len(selected)
                if selected
                else None,
                "calibration_overlap": sum(r.get("calibration_used") == "true" for r in selected),
            }
        )
    by_case = []
    for repository in sorted({r["repository_id"] for r in rows}):
        subset = [r for r in reviewed if r["repository_id"] == repository]
        by_case.append(
            {
                "repository_id": repository,
                "reviewed_count": len(subset),
                "agreement": sum(r["category"] == r["expected_category"] for r in subset)
                / len(subset)
                if subset
                else None,
            }
        )
    matrix = Counter((r["expected_category"], r["category"]) for r in reviewed)
    return {
        "accepted": not problems,
        "blocking_reasons": sorted(set(problems)),
        "sample_count": len(rows),
        "reviewed_count": len(reviewed),
        "agreement": agreement,
        "minimum_agreement": config.taxonomy_validation.minimum_agreement,
        "coverage": coverage,
        "by_case": by_case,
        "confusion_matrix": [
            {"expected_category": expected, "predicted_category": predicted, "count": count}
            for (expected, predicted), count in sorted(matrix.items())
        ],
        "cases": (inventory or {}).get("cases", []),
        "taxonomy_version": (inventory or {}).get("taxonomy_version"),
        "input_hashes": {
            "reviewed": sha256_file(path),
            "original": sha256_file(original) if original else None,
            "inventory": sha256_file(inventory_path) if inventory_path else None,
        },
    }
