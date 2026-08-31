from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from mlops_traceability.config import ResearchConfig, load_config
from mlops_traceability.github_search import SearchCandidateRow, SearchEvidenceRow
from mlops_traceability.sample_screen import (
    RepositorySnapshot,
    ScreeningRow,
    ToolEvidencePaths,
    screen_candidates,
)

CONFIG_PATH = "config/config.yaml"


class FakeGateway:
    def __init__(
        self,
        snapshots: dict[int, RepositorySnapshot | Exception],
        commit_counts: dict[int, int | Exception],
        contributor_counts: dict[int, int | Exception],
        last_human_commits: dict[int, datetime | None | Exception],
        tool_evidence: dict[int, tuple[bool, bool, bool] | Exception],
    ) -> None:
        self.snapshots = snapshots
        self.commit_counts = commit_counts
        self.contributor_counts = contributor_counts
        self.last_human_commits = last_human_commits
        self.tool_evidence = tool_evidence

    def get_repository_snapshot(self, candidate: SearchCandidateRow) -> RepositorySnapshot:
        value = self.snapshots[candidate.repository_numeric_id]
        if isinstance(value, Exception):
            raise value
        return value

    def get_commit_count(self, snapshot: RepositorySnapshot) -> int:
        value = self.commit_counts[snapshot.repository_numeric_id]
        if isinstance(value, Exception):
            raise value
        return value

    def get_contributor_count(self, snapshot: RepositorySnapshot) -> int:
        value = self.contributor_counts[snapshot.repository_numeric_id]
        if isinstance(value, Exception):
            raise value
        return value

    def find_last_human_commit(
        self,
        snapshot: RepositorySnapshot,
        selection_config: object,
        commit_filter_config: object,
    ) -> datetime | None:
        del selection_config, commit_filter_config
        value = self.last_human_commits[snapshot.repository_numeric_id]
        if isinstance(value, Exception):
            raise value
        return value

    def detect_tool_evidence(
        self,
        snapshot: RepositorySnapshot,
        evidence_paths: ToolEvidencePaths,
    ) -> tuple[bool, bool, bool]:
        del evidence_paths
        value = self.tool_evidence[snapshot.repository_numeric_id]
        if isinstance(value, Exception):
            raise value
        return value


def _candidate(
    repository_numeric_id: int,
    *,
    repository_id: str | None = None,
    description: str | None = "ML project",
    is_fork: bool = False,
) -> SearchCandidateRow:
    return SearchCandidateRow(
        repository_numeric_id=repository_numeric_id,
        repository_id=repository_id or f"owner/repo-{repository_numeric_id}",
        repository_url=f"https://github.com/owner/repo-{repository_numeric_id}",
        owner_login="owner",
        is_fork=is_fork,
        description=description,
        discovery_query_count=1,
        discovery_hit_count=1,
        observed_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        run_id="source-run",
    )


def _evidence(repository_numeric_id: int) -> SearchEvidenceRow:
    return SearchEvidenceRow(
        query_id="q1",
        query_expression="alpha",
        page_number=1,
        result_rank=1,
        repository_numeric_id=repository_numeric_id,
        repository_id=f"owner/repo-{repository_numeric_id}",
        file_path="dvc.yaml",
        file_sha="sha-1",
        file_url="https://example.test/evidence",
        run_id="source-run",
    )


