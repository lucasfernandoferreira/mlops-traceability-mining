from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from github.GithubException import GithubException

from mlops_traceability.config import load_config
from mlops_traceability.github_search import SearchCandidateRow
from mlops_traceability.sample_screen import (
    GitHubRateLimitCircuitOpen,
    GitHubRequestCancelled,
    GitHubScreeningGateway,
    ToolEvidencePaths,
    _GitHubRequestCoordinator,
    _is_rate_limit_error,
    _path_declares_mlflow,
)

CONFIG_PATH = "config/config.yaml"


def test_mlflow_confirmation_rejects_documentation_mentions() -> None:
    assert _path_declares_mlflow("README.md", "Use DVC with MLflow") is False
    assert _path_declares_mlflow("requirements.txt", "mlflow>=2.0") is True
    assert _path_declares_mlflow("train.py", "import mlflow") is True


class _PaginatedList(list[object]):
    def __init__(self, items: list[object], total_count: int | None = None) -> None:
        super().__init__(items)
        self.totalCount = len(items) if total_count is None else total_count

    def get_page(self, page_number: int) -> list[object]:
        return list(self) if page_number == 0 else []


class _FakeClock:
    def __init__(self) -> None:
        self.value = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds


class _FakeCommit:
    def __init__(
        self,
        *,
        sha: str,
        date: datetime,
        message: str,
        author_name: str = "Researcher",
        author_email: str = "researcher@example.com",
        login: str = "researcher",
        parents: list[object] | None = None,
    ) -> None:
        self.sha = sha
        self.parents = parents or [object()]
        self.author = SimpleNamespace(login=login)
        self.commit = SimpleNamespace(
            author=SimpleNamespace(name=author_name, email=author_email, date=date),
            committer=SimpleNamespace(name=author_name, email=author_email, date=date),
            message=message,
        )


class _FakeTreeItem:
    def __init__(self, path: str) -> None:
        self.path = path


class _FakeContent:
    def __init__(self, text: str) -> None:
        self.decoded_content = text.encode("utf-8")


class _FakeRateLimit:
    def __init__(self, remaining: int, reset_at: datetime) -> None:
        self.resources = SimpleNamespace(core=SimpleNamespace(remaining=remaining, reset=reset_at))


class _FakeRepo:
    def __init__(self) -> None:
        self.full_name = "owner/repo"
        self.html_url = "https://github.com/owner/repo"
        self.default_branch = "main"
        self.stargazers_count = 150
        self.fork = False
        self.archived = False
        self.disabled = False
        self._commits = _PaginatedList(
            [
                _FakeCommit(
                    sha="head",
                    date=datetime(2026, 1, 4, tzinfo=UTC),
                    message="feat: add model",
                ),
                _FakeCommit(
                    sha="merge",
                    date=datetime(2026, 1, 3, tzinfo=UTC),
                    message="merge pull request #1",
                    parents=[object(), object()],
                ),
                _FakeCommit(
                    sha="bot",
                    date=datetime(2026, 1, 2, tzinfo=UTC),
                    message="chore: update dependencies",
                    author_name="dependabot[bot]",
                    author_email="dependabot[bot]@users.noreply.github.com",
                    login="dependabot[bot]",
                ),
                _FakeCommit(
                    sha="human",
                    date=datetime(2026, 1, 1, tzinfo=UTC),
                    message="feat: train pipeline",
                ),
            ],
            total_count=4,
        )
        self._contributors = _PaginatedList([object() for _ in range(7)], total_count=7)
        self._tree = SimpleNamespace(
            tree=[
                _FakeTreeItem("dvc.yaml"),
                _FakeTreeItem("mlruns/experiment/metrics.json"),
                _FakeTreeItem("src/train.py"),
                _FakeTreeItem("src/utils.py"),
                _FakeTreeItem("README.md"),
            ],
            raw_data={"truncated": False},
        )
        self._contents: dict[str, object] = {
            "src/train.py": _FakeContent("import mlflow\n\nprint('train')\n"),
            "src/utils.py": _FakeContent("def helper():\n    return 1\n"),
        }

    def get_branch(self, branch_name: str) -> SimpleNamespace:
        assert branch_name == self.default_branch
        return SimpleNamespace(commit=SimpleNamespace(sha="head"))

    def get_commits(self, sha: str) -> _PaginatedList:
        assert sha == self.default_branch
        return self._commits

    def get_contributors(self) -> _PaginatedList:
        return self._contributors

    def get_git_tree(self, sha: str, recursive: bool = False) -> SimpleNamespace:
        assert sha == "head"
        assert recursive is True
        return self._tree

    def get_contents(self, path: str, ref: str | None = None) -> object:
        assert ref == "head"
        return self._contents[path]


