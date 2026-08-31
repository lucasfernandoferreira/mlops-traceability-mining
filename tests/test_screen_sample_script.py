from __future__ import annotations

import csv
import importlib.util
import json
import shutil
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from mlops_traceability.config import load_config
from mlops_traceability.manifest import RunContext
from mlops_traceability.run_storage import (
    build_run_pointer,
    load_latest_pointer,
    resolve_artifact,
    write_latest_pointer,
)
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

    interim = root / "data/interim"
    output_dir = interim / "runs/screen-run"
    summary_path = output_dir / "resumo_execucao_fase2.json"
    funnel_path = output_dir / "funil_amostral.csv"
    shortlist_path = output_dir / "shortlist.csv"

    assert summary_path.is_file()
    assert funnel_path.is_file()
    assert shortlist_path.is_file()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "SUCCESS"
    assert summary["source_run_id"] == source_run_id
    assert summary["eligible"] == 12
    assert summary["gates"]["shortlist_bounds"] is True
    assert summary["gates"]["required_strata_present"] is True
    pointer = load_latest_pointer(interim, "phase2_screen_sample")
    assert pointer is not None
    assert pointer.status == "SUCCESS"
    assert resolve_artifact(interim, pointer, "shortlist") == shortlist_path.resolve()


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

    interim = root / "data/interim"
    output_dir = interim / "runs/screen-run"
    summary_path = output_dir / "resumo_execucao_fase2.json"
    funnel_path = output_dir / "funil_amostral.csv"
    shortlist_path = output_dir / "shortlist.csv"

    assert summary_path.is_file()
    assert funnel_path.is_file()
    assert shortlist_path.is_file()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "FAILED"
    assert summary["gates"]["shortlist_bounds"] is False
    assert summary["gates"]["required_strata_present"] is False
    pointer = load_latest_pointer(interim, "phase2_screen_sample")
    assert pointer is not None
    assert pointer.status == "FAILED"


def test_cache_round_trip_and_rejects_incompatible_identity(tmp_path: Path) -> None:
    screen_script = _load_screen_script()
    cache_path = tmp_path / "cache.jsonl"
    identity = {
        "record_type": "metadata",
        "schema_version": "1.0.0",
        "source_run_id": "source-run",
    }

    assert (
        screen_script._prepare_cache(
            cache_path,
            identity,
            run_id="screen-run",
        )
        == []
    )
    screen_script._append_cache(
        cache_path,
        _eligible_row(1, "apenas_dvc"),
    )
    with cache_path.open("a", encoding="utf-8") as handle:
        handle.write("{linha-interrompida")

    recovered = screen_script._prepare_cache(
        cache_path,
        identity,
        run_id="resumed-run",
    )
    assert len(recovered) == 1
    assert recovered[0].repository_numeric_id == 1
    assert recovered[0].run_id == "resumed-run"

    incompatible = {**identity, "source_run_id": "another-source-run"}
    assert (
        screen_script._prepare_cache(
            cache_path,
            incompatible,
            run_id="fresh-run",
        )
        == []
    )


def test_cache_migrates_legacy_commit_identity_without_losing_rows(tmp_path: Path) -> None:
    screen_script = _load_screen_script()
    cache_directory = tmp_path / "cache"
    legacy_identity = {
        "record_type": "metadata",
        "schema_version": "1.0.0",
        "source_run_id": "source-run",
        "code_commit_sha": "old-commit",
        "protocol_version": "1.5.0",
        "config_sha256": "config-hash",
        "candidates_sha256": "candidates-hash",
        "evidences_sha256": "evidences-hash",
    }
    legacy_path = cache_directory / "legacy.jsonl"
    screen_script._write_json_lines_atomic(legacy_path, [legacy_identity])
    screen_script._append_cache(legacy_path, _eligible_row(1, "apenas_dvc"))
    current_identity = {
        **legacy_identity,
        "schema_version": screen_script.CACHE_SCHEMA_VERSION,
        "screening_semantics_version": screen_script.SCREENING_SEMANTICS_VERSION,
        "code_commit_sha": "new-operational-commit",
    }
    current_path = screen_script._cache_path(tmp_path, current_identity)

    source_path = screen_script._find_compatible_cache(
        cache_directory,
        current_identity,
        preferred_path=current_path,
    )
    recovered = screen_script._prepare_cache(
        current_path,
        current_identity,
        run_id="resumed-run",
        source_path=source_path,
    )

    assert source_path == legacy_path
    assert [row.repository_numeric_id for row in recovered] == [1]
    migrated_records, complete = screen_script._read_cache_records(current_path)
    assert complete is True
    assert migrated_records[0] == current_identity
    incompatible_semantics = {
        **current_identity,
        "screening_semantics_version": "2.0.0",
    }
    assert (
        screen_script._cache_identities_compatible(
            legacy_identity,
            incompatible_semantics,
        )
        is False
    )


