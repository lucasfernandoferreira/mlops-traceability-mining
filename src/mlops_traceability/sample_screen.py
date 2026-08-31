"""Triagem automática dos candidatos brutos da Fase 1."""

from __future__ import annotations

import ast
import re
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import partial
from typing import Any, Protocol

from github import Auth, Github
from github.GithubException import GithubException

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
class ToolEvidencePaths:
    dvc_paths: tuple[str, ...] = ()
    mlflow_paths: tuple[str, ...] = ()


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
        evidence_paths: ToolEvidencePaths,
    ) -> tuple[bool, bool, bool]:
        """Detecta DVC, MLflow e mlruns, nesta ordem."""


@dataclass(frozen=True)
class _CoreRateLimitSnapshot:
    remaining: int
    reset_at_utc: datetime


class GitHubRateLimitCircuitOpen(RuntimeError):
    """Indica que a execução desistiu de esperar por novos retries da API."""


class GitHubRequestCancelled(RuntimeError):
    """Indica cancelamento cooperativo de workers durante uma interrupção."""


def _github_error_message(exc: GithubException) -> str:
    data = exc.data
    if isinstance(data, Mapping):
        return str(data.get("message", ""))
    return str(data)


def _github_error_header(exc: GithubException, name: str) -> str | None:
    headers = exc.headers
    if not isinstance(headers, Mapping):
        return None
    expected = name.casefold()
    for key, value in headers.items():
        if str(key).casefold() == expected:
            return str(value)
    return None


def _is_rate_limit_error(exc: GithubException) -> bool:
    if exc.status == 429:
        return True
    if exc.status != 403:
        return False
    if _github_error_header(exc, "Retry-After") is not None:
        return True
    message = _github_error_message(exc).casefold()
    return any(
        marker in message
        for marker in (
            "rate limit",
            "abuse detection",
            "please wait a few minutes",
            "temporarily blocked",
        )
    )


