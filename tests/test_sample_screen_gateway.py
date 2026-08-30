from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from mlops_traceability.config import load_config
from mlops_traceability.github_search import SearchCandidateRow
from mlops_traceability.sample_screen import GitHubScreeningGateway

CONFIG_PATH = "config/config.yaml"


class _PaginatedList(list[object]):
    def __init__(self, items: list[object], total_count: int | None = None) -> None:
        super().__init__(items)
        self.totalCount = len(items) if total_count is None else total_count


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
        self._contents = {
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

    def get_contents(self, path: str, ref: str | None = None) -> _FakeContent:
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
    assert gateway.detect_tool_evidence(snapshot) == (True, True, True)


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
