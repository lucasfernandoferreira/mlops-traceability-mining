"""Geração de um histórico Git controlado para validar o instrumento."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from git import Actor, Repo

RESEARCHER = Actor("Synthetic Researcher", "researcher@example.invalid")
BOT = Actor(
    "dependabot[bot]",
    "49699333+dependabot[bot]@users.noreply.github.com",
)
SYNTHETIC_EPOCH = datetime(2024, 1, 1, tzinfo=UTC)


def commit_files(
    repo: Repo,
    root: Path,
    files: dict[str, str],
    message: str,
    committed_at: datetime,
    actor: Actor = RESEARCHER,
) -> None:
    relative_paths: list[str] = []

    for relative_path, content in files.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        relative_paths.append(relative_path)

    repo.index.add(relative_paths)
    repo.index.commit(
        message,
        author=actor,
        committer=actor,
        author_date=committed_at,
        commit_date=committed_at,
    )


def build_synthetic_repository(target: Path) -> Repo:
    repo = Repo.init(target, initial_branch="main")

    with repo.config_writer() as writer:
        writer.set_value("user", "name", RESEARCHER.name)
        writer.set_value("user", "email", RESEARCHER.email)

    commit_files(
        repo,
        target,
        {"src/train.py": "print('train')\n"},
        "feat: add training code",
        SYNTHETIC_EPOCH,
    )

    commit_files(
        repo,
        target,
        {"data/train.dvc": "outs:\n  - md5: synthetic-data-v1\n"},
        "data: add tracked dataset",
        SYNTHETIC_EPOCH + timedelta(minutes=1),
    )

    commit_files(
        repo,
        target,
        {"params.yaml": "model:\n  depth: 4\n"},
        "config: add model parameters",
        SYNTHETIC_EPOCH + timedelta(minutes=2),
    )

    commit_files(
        repo,
        target,
        {
            "src/train.py": "print('train v2')\n",
            "data/train.dvc": "outs:\n  - md5: synthetic-data-v2\n",
            "params.yaml": "model:\n  depth: 8\n",
        },
        "feat: change code data and parameters",
        SYNTHETIC_EPOCH + timedelta(minutes=3),
    )

    feature = repo.create_head("feature-docs")
    feature.checkout()

    commit_files(
        repo,
        target,
        {"docs/pipeline.md": "# Synthetic pipeline\n"},
        "docs: document pipeline",
        SYNTHETIC_EPOCH + timedelta(minutes=4),
    )

    repo.heads.main.checkout()

    commit_files(
        repo,
        target,
        {"src/evaluate.py": "print('evaluate')\n"},
        "feat: add evaluation code",
        SYNTHETIC_EPOCH + timedelta(minutes=5),
    )

    merge_date = (SYNTHETIC_EPOCH + timedelta(minutes=6)).isoformat()
    with repo.git.custom_environment(
        GIT_AUTHOR_DATE=merge_date,
        GIT_COMMITTER_DATE=merge_date,
    ):
        repo.git.merge(
            "feature-docs",
            "--no-ff",
            "-m",
            "merge: integrate documentation",
        )

    commit_files(
        repo,
        target,
        {".github/dependabot.yml": "version: 2\nupdates: []\n"},
        "chore: automated dependency update",
        SYNTHETIC_EPOCH + timedelta(minutes=7),
        actor=BOT,
    )

    return repo
