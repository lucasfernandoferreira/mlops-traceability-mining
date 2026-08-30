"""Carregamento e validação do protocolo executável da pesquisa.

Este módulo impede que limiares metodológicos sejam definidos diretamente
nos scripts de coleta ou mineração.
"""

from datetime import datetime
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Base que rejeita campos não previstos no protocolo."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ProtocolConfig(StrictModel):
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)


class PathsConfig(StrictModel):
    raw_repositories: Path
    interim: Path
    processed: Path
    manifests: Path
    reports: Path


class GitHubConfig(StrictModel):
    token_environment_variable: str = Field(min_length=1)
    minimum_remaining_requests: int = Field(ge=0)
    queries: list[str] = Field(min_length=1)


class SelectionConfig(StrictModel):
    min_candidates: int = Field(gt=0)
    min_commits: int = Field(gt=0)
    min_contributors: int = Field(gt=0)
    min_stars: int = Field(ge=0)
    active_after: datetime
    min_shortlist: int = Field(gt=0)
    final_sample_min: int = Field(gt=0)
    final_sample_max: int = Field(gt=0)
    forbidden_terms: list[str]

    @model_validator(mode="after")
    def validate_sample_sizes(self) -> Self:
        if self.final_sample_min > self.final_sample_max:
            raise ValueError("final_sample_min não pode ser maior que final_sample_max")

        if self.min_shortlist < self.final_sample_max:
            raise ValueError("min_shortlist deve ser maior ou igual a final_sample_max")

        return self


Stratum = Literal["apenas_dvc", "apenas_mlflow", "dvc_e_mlflow"]


class StrataConfig(StrictModel):
    required: list[Stratum] = Field(min_length=1)


class CommitFilterConfig(StrictModel):
    exclude_merges: bool
    exclude_bots: bool
    large_commit_max_files: int = Field(gt=0)
    large_commit_action: Literal["flag_only", "flag_and_skip"]
    bot_patterns: list[str] = Field(min_length=1)


class TaxonomyValidationConfig(StrictModel):
    samples_per_category: int = Field(gt=0)
    minimum_agreement: float = Field(ge=0, le=1)


class ReproducibilityConfig(StrictModel):
    require_clean_worktree: bool
    save_manifests: bool
    hash_algorithm: Literal["sha256"]


class ResearchConfig(StrictModel):
    protocol: ProtocolConfig
    paths: PathsConfig
    github: GitHubConfig
    selection: SelectionConfig
    strata: StrataConfig
    commit_filter: CommitFilterConfig
    taxonomy_validation: TaxonomyValidationConfig
    reproducibility: ReproducibilityConfig


def load_config(path: str | Path) -> ResearchConfig:
    """Carrega e valida integralmente o protocolo da pesquisa."""

    config_path = Path(path)

    if not config_path.is_file():
        raise FileNotFoundError(f"Configuração não encontrada: {config_path}")

    with config_path.open("r", encoding="utf-8") as stream:
        raw_config = yaml.safe_load(stream)

    if not isinstance(raw_config, dict):
        raise ValueError("A raiz de config.yaml deve ser um objeto YAML")

    return ResearchConfig.model_validate(raw_config)
