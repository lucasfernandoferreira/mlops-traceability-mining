from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from mlops_traceability.config import load_config

CONFIG_PATH = Path("config/config.yaml")


def test_load_valid_config() -> None:
    config = load_config(CONFIG_PATH)

    assert config.protocol.id == "TCC-MLOPS-TRACE-2026"
    assert config.selection.min_commits == 300
    assert config.selection.min_shortlist == 10
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
