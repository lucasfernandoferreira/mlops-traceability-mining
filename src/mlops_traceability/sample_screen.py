"""Triagem automática dos candidatos brutos da Fase 1."""

from __future__ import annotations

import ast
import threading
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from github import Auth, Github

from mlops_traceability.config import CommitFilterConfig, SelectionConfig, StrataConfig
from mlops_traceability.github_search import SearchCandidateRow, SearchEvidenceRow


@dataclass(frozen=True)
class RepositorySnapshot:
    repository_numeric_id: int
    repository_id: str
    repository_url: str
    default_branch: str
    head_commit_sha: str
    stars_count: int
    is_fork: bool
    is_archived: bool
    is_disabled: bool
    observed_at_utc: datetime
    repository_handle: Any = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class ScreeningRow:
    repository_numeric_id: int
    repository_id: str
    repository_url: str
    observed_at_utc: datetime
    head_commit_sha: str
    stars_count: int | None
    commit_count: int | None
    contributor_count: int | None
    last_human_commit_at_utc: datetime | None
    dvc_detected: bool | None
    mlflow_detected: bool | None
    mlruns_detected: bool | None
    stratum: str | None
    decision: str
    primary_reason: str | None
    decision_reasons: tuple[str, ...]
    error_detail: str | None
    cheap_gate_status: str
    expensive_gate_status: str
    exclusion_stage: str | None
    run_id: str


class ScreeningGateway(Protocol):
    def get_repository_snapshot(self, candidate: SearchCandidateRow) -> RepositorySnapshot:
        """Obtém o snapshot observável do repositório."""

    def get_commit_count(self, snapshot: RepositorySnapshot) -> int:
        """Retorna a contagem total de commits observáveis."""

    def get_contributor_count(self, snapshot: RepositorySnapshot) -> int:
        """Retorna a contagem total de contribuidores observáveis."""

    def find_last_human_commit(
        self,
        snapshot: RepositorySnapshot,
        selection_config: SelectionConfig,
        commit_filter_config: CommitFilterConfig,
    ) -> datetime | None:
        """Retorna o último commit humano elegível, se houver."""

    def detect_tool_evidence(
        self,
        snapshot: RepositorySnapshot,
        mlflow_evidence_paths: Sequence[str],
    ) -> tuple[bool, bool, bool]:
        """Detecta DVC, MLflow e mlruns, nesta ordem."""


@dataclass(frozen=True)
class _CoreRateLimitSnapshot:
    remaining: int
    reset_at_utc: datetime


def _format_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime precisa conter fuso horário.")
    return value.astimezone(UTC)


def _sleep_until_reset(
    *,
    snapshot: _CoreRateLimitSnapshot,
    reset_buffer_seconds: int,
    sleep_func: Any,
    now_func: Any,
) -> None:
    current_time = now_func()
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("now_func precisa retornar datetimes com fuso horário.")

    target_time = snapshot.reset_at_utc + timedelta(seconds=reset_buffer_seconds)
    remaining_seconds = (target_time - current_time).total_seconds()
    if remaining_seconds > 0:
        sleep_func(remaining_seconds)


def _contains_bot_marker(text: str, bot_patterns: Sequence[str]) -> bool:
    normalized = text.casefold()
    return any(pattern.casefold() in normalized for pattern in bot_patterns)


def _commit_is_merge(commit: Any) -> bool:
    parents = getattr(commit, "parents", ())
    try:
        return len(parents) > 1
    except TypeError:
        return False


def _commit_text(commit: Any) -> str:
    commit_data = getattr(commit, "commit", None)
    author = getattr(commit_data, "author", None)
    committer = getattr(commit_data, "committer", None)
    author_name = getattr(author, "name", "")
    author_email = getattr(author, "email", "")
    committer_name = getattr(committer, "name", "")
    committer_email = getattr(committer, "email", "")
    message = getattr(commit_data, "message", "")
    login = getattr(getattr(commit, "author", None), "login", "")
    return "\n".join(
        [
            str(author_name),
            str(author_email),
            str(committer_name),
            str(committer_email),
            str(message),
            str(login),
        ]
    )


def _commit_datetime(commit: Any) -> datetime:
    commit_data = getattr(commit, "commit", None)
    author = getattr(commit_data, "author", None)
    commit_date = getattr(author, "date", None)
    if not isinstance(commit_date, datetime):
        raise ValueError("Commit sem data de autoria observável.")
    return _format_datetime(commit_date)


