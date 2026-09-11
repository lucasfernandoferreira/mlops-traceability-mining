import csv
from pathlib import Path

import pytest
from pydantic import ValidationError

from mlops_traceability.config import load_config
from mlops_traceability.taxonomy import Category, load_taxonomy

TAXONOMY_PATH = Path("config/file_taxonomy.yaml")
CALIBRATION_PATH = Path("docs/evidencias/taxonomia_calibracao_1_2_0.csv")


@pytest.mark.parametrize(
    ("file_path", "expected_category"),
    [
        ("data/train.dvc", Category.DATA_META),
        ("dvc.yaml", Category.DATA_META),
        ("params.yaml", Category.CONFIG),
        ("config/config.yaml", Category.CONFIG),
        ("ultralytics/cfg/default.yaml", Category.CONFIG),
        ("data/config_files/basic_model.yml", Category.CONFIG),
        ("examples/configs/model/patchcore.yaml", Category.CONFIG),
        ("tests/configs/model.yaml", Category.TEST),
        (".github/workflows/config.yaml", Category.CI),
        ("configs/environment.yaml", Category.ENV),
        ("configs/dvc.yaml", Category.DATA_META),
        ("configs/train.py", Category.CODE),
        ("configs/readme.md", Category.DOC),
        ("data/unrelated.yaml", Category.OUTRO),
        ("requirements-dev.txt", Category.ENV),
        ("docker/Dockerfile", Category.ENV),
        (".github/workflows/ci.yml", Category.CI),
        ("tests/test_pipeline.py", Category.TEST),
        ("notebooks/exploration.ipynb", Category.NOTEBOOK),
        ("src/training.py", Category.CODE),
        ("docs/methodology.md", Category.DOC),
        ("data/observations.parquet", Category.DATA_RAW),
        ("LICENSE", Category.OUTRO),
    ],
)
def test_classify_representative_paths(
    file_path: str,
    expected_category: Category,
) -> None:
    taxonomy = load_taxonomy(TAXONOMY_PATH)

    assert taxonomy.classify(file_path) == expected_category


def test_taxonomy_version_is_1_2_0() -> None:
    assert load_taxonomy(TAXONOMY_PATH).config.version == "1.2.0"


# DM-027: each 1.1.0 divergence mechanism plus a guard against its nearest false positive.
@pytest.mark.parametrize(
    ("file_path", "expected_category"),
    [
        ("examples/cpp/common/yolo_show.hpp", Category.CODE),
        ("examples/cli/04_advanced/custom_components.sh", Category.CODE),
        ("application/ui/src/features/inspect/dataset/media-preview/hooks/util.tsx", Category.CODE),
        ("application/ui/src/features/inspect/models-list/model-list.module.scss", Category.OUTRO),
        ("locales/es/LC_MESSAGES/api/generated/pymc_marketing.mmm.causal.TBFPC.po", Category.OUTRO),
        ("docker/Dockerfile-nvidia-cuda", Category.ENV),
        ("application/docker/docker-compose.cuda.yaml", Category.ENV),
        ("scripts/docker/environment-dev.yml", Category.ENV),
        ("application/binary/tauri/package-lock.json", Category.ENV),
        ("setup.py", Category.ENV),
        ("application/backend/src/core/logging/setup.py", Category.CODE),
        ("notebooks/500_use_cases/501_dobot/cubes_config.yaml", Category.CONFIG),
        (".pre-commit-config.yaml", Category.OUTRO),
        ("application/ui/tsconfig.json", Category.OUTRO),
        ("ultralytics/models/v3/yolov3-tiny.yaml", Category.CONFIG),
        ("ultralytics/yolo/data/datasets/xView.yaml", Category.CONFIG),
        (".github/ISSUE_TEMPLATE/bug-report.yml", Category.OUTRO),
        ("docs/source/notebooks/mmm/multidimensional_model.nc", Category.DATA_RAW),
        ("docs/images/architecture.png", Category.DOC),
        ("application/ui/src/assets/background.png", Category.OUTRO),
        ("application/binary/tauri/src-tauri/icons/icon.png", Category.OUTRO),
        ("ultralytics/assets/bus.jpg", Category.DATA_RAW),
    ],
)
def test_taxonomy_1_2_0_divergence_rules(file_path: str, expected_category: Category) -> None:
    assert load_taxonomy(TAXONOMY_PATH).classify(file_path) == expected_category


