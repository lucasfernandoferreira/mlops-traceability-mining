from __future__ import annotations

import csv
import importlib.util
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from mlops_traceability.config import load_config
from mlops_traceability.manifest import RunContext
from mlops_traceability.sample_screen import ScreeningRow


def _load_screen_script() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts/02_screen_sample.py"
    spec = importlib.util.spec_from_file_location("screen_sample_script", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prepare_project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    (root / "data" / "interim").mkdir(parents=True)
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copy2(repo_root / "config/config.yaml", root / "config/config.yaml")
    shutil.copy2(repo_root / "config/file_taxonomy.yaml", root / "config/file_taxonomy.yaml")
    shutil.copy2(repo_root / "requirements.txt", root / "requirements.txt")
    return root


def _write_search_csvs(root: Path, run_id: str) -> None:
    interim = root / "data/interim"
    candidates_path = interim / "candidatos_brutos.csv"
    evidences_path = interim / "evidencias_busca.csv"

    with candidates_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
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
        )
        writer.writeheader()
        for index in range(1, 4):
            writer.writerow(
                {
                    "repository_numeric_id": index,
                    "repository_id": f"owner/repo-{index}",
                    "repository_url": f"https://github.com/owner/repo-{index}",
                    "owner_login": "owner",
                    "is_fork": "false",
                    "description": "clean project",
                    "discovery_query_count": 1,
                    "discovery_hit_count": 1,
                    "observed_at_utc": "2026-01-01T00:00:00Z",
                    "run_id": run_id,
                }
            )

    with evidences_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
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
        )
        writer.writeheader()
        for index in range(1, 4):
            writer.writerow(
                {
                    "query_id": "q1",
                    "query_expression": "alpha",
                    "page_number": 1,
                    "result_rank": index,
                    "repository_numeric_id": index,
                    "repository_id": f"owner/repo-{index}",
                    "file_path": "dvc.yaml",
                    "file_sha": f"sha-{index}",
                    "file_url": f"https://example.test/{index}",
                    "run_id": run_id,
                }
            )


def _eligible_row(repository_numeric_id: int, stratum: str) -> ScreeningRow:
    observed_at = datetime(2026, 1, 1, tzinfo=UTC)
    return ScreeningRow(
        repository_numeric_id=repository_numeric_id,
        repository_id=f"owner/repo-{repository_numeric_id}",
        repository_url=f"https://github.com/owner/repo-{repository_numeric_id}",
        observed_at_utc=observed_at,
        head_commit_sha="abc123",
        stars_count=150,
        commit_count=300,
        contributor_count=5,
        last_human_commit_at_utc=observed_at,
        dvc_detected=stratum in {"apenas_dvc", "dvc_e_mlflow"},
        mlflow_detected=stratum in {"apenas_mlflow", "dvc_e_mlflow"},
        mlruns_detected=True,
        stratum=stratum,
        decision="eligible",
        primary_reason="eligible",
        decision_reasons=("eligible",),
        error_detail=None,
        cheap_gate_status="passed",
        expensive_gate_status="passed",
        exclusion_stage=None,
        run_id="screen-run",
    )


def _rejected_row(repository_numeric_id: int) -> ScreeningRow:
    observed_at = datetime(2026, 1, 1, tzinfo=UTC)
    return ScreeningRow(
        repository_numeric_id=repository_numeric_id,
        repository_id=f"owner/repo-{repository_numeric_id}",
        repository_url=f"https://github.com/owner/repo-{repository_numeric_id}",
        observed_at_utc=observed_at,
        head_commit_sha="abc123",
        stars_count=150,
        commit_count=300,
        contributor_count=5,
        last_human_commit_at_utc=observed_at,
        dvc_detected=True,
        mlflow_detected=False,
        mlruns_detected=False,
        stratum="apenas_dvc",
        decision="rejected",
        primary_reason="tool_evidence_unconfirmed",
        decision_reasons=("tool_evidence_unconfirmed",),
        error_detail=None,
        cheap_gate_status="passed",
        expensive_gate_status="failed",
        exclusion_stage="expensive",
        run_id="screen-run",
    )