class _FakeGithubClient:
    def __init__(self) -> None:
        self.repo = _FakeRepo()

    def get_rate_limit(self) -> _FakeRateLimit:
        return _FakeRateLimit(remaining=100, reset_at=datetime(2026, 1, 1, tzinfo=UTC))

    def get_repo(self, full_name_or_id: int | str) -> _FakeRepo:
        assert full_name_or_id == 123
        return self.repo


def _candidate() -> SearchCandidateRow:
    return SearchCandidateRow(
        repository_numeric_id=123,
        repository_id="owner/repo",
        repository_url="https://github.com/owner/repo",
        owner_login="owner",
        is_fork=False,
        description="ML project",
        discovery_query_count=1,
        discovery_hit_count=1,
        observed_at_utc=datetime(2026, 1, 5, tzinfo=UTC),
        run_id="run-1",
    )


def test_gateway_reads_repository_metadata_and_evidence() -> None:
    config = load_config(CONFIG_PATH)
    gateway = GitHubScreeningGateway(
        token="unused",
        per_page=100,
        request_timeout_seconds=30,
        core_reserve=50,
        reset_buffer_seconds=2,
        github_client=_FakeGithubClient(),  # type: ignore[arg-type]
        sleep_func=lambda _seconds: None,
        now_func=lambda: datetime(2026, 1, 5, tzinfo=UTC),
    )

    snapshot = gateway.get_repository_snapshot(_candidate())

    assert snapshot.repository_id == "owner/repo"
    assert snapshot.head_commit_sha == "head"
    assert gateway.get_commit_count(snapshot) == 4
    assert gateway.get_contributor_count(snapshot) == 7
    assert gateway.find_last_human_commit(
        snapshot,
        config.selection,
        config.commit_filter,
    ) == datetime(2026, 1, 4, tzinfo=UTC)
    assert gateway.detect_tool_evidence(
        snapshot,
        ToolEvidencePaths(mlflow_paths=("src/train.py",)),
    ) == (True, True, True)


def test_gateway_falls_back_to_known_paths_when_tree_is_truncated() -> None:
    fake_client = _FakeGithubClient()
    fake_client.repo._tree = SimpleNamespace(tree=[], raw_data={"truncated": True})
    fake_client.repo._contents = {
        "dvc.yaml": None,
        "pipeline/model.dvc": _FakeContent("outs:\n  - model.pkl\n"),
        "requirements.txt": _FakeContent("mlflow>=2.0\n"),
        "mlruns": [_FakeContent("experiment")],
    }
    fallback_repositories: list[str] = []
    gateway = GitHubScreeningGateway(
        token="unused",
        per_page=100,
        request_timeout_seconds=30,
        core_reserve=50,
        reset_buffer_seconds=2,
        github_client=fake_client,  # type: ignore[arg-type]
        sleep_func=lambda _seconds: None,
        now_func=lambda: datetime(2026, 1, 5, tzinfo=UTC),
        on_tree_fallback=fallback_repositories.append,
    )

    snapshot = gateway.get_repository_snapshot(_candidate())

    assert gateway.detect_tool_evidence(
        snapshot,
        ToolEvidencePaths(
            dvc_paths=("pipeline/model.dvc",),
            mlflow_paths=("requirements.txt",),
        ),
    ) == (True, True, True)
    assert fallback_repositories == ["owner/repo"]


def test_gateway_skips_merges_and_bots_when_finding_recent_activity() -> None:
    config = load_config(CONFIG_PATH)
    fake_client = _FakeGithubClient()
    fake_client.repo._commits = _PaginatedList(
        [
            _FakeCommit(
                sha="merge",
                date=datetime(2026, 1, 5, tzinfo=UTC),
                message="merge pull request #2",
                parents=[object(), object()],
            ),
            _FakeCommit(
                sha="bot",
                date=datetime(2026, 1, 4, tzinfo=UTC),
                message="chore: bot update",
                author_name="renovate[bot]",
                author_email="renovate[bot]@users.noreply.github.com",
                login="renovate[bot]",
            ),
            _FakeCommit(
                sha="human",
                date=datetime(2026, 1, 3, tzinfo=UTC),
                message="feat: keep working",
            ),
        ],
        total_count=3,
    )
    gateway = GitHubScreeningGateway(
        token="unused",
        per_page=100,
        request_timeout_seconds=30,
        core_reserve=50,
        reset_buffer_seconds=2,
        github_client=fake_client,  # type: ignore[arg-type]
        sleep_func=lambda _seconds: None,
        now_func=lambda: datetime(2026, 1, 6, tzinfo=UTC),
    )

    snapshot = gateway.get_repository_snapshot(_candidate())

    assert gateway.find_last_human_commit(
        snapshot,
        config.selection,
        config.commit_filter,
    ) == datetime(2026, 1, 3, tzinfo=UTC)


