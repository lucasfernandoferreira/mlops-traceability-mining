from pathlib import Path

import pytest
from pydantic import ValidationError

from mlops_traceability.taxonomy import Category, load_taxonomy

TAXONOMY_PATH = Path("config/file_taxonomy.yaml")


@pytest.mark.parametrize(
    ("file_path", "expected_category"),
    [
        ("data/train.dvc", Category.DATA_META),
        ("dvc.yaml", Category.DATA_META),
        ("params.yaml", Category.CONFIG),
        ("config/config.yaml", Category.CONFIG),
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
