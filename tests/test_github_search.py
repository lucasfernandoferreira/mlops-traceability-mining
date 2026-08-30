from __future__ import annotations

from datetime import UTC, datetime

import pytest

from mlops_traceability.config import SearchQueryConfig
from mlops_traceability.github_search import (
    RateLimitSnapshot,
    SearchPage,
    SearchResult,
    collect_candidates,
)


class FakeGateway:
    def __init__(
        self,
        pages_by_query: dict[str, list[SearchPage]],
        rate_limits: list[RateLimitSnapshot],
    ) -> None:
        self.pages_by_query = pages_by_query
        self.rate_limits = rate_limits
        self.rate_limit_calls = 0
        self.search_calls: list[tuple[str, int, int]] = []

    def search_page(self, query: str, page: int, per_page: int) -> SearchPage:
        self.search_calls.append((query, page, per_page))
        pages = self.pages_by_query[query]
        if page > len(pages):
            return SearchPage(total_count=0, incomplete_results=False, results=[])
        return pages[page - 1]

    def get_code_search_rate_limit(self) -> RateLimitSnapshot:
        snapshot = self.rate_limits[min(self.rate_limit_calls, len(self.rate_limits) - 1)]
        self.rate_limit_calls += 1
        return snapshot


def _result(
    repository_numeric_id: int,
    repository_id: str,
    *,
    file_path: str,
    file_sha: str,
    file_url: str,
    repository_url: str | None = None,
    owner_login: str = "owner",
    is_fork: bool = False,
    description: str | None = None,
) -> SearchResult:
    return SearchResult(
        repository_numeric_id=repository_numeric_id,
        repository_id=repository_id,
        repository_url=repository_url or f"https://github.com/{repository_id}",
        owner_login=owner_login,
        is_fork=is_fork,
        description=description,
        file_path=file_path,
        file_sha=file_sha,
        file_url=file_url,
    )


def test_collect_candidates_deduplicates_by_numeric_id() -> None:
    queries = [
        SearchQueryConfig(id="q1", expression="alpha"),
        SearchQueryConfig(id="q2", expression="beta"),
    ]
    gateway = FakeGateway(
        {
            "alpha": [
                SearchPage(
                    total_count=1,
                    incomplete_results=False,
                    results=[
                        _result(
                            101,
                            "owner-a/repo-a",
                            file_path="dvc.yaml",
                            file_sha="sha-a",
                            file_url="https://example.test/a",
                        )
                    ],
                )
            ],
            "beta": [
                SearchPage(
                    total_count=1,
                    incomplete_results=False,
                    results=[
                        _result(
                            101,
                            "owner-b/renamed-repo",
                            file_path="other.dvc",
                            file_sha="sha-b",
                            file_url="https://example.test/b",
                        )
                    ],
                )
            ],
        },
        [
            RateLimitSnapshot(remaining=10, reset_at_utc=datetime(2026, 1, 1, tzinfo=UTC)),
        ],
    )

    collection = collect_candidates(
        gateway,
        queries,
        per_page=100,
        max_results_per_query=1000,
        observed_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        run_id="run-1",
    )

    assert len(collection.candidates) == 1
    candidate = collection.candidates[0]
    assert candidate.repository_numeric_id == 101
    assert candidate.discovery_query_count == 2
    assert candidate.discovery_hit_count == 2
    assert len(collection.evidences) == 2
    assert {row.query_id for row in collection.evidences} == {"q1", "q2"}


def test_collect_candidates_preserves_multiple_evidences_for_one_repository() -> None:
    queries = [SearchQueryConfig(id="q1", expression="alpha")]
    gateway = FakeGateway(
        {
            "alpha": [
                SearchPage(
                    total_count=2,
                    incomplete_results=False,
                    results=[
                        _result(
                            201,
                            "owner/repo",
                            file_path="dvc.yaml",
                            file_sha="sha-1",
                            file_url="u1",
                        ),
                        _result(
                            201,
                            "owner/repo",
                            file_path="params.yaml",
                            file_sha="sha-2",
                            file_url="u2",
                        ),
                    ],
                )
            ]
        },
        [RateLimitSnapshot(remaining=10, reset_at_utc=datetime(2026, 1, 1, tzinfo=UTC))],
    )

    collection = collect_candidates(
        gateway,
        queries,
        per_page=100,
        max_results_per_query=1000,
        observed_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        run_id="run-2",
    )

    assert len(collection.candidates) == 1
    assert collection.candidates[0].discovery_hit_count == 2
    assert [row.file_path for row in collection.evidences] == ["dvc.yaml", "params.yaml"]


