from __future__ import annotations

import importlib.util
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import cast
from unittest.mock import patch

import pytest

from mlops_traceability.config import load_config
from mlops_traceability.github_search import (
    SearchCandidateRow,
    SearchCollection,
    SearchEvidenceRow,
    SearchSummaryRow,
)
from mlops_traceability.manifest import RunContext


def _load_search_script() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts/01_search_candidates.py"
    spec = importlib.util.spec_from_file_location("search_candidates_script", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prepare_project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copy2(repo_root / "config/config.yaml", root / "config/config.yaml")
    shutil.copy2(repo_root / "config/file_taxonomy.yaml", root / "config/file_taxonomy.yaml")
    shutil.copy2(repo_root / "requirements.txt", root / "requirements.txt")
    return root


def _collection(candidate_count: int) -> SearchCollection:
    observed_at_utc = datetime(2026, 1, 1, tzinfo=UTC)
    finished_at_utc = datetime(2026, 1, 1, 0, 5, tzinfo=UTC)
    candidates = [
        SearchCandidateRow(
            repository_numeric_id=index,
            repository_id=f"owner/repo-{index}",
            repository_url=f"https://github.com/owner/repo-{index}",
            owner_login="owner",
            is_fork=False,
            description=None,
            discovery_query_count=1,
            discovery_hit_count=1,
            observed_at_utc=observed_at_utc,
            run_id="run-1",
        )
        for index in range(candidate_count)
    ]
    evidences = [
        SearchEvidenceRow(
            query_id="dvc_pipeline",
            query_expression="filename:dvc.yaml",
            page_number=1,
            result_rank=1,
            repository_numeric_id=1,
            repository_id="owner/repo-1",
            file_path="dvc.yaml",
            file_sha="sha-1",
            file_url="https://example.test/evidence",
            run_id="run-1",
        )
    ]
    summaries = [
        SearchSummaryRow(
            query_id="dvc_pipeline",
            query_expression="filename:dvc.yaml",
            reported_total_count=1,
            retrieved_hit_count=1,
            unique_repository_count=1,
            incomplete_results=False,
            truncated=False,
            started_at_utc=observed_at_utc,
            finished_at_utc=finished_at_utc,
            run_id="run-1",
        ),
        SearchSummaryRow(
            query_id="dvc_files",
            query_expression="extension:dvc",
            reported_total_count=1,
            retrieved_hit_count=1,
            unique_repository_count=1,
            incomplete_results=False,
            truncated=False,
            started_at_utc=observed_at_utc,
            finished_at_utc=finished_at_utc,
            run_id="run-1",
        ),
        SearchSummaryRow(
            query_id="mlflow_python",
            query_expression="mlflow language:Python",
            reported_total_count=1,
            retrieved_hit_count=1,
            unique_repository_count=1,
            incomplete_results=False,
            truncated=True,
            started_at_utc=observed_at_utc,
            finished_at_utc=finished_at_utc,
            run_id="run-1",
        ),
    ]
    return SearchCollection(candidates=candidates, evidences=evidences, summaries=summaries)


def test_missing_token_writes_failed_manifest_without_leaking_secret(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    search_script = _load_search_script()
    root = _prepare_project_root(tmp_path)
    context = RunContext(
        run_id="run-1",
        stage="phase1_search_candidates",
        started_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        code_commit_sha="0123456789abcdef0123456789abcdef01234567",
        dirty_worktree=False,
    )
    written: dict[str, object] = {}

    with (
        patch.object(search_script, "_project_root", return_value=root),
        patch.object(search_script, "start_run", return_value=context),
        patch.object(search_script, "collect_candidates"),
        patch.object(search_script, "write_manifest") as mocked_manifest,
    ):
        mocked_manifest.side_effect = lambda **kwargs: (
            written.update(kwargs) or root / "manifest.json"
        )
        with patch.dict(search_script.os.environ, {}, clear=True):
            exit_code = search_script.main()

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "fake-token" not in captured.out
    assert "fake-token" not in captured.err
    assert written["status"] == "FAILED"
    assert "GITHUB_TOKEN" in str(written["error"])


def test_successful_run_writes_csvs_and_manifest(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    search_script = _load_search_script()
    root = _prepare_project_root(tmp_path)
    config = load_config(root / "config/config.yaml")
    token_name = config.github.token_environment_variable
    context = RunContext(
        run_id="run-1",
        stage="phase1_search_candidates",
        started_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        code_commit_sha="0123456789abcdef0123456789abcdef01234567",
        dirty_worktree=False,
    )
    manifest_kwargs: dict[str, object] = {}

    def fake_write_manifest(**kwargs: object) -> Path:
        manifest_kwargs.update(kwargs)
        return root / config.paths.manifests / "run-1.json"

    with (
        patch.object(search_script, "_project_root", return_value=root),
        patch.object(search_script, "start_run", return_value=context),
        patch.object(search_script, "collect_candidates", return_value=_collection(300)),
        patch.object(search_script, "write_manifest", side_effect=fake_write_manifest),
        patch.dict(search_script.os.environ, {token_name: "fake-token"}, clear=True),
    ):
        exit_code = search_script.main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "fake-token" not in captured.out
    assert "fake-token" not in captured.err
    assert manifest_kwargs["status"] == "SUCCESS"
    artifacts = cast(list[object], manifest_kwargs["artifacts"])
    assert len(artifacts) == 7

    candidates_csv = root / "data/interim/candidatos_brutos.csv"
    evidences_csv = root / "data/interim/evidencias_busca.csv"
    summary_csv = root / "data/interim/resumo_busca.csv"
    report_json = root / "data/interim/resumo_execucao_fase1.json"

    assert candidates_csv.is_file()
    assert evidences_csv.is_file()
    assert summary_csv.is_file()
    assert report_json.is_file()

    summary_lines = summary_csv.read_text(encoding="utf-8").splitlines()
    assert summary_lines[1].endswith("Z,run-1")

    report = json.loads(report_json.read_text(encoding="utf-8"))
    assert report["status"] == "SUCCESS"
    assert report["candidate_count"] == 300
    assert report["evidence_count"] == 1
    assert report["query_count"] == 3
    assert report["truncated_query_count"] == 1


def test_insufficient_candidates_fails(tmp_path: Path) -> None:
    search_script = _load_search_script()
    root = _prepare_project_root(tmp_path)
    config = load_config(root / "config/config.yaml")
    token_name = config.github.token_environment_variable
    context = RunContext(
        run_id="run-1",
        stage="phase1_search_candidates",
        started_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        code_commit_sha="0123456789abcdef0123456789abcdef01234567",
        dirty_worktree=False,
    )
    manifest_kwargs: dict[str, object] = {}

    def fake_write_manifest(**kwargs: object) -> Path:
        manifest_kwargs.update(kwargs)
        return root / config.paths.manifests / "run-1.json"

    with (
        patch.object(search_script, "_project_root", return_value=root),
        patch.object(search_script, "start_run", return_value=context),
        patch.object(search_script, "collect_candidates", return_value=_collection(299)),
        patch.object(search_script, "write_manifest", side_effect=fake_write_manifest),
        patch.dict(search_script.os.environ, {token_name: "fake-token"}, clear=True),
    ):
        exit_code = search_script.main()

    assert exit_code == 1
    assert manifest_kwargs["status"] == "FAILED"
    assert "299 candidatos" in str(manifest_kwargs["error"])