def test_screen_script_writes_outputs_and_succeeds(tmp_path: Path) -> None:
    screen_script = _load_screen_script()
    root = _prepare_project_root(tmp_path)
    config = load_config(root / "config/config.yaml")
    source_run_id = "source-run"
    _write_search_csvs(root, source_run_id)

    manifest_kwargs: dict[str, object] = {}

    def fake_write_manifest(**kwargs: object) -> Path:
        manifest_kwargs.update(kwargs)
        return root / config.paths.manifests / "run.json"

    screened_rows = [
        _eligible_row(1, "apenas_dvc"),
        _eligible_row(2, "apenas_mlflow"),
        _eligible_row(3, "dvc_e_mlflow"),
    ] * 4

    context = RunContext(
        run_id="screen-run",
        stage="phase2_screen_sample",
        started_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        code_commit_sha="0123456789abcdef0123456789abcdef01234567",
        dirty_worktree=False,
    )

    with (
        patch.object(screen_script, "_project_root", return_value=root),
        patch.object(screen_script, "start_run", return_value=context),
        patch.object(screen_script, "screen_candidates", return_value=screened_rows),
        patch.object(screen_script, "write_manifest", side_effect=fake_write_manifest),
        patch.dict(
            screen_script.os.environ,
            {config.github.token_environment_variable: "fake-token"},
            clear=True,
        ),
    ):
        exit_code = screen_script.main()

    assert exit_code == 0
    assert manifest_kwargs["status"] == "SUCCESS"

    summary_path = root / "data/interim/resumo_execucao_fase2.json"
    funnel_path = root / "data/interim/funil_amostral.csv"
    shortlist_path = root / "data/interim/shortlist.csv"

    assert summary_path.is_file()
    assert funnel_path.is_file()
    assert shortlist_path.is_file()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "SUCCESS"
    assert summary["source_run_id"] == source_run_id
    assert summary["eligible"] == 12
    assert summary["gates"]["shortlist_bounds"] is True
    assert summary["gates"]["required_strata_present"] is True


def test_screen_script_preserves_outputs_when_gate_fails(tmp_path: Path) -> None:
    screen_script = _load_screen_script()
    root = _prepare_project_root(tmp_path)
    config = load_config(root / "config/config.yaml")
    source_run_id = "source-run"
    _write_search_csvs(root, source_run_id)

    manifest_kwargs: dict[str, object] = {}

    def fake_write_manifest(**kwargs: object) -> Path:
        manifest_kwargs.update(kwargs)
        return root / config.paths.manifests / "run.json"

    screened_rows = [_eligible_row(1, "apenas_dvc"), _eligible_row(2, "apenas_mlflow")]
    context = RunContext(
        run_id="screen-run",
        stage="phase2_screen_sample",
        started_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        code_commit_sha="0123456789abcdef0123456789abcdef01234567",
        dirty_worktree=False,
    )

    with (
        patch.object(screen_script, "_project_root", return_value=root),
        patch.object(screen_script, "start_run", return_value=context),
        patch.object(screen_script, "screen_candidates", return_value=screened_rows),
        patch.object(screen_script, "write_manifest", side_effect=fake_write_manifest),
        patch.dict(
            screen_script.os.environ,
            {config.github.token_environment_variable: "fake-token"},
            clear=True,
        ),
    ):
        exit_code = screen_script.main()

    assert exit_code == 1
    assert manifest_kwargs["status"] == "FAILED"

    summary_path = root / "data/interim/resumo_execucao_fase2.json"
    funnel_path = root / "data/interim/funil_amostral.csv"
    shortlist_path = root / "data/interim/shortlist.csv"

    assert summary_path.is_file()
    assert funnel_path.is_file()
    assert shortlist_path.is_file()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "FAILED"
    assert summary["gates"]["shortlist_bounds"] is False
    assert summary["gates"]["required_strata_present"] is False


def test_checkpoint_round_trip_and_rejects_incompatible_identity(tmp_path: Path) -> None:
    screen_script = _load_screen_script()
    checkpoint_path = tmp_path / "checkpoint.jsonl"
    identity = {
        "record_type": "metadata",
        "schema_version": "1.0.0",
        "source_run_id": "source-run",
    }

    assert (
        screen_script._prepare_checkpoint(
            checkpoint_path,
            identity,
            run_id="screen-run",
        )
        == []
    )
    screen_script._append_checkpoint(
        checkpoint_path,
        _eligible_row(1, "apenas_dvc"),
    )
    with checkpoint_path.open("a", encoding="utf-8") as handle:
        handle.write("{linha-interrompida")

    recovered = screen_script._prepare_checkpoint(
        checkpoint_path,
        identity,
        run_id="resumed-run",
    )
    assert len(recovered) == 1
    assert recovered[0].repository_numeric_id == 1
    assert recovered[0].run_id == "resumed-run"

    incompatible = {**identity, "source_run_id": "another-source-run"}
    assert (
        screen_script._prepare_checkpoint(
            checkpoint_path,
            incompatible,
            run_id="fresh-run",
        )
        == []
    )