def test_collect_candidates_stops_when_page_is_empty() -> None:
    queries = [SearchQueryConfig(id="q1", expression="alpha")]
    gateway = FakeGateway(
        {
            "alpha": [
                SearchPage(
                    total_count=2,
                    incomplete_results=False,
                    results=[
                        _result(
                            301,
                            "owner/repo",
                            file_path="dvc.yaml",
                            file_sha="sha-1",
                            file_url="u1",
                        ),
                    ],
                ),
                SearchPage(total_count=2, incomplete_results=False, results=[]),
            ]
        },
        [RateLimitSnapshot(remaining=10, reset_at_utc=datetime(2026, 1, 1, tzinfo=UTC))],
    )

    collection = collect_candidates(
        gateway,
        queries,
        per_page=1,
        max_results_per_query=1000,
        observed_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        run_id="run-3",
    )

    assert len(collection.evidences) == 1
    assert gateway.search_calls == [("alpha", 1, 1), ("alpha", 2, 1)]


def test_collect_candidates_marks_truncation_and_incomplete_results() -> None:
    queries = [SearchQueryConfig(id="q1", expression="alpha")]
    gateway = FakeGateway(
        {
            "alpha": [
                SearchPage(
                    total_count=5,
                    incomplete_results=True,
                    results=[
                        _result(
                            401,
                            "owner/repo",
                            file_path="a",
                            file_sha="sha-1",
                            file_url="u1",
                        ),
                        _result(
                            402,
                            "owner/repo-2",
                            file_path="b",
                            file_sha="sha-2",
                            file_url="u2",
                        ),
                    ],
                ),
                SearchPage(
                    total_count=5,
                    incomplete_results=True,
                    results=[
                        _result(
                            403,
                            "owner/repo-3",
                            file_path="c",
                            file_sha="sha-3",
                            file_url="u3",
                        ),
                        _result(
                            404,
                            "owner/repo-4",
                            file_path="d",
                            file_sha="sha-4",
                            file_url="u4",
                        ),
                    ],
                ),
            ]
        },
        [RateLimitSnapshot(remaining=10, reset_at_utc=datetime(2026, 1, 1, tzinfo=UTC))],
    )

    collection = collect_candidates(
        gateway,
        queries,
        per_page=2,
        max_results_per_query=3,
        observed_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        run_id="run-4",
    )

    assert len(collection.evidences) == 3
    summary = collection.summaries[0]
    assert summary.incomplete_results is True
    assert summary.truncated is True
    assert summary.retrieved_hit_count == 3
    assert summary.reported_total_count == 5


def test_collect_candidates_waits_for_rate_limit_reset() -> None:
    queries = [SearchQueryConfig(id="q1", expression="alpha")]
    gateway = FakeGateway(
        {
            "alpha": [SearchPage(total_count=0, incomplete_results=False, results=[])],
        },
        [RateLimitSnapshot(remaining=1, reset_at_utc=datetime(2026, 1, 1, 12, 0, 10, tzinfo=UTC))],
    )
    sleeps: list[float] = []
    current_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

    def fake_now() -> datetime:
        return current_time

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    collect_candidates(
        gateway,
        queries,
        per_page=100,
        max_results_per_query=1000,
        observed_at_utc=current_time,
        run_id="run-5",
        rate_limit_reserve=1,
        reset_buffer_seconds=2,
        sleep_func=fake_sleep,
        now_func=fake_now,
    )

    assert len(sleeps) == 1
    assert sleeps[0] == pytest.approx(12.0)


def test_collect_candidates_sorts_output_deterministically() -> None:
    queries = [
        SearchQueryConfig(id="q2", expression="beta"),
        SearchQueryConfig(id="q1", expression="alpha"),
    ]
    gateway = FakeGateway(
        {
            "alpha": [
                SearchPage(
                    total_count=1,
                    incomplete_results=False,
                    results=[
                        _result(501, "owner/z", file_path="z.txt", file_sha="sha-z", file_url="uz"),
                    ],
                )
            ],
            "beta": [
                SearchPage(
                    total_count=1,
                    incomplete_results=False,
                    results=[
                        _result(100, "owner/a", file_path="a.txt", file_sha="sha-a", file_url="ua"),
                    ],
                )
            ],
        },
        [RateLimitSnapshot(remaining=10, reset_at_utc=datetime(2026, 1, 1, tzinfo=UTC))],
    )

    collection = collect_candidates(
        gateway,
        queries,
        per_page=100,
        max_results_per_query=1000,
        observed_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        run_id="run-6",
    )

    assert [row.repository_numeric_id for row in collection.candidates] == [100, 501]
    assert [row.query_id for row in collection.evidences] == ["q1", "q2"]
    assert [row.query_id for row in collection.summaries] == ["q2", "q1"]
