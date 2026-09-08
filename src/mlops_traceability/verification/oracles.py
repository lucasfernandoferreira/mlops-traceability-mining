"""Independent arithmetic, without production metrics, diff, mining or selection imports.

This checks tables, not their correspondence to Git. Python integer arithmetic is
shared with the instrument; the extraction/source oracle remains a separate gate.
"""

from __future__ import annotations

import math
import sqlite3
from collections import Counter
from typing import Any

UNAVAILABLE = {
    "data_code_ratio_original",
    "data_code_cochange",
    "cace_index",
    "provenance_coverage",
    "env_versioning_rate",
    "experiment_redundancy",
}


def arithmetic(rows: list[dict[str, Any]]) -> dict[str, Any]:
    identities = [(r["repository_id"], r["commit_sha"]) for r in rows]
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate commit SHA")
    if len({r["repository_id"] for r in rows}) > 1:
        raise ValueError("Arithmetic must be assessed per case")
    funnel: Counter[str] = Counter()
    code = config = joint = keys = 0
    semantic: set[str] = set()
    for row in rows:
        status = row["eligibility_status"]
        if status not in {"included", "bot", "merge", "large_commit"}:
            raise ValueError(f"Unknown eligibility status: {status}")
        funnel[status] += 1
        if status != "included":
            continue
        if type(row["C"]) is not bool or type(row["P"]) is not bool:
            raise ValueError("C/P flags must be booleans")
        code += int(row["C"])
        config += int(row["P"])
        joint += int(row["C"] and row["P"])
        if row["P"]:
            semantic.add(row["config_semantic_status"])
            if row["config_semantic_status"] == "observed":
                count = row["config_changed_keys"]
                if type(count) is not int or count < 0:
                    raise ValueError("CONFIG key count must be a nonnegative integer")
                keys += count
    if semantic - {"observed", "error", "not_applicable"}:
        raise ValueError("Unknown CONFIG semantic status")
    magnitude_status = (
        "error"
        if "error" in semantic
        else "not_applicable"
        if "not_applicable" in semantic
        else "observed"
        if config
        else "undefined"
    )
    magnitude_numerator = None if semantic & {"error", "not_applicable"} else keys
    return {
        "reachable": len(rows),
        "funnel": dict(sorted(funnel.items())),
        "C": code,
        "P": config,
        "C_intersection_P": joint,
        "metrics": {
            "code_config_cochange": {
                "numerator": joint,
                "denominator": code,
                "status": "observed" if code else "undefined",
                "value": joint / code if code else None,
            },
            "config_magnitude": {
                "numerator": magnitude_numerator,
                "denominator": config,
                "status": magnitude_status,
                "value": keys / config if magnitude_status == "observed" else None,
            },
        },
    }


def compare_metrics(
    expected: dict[str, Any], measured: list[dict[str, Any]], *, tolerance: float = 1e-12
) -> list[str]:
    """Exact integer components and states, absolute float tolerance; no editorial rounding."""
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Invalid tolerance")
    ids = [r["metric_id"] for r in measured]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate metric")
    actual = {r["metric_id"]: r for r in measured}
    problems = []
    targets = {
        **expected["metrics"],
        **{
            name: dict(status="not_available", numerator=None, denominator=None, value=None)
            for name in UNAVAILABLE
        },
    }
    for name, target in targets.items():
        if name not in actual:
            problems.append(f"{name}:missing")
            continue
        for field in ("status", "numerator", "denominator", "value"):
            if field not in actual[name]:
                problems.append(f"{name}:{field}:missing")
                continue
            value, wanted = actual[name].get(field), target[field]
            if field == "value" and wanted is not None:
                matches = (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    and abs(value - wanted) <= tolerance
                )
            else:
                matches = type(value) is type(wanted) and value == wanted
            if not matches:
                problems.append(f"{name}:{field}")
    return problems


def taxonomy_tally(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Recount validated raw human labels in SQL, independently of evaluate_review."""
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE labels (repository TEXT, human TEXT, predicted TEXT)")
        connection.executemany(
            "INSERT INTO labels VALUES (?, ?, ?)",
            [(r["repository_id"], r["expected_category"], r["category"]) for r in rows],
        )
        correct, size = connection.execute(
            "SELECT COALESCE(SUM(human = predicted), 0), COUNT(*) FROM labels"
        ).fetchone()
        matrix = connection.execute(
            "SELECT human, predicted, COUNT(*) FROM labels "
            "GROUP BY human, predicted ORDER BY human, predicted"
        ).fetchall()
        by_case = connection.execute(
            "SELECT repository, human, predicted, COUNT(*) FROM labels "
            "GROUP BY repository, human, predicted ORDER BY repository, human, predicted"
        ).fetchall()
        return {
            "agreement_numerator": correct,
            "agreement_denominator": size,
            "confusion_matrix": [
                dict(expected_category=human, predicted_category=predicted, count=count)
                for human, predicted, count in matrix
            ],
            "by_case": [
                dict(
                    repository_id=repo,
                    expected_category=human,
                    predicted_category=predicted,
                    count=count,
                )
                for repo, human, predicted, count in by_case
            ],
        }
    finally:
        connection.close()
