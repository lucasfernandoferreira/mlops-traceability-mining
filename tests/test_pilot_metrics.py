from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import yaml

from mlops_traceability.config_diff import changed_keys, config_keys
from mlops_traceability.manifest import build_artifact
from mlops_traceability.metrics_gqm import compute_metrics
from mlops_traceability.mining import static_calls


@pytest.mark.parametrize(
    "path,before,after,expected",
    [
        ("cfg/a.yaml", b"x: 1\nnested: {a: 2}\n", b"# comment\nx: 1\nnested: {a: 3}\n", 1),
        ("params.yml", b"x: 1\ny: 2\n", b"y: 2\nx: 1\n", 0),
        ("config.json", b'{"a":true}', b'{"a":1}', 1),
        ("config.toml", b"[model]\nx=1\n", b"[model]\nx=2\n", 1),
        ("MLproject", None, b"name: training", 1),
        ("params.yaml", b"x: [1, 2]", b"x: [1, 2, 3]", 1),
        ("params.yaml", b"x: 1", None, 1),
        ("params.yaml", b"{}", b"{}", 0),
        ("params.yaml", b"", b"", 0),
        ("params.yaml", b"date: 2026-01-01", b"date: 2026-01-02", 1),
    ],
)
def test_semantic_differences(
    path: str, before: bytes | None, after: bytes | None, expected: int
) -> None:
    assert len(changed_keys(before, after, path)) == expected


@pytest.mark.parametrize(
    "path,content,error",
    [
        ("a.yaml", b"x: 1\nx: 2", ValueError),
        ("a.json", b'{"x": 1, "x": 2}', ValueError),
        ("a.ini", b"x=1", NotImplementedError),
        ("a.yaml", b"x: &loop {a: *loop}", yaml.YAMLError),
        ("a.yaml", b"\xff", UnicodeDecodeError),
    ],
)
def test_semantic_ambiguity_fails(path: str, content: bytes, error: type[Exception]) -> None:
    with pytest.raises(error):
        config_keys(content, path)


def test_binary_manifest_and_legacy_text(tmp_path: Path) -> None:
    path = tmp_path / "commits.parquet"
    pd.DataFrame({"sha": ["abc"], "count": [1]}).to_parquet(path)
    artifact = build_artifact(path)
    assert artifact.line_count is None and artifact.byte_count == path.stat().st_size
    path = tmp_path / "binary.dat"
    path.write_bytes(b"\xff\x00")
    assert build_artifact(path).line_count is None
    path.write_text("one\ntwo\n")
    assert build_artifact(path).line_count == 2


def test_import_aliases_and_artifacts_are_candidates() -> None:
    source = b"""import mlflow as mf
from mlflow import log_param as lp
import mlflow.sklearn
mf.log_artifact("weights.pt")
lp("a", 1)
mlflow.sklearn.log_model(model)
other.log_model(model)
"mlflow.log_model(model)"
get_logger().log_model(model)
"""
    calls = static_calls(source)
    assert [r["call"] for r in calls] == [
        "mlflow.log_artifact",
        "mlflow.log_param",
        "mlflow.sklearn.log_model",
    ]
    assert [r["line"] for r in calls] == [4, 5, 6]


def calculate(
    commits: list[dict[str, Any]], parse_errors: list[Any] | None = None
) -> dict[str, Any]:
    summary = {
        "repository_id": "test/repo",
        "head_commit_sha": "a" * 40,
        "period_start_utc": "2026-01-01T00:00:00Z",
        "period_end_utc": "2026-01-02T00:00:00Z",
    }
    inspection = {
        "runtime_evidence_detail": "Not collected",
        "parse_errors": parse_errors or [],
        "calls": [
            {"operation": "log_artifact", "category": "CODE"},
            {"operation": "log_artifact", "category": "TEST"},
        ],
    }
    return {
        r["metric_id"]: r
        for r in compute_metrics(
            commits, summary, inspection, protocol_version="2", taxonomy_version="1", run_id="test"
        )
    }


def test_denominators_absence_and_static_are_separate() -> None:
    commits = [
        {
            "eligibility_status": "included",
            "C": True,
            "P": True,
            "config_semantic_status": "observed",
            "config_changed_keys": 3,
        },
        {"eligibility_status": "included", "C": True, "P": False},
        {"eligibility_status": "merge", "C": True, "P": True},
    ]
    rows = calculate(commits)
    assert rows["code_config_cochange"]["value"] == 0.5
    assert rows["code_config_cochange"]["excluded_commit_count"] == 1
    assert rows["config_magnitude"]["value"] == 3
    assert rows["static_mlflow_artifact_calls"]["value"] == 1
    assert rows["static_mlflow_model_calls"]["value"] == 0
    for name in ("cace_index", "experiment_redundancy", "data_code_ratio_original"):
        assert rows[name]["status"] == "not_available"
        assert rows[name]["value"] is None
    assert calculate([])["code_config_cochange"]["status"] == "undefined"
    assert calculate([], ["syntax error"])["static_mlflow_model_calls"]["status"] == "error"
    for semantic, expected in (("error", "error"), ("not_applicable", "not_applicable")):
        commits[0]["config_semantic_status"] = semantic
        rows = calculate(commits)
        assert rows["config_magnitude"]["status"] == expected
        assert rows["config_magnitude"]["value"] is None
