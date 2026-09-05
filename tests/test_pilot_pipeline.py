from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import yaml
from git import Actor, Repo

from mlops_traceability.config import load_config
from mlops_traceability.mining import inspect_tree, mine_history
from mlops_traceability.pilot import (
    audit_collection,
    freeze_repository,
    run_stage,
    source_artifact,
    write_csv,
)
from mlops_traceability.taxonomy import Category, load_taxonomy
from mlops_traceability.validation.taxonomy_review import evaluate_review


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    for directory in ("config", "src", "scripts"):
        shutil.copytree(
            Path(directory), root / directory, ignore=shutil.ignore_patterns("__pycache__")
        )
    for name in ("requirements.txt", "requirements-dev.txt", "pyproject.toml"):
        shutil.copyfile(name, root / name)
    repo = Repo.init(root)
    repo.index.add(
        ["config", "src", "scripts", "requirements.txt", "requirements-dev.txt", "pyproject.toml"]
    )
    repo.index.commit("instrument")
    repo.close()
    return root


def change(repo: Repo, path: str, content: str, author: str = "human") -> str:
    target = Path(str(repo.working_tree_dir)) / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    repo.index.add([path])
    actor = Actor(author, f"{author}@example.test")
    return repo.index.commit(
        "synthetic",
        author=actor,
        committer=actor,
        author_date="2026-01-02 00:00:00 +0000",
        commit_date="2026-01-02 00:00:00 +0000",
    ).hexsha


def synthetic(root: Path) -> tuple[Repo, str]:
    repo = Repo.init(root / "source")
    change(repo, "train.py", "import mlflow\nmlflow.log_artifact('weights.pt')\n")
    change(repo, "cfg/model.yaml", "x: 1\n", "human2")
    change(repo, "cfg/model.yaml", "# comment\nx: 1\n", "human3")
    change(repo, "README.md", "documentation", "human4")
    sha = change(repo, "data/file.csv", "a,b\n1,2", "human5")
    return repo, sha


def test_mine_reachable_history_filters_semantics_and_tree(tmp_path: Path) -> None:
    repo, sha = synthetic(tmp_path)
    # This future commit must not leak into the frozen history.
    change(repo, "future.py", "x = 1")
    config, taxonomy = load_config("config/config.yaml"), load_taxonomy("config/file_taxonomy.yaml")
    commits, changes, summary = mine_history(
        Path(str(repo.working_tree_dir)), sha, "a/b", config, taxonomy, "run"
    )
    assert len(commits) == 5
    assert summary["active_contributors_count"] == 5
    assert sum(r["config_changed_keys"] for r in commits) == 1
    assert not any(r["file_path"] == "future.py" for r in changes)
    inspection = inspect_tree(Path(str(repo.working_tree_dir)), sha, "a/b", taxonomy)
    assert inspection["calls"][0]["operation"] == "log_artifact"
    assert inspection["mlruns_paths"] == []
    bot = change(repo, "bot.py", "x=1", "dependabot[bot]")
    invalid = change(repo, "cfg/broken.yaml", "a: [")
    change(repo, "nested/mlruns/1/meta.yaml", "experiment: 1")
    final = change(repo, "bad.py", "not valid python!")
    commits, changes, summary = mine_history(
        Path(str(repo.working_tree_dir)), final, "a/b", config, taxonomy, "run"
    )
    by_sha = {r["commit_sha"]: r for r in commits}
    assert by_sha[bot]["eligibility_status"] == "bot"
    assert by_sha[invalid]["config_semantic_status"] == "error"
    assert summary["semantic_errors"] == 1
    inspection = inspect_tree(Path(str(repo.working_tree_dir)), final, "a/b", taxonomy)
    assert inspection["mlruns_paths"] == ["nested/mlruns/1/meta.yaml"]
    assert inspection["parse_errors"]
    # Force a large commit, then test a merge with a distinct side-branch change.
    config = config.model_copy(
        update={
            "commit_filter": config.commit_filter.model_copy(update={"large_commit_max_files": 1})
        }
    )
    change(repo, "one.py", "1")
    other = Path(str(repo.working_tree_dir)) / "two.py"
    other.write_text("2")
    repo.index.add(["two.py"])
    large = repo.index.commit("large", parent_commits=[repo.commit(sha)]).hexsha
    commits, _, _ = mine_history(
        Path(str(repo.working_tree_dir)), large, "a/b", config, taxonomy, "run"
    )
    assert commits[-1]["eligibility_status"] == "large_commit"
    merge = repo.index.commit(
        "merge", parent_commits=[repo.commit(large), repo.commit(final)]
    ).hexsha
    commits, _, summary = mine_history(
        Path(str(repo.working_tree_dir)), merge, "a/b", config, taxonomy, "run"
    )
    assert commits[-1]["eligibility_status"] == "merge"
    assert sum(summary["funnel"].values()) == len(commits)
    repo.close()


