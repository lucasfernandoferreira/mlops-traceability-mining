"""Orquestrador da Fase 2: triagem automática da amostra."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mlops_traceability.config import ResearchConfig, load_config
from mlops_traceability.github_search import SearchCandidateRow, SearchEvidenceRow
from mlops_traceability.manifest import build_artifact, start_run, write_manifest
from mlops_traceability.sample_screen import (
    GitHubScreeningGateway,
    ScreeningGateway,
    screen_candidates,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _format_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Datetime precisa conter fuso horário.")
    return parsed.astimezone(UTC)


def _parse_bool(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"Valor booleano inválido: {value!r}")


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return _format_datetime(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, tuple):
        return " | ".join(value)
    if value is None:
        return ""
    return value


def _write_csv_atomic(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
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
            writer.writerow({key: _serialize_value(value) for key, value in row.items()})

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


def _load_search_candidates(path: Path) -> list[SearchCandidateRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[SearchCandidateRow] = []
        for raw in reader:
            rows.append(
                SearchCandidateRow(
                    repository_numeric_id=int(raw["repository_numeric_id"]),
                    repository_id=raw["repository_id"],
                    repository_url=raw["repository_url"],
                    owner_login=raw["owner_login"],
                    is_fork=_parse_bool(raw["is_fork"]),
                    description=raw["description"] or None,
                    discovery_query_count=int(raw["discovery_query_count"]),
                    discovery_hit_count=int(raw["discovery_hit_count"]),
                    observed_at_utc=_parse_datetime(raw["observed_at_utc"]),
                    run_id=raw["run_id"],
                )
            )
    return rows


def _load_search_evidences(path: Path) -> list[SearchEvidenceRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[SearchEvidenceRow] = []
        for raw in reader:
            rows.append(
                SearchEvidenceRow(
                    query_id=raw["query_id"],
                    query_expression=raw["query_expression"],
                    page_number=int(raw["page_number"]),
                    result_rank=int(raw["result_rank"]),
                    repository_numeric_id=int(raw["repository_numeric_id"]),
                    repository_id=raw["repository_id"],
                    file_path=raw["file_path"],
                    file_sha=raw["file_sha"],
                    file_url=raw["file_url"],
                    run_id=raw["run_id"],
                )
            )
    return rows


def _build_gateway(config: ResearchConfig) -> ScreeningGateway:
    token_name = config.github.token_environment_variable
    token = os.getenv(token_name)
    if not token:
        raise RuntimeError(
            f"Variável {token_name} não definida. "
            "Exporte um token de leitura para executar a Fase 2."
        )

    return GitHubScreeningGateway(
        token=token,
        per_page=config.github.per_page,
        request_timeout_seconds=config.github.request_timeout_seconds,
        core_reserve=config.github.rate_limit.core_reserve,
        reset_buffer_seconds=config.github.rate_limit.reset_buffer_seconds,
    )


def _validate_single_run_id(rows: list[Any], *, label: str) -> str:
    run_ids = {row.run_id for row in rows}
    if len(run_ids) != 1:
        raise RuntimeError(
            f"{label} precisa conter um único run_id, mas foram encontrados: {sorted(run_ids)}"
        )
    return str(next(iter(run_ids)))


def _candidate_to_output_row(row: Any, source_run_id: str) -> dict[str, Any]:
    return {
        "repository_numeric_id": row.repository_numeric_id,
        "repository_id": row.repository_id,
        "repository_url": row.repository_url,
        "source_run_id": source_run_id,
        "screening_run_id": row.run_id,
        "observed_at_utc": row.observed_at_utc,
        "head_commit_sha": row.head_commit_sha,
        "stars_count": row.stars_count,
        "commit_count": row.commit_count,
        "contributor_count": row.contributor_count,
        "last_human_commit_at_utc": row.last_human_commit_at_utc,
        "dvc_detected": row.dvc_detected,
        "mlflow_detected": row.mlflow_detected,
        "mlruns_detected": row.mlruns_detected,
        "stratum": row.stratum,
        "cheap_gate_status": row.cheap_gate_status,
        "expensive_gate_status": row.expensive_gate_status,
        "decision": row.decision,
        "exclusion_stage": row.exclusion_stage,
        "primary_reason": row.primary_reason,
        "decision_reasons": row.decision_reasons,
        "error_detail": row.error_detail,
    }


def _funnel_rows(
    screened_rows: list[Any],
    *,
    source_run_id: str,
) -> list[dict[str, Any]]:
    return [_candidate_to_output_row(row, source_run_id) for row in screened_rows]


def _screening_summary(
    *,
    candidates: list[SearchCandidateRow],
    screened_rows: list[Any],
    source_run_id: str,
    screening_run_id: str,
    input_run_ids_match: bool,
    config: Any,
    input_artifacts: list[dict[str, Any]],
    output_artifacts: list[dict[str, Any]],
    worktree_clean: bool,
) -> dict[str, Any]:
    decisions = Counter(row.decision for row in screened_rows)
    discard_reasons = Counter(
        reason
        for row in screened_rows
        if row.decision != "eligible"
        for reason in row.decision_reasons
    )
    strata_distribution = Counter(
        row.stratum
        for row in screened_rows
        if row.decision == "eligible" and row.stratum is not None
    )
    eligible_rows = [row for row in screened_rows if row.decision == "eligible"]
    gates = {
        "worktree_clean": worktree_clean,
        "input_run_ids_match": input_run_ids_match,
        "shortlist_bounds": config.selection.min_shortlist
        <= len(eligible_rows)
        <= config.selection.max_shortlist,
        "required_strata_present": all(
            required in {row.stratum for row in eligible_rows if row.stratum is not None}
            for required in config.strata.required
        ),
        "mlruns_evaluated_on_eligible": all(
            row.mlruns_detected is not None for row in eligible_rows
        ),
    }
    status = "SUCCESS" if all(gates.values()) else "FAILED"
    return {
        "schema_version": "1.0.0",
        "stage": "phase2_screen_sample",
        "status": status,
        "screening_run_id": screening_run_id,
        "source_run_id": source_run_id,
        "received_candidates": len(candidates),
        "screened_rows": len(screened_rows),
        "eligible": decisions.get("eligible", 0),
        "rejected": decisions.get("rejected", 0),
        "errors": decisions.get("error", 0),
        "discard_counts_by_primary_reason": dict(sorted(discard_reasons.items())),
        "strata_distribution": dict(sorted(strata_distribution.items())),
        "mlruns_detected_count": sum(1 for row in eligible_rows if row.mlruns_detected is True),
        "gates": gates,
        "input_artifacts": input_artifacts,
        "output_artifacts": output_artifacts,
    }


def main() -> int:
    root = _project_root()
    config_path = root / "config/config.yaml"
    taxonomy_path = root / "config/file_taxonomy.yaml"
    requirements_path = root / "requirements.txt"

    config: ResearchConfig = load_config(config_path)
    context = start_run(project_root=root, stage="phase2_screen_sample")
    manifest_path: Path | None = None

    try:
        if config.reproducibility.require_clean_worktree and context.dirty_worktree:
            raise RuntimeError(
                "A execução científica exige um worktree limpo. "
                "Faça commit ou registre explicitamente a alteração antes de executar."
            )

        interim_dir = root / config.paths.interim
        candidates_path = interim_dir / "candidatos_brutos.csv"
        evidences_path = interim_dir / "evidencias_busca.csv"

        candidates = _load_search_candidates(candidates_path)
        evidences = _load_search_evidences(evidences_path)

        if len({row.repository_numeric_id for row in candidates}) != len(candidates):
            raise RuntimeError(
                "candidatos_brutos.csv precisa estar deduplicado por repository_numeric_id"
            )

        source_run_id = _validate_single_run_id(candidates, label="candidatos_brutos.csv")
        evidences_run_id = _validate_single_run_id(evidences, label="evidencias_busca.csv")
        input_run_ids_match = source_run_id == evidences_run_id
        if not input_run_ids_match:
            raise RuntimeError(
                "candidatos e evidências precisam compartilhar o mesmo run_id de origem"
            )

        gateway = _build_gateway(config)
        screened_rows = screen_candidates(
            candidates,
            evidences,
            gateway,
            config.selection,
            config.strata,
            config.commit_filter,
            run_id=context.run_id,
        )

        funnel_path = interim_dir / "funil_amostral.csv"
        shortlist_path = interim_dir / "shortlist.csv"
        summary_path = interim_dir / "resumo_execucao_fase2.json"

        funnel_rows = _funnel_rows(screened_rows, source_run_id=source_run_id)
        shortlist_rows = [row for row in funnel_rows if row["decision"] == "eligible"]

        _write_csv_atomic(
            funnel_path,
            [
                "repository_numeric_id",
                "repository_id",
                "repository_url",
                "source_run_id",
                "screening_run_id",
                "observed_at_utc",
                "head_commit_sha",
                "stars_count",
                "commit_count",
                "contributor_count",
                "last_human_commit_at_utc",
                "dvc_detected",
                "mlflow_detected",
                "mlruns_detected",
                "stratum",
                "cheap_gate_status",
                "expensive_gate_status",
                "decision",
                "exclusion_stage",
                "primary_reason",
                "decision_reasons",
                "error_detail",
            ],
            funnel_rows,
        )
        _write_csv_atomic(
            shortlist_path,
            [
                "repository_numeric_id",
                "repository_id",
                "repository_url",
                "source_run_id",
                "screening_run_id",
                "observed_at_utc",
                "head_commit_sha",
                "stars_count",
                "commit_count",
                "contributor_count",
                "last_human_commit_at_utc",
                "dvc_detected",
                "mlflow_detected",
                "mlruns_detected",
                "stratum",
                "cheap_gate_status",
                "expensive_gate_status",
                "decision",
                "exclusion_stage",
                "primary_reason",
                "decision_reasons",
                "error_detail",
            ],
            shortlist_rows,
        )

        input_artifacts = [
            {"path": str(path.as_posix()), "sha256": build_artifact(path).sha256}
            for path in [candidates_path, evidences_path]
        ]
        output_artifacts = [
            {"path": str(path.as_posix()), "sha256": build_artifact(path).sha256}
            for path in [funnel_path, shortlist_path]
        ]
        summary_payload = _screening_summary(
            candidates=candidates,
            screened_rows=screened_rows,
            source_run_id=source_run_id,
            screening_run_id=context.run_id,
            input_run_ids_match=input_run_ids_match,
            config=config,
            input_artifacts=input_artifacts,
            output_artifacts=output_artifacts,
            worktree_clean=not context.dirty_worktree,
        )
        _write_json_atomic(summary_path, summary_payload)

        manifest_path = write_manifest(
            context=context,
            manifest_directory=root / config.paths.manifests,
            config_path=config_path,
            taxonomy_path=taxonomy_path,
            requirements_path=requirements_path,
            protocol_id=config.protocol.id,
            protocol_version=config.protocol.version,
            status=summary_payload["status"],
            artifacts=[
                build_artifact(candidates_path),
                build_artifact(evidences_path),
                build_artifact(funnel_path),
                build_artifact(shortlist_path),
                build_artifact(summary_path),
            ],
            error=None
            if summary_payload["status"] == "SUCCESS"
            else "Gates da Fase 2 não satisfeitos",
        )

        if summary_payload["status"] != "SUCCESS":
            print("Fase 2 concluída com gates violados.")
            print(f"Manifesto: {manifest_path}")
            return 1

        print("Fase 2 concluída com sucesso.")
        print(f"Manifesto: {manifest_path}")
        print(f"Funil: {funnel_path}")
        print(f"Shortlist: {shortlist_path}")
        print(f"Resumo: {summary_path}")
        print(f"Elegíveis: {summary_payload['eligible']}")
        print(f"Rejeitados: {summary_payload['rejected']}")
        print(f"Erros: {summary_payload['errors']}")
        return 0
    except Exception as exc:  # noqa: BLE001
        try:
            manifest_path = write_manifest(
                context=context,
                manifest_directory=root / config.paths.manifests,
                config_path=config_path,
                taxonomy_path=taxonomy_path,
                requirements_path=requirements_path,
                protocol_id=config.protocol.id,
                protocol_version=config.protocol.version,
                status="FAILED",
                artifacts=[],
                error=str(exc),
            )
        except Exception:  # noqa: BLE001
            pass
        print(str(exc))
        if manifest_path is not None:
            print(f"Manifesto de falha: {manifest_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
