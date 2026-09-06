"""Human review gate, separate from rule calibration and automated regression tests."""

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from mlops_traceability.config import ResearchConfig
from mlops_traceability.taxonomy import Category


def evaluate_review(path: Path, config: ResearchConfig) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    categories = {item.value for item in Category}
    reviewed = [
        row
        for row in rows
        if row.get("expected_category") in categories
        and row.get("reviewer", "").strip()
        and row.get("reviewed_at_utc", "").strip()
    ]
    counts = Counter(row["category"] for row in reviewed)
    correct = sum(row["category"] == row["expected_category"] for row in reviewed)
    agreement = correct / len(reviewed) if reviewed else None
    identities = {(row["repository_id"], row["head_commit_sha"], row["file_path"]) for row in rows}
    missing = {
        category: max(0, config.taxonomy_validation.samples_per_category - counts[category])
        for category in sorted(categories)
    }
    accepted = (
        bool(rows)
        and len(reviewed) == len(rows)
        and len(identities) == len(rows)
        and not any(missing.values())
        and agreement is not None
        and agreement >= config.taxonomy_validation.minimum_agreement
    )
    return {
        "accepted": accepted,
        "sample_count": len(rows),
        "reviewed_count": len(reviewed),
        "agreement": agreement,
        "missing_per_category": missing,
        "minimum_agreement": config.taxonomy_validation.minimum_agreement,
    }