def test_three_stage_pipeline_and_tampering(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, sha = synthetic(project)
    target = project / "data/raw/repos/test__case.git"
    Repo.clone_from(str(repo.working_tree_dir), target, bare=True).close()
    bare = Repo(target)
    bare.remotes.origin.set_url("https://github.com/test/case.git")
    bare.close()
    sample_path = project / "config/amostra_final.yaml"
    sample = yaml.safe_load(sample_path.read_text())
    sample["repositories"] = [
        {"repository_id": "test/case", "head_commit_sha": sha, "stratum": "apenas_mlflow"}
    ]
    sample_path.write_text(yaml.safe_dump(sample))
    monkeypatch.setattr("mlops_traceability.pilot.audit_collection", lambda *_: {"verified": True})
    arguments = ["--allow-dirty", "--repository", "test/case"]
    assert run_stage("phase3_clone_repos", arguments, project) == 0
    first, _ = source_artifact(project, "phase3_clone_repos", "frozen_sample")
    assert run_stage("phase3_clone_repos", arguments, project) == 0
    second, _ = source_artifact(project, "phase3_clone_repos", "frozen_sample")
    assert first != second and first.is_file()
    assert run_stage("phase4_mine_commits", arguments, project) == 0
    assert run_stage("phase5_compute_metrics", arguments, project) == 0
    metrics, _ = source_artifact(project, "phase5_compute_metrics", "metrics")
    frame = pd.read_csv(metrics).set_index("metric_id")
    assert frame.loc["config_magnitude", "value"] == 0.5
    assert frame.loc["code_config_cochange", "value"] == 0
    assert frame.loc["provenance_coverage", "status"] == "not_available"
    with second.open("a") as stream:
        stream.write("tampered")
    assert run_stage("phase4_mine_commits", arguments, project) == 1
    with pytest.raises(ValueError, match="Missing successful"):
        source_artifact(project, "phase4_mine_commits", "commits")
    assert run_stage("phase3_clone_repos", [], project) == 1  # dirty official run
    assert (
        run_stage("phase3_clone_repos", ["--allow-dirty", "--repository", "unknown/repo"], project)
        == 1
    )
    repo.close()


def test_freeze_rejects_wrong_origin_and_invalid_id(project: Path) -> None:
    repo, sha = synthetic(project)
    selected = {"repository_id": "test/case", "head_commit_sha": sha, "stratum": "apenas_mlflow"}
    target = project / "data/raw/repos/test__case.git"
    Repo.clone_from(str(repo.working_tree_dir), target, bare=True).close()
    with pytest.raises(ValueError, match="origin"):
        freeze_repository(project, selected, Path("data/raw/repos"))
    with pytest.raises(ValueError, match="Invalid"):
        freeze_repository(
            project, {**selected, "repository_id": "../../escape"}, Path("data/raw/repos")
        )
    repo.close()


def test_original_audit_and_tampering(project: Path) -> None:
    repo = Repo(project)
    sha = repo.head.commit.hexsha
    from mlops_traceability.manifest import sha256_file

    directory = project / "data/interim/runs/original"
    directory.mkdir(parents=True)
    shortlist = directory / "shortlist.csv"
    write_csv(shortlist, [{"repository_id": "a/b", "head_commit_sha": sha, "decision": "eligible"}])
    manifests = project / "data/processed/manifests"
    manifests.mkdir(parents=True)
    manifest: dict[str, Any] = {
        "status": "SUCCESS",
        "dirty_worktree": False,
        "code_commit_sha": sha,
        "protocol_version": "2.0.0",
        "config_sha256": sha256_file(project / "config/config.yaml"),
        "taxonomy_sha256": sha256_file(project / "config/file_taxonomy.yaml"),
        "requirements_sha256": sha256_file(project / "requirements.txt"),
        "artifacts": [
            {"path": str(shortlist), "sha256": sha256_file(shortlist)},
            {
                "path": str(project / "config/config.yaml"),
                "sha256": sha256_file(project / "config/config.yaml"),
            },
        ],
    }
    manifest_path = manifests / "original.json"
    manifest_path.write_text(json.dumps(manifest))
    sample: dict[str, Any] = {
        "source_runs": {"phase2_screen_sample": "original"},
        "source_shortlist_sha256": sha256_file(shortlist),
        "repositories": [{"repository_id": "a/b", "head_commit_sha": sha}],
    }
    assert audit_collection(project, sample)["verified"]
    assert not list(directory.glob("*backup*"))
    sample["source_shortlist_sha256"] = "wrong"
    with pytest.raises(ValueError, match="Shortlist"):
        audit_collection(project, sample)
    sample["source_shortlist_sha256"] = sha256_file(shortlist)
    sample["repositories"][0]["head_commit_sha"] = "wrong"
    with pytest.raises(ValueError, match="Selection"):
        audit_collection(project, sample)
    manifest["config_sha256"] = "wrong"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="instrument"):
        audit_collection(project, sample)
    manifest["artifacts"][0]["sha256"] = "wrong"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="artifact"):
        audit_collection(project, sample)
    manifest["status"] = "FAILED"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Unaccepted"):
        audit_collection(project, sample)
    repo.close()


def test_human_validation_cannot_pass_blank_or_duplicate_labels(tmp_path: Path) -> None:
    config = load_config("config/config.yaml")
    rows = [
        {
            "repository_id": "a/b",
            "head_commit_sha": "a" * 40,
            "file_path": f"{category}/{i}",
            "category": category.value,
            "expected_category": category.value,
            "reviewer": "researcher",
            "reviewed_at_utc": "2026-09-05T00:00:00Z",
        }
        for category in Category
        for i in range(20)
    ]
    path = tmp_path / "review.csv"
    write_csv(path, rows)
    assert evaluate_review(path, config)["accepted"]
    rows[0]["expected_category"] = ""
    write_csv(path, rows)
    assert not evaluate_review(path, config)["accepted"]
    rows[0] = rows[1]
    write_csv(path, rows)
    assert not evaluate_review(path, config)["accepted"]
    with path.open() as stream:
        assert len(list(csv.DictReader(stream))) == 200
