"""Orquestrador da Fase 2: triagem automática da amostra."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mlops_traceability.config import ResearchConfig, load_config
from mlops_traceability.github_search import SearchCandidateRow, SearchEvidenceRow
from mlops_traceability.manifest import (
    build_artifact,
    sha256_file,
    start_run,
    write_manifest,
)
from mlops_traceability.observability import ExecutionObserver
from mlops_traceability.run_storage import (
    LatestRunPointer,
    build_run_pointer,
    load_latest_pointer,
    resolve_artifact,
    run_directory,
    write_latest_pointer,
)
from mlops_traceability.sample_screen import (
    GitHubScreeningGateway,
    ScreeningRow,
    screen_candidates,
)

CACHE_SCHEMA_VERSION = "1.1.0"
SCREENING_SEMANTICS_VERSION = "1.0.0"
CACHE_COMPATIBILITY_FIELDS = (
    "source_run_id",
    "protocol_version",
    "config_sha256",
    "candidates_sha256",
    "evidences_sha256",
)
SCREENING_FIELDS = [
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
]


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


def _parse_optional_bool(value: str) -> bool | None:
    return None if not value else _parse_bool(value)


def _parse_optional_int(value: str) -> int | None:
    return None if not value else int(value)


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


def _load_screening_rows(path: Path, *, run_id: str) -> list[ScreeningRow]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[ScreeningRow] = []
        for raw in reader:
            rows.append(
                ScreeningRow(
                    repository_numeric_id=int(raw["repository_numeric_id"]),
                    repository_id=raw["repository_id"],
                    repository_url=raw["repository_url"],
                    observed_at_utc=_parse_datetime(raw["observed_at_utc"]),
                    head_commit_sha=raw["head_commit_sha"],
                    stars_count=_parse_optional_int(raw["stars_count"]),
                    commit_count=_parse_optional_int(raw["commit_count"]),
                    contributor_count=_parse_optional_int(raw["contributor_count"]),
                    last_human_commit_at_utc=(
                        None
                        if not raw["last_human_commit_at_utc"]
                        else _parse_datetime(raw["last_human_commit_at_utc"])
                    ),
                    dvc_detected=_parse_optional_bool(raw["dvc_detected"]),
                    mlflow_detected=_parse_optional_bool(raw["mlflow_detected"]),
                    mlruns_detected=_parse_optional_bool(raw["mlruns_detected"]),
                    stratum=raw["stratum"] or None,
                    cheap_gate_status=raw["cheap_gate_status"],
                    expensive_gate_status=raw["expensive_gate_status"],
                    decision=raw["decision"],
                    exclusion_stage=raw["exclusion_stage"] or None,
                    primary_reason=raw["primary_reason"] or None,
                    decision_reasons=tuple(
                        reason.strip()
                        for reason in raw["decision_reasons"].split("|")
                        if reason.strip()
                    ),
                    error_detail=raw["error_detail"] or None,
                    run_id=run_id,
                )
            )
    return rows


def _resolve_phase1_inputs(
    interim_dir: Path,
) -> tuple[Path, Path, LatestRunPointer | None]:
    pointer = load_latest_pointer(interim_dir, "phase1_search_candidates")
    if pointer is None:
        return (
            interim_dir / "candidatos_brutos.csv",
            interim_dir / "evidencias_busca.csv",
            None,
        )
    if pointer.status != "SUCCESS":
        raise RuntimeError("A execução latest da Fase 1 não foi concluída com sucesso.")
    return (
        resolve_artifact(interim_dir, pointer, "candidates"),
        resolve_artifact(interim_dir, pointer, "evidences"),
        pointer,
    )


def _build_observed_gateway(
    config: ResearchConfig,
    observer: ExecutionObserver,
) -> GitHubScreeningGateway:
    token_name = config.github.token_environment_variable
    token = os.getenv(token_name)
    if not token:
        raise RuntimeError(
            f"Variável {token_name} não definida. Configure o token local para executar a Fase 2."
        )

    def report_rate_limit_wait(wait_seconds: float, reset_at_utc: datetime) -> None:
        observer.event(
            "github_core_rate_limit_wait",
            "Cota core reservada; aguardando renovação coordenada",
            wait_seconds=round(wait_seconds, 1),
            reset_at_utc=_format_datetime(reset_at_utc),
        )

    def report_rate_limit_event(name: str, details: dict[str, Any]) -> None:
        messages = {
            "github_rate_limit_wait": "Limite da API detectado; workers em cooldown coordenado",
            "github_rate_limit_recovered": "Acesso à API restabelecido após cooldown",
            "github_rate_limit_circuit_open": (
                "Limite persistente; circuito aberto e pendências serão marcadas como erro"
            ),
        }
        observer.event(name, messages[name], **details)

    def report_tree_fallback(repository_id: str) -> None:
        observer.event(
            "tree_fallback",
            "Árvore Git truncada; confirmando caminhos dirigidos",
            repository=repository_id,
        )

    return GitHubScreeningGateway(
        token=token,
        per_page=config.github.per_page,
        request_timeout_seconds=config.github.request_timeout_seconds,
        core_reserve=config.github.rate_limit.core_reserve,
        reset_buffer_seconds=config.github.rate_limit.reset_buffer_seconds,
        on_rate_limit_wait=report_rate_limit_wait,
        on_rate_limit_event=report_rate_limit_event,
        on_tree_fallback=report_tree_fallback,
        mlflow_manifest_scan_limit=config.execution.mlflow_manifest_scan_limit,
        request_interval_seconds=config.github.rate_limit.request_interval_seconds,
        secondary_cooldown_seconds=config.github.rate_limit.secondary_cooldown_seconds,
        secondary_max_retries=config.github.rate_limit.secondary_max_retries,
        max_rate_limit_wait_seconds=(config.github.rate_limit.max_rate_limit_wait_seconds),
    )


def _cache_identity(
    *,
    source_run_id: str,
    context: Any,
    config: ResearchConfig,
    config_path: Path,
    candidates_path: Path,
    evidences_path: Path,
) -> dict[str, Any]:
    return {
        "record_type": "metadata",
        "schema_version": CACHE_SCHEMA_VERSION,
        "screening_semantics_version": SCREENING_SEMANTICS_VERSION,
        "source_run_id": source_run_id,
        "code_commit_sha": context.code_commit_sha,
        "protocol_version": config.protocol.version,
        "config_sha256": sha256_file(config_path),
        "candidates_sha256": sha256_file(candidates_path),
        "evidences_sha256": sha256_file(evidences_path),
    }


def _cache_path(interim_dir: Path, identity: dict[str, Any]) -> Path:
    serialized = json.dumps(
        _cache_compatibility_identity(identity),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    cache_key = hashlib.sha256(serialized).hexdigest()[:20]
    return interim_dir / "cache/phase2" / f"{cache_key}.jsonl"


def _cache_compatibility_identity(identity: dict[str, Any]) -> dict[str, Any]:
    compatible = {
        field: identity[field] for field in CACHE_COMPATIBILITY_FIELDS if field in identity
    }
    if compatible:
        compatible["screening_semantics_version"] = identity.get(
            "screening_semantics_version",
            SCREENING_SEMANTICS_VERSION,
        )
        return compatible
    return {
        key: value
        for key, value in identity.items()
        if key not in {"schema_version", "code_commit_sha"}
    }


def _cache_identities_compatible(
    observed: dict[str, Any],
    expected: dict[str, Any],
) -> bool:
    return _cache_compatibility_identity(observed) == _cache_compatibility_identity(expected)


def _read_cache_records(path: Path) -> tuple[list[dict[str, Any]], bool]:
    records: list[dict[str, Any]] = []
    complete = True
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                complete = False
                break
            if not isinstance(record, dict):
                complete = False
                break
            records.append(record)
    return records, complete


def _find_compatible_cache(
    cache_directory: Path,
    identity: dict[str, Any],
    *,
    preferred_path: Path,
) -> Path | None:
    if preferred_path.is_file():
        candidates = [preferred_path]
    else:
        candidates = []
    candidates.extend(
        path
        for path in sorted(
            cache_directory.glob("*.jsonl"),
            key=lambda candidate: candidate.stat().st_mtime,
            reverse=True,
        )
        if path != preferred_path
    )
    for candidate in candidates:
        try:
            records, _complete = _read_cache_records(candidate)
            if records and _cache_identities_compatible(records[0], identity):
                return candidate
        except OSError:
            continue
    return None


def _load_retry_rows(
    interim_dir: Path,
    *,
    source_run_id: str,
    run_id: str,
) -> list[ScreeningRow]:
    pointer = load_latest_pointer(interim_dir, "phase2_screen_sample")
    if pointer is None:
        raise RuntimeError("Não existe execução latest da Fase 2 para reprocessar.")
    if pointer.source_run_id != source_run_id:
        raise RuntimeError(
            "A execução latest da Fase 2 usa outra coleta da Fase 1; "
            "não é seguro reutilizar seus resultados."
        )
    rows = _load_screening_rows(
        resolve_artifact(interim_dir, pointer, "funnel"),
        run_id=run_id,
    )
    return [row for row in rows if row.decision != "error"]


def _cache_row_payload(row: ScreeningRow) -> dict[str, Any]:
    payload = asdict(row)
    payload["observed_at_utc"] = _format_datetime(row.observed_at_utc)
    payload["last_human_commit_at_utc"] = (
        None
        if row.last_human_commit_at_utc is None
        else _format_datetime(row.last_human_commit_at_utc)
    )
    payload["decision_reasons"] = list(row.decision_reasons)
    return {"record_type": "row", "row": payload}


def _cache_payload_to_row(payload: dict[str, Any], run_id: str) -> ScreeningRow:
    row = payload["row"]
    return ScreeningRow(
        repository_numeric_id=int(row["repository_numeric_id"]),
        repository_id=str(row["repository_id"]),
        repository_url=str(row["repository_url"]),
        observed_at_utc=_parse_datetime(str(row["observed_at_utc"])),
        head_commit_sha=str(row["head_commit_sha"]),
        stars_count=None if row["stars_count"] is None else int(row["stars_count"]),
        commit_count=None if row["commit_count"] is None else int(row["commit_count"]),
        contributor_count=(
            None if row["contributor_count"] is None else int(row["contributor_count"])
        ),
        last_human_commit_at_utc=(
            None
            if row["last_human_commit_at_utc"] is None
            else _parse_datetime(str(row["last_human_commit_at_utc"]))
        ),
        dvc_detected=row["dvc_detected"],
        mlflow_detected=row["mlflow_detected"],
        mlruns_detected=row["mlruns_detected"],
        stratum=row["stratum"],
        decision=str(row["decision"]),
        primary_reason=row["primary_reason"],
        decision_reasons=tuple(row["decision_reasons"]),
        error_detail=row["error_detail"],
        cheap_gate_status=str(row["cheap_gate_status"]),
        expensive_gate_status=str(row["expensive_gate_status"]),
        exclusion_stage=row["exclusion_stage"],
        run_id=run_id,
    )


def _prepare_cache(
    path: Path,
    identity: dict[str, Any],
    *,
    run_id: str,
    source_path: Path | None = None,
) -> list[ScreeningRow]:
    rows: list[ScreeningRow] = []
    cache_matches = False
    complete = True
    selected_path = source_path if source_path is not None else path
    if selected_path.is_file():
        try:
            records, complete = _read_cache_records(selected_path)
            cache_matches = bool(records) and _cache_identities_compatible(records[0], identity)
            if cache_matches:
                rows = [
                    _cache_payload_to_row(record, run_id)
                    for record in records[1:]
                    if record.get("record_type") == "row"
                ]
        except (KeyError, TypeError, ValueError):
            cache_matches = False
            rows = []

    deduplicated = {row.repository_numeric_id: row for row in rows}
    if not cache_matches:
        _write_json_lines_atomic(path, [identity])
    elif selected_path != path or records[0] != identity or not complete:
        _write_json_lines_atomic(
            path,
            [identity, *(_cache_row_payload(row) for row in deduplicated.values())],
        )

    return list(deduplicated.values())


def _write_json_lines_atomic(path: Path, records: list[dict[str, Any]]) -> None:
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
        for record in records:
            json.dump(record, handle, ensure_ascii=False)
            handle.write("\n")
    os.replace(temp_path, path)


def _append_cache(path: Path, row: ScreeningRow) -> None:
    with path.open("a", encoding="utf-8") as handle:
        json.dump(_cache_row_payload(row), handle, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


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
    reused_rows: int,
) -> dict[str, Any]:
    decisions = Counter(row.decision for row in screened_rows)
    discard_reasons = Counter(
        reason
        for row in screened_rows
        if row.decision != "eligible"
        for reason in row.decision_reasons
    )
    primary_discard_reasons = Counter(
        row.primary_reason
        for row in screened_rows
        if row.decision != "eligible" and row.primary_reason is not None
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
        "schema_version": "1.1.0",
        "stage": "phase2_screen_sample",
        "status": status,
        "screening_run_id": screening_run_id,
        "source_run_id": source_run_id,
        "received_candidates": len(candidates),
        "screened_rows": len(screened_rows),
        "eligible": decisions.get("eligible", 0),
        "rejected": decisions.get("rejected", 0),
        "errors": decisions.get("error", 0),
        "reused_rows": reused_rows,
        "processed_rows": len(screened_rows) - reused_rows,
        "discard_counts_by_primary_reason": dict(sorted(primary_discard_reasons.items())),
        "discard_counts_by_reason": dict(sorted(discard_reasons.items())),
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
    observer = ExecutionObserver(
        stage=context.stage,
        run_id=context.run_id,
        log_directory=root / "tmp/logs",
    )
    manifest_path: Path | None = None

    try:
        observer.event(
            "run_started",
            "Fase 2 iniciada",
            workers=config.execution.screening_workers,
            log_path=observer.log_path,
        )
        if config.reproducibility.require_clean_worktree and context.dirty_worktree:
            raise RuntimeError(
                "A execução científica exige um worktree limpo. "
                "Faça commit ou registre explicitamente a alteração antes de executar."
            )

        interim_dir = root / config.paths.interim
        candidates_path, evidences_path, phase1_pointer = _resolve_phase1_inputs(interim_dir)

        candidates = _load_search_candidates(candidates_path)
        evidences = _load_search_evidences(evidences_path)
        observer.event(
            "inputs_loaded",
            "Entradas da Fase 1 carregadas",
            candidates=len(candidates),
            evidences=len(evidences),
            phase1_pointer=("legacy" if phase1_pointer is None else phase1_pointer.run_id),
        )

        if len({row.repository_numeric_id for row in candidates}) != len(candidates):
            raise RuntimeError(
                "candidatos_brutos.csv precisa estar deduplicado por repository_numeric_id"
            )

        source_run_id = _validate_single_run_id(candidates, label="candidatos_brutos.csv")
        evidences_run_id = _validate_single_run_id(evidences, label="evidencias_busca.csv")
        input_run_ids_match = source_run_id == evidences_run_id
        if phase1_pointer is not None and phase1_pointer.run_id != source_run_id:
            input_run_ids_match = False
        if not input_run_ids_match:
            raise RuntimeError(
                "candidatos e evidências precisam compartilhar o mesmo run_id de origem"
            )

        identity = _cache_identity(
            source_run_id=source_run_id,
            context=context,
            config=config,
            config_path=config_path,
            candidates_path=candidates_path,
            evidences_path=evidences_path,
        )
        cache_path = _cache_path(interim_dir, identity)
        compatible_cache_path = _find_compatible_cache(
            cache_path.parent,
            identity,
            preferred_path=cache_path,
        )
        cached_rows = _prepare_cache(
            cache_path,
            identity,
            run_id=context.run_id,
            source_path=compatible_cache_path,
        )
        if compatible_cache_path is not None and compatible_cache_path != cache_path:
            observer.event(
                "cache_migrated",
                "Cache compatível migrado para a identidade semântica estável",
                source_cache_path=compatible_cache_path,
                cache_path=cache_path,
                recovered_candidates=len(cached_rows),
            )
        reusable_by_id = {
            row.repository_numeric_id: row for row in cached_rows if row.decision != "error"
        }
        retry_errors_only = os.getenv("SCREEN_RETRY_ERRORS_ONLY") == "1"
        if retry_errors_only:
            retry_rows = _load_retry_rows(
                interim_dir,
                source_run_id=source_run_id,
                run_id=context.run_id,
            )
            for row in retry_rows:
                if row.repository_numeric_id not in reusable_by_id:
                    reusable_by_id[row.repository_numeric_id] = row
                    _append_cache(cache_path, row)
        existing_rows = list(reusable_by_id.values())
        if existing_rows:
            observer.event(
                "cache_reused",
                "Resultados compatíveis reutilizados; processando pendências e erros",
                recovered_candidates=len(existing_rows),
                pending_candidates=len(candidates) - len(existing_rows),
                retry_errors_only=retry_errors_only,
            )
        else:
            observer.event(
                "cache_created",
                "Cache incremental criado",
                cache_path=cache_path,
            )

        gateway = _build_observed_gateway(config, observer)
        decision_counts = Counter(row.decision for row in existing_rows)
        with observer.progress(
            name="screening",
            total=len(candidates),
            initial_completed=len(existing_rows),
            interval_seconds=config.execution.progress_interval_seconds,
            stall_threshold_seconds=(config.execution.progress_stall_threshold_seconds),
            details_provider=gateway.rate_limit_status,
        ) as progress:

            def persist_result(row: ScreeningRow, completed: int, total: int) -> None:
                del total
                _append_cache(cache_path, row)
                decision_counts[row.decision] += 1
                progress.update(
                    completed,
                    current_item=row.repository_id,
                    counts={
                        "eligible": decision_counts["eligible"],
                        "rejected": decision_counts["rejected"],
                        "errors": decision_counts["error"],
                    },
                )

            screened_rows = screen_candidates(
                candidates,
                evidences,
                gateway,
                config.selection,
                config.strata,
                config.commit_filter,
                run_id=context.run_id,
                max_workers=config.execution.screening_workers,
                existing_rows=existing_rows,
                on_result=persist_result,
            )

        output_dir = run_directory(interim_dir, context.run_id)
        funnel_path = output_dir / "funil_amostral.csv"
        shortlist_path = output_dir / "shortlist.csv"
        summary_path = output_dir / "resumo_execucao_fase2.json"

        funnel_rows = _funnel_rows(screened_rows, source_run_id=source_run_id)
        shortlist_rows = [row for row in funnel_rows if row["decision"] == "eligible"]

        _write_csv_atomic(
            funnel_path,
            SCREENING_FIELDS,
            funnel_rows,
        )
        _write_csv_atomic(
            shortlist_path,
            SCREENING_FIELDS,
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
            reused_rows=len(existing_rows),
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
        latest_pointer = write_latest_pointer(
            interim_dir,
            build_run_pointer(
                interim_directory=interim_dir,
                stage="phase2_screen_sample",
                status=summary_payload["status"],
                run_id=context.run_id,
                source_run_id=source_run_id,
                artifacts={
                    "funnel": funnel_path,
                    "shortlist": shortlist_path,
                    "execution_report": summary_path,
                },
                manifest_path=manifest_path,
            ),
        )
        observer.event(
            "run_finished",
            "Fase 2 finalizada",
            status=summary_payload["status"],
            eligible=summary_payload["eligible"],
            rejected=summary_payload["rejected"],
            errors=summary_payload["errors"],
            reused_rows=len(existing_rows),
            latest_pointer=latest_pointer,
        )

        if summary_payload["status"] != "SUCCESS":
            print("Fase 2 concluída com gates violados.")
            print(f"Manifesto: {manifest_path}")
            print(f"Funil: {funnel_path}")
            print(f"Shortlist: {shortlist_path}")
            print(f"Resumo: {summary_path}")
            print(f"Ponteiro latest: {latest_pointer}")
            return 1

        print("Fase 2 concluída com sucesso.")
        print(f"Manifesto: {manifest_path}")
        print(f"Funil: {funnel_path}")
        print(f"Shortlist: {shortlist_path}")
        print(f"Resumo: {summary_path}")
        print(f"Ponteiro latest: {latest_pointer}")
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
        observer.event("run_failed", "Fase 2 interrompida por erro", error=str(exc))
        print(str(exc))
        if manifest_path is not None:
            print(f"Manifesto de falha: {manifest_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
