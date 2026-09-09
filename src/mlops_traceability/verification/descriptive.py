"""Plain-Python descriptive reference, independent of pandas production aggregation."""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any


def describe(
    commits: list[dict[str, Any]],
    changes: list[dict[str, Any]],
    repository: str,
    plan: dict[str, Any],
) -> dict[str, Any]:
    if plan["quantile_method"] != "linear":
        raise ValueError("Only the declared linear quantiles are supported")
    eligible = [r for r in commits if r["eligibility_status"] == "included"]
    config = [r for r in eligible if r["P"]]
    states = {r["config_semantic_status"] for r in config}
    state = (
        "error"
        if "error" in states
        else "not_applicable"
        if states - {"observed"}
        else "observed"
        if config
        else "undefined"
    )
    distribution: dict[str, Any] = {
        "repository_id": repository,
        "status": state,
        "denominator": len(config),
        "unit": "keys/config_commit",
        "quantile_method": "linear",
        **dict.fromkeys(
            (
                "mean",
                "median",
                "p90",
                "p95",
                "maximum",
                "semantic_zero_fraction",
                "top_fraction_share",
            )
        ),
    }
    if state == "observed":
        values = sorted(r["config_changed_keys"] for r in config)
        total, size = sum(values), len(values)

        def quantile(p: float) -> float:
            point = (size - 1) * p
            low = math.floor(point)
            return float(values[low] + (values[math.ceil(point)] - values[low]) * (point - low))

        distribution.update(
            mean=total / size,
            median=quantile(0.5),
            p90=quantile(0.9),
            p95=quantile(0.95),
            maximum=float(values[-1]),
            semantic_zero_fraction=values.count(0) / size,
            top_fraction_share=sum(values[-math.ceil(size * plan["concentration_top_fraction"]) :])
            / total
            if total
            else None,
        )
    months: dict[int, list[int]] = {}
    for row in eligible:
        instant = datetime.fromisoformat(row["committed_at_utc"]).astimezone(UTC)
        month = instant.year * 12 + instant.month - 1
        counts = months.setdefault(month, [0, 0])
        counts[0] += int(row["C"] and row["P"])
        counts[1] += int(row["C"])
    series = []
    if months:
        for month in range(min(months), max(months) + 1):
            numerator, denominator = months.get(month, [0, 0])
            series.append(
                dict(
                    repository_id=repository,
                    month_utc=f"{month // 12:04}-{month % 12 + 1:02}",
                    numerator=numerator,
                    denominator=denominator,
                    value=numerator / denominator if denominator else None,
                    status="observed" if denominator else "undefined",
                )
            )
    files = [r for r in changes if r["category"] == "CONFIG"]
    additions: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in files:
        if row["change_type"] == "A" and row["after_blob_sha"]:
            additions[(row["commit_sha"], row["after_blob_sha"])].append(row["file_path"])
    for queue in additions.values():
        queue.sort(reverse=True)
    moved: set[tuple[str, str]] = set()
    for row in sorted(files, key=lambda r: (r["commit_sha"], r["file_path"])):
        queue = additions.get((row["commit_sha"], row["before_blob_sha"]), [])
        if row["change_type"] == "D" and queue:
            moved.update({(row["commit_sha"], row["file_path"]), (row["commit_sha"], queue.pop())})
    reductions = dict(principal=0, identical_blob_moves=0, class_map_keys=0, dataset_paths=0)
    for row in files:
        keys = row["changed_key_count"] or 0
        if (row["commit_sha"], row["file_path"]) in moved:
            reductions["identical_blob_moves"] += keys
        reductions["class_map_keys"] += sum(
            plan["class_map_key"] in json.loads(k) for k in row["changed_keys"]
        )
        if re.search(plan["dataset_path_pattern"], row["file_path"]):
            reductions["dataset_paths"] += keys
    total = sum(r["config_changed_keys"] or 0 for r in config)
    sensitivity = []
    for variant, reduction in reductions.items():
        observed = state == "observed"
        sensitivity.append(
            dict(
                repository_id=repository,
                variant=variant,
                status=state,
                numerator=total - reduction if observed else None,
                denominator=len(config),
                value=(total - reduction) / len(config) if observed else None,
                removed_key_contribution=reduction if observed else None,
                paired_move_paths=len(moved),
                unit="keys/config_commit",
            )
        )
    return dict(distribution=[distribution], months=series, sensitivity=sensitivity)