def test_retry_errors_reuses_only_non_error_rows(tmp_path: Path) -> None:
    screen_script = _load_screen_script()
    root = _prepare_project_root(tmp_path)
    config = load_config(root / "config/config.yaml")
    source_run_id = "source-run"
    _write_search_csvs(root, source_run_id)
    interim = root / "data/interim"
    prior_dir = interim / "runs/prior-screen-run"
    prior_funnel = prior_dir / "funil_amostral.csv"
    error_row = replace(
        _rejected_row(3),
        decision="error",
        primary_reason="expensive_gate_unavailable",
        decision_reasons=("expensive_gate_unavailable",),
        error_detail="tree truncated",
        expensive_gate_status="error",
    )
    prior_rows = [_eligible_row(1, "apenas_dvc"), _rejected_row(2), error_row]
    screen_script._write_csv_atomic(
        prior_funnel,
        screen_script.SCREENING_FIELDS,
        screen_script._funnel_rows(prior_rows, source_run_id=source_run_id),
    )
    write_latest_pointer(
        interim,
        build_run_pointer(
            interim_directory=interim,
            stage="phase2_screen_sample",
            status="FAILED",
            run_id="prior-screen-run",
            source_run_id=source_run_id,
            artifacts={"funnel": prior_funnel},
        ),
    )
    context = RunContext(
        run_id="retry-run",
        stage="phase2_screen_sample",
        started_at_utc=datetime(2026, 1, 2, tzinfo=UTC),
        code_commit_sha="0123456789abcdef0123456789abcdef01234567",
        dirty_worktree=False,
    )

    with (
        patch.object(screen_script, "_project_root", return_value=root),
        patch.object(screen_script, "start_run", return_value=context),
        patch.object(
            screen_script,
            "screen_candidates",
            return_value=[
                _eligible_row(1, "apenas_dvc"),
                _rejected_row(2),
                _eligible_row(3, "dvc_e_mlflow"),
            ],
        ) as mocked_screen,
        patch.object(
            screen_script,
            "write_manifest",
            return_value=root / config.paths.manifests / "retry-run.json",
        ),
        patch.dict(
            screen_script.os.environ,
            {
                config.github.token_environment_variable: "fake-token",
                "SCREEN_RETRY_ERRORS_ONLY": "1",
            },
            clear=True,
        ),
    ):
        screen_script.main()

    reused_rows = mocked_screen.call_args.kwargs["existing_rows"]
    assert {row.repository_numeric_id for row in reused_rows} == {1, 2}
    assert all(row.decision != "error" for row in reused_rows)


def test_summary_separates_primary_and_all_discard_reasons() -> None:
    screen_script = _load_screen_script()
    config = load_config("config/config.yaml")
    row = replace(
        _rejected_row(1),
        primary_reason="first_reason",
        decision_reasons=("first_reason", "second_reason"),
    )

    summary = screen_script._screening_summary(
        candidates=[],
        screened_rows=[row],
        source_run_id="source-run",
        screening_run_id="screen-run",
        input_run_ids_match=True,
        config=config,
        input_artifacts=[],
        output_artifacts=[],
        worktree_clean=True,
        reused_rows=0,
    )

    assert summary["discard_counts_by_primary_reason"] == {"first_reason": 1}
    assert summary["discard_counts_by_reason"] == {
        "first_reason": 1,
        "second_reason": 1,
    }