def calibration_rows() -> list[dict[str, str]]:
    with CALIBRATION_PATH.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_taxonomy_reproduces_human_calibration_labels() -> None:
    taxonomy = load_taxonomy(TAXONOMY_PATH)
    rows = calibration_rows()

    assert len(rows) == 180
    assert sum(r["category_1_1_0"] == r["expected_category"] for r in rows) == 164
    mismatches = [r for r in rows if taxonomy.classify(r["file_path"]) != r["expected_category"]]
    assert mismatches == []


def test_reviewed_units_are_calibration_units() -> None:
    configured = load_config("config/config.yaml").taxonomy_validation.calibration_units
    reviewed = {f"{r['repository_id']}:{r['file_path']}" for r in calibration_rows()}

    assert len(configured) == len(set(configured))
    assert reviewed <= set(configured)
    assert set(configured) - reviewed == {"ultralytics/ultralytics:ultralytics/cfg/default.yaml"}


def test_first_matching_rule_has_precedence() -> None:
    taxonomy = load_taxonomy(TAXONOMY_PATH)

    assert taxonomy.classify("tests/README.md") == Category.TEST
    assert taxonomy.classify("tests/fixtures/sample.csv") == Category.TEST


def test_classification_normalizes_windows_and_relative_paths() -> None:
    taxonomy = load_taxonomy(TAXONOMY_PATH)

    assert taxonomy.classify(r"tests\test_pipeline.py") == Category.TEST
    assert taxonomy.classify("./.github/workflows/ci.yml") == Category.CI


def test_classification_is_case_insensitive() -> None:
    taxonomy = load_taxonomy(TAXONOMY_PATH)

    assert taxonomy.classify("DOCS/METHODOLOGY.MD") == Category.DOC
    assert taxonomy.classify("DATA/OBSERVATIONS.PARQUET") == Category.DATA_RAW


def test_reject_missing_taxonomy_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.yaml"

    with pytest.raises(FileNotFoundError, match="Taxonomia não encontrada"):
        load_taxonomy(missing_path)


@pytest.mark.parametrize("yaml_content", ["- not\n- an\n- object\n", "null\n"])
def test_reject_non_mapping_yaml_root(tmp_path: Path, yaml_content: str) -> None:
    target = tmp_path / "taxonomy.yaml"
    target.write_text(yaml_content, encoding="utf-8")

    with pytest.raises(ValueError, match="deve ser um objeto YAML"):
        load_taxonomy(target)


def test_reject_invalid_regular_expression(tmp_path: Path) -> None:
    target = tmp_path / "taxonomy.yaml"
    target.write_text(
        """\
version: "1.0.0"
default_category: "OUTRO"
rules:
  - category: "CODE"
    description: "Invalid test rule."
    patterns: ["["]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="Regex inválido"):
        load_taxonomy(target)


def test_reject_duplicate_categories(tmp_path: Path) -> None:
    target = tmp_path / "taxonomy.yaml"
    target.write_text(
        """\
version: "1.0.0"
default_category: "OUTRO"
rules:
  - category: "CODE"
    description: "First code rule."
    patterns: ["[.]py$"]
  - category: "CODE"
    description: "Duplicate code rule."
    patterns: ["[.]r$"]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="Cada categoria deve aparecer apenas uma vez"):
        load_taxonomy(target)


def test_reject_unknown_fields(tmp_path: Path) -> None:
    target = tmp_path / "taxonomy.yaml"
    target.write_text(
        """\
version: "1.0.0"
default_category: "OUTRO"
unknown_setting: true
rules:
  - category: "CODE"
    description: "Code rule."
    patterns: ["[.]py$"]
""",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        load_taxonomy(target)
