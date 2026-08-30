"""Orquestrador da Fase 1: busca paginada e geração dos candidatos brutos."""

from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mlops_traceability.config import load_config
from mlops_traceability.github_search import (
    PyGithubSearchGateway,
    SearchCollection,
    collect_candidates,
)
from mlops_traceability.manifest import (
    ManifestArtifact,
    build_artifact,
    start_run,
    write_manifest,
)


def _format_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return _format_datetime(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return value


def _row_to_csv_dict(row: Any) -> dict[str, Any]:
    data = asdict(row)
    return {key: _serialize_value(value) for key, value in data.items()}


def _write_csv_atomic(path: Path, fieldnames: list[str], rows: Sequence[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow(_row_to_csv_dict(row))

    os.replace(temp_path, path)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    os.replace(temp_path, path)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _build_artifacts(paths: list[Path]) -> list[ManifestArtifact]:
    return [build_artifact(path) for path in paths]


def _artifact_payload(path: Path) -> dict[str, Any]:
    artifact = build_artifact(path)
    return {
        "path": str(path.as_posix()),
        "sha256": artifact.sha256,
        "line_count": artifact.line_count,
    }


def _build_execution_report(
    *,
    run_id: str,
    started_at_utc: datetime,
    finished_at_utc: datetime,
    config_path: Path,
    candidates_path: Path,
    evidences_path: Path,
    summary_path: Path,
    collection: SearchCollection,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "stage": "phase1_search_candidates",
        "started_at_utc": _format_datetime(started_at_utc),
        "finished_at_utc": _format_datetime(finished_at_utc),
        "candidate_count": len(collection.candidates),
        "evidence_count": len(collection.evidences),
        "query_count": len(collection.summaries),
        "truncated_query_count": sum(1 for row in collection.summaries if row.truncated),
        "incomplete_query_count": sum(1 for row in collection.summaries if row.incomplete_results),
        "queries": [
            {
                "query_id": row.query_id,
                "reported_total_count": row.reported_total_count,
                "retrieved_hit_count": row.retrieved_hit_count,
                "unique_repository_count": row.unique_repository_count,
                "incomplete_results": row.incomplete_results,
                "truncated": row.truncated,
            }
            for row in collection.summaries
        ],
        "artifacts": [
            _artifact_payload(candidates_path),
            _artifact_payload(evidences_path),
            _artifact_payload(summary_path),
        ],
        "status": "SUCCESS",
    }


def main() -> int:
    root = _project_root()
    config_path = root / "config/config.yaml"
    taxonomy_path = root / "config/file_taxonomy.yaml"
    requirements_path = root / "requirements.txt"

    config = load_config(config_path)
    context = start_run(project_root=root, stage="phase1_search_candidates")

    manifest_path: Path | None = None

    try:
        if config.reproducibility.require_clean_worktree and context.dirty_worktree:
            raise RuntimeError(
                "A execução científica exige um worktree limpo. "
                "Faça commit ou registre explicitamente a alteração antes de executar."
            )

        token_name = config.github.token_environment_variable
        token = os.getenv(token_name)
        if not token:
            raise RuntimeError(
                f"Variável {token_name} não definida.\n"
                "Exporte um token de leitura antes de executar make search."
            )

        gateway = PyGithubSearchGateway(
            token=token,
            per_page=config.github.per_page,
            request_timeout_seconds=config.github.request_timeout_seconds,
        )
        observed_at_utc = datetime.now(UTC)
        collection: SearchCollection = collect_candidates(
            gateway,
            config.github.queries,
            per_page=config.github.per_page,
            max_results_per_query=config.github.max_results_per_query,
            observed_at_utc=observed_at_utc,
            run_id=context.run_id,
            rate_limit_reserve=config.github.rate_limit.code_search_reserve,
            reset_buffer_seconds=config.github.rate_limit.reset_buffer_seconds,
        )

        if len(collection.candidates) < config.selection.min_candidates:
            raise RuntimeError(
                f"A coleta produziu apenas {len(collection.candidates)} candidatos "
                f"e o mínimo exigido é {config.selection.min_candidates}."
            )

        interim_dir = root / config.paths.interim
        candidates_path = interim_dir / "candidatos_brutos.csv"
        evidences_path = interim_dir / "evidencias_busca.csv"
        summary_path = interim_dir / "resumo_busca.csv"
        report_path = interim_dir / "resumo_execucao_fase1.json"

        _write_csv_atomic(
            candidates_path,
            [
                "repository_numeric_id",
                "repository_id",
                "repository_url",
                "owner_login",
                "is_fork",
                "description",
                "discovery_query_count",
                "discovery_hit_count",
                "observed_at_utc",
                "run_id",
            ],
            collection.candidates,
        )
        _write_csv_atomic(
            evidences_path,
            [
                "query_id",
                "query_expression",
                "page_number",
                "result_rank",
                "repository_numeric_id",
                "repository_id",
                "file_path",
                "file_sha",
                "file_url",
                "run_id",
            ],
            collection.evidences,
        )
        _write_csv_atomic(
            summary_path,
            [
                "query_id",
                "query_expression",
                "reported_total_count",
                "retrieved_hit_count",
                "unique_repository_count",
                "incomplete_results",
                "truncated",
                "started_at_utc",
                "finished_at_utc",
                "run_id",
            ],
            collection.summaries,
        )

        report_payload = _build_execution_report(
            run_id=context.run_id,
            started_at_utc=context.started_at_utc,
            finished_at_utc=datetime.now(UTC),
            config_path=config_path,
            candidates_path=candidates_path,
            evidences_path=evidences_path,
            summary_path=summary_path,
            collection=collection,
        )
        _write_json_atomic(report_path, report_payload)

        artifacts = _build_artifacts(
            [
                config_path,
                taxonomy_path,
                requirements_path,
                candidates_path,
                evidences_path,
                summary_path,
                report_path,
            ]
        )

        manifest_path = write_manifest(
            context=context,
            manifest_directory=root / config.paths.manifests,
            config_path=config_path,
            taxonomy_path=taxonomy_path,
            requirements_path=requirements_path,
            protocol_id=config.protocol.id,
            protocol_version=config.protocol.version,
            status="SUCCESS",
            artifacts=artifacts,
        )
    except Exception as error:
        manifest_path = write_manifest(
            context=context,
            manifest_directory=root / config.paths.manifests,
            config_path=config_path,
            taxonomy_path=taxonomy_path,
            requirements_path=requirements_path,
            protocol_id=config.protocol.id,
            protocol_version=config.protocol.version,
            status="FAILED",
            error=str(error),
        )
        print(str(error), file=sys.stderr)
        print(f"Manifesto de falha: {manifest_path}", file=sys.stderr)
        return 1

    print("Fase 1 concluída com sucesso.")
    print(f"Manifesto: {manifest_path}")
    print(f"Candidatos: {len(collection.candidates)}")
    print(f"Evidências: {len(collection.evidences)}")
    print(f"Consultas: {len(collection.summaries)}")
    print(f"Relatório: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