def _coordinator(
    clock: _FakeClock,
    *,
    max_retries: int = 2,
    max_wait_seconds: float = 300,
    on_event: Callable[[str, dict[str, Any]], None] | None = None,
) -> _GitHubRequestCoordinator:
    return _GitHubRequestCoordinator(
        request_interval_seconds=0.25,
        secondary_cooldown_seconds=60,
        secondary_max_retries=max_retries,
        max_rate_limit_wait_seconds=max_wait_seconds,
        reset_buffer_seconds=2,
        sleep_func=clock.sleep,
        monotonic_func=clock.monotonic,
        now_func=lambda: datetime(2026, 1, 1, tzinfo=UTC),
        on_event=on_event,
    )


def _secondary_limit(*, retry_after: str | None = None) -> GithubException:
    headers = {} if retry_after is None else {"Retry-After": retry_after}
    return GithubException(
        403,
        {"message": "You have exceeded a secondary rate limit."},
        headers,
    )


def test_request_coordinator_recovers_with_one_shared_cooldown() -> None:
    clock = _FakeClock()
    events: list[tuple[str, dict[str, object]]] = []
    coordinator = _coordinator(
        clock,
        on_event=lambda name, details: events.append((name, details)),
    )
    calls = 0
    status_during_wait: list[dict[str, object]] = []

    def operation() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise _secondary_limit(retry_after="3")
        return "ok"

    original_sleep = clock.sleep

    def observed_sleep(seconds: float) -> None:
        status_during_wait.append(coordinator.status())
        original_sleep(seconds)

    coordinator._sleep_func = observed_sleep

    assert coordinator.run("repository", operation) == "ok"
    assert calls == 2
    assert clock.sleeps == [5.0]
    assert status_during_wait[0]["github_rate_limit_state"] == "cooldown"
    assert status_during_wait[0]["blocked_workers"] == 1
    assert [name for name, _details in events] == [
        "github_rate_limit_wait",
        "github_rate_limit_recovered",
    ]
    assert coordinator.status()["github_rate_limit_state"] == "ready"


def test_request_coordinator_opens_circuit_after_bounded_retries() -> None:
    clock = _FakeClock()
    events: list[str] = []
    coordinator = _coordinator(
        clock,
        max_retries=1,
        on_event=lambda name, _details: events.append(name),
    )

    with pytest.raises(GitHubRateLimitCircuitOpen):
        coordinator.run("repository", lambda: (_ for _ in ()).throw(_secondary_limit()))

    assert clock.sleeps == [60]
    assert events == ["github_rate_limit_wait", "github_rate_limit_circuit_open"]
    assert coordinator.status()["github_rate_limit_state"] == "circuit_open"
    with pytest.raises(GitHubRateLimitCircuitOpen):
        coordinator.run("repository", lambda: "never")


def test_request_coordinator_caps_required_wait_and_supports_cancel() -> None:
    clock = _FakeClock()
    coordinator = _coordinator(clock, max_wait_seconds=30)

    with pytest.raises(GitHubRateLimitCircuitOpen):
        coordinator.run("repository", lambda: (_ for _ in ()).throw(_secondary_limit()))

    cancelled = _coordinator(clock)
    cancelled.cancel()
    with pytest.raises(GitHubRequestCancelled):
        cancelled.run("repository", lambda: "never")


def test_secondary_limit_ignores_core_reset_when_core_quota_remains() -> None:
    clock = _FakeClock()
    coordinator = _coordinator(clock)
    calls = 0

    def operation() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise GithubException(
                403,
                {"message": "You have exceeded a secondary rate limit."},
                {
                    "X-RateLimit-Remaining": "4999",
                    "X-RateLimit-Reset": "1767229200",
                },
            )
        return "ok"

    assert coordinator.run("repository", operation) == "ok"
    assert clock.sleeps == [60]


def test_request_coordinator_paces_calls_and_does_not_retry_regular_403() -> None:
    clock = _FakeClock()
    coordinator = _coordinator(clock)

    assert coordinator.run("one", lambda: 1) == 1
    assert coordinator.run("two", lambda: 2) == 2
    assert clock.sleeps == [0.25]

    forbidden = GithubException(403, {"message": "Resource not accessible"}, {})
    assert _is_rate_limit_error(forbidden) is False
    assert _is_rate_limit_error(GithubException(429, {}, {})) is True
    with pytest.raises(GithubException):
        coordinator.run("forbidden", lambda: (_ for _ in ()).throw(forbidden))
