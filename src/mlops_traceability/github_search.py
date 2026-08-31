"""Descoberta paginada de candidatos a partir da API de busca do GitHub."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from github import Auth, Github

from mlops_traceability.config import SearchQueryConfig


@dataclass(frozen=True)
class RateLimitSnapshot:
    remaining: int
    reset_at_utc: datetime


@dataclass(frozen=True)
class SearchResult:
    repository_numeric_id: int
    repository_id: str
    repository_url: str
    owner_login: str
    is_fork: bool
    description: str | None
    file_path: str
    file_sha: str
    file_url: str


@dataclass(frozen=True)
class SearchPage:
    total_count: int
    incomplete_results: bool
    results: list[SearchResult]


@dataclass(frozen=True)
class SearchEvidenceRow:
    query_id: str
    query_expression: str
    page_number: int
    result_rank: int
    repository_numeric_id: int
    repository_id: str
    file_path: str
    file_sha: str
    file_url: str
    run_id: str


@dataclass(frozen=True)
class SearchCandidateRow:
    repository_numeric_id: int
    repository_id: str
    repository_url: str
    owner_login: str
    is_fork: bool
    description: str | None
    discovery_query_count: int
    discovery_hit_count: int
    observed_at_utc: datetime
    run_id: str


@dataclass(frozen=True)
class SearchSummaryRow:
    query_id: str
    query_expression: str
    reported_total_count: int
    retrieved_hit_count: int
    unique_repository_count: int
    incomplete_results: bool
    truncated: bool
    started_at_utc: datetime
    finished_at_utc: datetime
    run_id: str


@dataclass(frozen=True)
class SearchCollection:
    candidates: list[SearchCandidateRow]
    evidences: list[SearchEvidenceRow]
    summaries: list[SearchSummaryRow]


class SearchGateway(Protocol):
    def search_page(self, query: str, page: int, per_page: int) -> SearchPage:
        """Executa uma consulta e devolve a página pedida."""

    def get_code_search_rate_limit(self) -> RateLimitSnapshot:
        """Devolve o snapshot da cota de Code Search."""


class PyGithubSearchGateway:
    """Adaptador real da API do GitHub via PyGithub."""

    def __init__(self, *, token: str, per_page: int, request_timeout_seconds: int) -> None:
        self._github = Github(
            auth=Auth.Token(token),
            per_page=per_page,
            timeout=request_timeout_seconds,
        )

    def search_page(self, query: str, page: int, per_page: int) -> SearchPage:
        paginated = self._github.search_code(query)
        results = paginated.get_page(page - 1)

        return SearchPage(
            total_count=paginated.totalCount,
            incomplete_results=bool(paginated.incomplete_results),
            results=[_convert_search_result(result) for result in results],
        )

    def get_code_search_rate_limit(self) -> RateLimitSnapshot:
        overview = self._github.get_rate_limit()
        rate = overview.resources.code_search
        return RateLimitSnapshot(remaining=rate.remaining, reset_at_utc=rate.reset.astimezone(UTC))


@dataclass
class _CandidateAccumulator:
    repository_numeric_id: int
    repository_id: str
    repository_url: str
    owner_login: str
    is_fork: bool
    description: str | None
    observed_at_utc: datetime
    run_id: str
    query_ids: set[str]
    hit_count: int = 0

    def record_hit(self, query_id: str) -> None:
        self.query_ids.add(query_id)
        self.hit_count += 1

    def to_row(self) -> SearchCandidateRow:
        return SearchCandidateRow(
            repository_numeric_id=self.repository_numeric_id,
            repository_id=self.repository_id,
            repository_url=self.repository_url,
            owner_login=self.owner_login,
            is_fork=self.is_fork,
            description=self.description,
            discovery_query_count=len(self.query_ids),
            discovery_hit_count=self.hit_count,
            observed_at_utc=self.observed_at_utc,
            run_id=self.run_id,
        )


def _convert_search_result(result: Any) -> SearchResult:
    repository = result.repository
    owner = repository.owner

    return SearchResult(
        repository_numeric_id=int(repository.id),
        repository_id=str(repository.full_name),
        repository_url=str(repository.html_url),
        owner_login=str(owner.login),
        is_fork=bool(repository.fork),
        description=repository.description,
        file_path=str(result.path),
        file_sha=str(result.sha),
        file_url=str(result.html_url),
    )


def _sleep_until_reset(
    *,
    snapshot: RateLimitSnapshot,
    reset_buffer_seconds: int,
    sleep_func: Callable[[float], None],
    now_func: Callable[[], datetime],
) -> float:
    current_time = now_func()
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("now_func precisa retornar datetimes com fuso horário.")

    target_time = snapshot.reset_at_utc + timedelta(seconds=reset_buffer_seconds)
    remaining_seconds = (target_time - current_time).total_seconds()
    if remaining_seconds > 0:
        sleep_func(remaining_seconds)
        return remaining_seconds
    return 0.0


def collect_candidates(
    gateway: SearchGateway,
    queries: list[SearchQueryConfig],
    *,
    per_page: int,
    max_results_per_query: int,
    observed_at_utc: datetime,
    run_id: str,
    rate_limit_reserve: int = 1,
    reset_buffer_seconds: int = 2,
    sleep_func: Callable[[float], None] = time.sleep,
    now_func: Callable[[], datetime] = lambda: datetime.now(UTC),
    on_event: Callable[[str, dict[str, Any]], None] | None = None,
) -> SearchCollection:
    if observed_at_utc.tzinfo is None or observed_at_utc.utcoffset() is None:
        raise ValueError("observed_at_utc precisa conter fuso horário.")

    observed_at_utc = observed_at_utc.astimezone(UTC)
    candidate_index: dict[int, _CandidateAccumulator] = {}
    evidence_rows: list[SearchEvidenceRow] = []
    summary_rows: list[SearchSummaryRow] = []

    for query_index, query in enumerate(queries, start=1):
        started_at_utc = now_func().astimezone(UTC)
        page_number = 1
        retrieved_hit_count = 0
        reported_total_count = 0
        incomplete_results = False
        if on_event is not None:
            on_event(
                "query_started",
                {
                    "query_id": query.id,
                    "query_index": query_index,
                    "query_total": len(queries),
                },
            )

        while retrieved_hit_count < max_results_per_query:
            snapshot = gateway.get_code_search_rate_limit()
            if snapshot.remaining <= rate_limit_reserve:
                wait_target = snapshot.reset_at_utc + timedelta(seconds=reset_buffer_seconds)
                wait_seconds = max(0.0, (wait_target - now_func()).total_seconds())
                if on_event is not None:
                    on_event(
                        "rate_limit_wait",
                        {
                            "query_id": query.id,
                            "wait_seconds": round(wait_seconds, 1),
                            "reset_at_utc": snapshot.reset_at_utc,
                        },
                    )
                _sleep_until_reset(
                    snapshot=snapshot,
                    reset_buffer_seconds=reset_buffer_seconds,
                    sleep_func=sleep_func,
                    now_func=now_func,
                )

            page = gateway.search_page(query.expression, page_number, per_page)
            if page_number == 1 or page.total_count > reported_total_count:
                reported_total_count = page.total_count
            incomplete_results = incomplete_results or page.incomplete_results
            if on_event is not None:
                on_event(
                    "page_collected",
                    {
                        "query_id": query.id,
                        "page": page_number,
                        "page_results": len(page.results),
                        "reported_total": reported_total_count,
                        "retrieved_before_page": retrieved_hit_count,
                    },
                )

            if not page.results:
                break

            for result_rank, result in enumerate(page.results, start=1):
                if retrieved_hit_count >= max_results_per_query:
                    break

                evidence_rows.append(
                    SearchEvidenceRow(
                        query_id=query.id,
                        query_expression=query.expression,
                        page_number=page_number,
                        result_rank=result_rank,
                        repository_numeric_id=result.repository_numeric_id,
                        repository_id=result.repository_id,
                        file_path=result.file_path,
                        file_sha=result.file_sha,
                        file_url=result.file_url,
                        run_id=run_id,
                    )
                )

                accumulator = candidate_index.get(result.repository_numeric_id)
                if accumulator is None:
                    accumulator = _CandidateAccumulator(
                        repository_numeric_id=result.repository_numeric_id,
                        repository_id=result.repository_id,
                        repository_url=result.repository_url,
                        owner_login=result.owner_login,
                        is_fork=result.is_fork,
                        description=result.description,
                        observed_at_utc=observed_at_utc,
                        run_id=run_id,
                        query_ids=set(),
                    )
                    candidate_index[result.repository_numeric_id] = accumulator

                accumulator.record_hit(query.id)
                retrieved_hit_count += 1

            if retrieved_hit_count >= max_results_per_query:
                break

            if len(page.results) < per_page or retrieved_hit_count >= reported_total_count:
                break

            page_number += 1

        truncated = (
            reported_total_count > max_results_per_query
            or retrieved_hit_count >= max_results_per_query
        )
        unique_repository_count = len(
            {row.repository_numeric_id for row in evidence_rows if row.query_id == query.id}
        )
        summary_rows.append(
            SearchSummaryRow(
                query_id=query.id,
                query_expression=query.expression,
                reported_total_count=reported_total_count,
                retrieved_hit_count=retrieved_hit_count,
                unique_repository_count=unique_repository_count,
                incomplete_results=incomplete_results,
                truncated=truncated,
                started_at_utc=started_at_utc,
                finished_at_utc=now_func().astimezone(UTC),
                run_id=run_id,
            )
        )
        if on_event is not None:
            on_event(
                "query_finished",
                {
                    "query_id": query.id,
                    "query_index": query_index,
                    "query_total": len(queries),
                    "retrieved_hits": retrieved_hit_count,
                    "unique_repositories": unique_repository_count,
                    "truncated": truncated,
                },
            )

    sorted_candidates = sorted(
        (accumulator.to_row() for accumulator in candidate_index.values()),
        key=lambda row: (row.repository_numeric_id, row.repository_id),
    )
    sorted_evidence = sorted(
        evidence_rows,
        key=lambda row: (
            row.query_id,
            row.page_number,
            row.result_rank,
            row.repository_numeric_id,
            row.file_path,
        ),
    )
    return SearchCollection(
        candidates=sorted_candidates,
        evidences=sorted_evidence,
        summaries=summary_rows,
    )
