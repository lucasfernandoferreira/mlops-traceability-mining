"""Contracted pilot metrics; unavailable evidence never becomes a numeric zero."""

from __future__ import annotations

from typing import Any


def compute_metrics(
    commits: list[dict[str, Any]],
    summary: dict[str, Any],
    inspection: dict[str, Any],
    *,
    protocol_version: str,
    taxonomy_version: str,
    run_id: str,
) -> list[dict[str, Any]]:
    eligible = [row for row in commits if row["eligibility_status"] == "included"]
    code = [row for row in eligible if row["C"]]
    config = [row for row in eligible if row["P"]]
    rows: list[dict[str, Any]] = []

    def add(
        metric_id: str,
        numerator: int | None,
        denominator: int | None,
        unit: str,
        *,
        status: str = "observed",
        detail: str = "",
    ) -> None:
        if status == "observed" and denominator == 0:
            status, detail = "undefined", "Denominador elegível igual a zero."
        rows.append(
            {
                "repository_id": summary["repository_id"],
                "metric_id": metric_id,
                "head_commit_sha": summary["head_commit_sha"],
                "period_start_utc": summary["period_start_utc"],
                "period_end_utc": summary["period_end_utc"],
                "value": numerator / denominator
                if status == "observed" and numerator is not None and denominator
                else None,
                "status": status,
                "status_detail": detail,
                "numerator": numerator,
                "denominator": denominator,
                "unit": unit,
                "excluded_commit_count": len(commits) - len(eligible),
                "protocol_version": protocol_version,
                "taxonomy_version": taxonomy_version,
                "run_id": run_id,
                "validation_status": "pending_human_validation",
            }
        )

    add("code_config_cochange", sum(row["P"] for row in code), len(code), "proportion")
    semantic_errors = any(row["config_semantic_status"] == "error" for row in config)
    unsupported = any(row["config_semantic_status"] == "not_applicable" for row in config)
    add(
        "config_magnitude",
        None
        if semantic_errors or unsupported
        else sum(row["config_changed_keys"] for row in config),
        len(config),
        "keys/config_commit",
        status="error" if semantic_errors else "not_applicable" if unsupported else "observed",
        detail="Há CONFIG sem diferença semântica válida; não publicar média parcial."
        if semantic_errors or unsupported
        else "",
    )
    for metric_id in ("data_code_ratio_original", "data_code_cochange", "cace_index"):
        add(
            metric_id,
            None,
            None,
            "ratio" if metric_id.endswith("original") else "proportion",
            status="not_available",
            detail="Dimensão D não validada para dados MLflow; DATA_META detecta DVC.",
        )
    for metric_id in ("provenance_coverage", "env_versioning_rate", "experiment_redundancy"):
        add(
            metric_id,
            None,
            None,
            "runs/promoted_version" if metric_id == "experiment_redundancy" else "proportion",
            status="not_available",
            detail=inspection["runtime_evidence_detail"],
        )
    operations = {
        "static_mlflow_param_calls": {"log_param", "log_params"},
        "static_mlflow_metric_calls": {"log_metric", "log_metrics"},
        "static_mlflow_artifact_calls": {"log_artifact", "log_artifacts"},
        "static_mlflow_model_calls": {"log_model", "register_model"},
    }
    for metric_id, names in operations.items():
        count = sum(
            row["operation"] in names and row["category"] == "CODE" for row in inspection["calls"]
        )
        add(
            metric_id,
            count if not inspection["parse_errors"] else None,
            1,
            "syntactic_call_sites_at_sha",
            status="error" if inspection["parse_errors"] else "observed",
            detail=(
                "Candidatos sintáticos em CODE no SHA; sem inferência de execução, "
                "wrappers ou alias reatribuído."
            ),
        )
    return rows
