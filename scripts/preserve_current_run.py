"""Preserva artefatos legados da última execução em diretórios por run_id."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from mlops_traceability.config import load_config
from mlops_traceability.run_storage import RunStatus, preserve_legacy_run


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON precisa conter um objeto: {path}")
    return payload


def _manifest_path(root: Path, manifests: Path, run_id: str) -> Path | None:
    path = root / manifests / f"{run_id}.json"
    return path if path.is_file() else None


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    config = load_config(root / "config/config.yaml")
    interim = root / config.paths.interim

    phase1_report_path = interim / "resumo_execucao_fase1.json"
    phase1_report = _read_json(phase1_report_path)
    phase1_run_id = str(phase1_report["run_id"])
    preserve_legacy_run(
        interim_directory=interim,
        stage="phase1_search_candidates",
        status=cast(RunStatus, str(phase1_report["status"])),
        run_id=phase1_run_id,
        legacy_artifacts={
            "candidates": interim / "candidatos_brutos.csv",
            "evidences": interim / "evidencias_busca.csv",
            "search_summary": interim / "resumo_busca.csv",
            "execution_report": phase1_report_path,
        },
        manifest_path=_manifest_path(root, config.paths.manifests, phase1_run_id),
    )

    phase2_summary_path = interim / "resumo_execucao_fase2.json"
    phase2_summary = _read_json(phase2_summary_path)
    phase2_run_id = str(phase2_summary["screening_run_id"])
    preserve_legacy_run(
        interim_directory=interim,
        stage="phase2_screen_sample",
        status=cast(RunStatus, str(phase2_summary["status"])),
        run_id=phase2_run_id,
        source_run_id=str(phase2_summary["source_run_id"]),
        legacy_artifacts={
            "funnel": interim / "funil_amostral.csv",
            "shortlist": interim / "shortlist.csv",
            "execution_report": phase2_summary_path,
        },
        manifest_path=_manifest_path(root, config.paths.manifests, phase2_run_id),
    )

    print(f"Fase 1 preservada: {phase1_run_id}")
    print(f"Fase 2 preservada: {phase2_run_id} (status={phase2_summary['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