def _snapshot(
    candidate: SearchCandidateRow,
    *,
    stars_count: int = 100,
    is_fork: bool = False,
    is_archived: bool = False,
    is_disabled: bool = False,
) -> RepositorySnapshot:
    return RepositorySnapshot(
        repository_numeric_id=candidate.repository_numeric_id,
        repository_id=candidate.repository_id,
        repository_url=candidate.repository_url,
        default_branch="main",
        head_commit_sha="abc123",
        stars_count=stars_count,
        is_fork=is_fork,
        is_archived=is_archived,
        is_disabled=is_disabled,
        observed_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _config() -> ResearchConfig:
    return load_config(CONFIG_PATH)


def _eligible_gateway(candidate: SearchCandidateRow) -> FakeGateway:
    config = _config()
    snapshot = _snapshot(candidate)
    return FakeGateway(
        snapshots={candidate.repository_numeric_id: snapshot},
        commit_counts={candidate.repository_numeric_id: config.selection.min_commits},
        contributor_counts={candidate.repository_numeric_id: config.selection.min_contributors},
        last_human_commits={
            candidate.repository_numeric_id: config.selection.active_after + timedelta(days=1)
        },
        tool_evidence={candidate.repository_numeric_id: (True, False, False)},
    )


def test_screen_candidates_applies_star_threshold() -> None:
    config = _config()
    candidate = _candidate(1)
    rows = screen_candidates(
        [candidate],
        [_evidence(1)],
        _eligible_gateway(candidate),
        config.selection,
        config.strata,
        config.commit_filter,
        run_id="screen-run",
    )
    assert rows[0].decision == "eligible"

    low_star_gateway = FakeGateway(
        snapshots={1: _snapshot(candidate, stars_count=config.selection.min_stars - 1)},
        commit_counts={1: config.selection.min_commits},
        contributor_counts={1: config.selection.min_contributors},
        last_human_commits={1: config.selection.active_after + timedelta(days=1)},
        tool_evidence={1: (True, False, False)},
    )
    low_star_rows = screen_candidates(
        [candidate],
        [_evidence(1)],
        low_star_gateway,
        config.selection,
        config.strata,
        config.commit_filter,
        run_id="screen-run",
    )
    assert low_star_rows[0].decision == "rejected"
    assert low_star_rows[0].primary_reason == "stars_below_minimum"


@pytest.mark.parametrize(
    ("commit_count", "contributor_count", "expected_reason"),
    [
        (300, 5, None),
        (299, 5, "commit_count_below_minimum"),
        (300, 4, "contributor_count_below_minimum"),
    ],
)
def test_screen_candidates_applies_expensive_thresholds(
    commit_count: int,
    contributor_count: int,
    expected_reason: str | None,
) -> None:
    config = _config()
    candidate = _candidate(2)
    gateway = FakeGateway(
        snapshots={2: _snapshot(candidate)},
        commit_counts={2: commit_count},
        contributor_counts={2: contributor_count},
        last_human_commits={2: config.selection.active_after + timedelta(days=1)},
        tool_evidence={2: (True, False, False)},
    )
    rows = screen_candidates(
        [candidate],
        [_evidence(2)],
        gateway,
        config.selection,
        config.strata,
        config.commit_filter,
        run_id="screen-run",
    )

    if expected_reason is None:
        assert rows[0].decision == "eligible"
    else:
        assert rows[0].decision == "rejected"
        assert rows[0].primary_reason == expected_reason


@pytest.mark.parametrize(
    ("last_human_commit", "expected_reason"),
    [
        (datetime(2026, 1, 1, tzinfo=UTC), None),
        (datetime(2025, 9, 1, tzinfo=UTC), "inactive_after_cutoff"),
        (None, "active_commit_not_found"),
    ],
)
def test_screen_candidates_rejects_inactive_repositories(
    last_human_commit: datetime | None,
    expected_reason: str | None,
) -> None:
    config = _config()
    candidate = _candidate(3)
    gateway = FakeGateway(
        snapshots={3: _snapshot(candidate)},
        commit_counts={3: config.selection.min_commits},
        contributor_counts={3: config.selection.min_contributors},
        last_human_commits={3: last_human_commit},
        tool_evidence={3: (True, False, False)},
    )
    rows = screen_candidates(
        [candidate],
        [_evidence(3)],
        gateway,
        config.selection,
        config.strata,
        config.commit_filter,
        run_id="screen-run",
    )

    if expected_reason is None:
        assert rows[0].decision == "eligible"
    else:
        assert rows[0].decision == "rejected"
        assert rows[0].primary_reason == expected_reason


def test_screen_candidates_classifies_the_three_strata() -> None:
    config = _config()
    candidates = [_candidate(10), _candidate(11), _candidate(12), _candidate(13)]
    gateway = FakeGateway(
        snapshots={
            candidate.repository_numeric_id: _snapshot(candidate) for candidate in candidates
        },
        commit_counts={
            candidate.repository_numeric_id: config.selection.min_commits
            for candidate in candidates
        },
        contributor_counts={
            candidate.repository_numeric_id: config.selection.min_contributors
            for candidate in candidates
        },
        last_human_commits={
            candidate.repository_numeric_id: config.selection.active_after + timedelta(days=1)
            for candidate in candidates
        },
        tool_evidence={
            10: (True, False, True),
            11: (False, True, True),
            12: (True, True, True),
            13: (False, False, True),
        },
    )

    rows = screen_candidates(
        candidates,
        [_evidence(candidate.repository_numeric_id) for candidate in candidates],
        gateway,
        config.selection,
        config.strata,
        config.commit_filter,
        run_id="screen-run",
    )

    assert [row.stratum for row in rows[:3]] == [
        "apenas_dvc",
        "apenas_mlflow",
        "dvc_e_mlflow",
    ]
    assert rows[3].decision == "rejected"
    assert rows[3].primary_reason == "tool_evidence_unconfirmed"


def test_screen_candidates_rejects_api_errors_instead_of_marking_rejection() -> None:
    config = _config()
    candidate = _candidate(20)
    gateway = FakeGateway(
        snapshots={20: RuntimeError("snapshot failure")},
        commit_counts={20: config.selection.min_commits},
        contributor_counts={20: config.selection.min_contributors},
        last_human_commits={20: config.selection.active_after + timedelta(days=1)},
        tool_evidence={20: (True, False, False)},
    )
    rows = screen_candidates(
        [candidate],
        [_evidence(20)],
        gateway,
        config.selection,
        config.strata,
        config.commit_filter,
        run_id="screen-run",
    )

    assert rows[0].decision == "error"
    assert rows[0].primary_reason == "repository_snapshot_unavailable"
    assert rows[0].error_detail == "snapshot failure"


def test_screen_candidates_is_deterministic_and_preserves_all_candidates() -> None:
    config = _config()
    candidates = [_candidate(30), _candidate(5), _candidate(18)]
    gateway = FakeGateway(
        snapshots={
            candidate.repository_numeric_id: _snapshot(candidate) for candidate in candidates
        },
        commit_counts={
            candidate.repository_numeric_id: config.selection.min_commits
            for candidate in candidates
        },
        contributor_counts={
            candidate.repository_numeric_id: config.selection.min_contributors
            for candidate in candidates
        },
        last_human_commits={
            candidate.repository_numeric_id: config.selection.active_after + timedelta(days=1)
            for candidate in candidates
        },
        tool_evidence={
            candidate.repository_numeric_id: (True, False, False) for candidate in candidates
        },
    )

    progress: list[tuple[int, int]] = []
    rows = screen_candidates(
        list(reversed(candidates)),
        [_evidence(candidate.repository_numeric_id) for candidate in candidates],
        gateway,
        config.selection,
        config.strata,
        config.commit_filter,
        run_id="screen-run",
        max_workers=2,
        on_result=lambda _row, completed, total: progress.append((completed, total)),
    )

    assert [row.repository_numeric_id for row in rows] == [5, 18, 30]
    assert all(isinstance(row, ScreeningRow) for row in rows)
    assert len(rows) == len(candidates)
    assert progress == [(1, 3), (2, 3), (3, 3)]


def test_screen_candidates_reuses_cached_rows() -> None:
    config = _config()
    candidates = [_candidate(1), _candidate(2)]
    first_gateway = _eligible_gateway(candidates[0])
    existing = screen_candidates(
        [candidates[0]],
        [_evidence(1)],
        first_gateway,
        config.selection,
        config.strata,
        config.commit_filter,
        run_id="first-run",
    )
    second_gateway = _eligible_gateway(candidates[1])
    progress: list[tuple[int, int]] = []

    rows = screen_candidates(
        candidates,
        [_evidence(1), _evidence(2)],
        second_gateway,
        config.selection,
        config.strata,
        config.commit_filter,
        run_id="resumed-run",
        existing_rows=existing,
        on_result=lambda _row, completed, total: progress.append((completed, total)),
    )

    assert [row.repository_numeric_id for row in rows] == [1, 2]
    assert progress == [(2, 2)]
