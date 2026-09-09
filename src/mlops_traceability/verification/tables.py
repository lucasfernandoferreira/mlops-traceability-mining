"""Lossless transport normalization for nullable Parquet integers and CSV cells."""

from __future__ import annotations

import csv
import math
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd

INTEGER_FIELDS = {
    "numerator",
    "denominator",
    "config_changed_keys",
    "changed_key_count",
    "parent_count",
    "files_changed_count",
    "group_position",
    "selection_position",
    "config_magnitude",
    "paired_move_paths",
    "removed_key_contribution",
}
FLOAT_FIELDS = {
    "value",
    "mean",
    "median",
    "p90",
    "p95",
    "maximum",
    "semantic_zero_fraction",
    "top_fraction_share",
}


def read_table(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".parquet":
        rows = pd.read_parquet(path).to_dict("records")
    else:
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
    result = []
    for row in rows:
        normalized = {}
        for key, value in row.items():
            if hasattr(value, "tolist"):
                value = value.tolist()
            if key in INTEGER_FIELDS | FLOAT_FIELDS:
                if value is None or value == "" or (isinstance(value, float) and math.isnan(value)):
                    value = None
                elif key in INTEGER_FIELDS:
                    if isinstance(value, bool):
                        raise ValueError(f"Boolean is not an integer count: {key}")
                    if isinstance(value, float) and (
                        not math.isfinite(value) or not value.is_integer()
                    ):
                        raise ValueError(f"Noninteger count: {key}")
                    if isinstance(value, str):
                        try:
                            number = Decimal(value)
                        except InvalidOperation as error:
                            raise ValueError(f"Invalid integer count: {key}") from error
                        if not number.is_finite() or number != number.to_integral_value():
                            raise ValueError(f"Noninteger count: {key}")
                        value = int(number)
                    else:
                        value = int(value)
                else:
                    value = float(value)
                    if not math.isfinite(value):
                        raise ValueError(f"Nonfinite metric: {key}")
            normalized[key] = value
        result.append(normalized)
    return result
