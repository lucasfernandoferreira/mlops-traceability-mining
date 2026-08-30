"""Classificação taxonômica de artefatos versionados.

A classificação é mutuamente exclusiva e utiliza a primeira regra
correspondente à ordem declarada no YAML.
"""

import re
from enum import StrEnum
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Category(StrEnum):
    DATA_META = "DATA_META"
    CONFIG = "CONFIG"
    ENV = "ENV"
    CI = "CI"
    TEST = "TEST"
    NOTEBOOK = "NOTEBOOK"
    CODE = "CODE"
    DOC = "DOC"
    DATA_RAW = "DATA_RAW"
    OUTRO = "OUTRO"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TaxonomyRule(StrictModel):
    category: Category
    description: str
    patterns: list[str]

    @field_validator("patterns")
    @classmethod
    def validate_regular_expressions(cls, patterns: list[str]) -> list[str]:
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as error:
                raise ValueError(f"Regex inválido {pattern!r}: {error}") from error

        return patterns


class TaxonomyConfig(StrictModel):
    version: str = Field(min_length=1)
    default_category: Category
    rules: list[TaxonomyRule] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_categories(self) -> Self:
        categories = [rule.category for rule in self.rules]

        if len(categories) != len(set(categories)):
            raise ValueError("Cada categoria deve aparecer apenas uma vez")

        return self


class FileTaxonomy:
    """Classificador ordenado de caminhos de arquivos."""

    def __init__(self, config: TaxonomyConfig) -> None:
        self.config = config
        self._compiled_rules = [
            (
                rule.category,
                [re.compile(pattern, flags=re.IGNORECASE) for pattern in rule.patterns],
            )
            for rule in config.rules
        ]

    def classify(self, file_path: str) -> Category:
        normalized_path = file_path.replace("\\", "/").removeprefix("./")

        for category, patterns in self._compiled_rules:
            if any(pattern.search(normalized_path) for pattern in patterns):
                return category

        return self.config.default_category


def load_taxonomy(path: str | Path) -> FileTaxonomy:
    taxonomy_path = Path(path)

    if not taxonomy_path.is_file():
        raise FileNotFoundError(f"Taxonomia não encontrada: {taxonomy_path}")

    with taxonomy_path.open("r", encoding="utf-8") as stream:
        raw_taxonomy = yaml.safe_load(stream)

    if not isinstance(raw_taxonomy, dict):
        raise ValueError("A raiz de file_taxonomy.yaml deve ser um objeto YAML")

    config = TaxonomyConfig.model_validate(raw_taxonomy)
    return FileTaxonomy(config)
