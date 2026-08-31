from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from mlops_traceability.config import load_config

CONFIG_PATH = Path("config/config.yaml")


def test_load_valid_config() -> None:
    config = load_config(CONFIG_PATH)

    assert config.protocol.id == "TCC-MLOPS-TRACE-2026"
    assert config.protocol.version == "1.4.0"
    assert config.execution.screening_workers == 4
    assert config.execution.progress_interval_seconds == 10
    assert config.github.per_page == 100
    assert config.github.max_results_per_query == 1000
    assert config.github.request_timeout_seconds == 30
    assert config.github.rate_limit.code_search_reserve == 1
    assert config.github.rate_limit.core_reserve == 50
    assert config.github.queries[0].id == "dvc_pipeline"
    assert config.github.queries[0].expression == "filename:dvc.yaml"
    assert config.selection.min_shortlist == 10
    assert config.selection.max_shortlist == 200
    assert config.selection.exclude_forks is True
    assert config.taxonomy_validation.minimum_agreement == 0.95


def test_reject_unknown_fields(tmp_path: Path) -> None:
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    raw["selection"]["unknown_threshold"] = 123

    target = tmp_path / "config.yaml"
    target.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_config(target)


def test_reject_invalid_sample_interval(tmp_path: Path) -> None:
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    raw["selection"]["final_sample_min"] = 6
    raw["selection"]["final_sample_max"] = 5

    target = tmp_path / "config.yaml"
    target.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_config(target)


def test_reject_missing_methodological_threshold(tmp_path: Path) -> None:
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    del raw["selection"]["min_commits"]

    target = tmp_path / "config.yaml"
    target.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_config(target)


def test_reject_duplicate_query_ids(tmp_path: Path) -> None:
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    raw["github"]["queries"][1]["id"] = raw["github"]["queries"][0]["id"]

    target = tmp_path / "config.yaml"
    target.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ValidationError):
        load_config(target)
