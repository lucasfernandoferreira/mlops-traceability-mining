"""Case-level descriptions; no independence assumption or inferential p-values."""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from typing import Any

import pandas as pd

from mlops_traceability.config import AnalysisConfig


def monthly_series(commits: list[dict[str, Any]], repository: str) -> list[dict[str, Any]]:
    eligible = [r for r in commits if r["eligibility_status"] == "included"]
    if not eligible:
        return []
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        month = pd.Timestamp(row["committed_at_utc"]).tz_convert("UTC").strftime("%Y-%m")
        groups[month].append(row)
    result: list[dict[str, Any]] = []
    for month in pd.period_range(min(groups), max(groups), freq="M"):
        code = [r for r in groups[str(month)] if r["C"]]
        numerator, denominator = sum(bool(r["P"]) for r in code), len(code)
        result.append(
            {
                "repository_id": repository,
                "month_utc": str(month),
                "numerator": numerator,
                "denominator": denominator,
                "value": numerator / denominator if denominator else None,
                "status": "observed" if denominator else "undefined",
            }
        )
    if sum(r["denominator"] for r in result) != sum(bool(r["C"]) for r in eligible) or sum(
        r["numerator"] for r in result
    ) != sum(bool(r["C"] and r["P"]) for r in eligible):
        raise ValueError("Monthly totals do not reconcile")
    return result


def distribution(
    commits: list[dict[str, Any]], repository: str, plan: AnalysisConfig
) -> dict[str, Any]:
    rows = [r for r in commits if r["eligibility_status"] == "included" and r["P"]]
    status = (
        "error"
        if any(r["config_semantic_status"] == "error" for r in rows)
        else "not_applicable"
        if any(r["config_semantic_status"] != "observed" for r in rows)
        else "observed"
        if rows
        else "undefined"
    )
    result: dict[str, Any] = {
        "repository_id": repository,
        "status": status,
        "denominator": len(rows),
        "unit": "keys/config_commit",
        "quantile_method": plan.quantile_method,
    }
    values = pd.Series([r["config_changed_keys"] for r in rows], dtype=float)
    for name in (
        "mean",
        "median",
        "p90",
        "p95",
        "maximum",
        "semantic_zero_fraction",
        "top_fraction_share",
    ):
        result[name] = None
    if status == "observed":
        result.update(
            mean=float(values.mean()),
            median=float(values.median()),
            p90=float(values.quantile(0.90, interpolation=plan.quantile_method)),
            p95=float(values.quantile(0.95, interpolation=plan.quantile_method)),
            maximum=float(values.max()),
            semantic_zero_fraction=float((values == 0).mean()),
            top_fraction_share=float(
                values.nlargest(math.ceil(len(values) * plan.concentration_top_fraction)).sum()
                / values.sum()
            )
            if values.sum()
            else None,
        )
    return result


def configuration_sensitivity(
    commits: list[dict[str, Any]],
    changes: list[dict[str, Any]],
    repository: str,
    plan: AnalysisConfig,
) -> list[dict[str, Any]]:
    principal = distribution(commits, repository, plan)
    rows = [r for r in changes if r["category"] == "CONFIG"]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["commit_sha"]].append(row)
    moved = set()
    for sha, files in grouped.items():
        additions: dict[str, list[str]] = defaultdict(list)
        deletions: dict[str, list[str]] = defaultdict(list)
        for row in files:
            if row["change_type"] == "A" and row.get("after_blob_sha"):
                additions[row["after_blob_sha"]].append(row["file_path"])
            if row["change_type"] == "D" and row.get("before_blob_sha"):
                deletions[row["before_blob_sha"]].append(row["file_path"])
        for blob in additions.keys() & deletions.keys():
            for added, deleted in zip(
                sorted(additions[blob]), sorted(deletions[blob]), strict=False
            ):
                moved.update({(sha, added), (sha, deleted)})
    reductions = {
        "identical_blob_moves": sum(
            r["changed_key_count"] or 0 for r in rows if (r["commit_sha"], r["file_path"]) in moved
        ),
        "class_map_keys": sum(
            sum(plan.class_map_key in json.loads(k) for k in r["changed_keys"]) for r in rows
        ),
        "dataset_paths": sum(
            r["changed_key_count"] or 0
            for r in rows
            if re.search(plan.dataset_path_pattern, r["file_path"])
        ),
    }
    total = sum(
        r["config_changed_keys"] or 0
        for r in commits
        if r["eligibility_status"] == "included" and r["P"]
    )
    result = []
    for variant, reduction in {"principal": 0, **reductions}.items():
        observed = principal["status"] == "observed"
        result.append(
            {
                "repository_id": repository,
                "variant": variant,
                "status": principal["status"],
                "numerator": total - reduction if observed else None,
                "denominator": principal["denominator"],
                "value": (total - reduction) / principal["denominator"] if observed else None,
                "removed_key_contribution": reduction if observed else None,
                "unit": "keys/config_commit",
                "paired_move_paths": len(moved),
                "rule": {
                    "principal": "all changed CONFIG keys; A/D preserved",
                    "identical_blob_moves": (
                        "same-commit identical-blob A/D; lexicographic one-to-one"
                    ),
                    "class_map_keys": "exclude typed key component " + plan.class_map_key,
                    "dataset_paths": "exclude CONFIG paths matching " + plan.dataset_path_pattern,
                }[variant],
            }
        )
    return result