class _GitHubRequestCoordinator:
    """Serializa o início das requisições e coordena cooldown entre workers."""

    def __init__(
        self,
        *,
        request_interval_seconds: float,
        secondary_cooldown_seconds: float,
        secondary_max_retries: int,
        max_rate_limit_wait_seconds: float,
        reset_buffer_seconds: int,
        sleep_func: Callable[[float], None],
        monotonic_func: Callable[[], float] = time.monotonic,
        now_func: Callable[[], datetime] = lambda: datetime.now(UTC),
        on_event: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self._request_interval_seconds = request_interval_seconds
        self._secondary_cooldown_seconds = secondary_cooldown_seconds
        self._secondary_max_retries = secondary_max_retries
        self._max_rate_limit_wait_seconds = max_rate_limit_wait_seconds
        self._reset_buffer_seconds = reset_buffer_seconds
        self._sleep_func = sleep_func
        self._monotonic_func = monotonic_func
        self._now_func = now_func
        self._on_event = on_event
        self._request_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._cancelled = threading.Event()
        self._cooldown_until = 0.0
        self._next_request_at = 0.0
        self._rate_limit_retries = 0
        self._waiting_workers = 0
        self._circuit_open = False

    def run(self, operation: str, call: Callable[[], Any]) -> Any:
        while True:
            self._wait_for_availability()
            with self._request_lock:
                if not self._is_available():
                    continue
                self._pace_request()
                try:
                    result = call()
                except GithubException as exc:
                    if not _is_rate_limit_error(exc):
                        raise
                    self._record_rate_limit(operation, exc)
                    continue
                self._record_success(operation)
                return result

    def wait(self, seconds: float) -> None:
        self._sleep_interruptibly(seconds)

    def cancel(self) -> None:
        self._cancelled.set()

    def status(self) -> dict[str, Any]:
        with self._state_lock:
            remaining = max(0.0, self._cooldown_until - self._monotonic_func())
            if self._circuit_open:
                state = "circuit_open"
            elif remaining > 0:
                state = "cooldown"
            else:
                state = "ready"
            return {
                "github_rate_limit_state": state,
                "blocked_workers": self._waiting_workers,
                "rate_limit_wait_remaining_seconds": round(remaining, 1),
                "rate_limit_retry": self._rate_limit_retries,
                "rate_limit_max_retries": self._secondary_max_retries,
            }

    def _wait_for_availability(self) -> None:
        while True:
            with self._state_lock:
                self._raise_if_unavailable()
                remaining = self._cooldown_until - self._monotonic_func()
                if remaining <= 0:
                    return
                self._waiting_workers += 1
            try:
                self._sleep_interruptibly(remaining)
            finally:
                with self._state_lock:
                    self._waiting_workers -= 1

    def _is_available(self) -> bool:
        with self._state_lock:
            self._raise_if_unavailable()
            return self._monotonic_func() >= self._cooldown_until

    def _pace_request(self) -> None:
        now = self._monotonic_func()
        wait_seconds = max(0.0, self._next_request_at - now)
        self._sleep_interruptibly(wait_seconds)
        self._next_request_at = self._monotonic_func() + self._request_interval_seconds

    def _sleep_interruptibly(self, seconds: float) -> None:
        if seconds <= 0:
            self._raise_if_cancelled()
            return
        if self._sleep_func is time.sleep:
            if self._cancelled.wait(seconds):
                raise GitHubRequestCancelled("Triagem cancelada pelo operador.")
        else:
            self._sleep_func(seconds)
            self._raise_if_cancelled()

    def _record_rate_limit(self, operation: str, exc: GithubException) -> None:
        wait_seconds = self._rate_limit_wait_seconds(exc)
        event_name: str
        details: dict[str, Any]
        with self._state_lock:
            self._rate_limit_retries += 1
            retry = self._rate_limit_retries
            if (
                retry > self._secondary_max_retries
                or wait_seconds > self._max_rate_limit_wait_seconds
            ):
                self._circuit_open = True
                event_name = "github_rate_limit_circuit_open"
                details = {
                    "operation": operation,
                    "retry": retry,
                    "max_retries": self._secondary_max_retries,
                    "required_wait_seconds": round(wait_seconds, 1),
                }
            else:
                self._cooldown_until = max(
                    self._cooldown_until,
                    self._monotonic_func() + wait_seconds,
                )
                event_name = "github_rate_limit_wait"
                details = {
                    "operation": operation,
                    "retry": retry,
                    "max_retries": self._secondary_max_retries,
                    "wait_seconds": round(wait_seconds, 1),
                }
        self._emit(event_name, details)
        if event_name == "github_rate_limit_circuit_open":
            raise GitHubRateLimitCircuitOpen(
                "Limite da API do GitHub persistiu após os retries configurados; "
                "as pendências foram registradas como erro para reprocessamento posterior."
            ) from exc

    def _record_success(self, operation: str) -> None:
        with self._state_lock:
            recovered_after = self._rate_limit_retries
            if recovered_after == 0:
                return
            self._rate_limit_retries = 0
            self._cooldown_until = 0.0
        self._emit(
            "github_rate_limit_recovered",
            {"operation": operation, "recovered_after_retries": recovered_after},
        )

    def _rate_limit_wait_seconds(self, exc: GithubException) -> float:
        retry_after = _github_error_header(exc, "Retry-After")
        if retry_after is not None:
            try:
                return max(0.0, float(retry_after)) + self._reset_buffer_seconds
            except ValueError:
                pass

        reset_epoch = _github_error_header(exc, "X-RateLimit-Reset")
        rate_remaining = _github_error_header(exc, "X-RateLimit-Remaining")
        if reset_epoch is not None and rate_remaining == "0":
            try:
                reset_at = datetime.fromtimestamp(float(reset_epoch), tz=UTC)
                reset_wait = (reset_at - self._now_func()).total_seconds()
                if reset_wait > 0:
                    return reset_wait + self._reset_buffer_seconds
            except (OverflowError, ValueError):
                pass
        return self._secondary_cooldown_seconds

    def _raise_if_unavailable(self) -> None:
        self._raise_if_cancelled()
        if self._circuit_open:
            raise GitHubRateLimitCircuitOpen(
                "Circuito da API do GitHub aberto após esgotar os retries configurados."
            )

    def _raise_if_cancelled(self) -> None:
        if self._cancelled.is_set():
            raise GitHubRequestCancelled("Triagem cancelada pelo operador.")

    def _emit(self, name: str, details: dict[str, Any]) -> None:
        if self._on_event is not None:
            self._on_event(name, details)


def _format_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Datetime precisa conter fuso horário.")
    return value.astimezone(UTC)


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


_MLFLOW_DEPENDENCY_PATTERN = re.compile(
    r"(?<![\w.-])mlflow(?:-skinny)?(?:\[[^\]\n]+\])?(?=\s*(?:[<>=~!;,\]\"']|$))",
    flags=re.IGNORECASE | re.MULTILINE,
)


def _path_declares_mlflow(path: str, source: str) -> bool:
    if path.casefold().endswith(".py"):
        return _python_imports_mlflow(source)
    if _is_mlflow_manifest(path):
        return _MLFLOW_DEPENDENCY_PATTERN.search(source) is not None
    return False


def _is_mlflow_manifest(path: str) -> bool:
    name = path.rsplit("/", maxsplit=1)[-1].casefold()
    return (
        name == "pyproject.toml"
        or name == "setup.py"
        or name == "setup.cfg"
        or name.startswith("requirements")
        and name.endswith(".txt")
    )


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
        on_rate_limit_event: Callable[[str, dict[str, Any]], None] | None = None,
        on_tree_fallback: Callable[[str], None] | None = None,
        mlflow_manifest_scan_limit: int = 50,
        request_interval_seconds: float = 0.25,
        secondary_cooldown_seconds: int = 60,
        secondary_max_retries: int = 2,
        max_rate_limit_wait_seconds: int = 300,
    ) -> None:
        self._token = token
        self._per_page = per_page
        self._request_timeout_seconds = request_timeout_seconds
        self._github_override = github_client
        self._thread_local = threading.local()
        self._core_reserve = core_reserve
        self._reset_buffer_seconds = reset_buffer_seconds
        self._now_func = now_func
        self._on_rate_limit_wait = on_rate_limit_wait
        self._on_tree_fallback = on_tree_fallback
        self._mlflow_manifest_scan_limit = mlflow_manifest_scan_limit
        self._rate_limit_lock = threading.Lock()
        self._estimated_remaining: int | None = None
        self._next_rate_refresh = 0.0
        self._requests = _GitHubRequestCoordinator(
            request_interval_seconds=request_interval_seconds,
            secondary_cooldown_seconds=secondary_cooldown_seconds,
            secondary_max_retries=secondary_max_retries,
            max_rate_limit_wait_seconds=max_rate_limit_wait_seconds,
            reset_buffer_seconds=reset_buffer_seconds,
            sleep_func=sleep_func,
            now_func=now_func,
            on_event=on_rate_limit_event,
        )

    def _client(self) -> Any:
        if self._github_override is not None:
            return self._github_override
        client = getattr(self._thread_local, "github", None)
        if client is None:
            client = Github(
                auth=Auth.Token(self._token),
                per_page=self._per_page,
                timeout=self._request_timeout_seconds,
                retry=None,
                seconds_between_requests=0,
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
                snapshot = self._requests.run(
                    "core_rate_limit",
                    lambda: self._core_rate_limit_snapshot(self._client()),
                )
                self._estimated_remaining = snapshot.remaining
                self._next_rate_refresh = monotonic_now + 30
                if snapshot.remaining <= self._core_reserve:
                    target = snapshot.reset_at_utc + timedelta(seconds=self._reset_buffer_seconds)
                    wait_seconds = max(0.0, (target - self._now_func()).total_seconds())
                    if self._on_rate_limit_wait is not None and wait_seconds > 0:
                        self._on_rate_limit_wait(wait_seconds, snapshot.reset_at_utc)
                    self._requests.wait(wait_seconds)
                    self._estimated_remaining = None
                    self._next_rate_refresh = 0.0
                    return

            if self._estimated_remaining is not None:
                self._estimated_remaining -= 1

    def _repo(self, repository_numeric_id: int) -> Any:
        self._wait_for_core_budget()
        return self._requests.run(
            "repository",
            lambda: self._client().get_repo(repository_numeric_id),
        )

    def _request(self, operation: str, call: Callable[[], Any]) -> Any:
        self._wait_for_core_budget()
        return self._requests.run(operation, call)

    def cancel(self) -> None:
        self._requests.cancel()

    def rate_limit_status(self) -> dict[str, Any]:
        return self._requests.status()

    def _snapshot_repo(self, snapshot: RepositorySnapshot) -> Any:
        if snapshot.repository_handle is not None:
            return snapshot.repository_handle
        return self._repo(snapshot.repository_numeric_id)

    def _get_content_if_available(
        self,
        repo: Any,
        path: str,
        *,
        ref: str,
    ) -> Any | None:
        try:
            content = self._request(
                "repository_content",
                lambda: repo.get_contents(path, ref=ref),
            )
        except GithubException as exc:
            if exc.status == 404:
                return None
            raise
        return content

    def get_repository_snapshot(self, candidate: SearchCandidateRow) -> RepositorySnapshot:
        repo = self._repo(candidate.repository_numeric_id)
        branch = self._request(
            "default_branch",
            lambda: repo.get_branch(repo.default_branch),
        )
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
        return int(
            self._request(
                "commit_count",
                lambda: repo.get_commits(sha=snapshot.default_branch).totalCount,
            )
        )

    def get_contributor_count(self, snapshot: RepositorySnapshot) -> int:
        repo = self._snapshot_repo(snapshot)
        return int(
            self._request(
                "contributor_count",
                lambda: repo.get_contributors().totalCount,
            )
        )

    def find_last_human_commit(
        self,
        snapshot: RepositorySnapshot,
        selection_config: SelectionConfig,
        commit_filter_config: CommitFilterConfig,
    ) -> datetime | None:
        repo = self._snapshot_repo(snapshot)
        commits = repo.get_commits(sha=snapshot.default_branch)
        cutoff = selection_config.active_after.astimezone(UTC)

        page_number = 0
        while True:
            page = self._request(
                "commit_history_page",
                partial(commits.get_page, page_number),
            )
            if not page:
                break
            for commit in page:
                commit_date = _commit_datetime(commit)
                if commit_date <= cutoff:
                    return None
                commit_text = _commit_text(commit)
                if commit_filter_config.exclude_merges and _commit_is_merge(commit):
                    continue
                if commit_filter_config.exclude_bots and _contains_bot_marker(
                    commit_text,
                    commit_filter_config.bot_patterns,
                ):
                    continue
                return commit_date
            page_number += 1

        return None

    def detect_tool_evidence(
        self,
        snapshot: RepositorySnapshot,
        evidence_paths: ToolEvidencePaths,
    ) -> tuple[bool, bool, bool]:
        repo = self._snapshot_repo(snapshot)
        tree = self._request(
            "repository_tree",
            lambda: repo.get_git_tree(snapshot.head_commit_sha, recursive=True),
        )
        tree_raw = getattr(tree, "raw_data", {})
        tree_truncated = bool(isinstance(tree_raw, dict) and tree_raw.get("truncated"))
        if tree_truncated and self._on_tree_fallback is not None:
            self._on_tree_fallback(snapshot.repository_id)

        tree_items = list(getattr(tree, "tree", []))
        paths = [str(getattr(item, "path", "")) for item in tree_items]
        dvc_detected = any(path == "dvc.yaml" or path.endswith(".dvc") for path in paths)
        mlruns_detected = any(path == "mlruns" or path.startswith("mlruns/") for path in paths)
        mlflow_detected = False

        available_paths = set(paths)
        if tree_truncated and not dvc_detected:
            dvc_targets = {"dvc.yaml", *evidence_paths.dvc_paths}
            dvc_detected = any(
                self._get_content_if_available(
                    repo,
                    path,
                    ref=snapshot.head_commit_sha,
                )
                is not None
                for path in sorted(dvc_targets)
                if path == "dvc.yaml" or path.endswith(".dvc")
            )

        manifest_paths = sorted(path for path in paths if _is_mlflow_manifest(path))[
            : self._mlflow_manifest_scan_limit
        ]
        evidence_targets = list(dict.fromkeys(sorted(evidence_paths.mlflow_paths)))
        paths_to_confirm = evidence_targets + [
            path for path in manifest_paths if path not in evidence_targets
        ]
        if not tree_truncated:
            paths_to_confirm = [path for path in paths_to_confirm if path in available_paths]

        for path in paths_to_confirm:
            content = self._get_content_if_available(
                repo,
                path,
                ref=snapshot.head_commit_sha,
            )
            if content is None or isinstance(content, list):
                continue
            if _path_declares_mlflow(path, _content_text(content)):
                mlflow_detected = True
                break

        if tree_truncated and not mlruns_detected:
            mlruns_detected = (
                self._get_content_if_available(
                    repo,
                    "mlruns",
                    ref=snapshot.head_commit_sha,
                )
                is not None
            )

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
    evidence_paths: ToolEvidencePaths,
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
            evidence_paths,
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
    dvc_paths: dict[int, set[str]] = {}
    mlflow_paths: dict[int, set[str]] = {}
    for evidence in evidences:
        if "mlflow" in evidence.query_expression.casefold():
            mlflow_paths.setdefault(evidence.repository_numeric_id, set()).add(evidence.file_path)
        if "dvc" in evidence.query_expression.casefold() and (
            evidence.file_path == "dvc.yaml" or evidence.file_path.endswith(".dvc")
        ):
            dvc_paths.setdefault(evidence.repository_numeric_id, set()).add(evidence.file_path)

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
            evidence_paths=ToolEvidencePaths(
                dvc_paths=tuple(sorted(dvc_paths.get(candidate.repository_numeric_id, ()))),
                mlflow_paths=tuple(sorted(mlflow_paths.get(candidate.repository_numeric_id, ()))),
            ),
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
            cancel_gateway = getattr(gateway, "cancel", None)
            if callable(cancel_gateway):
                cancel_gateway()
            for future in futures:
                future.cancel()
            executor.shutdown(wait=True, cancel_futures=True)
            raise
        else:
            executor.shutdown(wait=True)

    return [rows_by_id[candidate.repository_numeric_id] for candidate in sorted_candidates]