def _python_imports_mlflow(source: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "mlflow" or alias.name.startswith("mlflow."):
                    return True
        elif isinstance(node, ast.ImportFrom):
            if node.module == "mlflow" or (
                node.module is not None and node.module.startswith("mlflow.")
            ):
                return True

    return False


def _content_text(content: Any) -> str:
    decoded = getattr(content, "decoded_content", b"")
    if isinstance(decoded, bytes):
        return decoded.decode("utf-8", errors="ignore")
    return str(decoded)


class GitHubScreeningGateway:
    """Gateway real para a triagem da amostra usando PyGithub."""

    def __init__(
        self,
        *,
        token: str,
        per_page: int,
        request_timeout_seconds: int,
        core_reserve: int,
        reset_buffer_seconds: int,
        sleep_func: Any = time.sleep,
        now_func: Any = lambda: datetime.now(UTC),
        github_client: Github | None = None,
        on_rate_limit_wait: Callable[[float, datetime], None] | None = None,
    ) -> None:
        self._token = token
        self._per_page = per_page
        self._request_timeout_seconds = request_timeout_seconds
        self._github_override = github_client
        self._thread_local = threading.local()
        self._core_reserve = core_reserve
        self._reset_buffer_seconds = reset_buffer_seconds
        self._sleep_func = sleep_func
        self._now_func = now_func
        self._on_rate_limit_wait = on_rate_limit_wait
        self._rate_limit_lock = threading.Lock()
        self._estimated_remaining: int | None = None
        self._next_rate_refresh = 0.0

    def _client(self) -> Any:
        if self._github_override is not None:
            return self._github_override
        client = getattr(self._thread_local, "github", None)
        if client is None:
            client = Github(
                auth=Auth.Token(self._token),
                per_page=self._per_page,
                timeout=self._request_timeout_seconds,
            )
            self._thread_local.github = client
        return client

    def _core_rate_limit_snapshot(self, client: Any) -> _CoreRateLimitSnapshot:
        overview = client.get_rate_limit()
        rate = overview.resources.core
        return _CoreRateLimitSnapshot(
            remaining=rate.remaining,
            reset_at_utc=rate.reset.astimezone(UTC),
        )

    def _wait_for_core_budget(self) -> None:
        with self._rate_limit_lock:
            monotonic_now = time.monotonic()
            if (
                self._estimated_remaining is None
                or monotonic_now >= self._next_rate_refresh
                or self._estimated_remaining <= self._core_reserve
            ):
                snapshot = self._core_rate_limit_snapshot(self._client())
                self._estimated_remaining = snapshot.remaining
                self._next_rate_refresh = monotonic_now + 30
                if snapshot.remaining <= self._core_reserve:
                    target = snapshot.reset_at_utc + timedelta(seconds=self._reset_buffer_seconds)
                    wait_seconds = max(0.0, (target - self._now_func()).total_seconds())
                    if self._on_rate_limit_wait is not None and wait_seconds > 0:
                        self._on_rate_limit_wait(wait_seconds, snapshot.reset_at_utc)
                    _sleep_until_reset(
                        snapshot=snapshot,
                        reset_buffer_seconds=self._reset_buffer_seconds,
                        sleep_func=self._sleep_func,
                        now_func=self._now_func,
                    )
                    self._estimated_remaining = None
                    self._next_rate_refresh = 0.0
                    return

            if self._estimated_remaining is not None:
                self._estimated_remaining -= 1

    def _repo(self, repository_numeric_id: int) -> Any:
        self._wait_for_core_budget()
        return self._client().get_repo(repository_numeric_id)

    def _snapshot_repo(self, snapshot: RepositorySnapshot) -> Any:
        if snapshot.repository_handle is not None:
            return snapshot.repository_handle
        return self._repo(snapshot.repository_numeric_id)

    def get_repository_snapshot(self, candidate: SearchCandidateRow) -> RepositorySnapshot:
        repo = self._repo(candidate.repository_numeric_id)
        self._wait_for_core_budget()
        branch = repo.get_branch(repo.default_branch)
        head_commit_sha = str(branch.commit.sha)
        return RepositorySnapshot(
            repository_numeric_id=candidate.repository_numeric_id,
            repository_id=str(repo.full_name),
            repository_url=str(repo.html_url),
            default_branch=str(repo.default_branch),
            head_commit_sha=head_commit_sha,
            stars_count=int(repo.stargazers_count),
            is_fork=bool(repo.fork),
            is_archived=bool(repo.archived),
            is_disabled=bool(repo.disabled),
            observed_at_utc=_format_datetime(datetime.now(UTC)),
            repository_handle=repo,
        )

    def get_commit_count(self, snapshot: RepositorySnapshot) -> int:
        repo = self._snapshot_repo(snapshot)
        self._wait_for_core_budget()
        commits = repo.get_commits(sha=snapshot.default_branch)
        return int(commits.totalCount)

    def get_contributor_count(self, snapshot: RepositorySnapshot) -> int:
        repo = self._snapshot_repo(snapshot)
        self._wait_for_core_budget()
        contributors = repo.get_contributors()
        return int(contributors.totalCount)

    def find_last_human_commit(
        self,
        snapshot: RepositorySnapshot,
        selection_config: SelectionConfig,
        commit_filter_config: CommitFilterConfig,
    ) -> datetime | None:
        repo = self._snapshot_repo(snapshot)
        self._wait_for_core_budget()
        commits = repo.get_commits(sha=snapshot.default_branch)
        cutoff = selection_config.active_after.astimezone(UTC)

        for commit in commits:
            commit_date = _commit_datetime(commit)
            if commit_date <= cutoff:
                break
            commit_text = _commit_text(commit)
            if commit_filter_config.exclude_merges and _commit_is_merge(commit):
                continue
            if commit_filter_config.exclude_bots and _contains_bot_marker(
                commit_text,
                commit_filter_config.bot_patterns,
            ):
                continue
            return commit_date

        return None

    def detect_tool_evidence(
        self,
        snapshot: RepositorySnapshot,
        mlflow_evidence_paths: Sequence[str],
    ) -> tuple[bool, bool, bool]:
        repo = self._snapshot_repo(snapshot)
        self._wait_for_core_budget()
        tree = repo.get_git_tree(snapshot.head_commit_sha, recursive=True)
        tree_raw = getattr(tree, "raw_data", {})
        if isinstance(tree_raw, dict) and tree_raw.get("truncated"):
            raise RuntimeError("Git tree truncado; não é possível confirmar evidências.")

        tree_items = list(getattr(tree, "tree", []))
        paths = [str(getattr(item, "path", "")) for item in tree_items]
        dvc_detected = any(path == "dvc.yaml" or path.endswith(".dvc") for path in paths)
        mlruns_detected = any(path == "mlruns" or path.startswith("mlruns/") for path in paths)
        mlflow_detected = False

        available_paths = set(paths)
        paths_to_confirm = sorted(
            {
                path
                for path in mlflow_evidence_paths
                if path.endswith(".py") and path in available_paths
            }
        )
        for path in paths_to_confirm:
            if not path.endswith(".py"):
                continue
            self._wait_for_core_budget()
            content = repo.get_contents(path, ref=snapshot.head_commit_sha)
            if isinstance(content, list):
                continue
            if _python_imports_mlflow(_content_text(content)):
                mlflow_detected = True
                break

        return dvc_detected, mlflow_detected, mlruns_detected


def _utc_datetime(value: datetime) -> datetime:
    return _format_datetime(value)


def _contains_forbidden_term(text: str, forbidden_terms: Sequence[str]) -> bool:
    normalized = text.casefold()
    return any(term.casefold() in normalized for term in forbidden_terms)


def _classify_stratum(dvc_detected: bool, mlflow_detected: bool) -> str | None:
    if dvc_detected and mlflow_detected:
        return "dvc_e_mlflow"
    if dvc_detected:
        return "apenas_dvc"
    if mlflow_detected:
        return "apenas_mlflow"
    return None


def _row(
    *,
    candidate: SearchCandidateRow,
    snapshot: RepositorySnapshot | None,
    run_id: str,
    decision: str,
    primary_reason: str | None,
    decision_reasons: Sequence[str],
    error_detail: str | None,
    cheap_gate_status: str,
    expensive_gate_status: str,
    exclusion_stage: str | None,
    commit_count: int | None = None,
    contributor_count: int | None = None,
    last_human_commit_at_utc: datetime | None = None,
    dvc_detected: bool | None = None,
    mlflow_detected: bool | None = None,
    mlruns_detected: bool | None = None,
    stratum: str | None = None,
) -> ScreeningRow:
    return ScreeningRow(
        repository_numeric_id=candidate.repository_numeric_id,
        repository_id=candidate.repository_id,
        repository_url=candidate.repository_url if snapshot is None else snapshot.repository_url,
        observed_at_utc=candidate.observed_at_utc,
        head_commit_sha="" if snapshot is None else snapshot.head_commit_sha,
        stars_count=None if snapshot is None else snapshot.stars_count,
        commit_count=commit_count,
        contributor_count=contributor_count,
        last_human_commit_at_utc=last_human_commit_at_utc,
        dvc_detected=dvc_detected,
        mlflow_detected=mlflow_detected,
        mlruns_detected=mlruns_detected,
        stratum=stratum,
        decision=decision,
        primary_reason=primary_reason,
        decision_reasons=tuple(decision_reasons),
        error_detail=error_detail,
        cheap_gate_status=cheap_gate_status,
        expensive_gate_status=expensive_gate_status,
        exclusion_stage=exclusion_stage,
        run_id=run_id,
    )


def _screen_candidate(
    candidate: SearchCandidateRow,
    gateway: ScreeningGateway,
    selection_config: SelectionConfig,
    strata_config: StrataConfig,
    commit_filter_config: CommitFilterConfig,
    *,
    run_id: str,
    mlflow_evidence_paths: Sequence[str],
) -> ScreeningRow:
    try:
        snapshot = gateway.get_repository_snapshot(candidate)
    except Exception as exc:  # noqa: BLE001
        return _row(
            candidate=candidate,
            snapshot=None,
            run_id=run_id,
            decision="error",
            primary_reason="repository_snapshot_unavailable",
            decision_reasons=("repository_snapshot_unavailable",),
            error_detail=str(exc),
            cheap_gate_status="error",
            expensive_gate_status="not_evaluated",
            exclusion_stage="snapshot",
        )

    cheap_failures: list[str] = []
    if selection_config.exclude_forks and snapshot.is_fork:
        cheap_failures.append("fork_excluded")
    if selection_config.exclude_archived and snapshot.is_archived:
        cheap_failures.append("archived_excluded")
    if snapshot.is_disabled:
        cheap_failures.append("disabled_excluded")

    searchable_text = f"{candidate.repository_id}\n{candidate.description or ''}"
    if _contains_forbidden_term(searchable_text, selection_config.forbidden_terms):
        cheap_failures.append("forbidden_term_detected")
    if snapshot.stars_count < selection_config.min_stars:
        cheap_failures.append("stars_below_minimum")

    if cheap_failures:
        return _row(
            candidate=candidate,
            snapshot=snapshot,
            run_id=run_id,
            decision="rejected",
            primary_reason=cheap_failures[0],
            decision_reasons=cheap_failures,
            error_detail=None,
            cheap_gate_status="failed",
            expensive_gate_status="not_evaluated",
            exclusion_stage="cheap",
        )

    try:
        commit_count = gateway.get_commit_count(snapshot)
        if commit_count < selection_config.min_commits:
            return _row(
                candidate=candidate,
                snapshot=snapshot,
                run_id=run_id,
                decision="rejected",
                primary_reason="commit_count_below_minimum",
                decision_reasons=("commit_count_below_minimum",),
                error_detail=None,
                commit_count=commit_count,
                cheap_gate_status="passed",
                expensive_gate_status="failed",
                exclusion_stage="expensive",
            )

        contributor_count = gateway.get_contributor_count(snapshot)
        if contributor_count < selection_config.min_contributors:
            return _row(
                candidate=candidate,
                snapshot=snapshot,
                run_id=run_id,
                decision="rejected",
                primary_reason="contributor_count_below_minimum",
                decision_reasons=("contributor_count_below_minimum",),
                error_detail=None,
                commit_count=commit_count,
                contributor_count=contributor_count,
                cheap_gate_status="passed",
                expensive_gate_status="failed",
                exclusion_stage="expensive",
            )

        last_human_commit_at_utc = gateway.find_last_human_commit(
            snapshot,
            selection_config,
            commit_filter_config,
        )
        if last_human_commit_at_utc is None:
            return _row(
                candidate=candidate,
                snapshot=snapshot,
                run_id=run_id,
                decision="rejected",
                primary_reason="active_commit_not_found",
                decision_reasons=("active_commit_not_found",),
                error_detail=None,
                commit_count=commit_count,
                contributor_count=contributor_count,
                cheap_gate_status="passed",
                expensive_gate_status="failed",
                exclusion_stage="expensive",
            )

        last_human_commit_at_utc = _utc_datetime(last_human_commit_at_utc)
        if last_human_commit_at_utc <= selection_config.active_after.astimezone(UTC):
            return _row(
                candidate=candidate,
                snapshot=snapshot,
                run_id=run_id,
                decision="rejected",
                primary_reason="inactive_after_cutoff",
                decision_reasons=("inactive_after_cutoff",),
                error_detail=None,
                commit_count=commit_count,
                contributor_count=contributor_count,
                last_human_commit_at_utc=last_human_commit_at_utc,
                cheap_gate_status="passed",
                expensive_gate_status="failed",
                exclusion_stage="expensive",
            )

        dvc_detected, mlflow_detected, mlruns_detected = gateway.detect_tool_evidence(
            snapshot,
            mlflow_evidence_paths,
        )
    except Exception as exc:  # noqa: BLE001
        return _row(
            candidate=candidate,
            snapshot=snapshot,
            run_id=run_id,
            decision="error",
            primary_reason="expensive_gate_unavailable",
            decision_reasons=("expensive_gate_unavailable",),
            error_detail=str(exc),
            cheap_gate_status="passed",
            expensive_gate_status="error",
            exclusion_stage="expensive",
        )

    stratum = _classify_stratum(dvc_detected, mlflow_detected)
    expensive_failures: list[str] = []
    if stratum is None:
        expensive_failures.append("tool_evidence_unconfirmed")
    elif stratum not in strata_config.required:
        expensive_failures.append("stratum_not_required")

    return _row(
        candidate=candidate,
        snapshot=snapshot,
        run_id=run_id,
        decision="rejected" if expensive_failures else "eligible",
        primary_reason=expensive_failures[0] if expensive_failures else "eligible",
        decision_reasons=expensive_failures or ("eligible",),
        error_detail=None,
        commit_count=commit_count,
        contributor_count=contributor_count,
        last_human_commit_at_utc=last_human_commit_at_utc,
        dvc_detected=dvc_detected,
        mlflow_detected=mlflow_detected,
        mlruns_detected=mlruns_detected,
        stratum=stratum,
        cheap_gate_status="passed",
        expensive_gate_status="failed" if expensive_failures else "passed",
        exclusion_stage="expensive" if expensive_failures else None,
    )


def screen_candidates(
    candidates: Sequence[SearchCandidateRow],
    evidences: Sequence[SearchEvidenceRow],
    gateway: ScreeningGateway,
    selection_config: SelectionConfig,
    strata_config: StrataConfig,
    commit_filter_config: CommitFilterConfig,
    *,
    run_id: str,
    max_workers: int = 1,
    existing_rows: Sequence[ScreeningRow] = (),
    on_result: Callable[[ScreeningRow, int, int], None] | None = None,
) -> list[ScreeningRow]:
    """Aplica os filtros baratos e caros sobre os candidatos da Fase 1."""

    if max_workers < 1:
        raise ValueError("max_workers precisa ser maior que zero")

    sorted_candidates = sorted(
        candidates,
        key=lambda row: (row.repository_numeric_id, row.repository_id),
    )
    candidate_ids = {candidate.repository_numeric_id for candidate in sorted_candidates}
    rows_by_id = {
        row.repository_numeric_id: row
        for row in existing_rows
        if row.repository_numeric_id in candidate_ids
    }
    evidence_paths: dict[int, list[str]] = {}
    for evidence in evidences:
        if "mlflow" in evidence.query_expression.casefold():
            evidence_paths.setdefault(evidence.repository_numeric_id, []).append(evidence.file_path)

    pending = [
        candidate
        for candidate in sorted_candidates
        if candidate.repository_numeric_id not in rows_by_id
    ]
    total = len(sorted_candidates)

    def process(candidate: SearchCandidateRow) -> ScreeningRow:
        return _screen_candidate(
            candidate,
            gateway,
            selection_config,
            strata_config,
            commit_filter_config,
            run_id=run_id,
            mlflow_evidence_paths=evidence_paths.get(candidate.repository_numeric_id, ()),
        )

    if max_workers == 1:
        completed = len(rows_by_id)
        for candidate in pending:
            row = process(candidate)
            rows_by_id[candidate.repository_numeric_id] = row
            completed += 1
            if on_result is not None:
                on_result(row, completed, total)
    else:
        executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="screen")
        try:
            futures = {executor.submit(process, candidate): candidate for candidate in pending}
            completed = len(rows_by_id)
            for future in as_completed(futures):
                row = future.result()
                rows_by_id[row.repository_numeric_id] = row
                completed += 1
                if on_result is not None:
                    on_result(row, completed, total)
        except BaseException:
            for future in futures:
                future.cancel()
            executor.shutdown(wait=True, cancel_futures=True)
            raise
        else:
            executor.shutdown(wait=True)

    return [rows_by_id[candidate.repository_numeric_id] for candidate in sorted_candidates]
