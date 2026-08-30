from pathlib import Path

from git import Repo

from mlops_traceability.validation.synthetic_repo import (
    BOT,
    RESEARCHER,
    build_synthetic_repository,
)


def test_build_synthetic_repository_creates_expected_history(tmp_path: Path) -> None:
    repository_path = tmp_path / "synthetic-repository"
    repository = build_synthetic_repository(repository_path)

    assert isinstance(repository, Repo)
    assert not repository.bare
    assert repository.active_branch.name == "main"
    assert {head.name for head in repository.heads} == {"feature-docs", "main"}
    assert len(list(repository.iter_commits("--all"))) == 8

    tracked_files = set(repository.git.ls_files().splitlines())
    assert tracked_files == {
        ".github/dependabot.yml",
        "data/train.dvc",
        "docs/pipeline.md",
        "params.yaml",
        "src/evaluate.py",
        "src/train.py",
    }
    assert not repository.is_dirty(untracked_files=True)


def test_synthetic_history_contains_research_scenarios(tmp_path: Path) -> None:
    repository = build_synthetic_repository(tmp_path / "synthetic-repository")
    commits = list(repository.iter_commits("--all"))
    commits_by_message = {commit.message.strip(): commit for commit in commits}

    mixed_commit = commits_by_message["feat: change code data and parameters"]
    assert set(mixed_commit.stats.files) == {
        "data/train.dvc",
        "params.yaml",
        "src/train.py",
    }
    assert mixed_commit.author.name == RESEARCHER.name
    assert mixed_commit.author.email == RESEARCHER.email

    merge_commit = commits_by_message["merge: integrate documentation"]
    assert len(merge_commit.parents) == 2
    assert "docs/pipeline.md" in repository.git.ls_tree("-r", "--name-only", merge_commit.hexsha)

    automated_commit = commits_by_message["chore: automated dependency update"]
    assert repository.head.commit == automated_commit
    assert automated_commit.author.name == BOT.name
    assert automated_commit.author.email == BOT.email
    assert set(automated_commit.stats.files) == {".github/dependabot.yml"}

    working_tree_dir = repository.working_tree_dir
    assert working_tree_dir is not None
    working_tree = Path(working_tree_dir)
    assert (working_tree / "src/train.py").read_text(encoding="utf-8") == "print('train v2')\n"
    assert (working_tree / "params.yaml").read_text(encoding="utf-8") == "model:\n  depth: 8\n"


def test_synthetic_history_is_deterministic(tmp_path: Path) -> None:
    first = build_synthetic_repository(tmp_path / "first-repository")
    second = build_synthetic_repository(tmp_path / "second-repository")

    first_commits = {
        commit.message.strip(): commit.hexsha for commit in first.iter_commits("--all")
    }
    second_commits = {
        commit.message.strip(): commit.hexsha for commit in second.iter_commits("--all")
    }

    assert first_commits == second_commits
    assert first.head.commit.hexsha == second.head.commit.hexsha
