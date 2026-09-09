"""Known source semantics and empirical-bug regressions in temporary repositories."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest
import yaml
from git import Actor, Repo
from test_pilot_pipeline import change, synthetic

from mlops_traceability.config import load_config
from mlops_traceability.config_diff import changed_keys
from mlops_traceability.descriptive_analysis import (
    configuration_sensitivity,
    distribution,
    monthly_series,
)
from mlops_traceability.mining import mine_history, read_blob
from mlops_traceability.taxonomy import load_taxonomy
from mlops_traceability.verification.descriptive import describe
from mlops_traceability.verification.git_oracle import object_reader, reconcile_rows, source_history
from mlops_traceability.verification.runner import CHANGE_FIELDS, COMMIT_FIELDS
from mlops_traceability.verification.semantics import reference_keys
from mlops_traceability.verification.tables import read_table


@pytest.mark.parametrize(
    "path,before,after,expected",
    [
        ("config.yaml", b"a: 1\nb: 2", b"# comment\nb: 2\na: 1", []),
        ("config.yaml", b"a: 1", b"a: 2", ['["str:a"]']),
        ("config.yaml", b"a: 1", b"a: {b: 2}", ['["str:a", "str:b"]', '["str:a"]']),
        ("config.yaml", b"1: a", b"'1': a", ['["int:1"]', '["str:1"]']),
        ("config.yaml", b"a: []", b"a: [1]", ['["str:a"]']),
        ("MLproject", None, b"{}", ["[]"]),
        ("a.json", b"null", b'{"a": null}', ['["str:a"]']),
        ("a.toml", b"a = 1", None, ['["str:a"]']),
        ("a.yaml", b"a: 2026-01-01", b"a: '2026-01-01'", []),
        ("a.yaml", b"a: &x {v: 1}\nb: *x", b"a: {v: 1}\nb: {v: 1}", []),
    ],
)
def test_paired_semantics_known_answers(
    path: str, before: bytes | None, after: bytes | None, expected: list[str]
) -> None:
    assert reference_keys(before, after, path) == expected
    assert changed_keys(before, after, path) == expected
    assert reference_keys(after, before, path) == expected


@pytest.mark.parametrize(
    "path,content",
    [
        ("a.yaml", b"x: ["),
        ("a.yaml", b"a: 1\na: 2"),
        ("a.yaml", b"x: &x {a: *x}"),
        ("a.yaml", b"\xff"),
        ("a.json", b'{"a": 1, "a": 2}'),
        ("a.toml", b"x = ["),
    ],
)
def test_semantics_rejects_ambiguity(path: str, content: bytes) -> None:
    with pytest.raises((ValueError, yaml.YAMLError)):
        reference_keys(None, content, path)
    with pytest.raises((ValueError, yaml.YAMLError)):
        changed_keys(None, content, path)


def test_unsupported_parser_is_explicit() -> None:
    with pytest.raises(NotImplementedError):
        reference_keys(None, b"a=1", "a.ini")


@pytest.mark.counterexample
def test_directory_to_symlink_does_not_record_tree_as_blob(tmp_path: Path) -> None:
    with Repo.init(tmp_path) as repo:
        first = change(repo, "config.yaml/nested.py", "x = 1\n")
        change(repo, "target.yaml", "x: 2\n")
        repo.index.remove(["config.yaml/nested.py"], working_tree=True)
        if (tmp_path / "config.yaml").exists():
            (tmp_path / "config.yaml").rmdir()
        (tmp_path / "config.yaml").symlink_to("target.yaml")
        repo.index.add(["config.yaml"])
        head = repo.index.commit("Directory becomes symlink").hexsha
        assert read_blob(repo, first, "config.yaml") is None
        cfg = load_config("config/config.yaml")
        rows, changes, _ = mine_history(
            tmp_path,
            head,
            "fixture/symlink",
            cfg,
            load_taxonomy("config/file_taxonomy.yaml"),
            "fixture",
        )
        source, files, _ = source_history(
            tmp_path,
            head,
            "fixture/symlink",
            cfg.model_dump(mode="json"),
            yaml.safe_load(Path("config/file_taxonomy.yaml").read_text()),
        )
        assert not reconcile_rows(source, rows, ("commit_sha",), COMMIT_FIELDS)
        assert not reconcile_rows(files, changes, ("commit_sha", "file_path"), CHANGE_FIELDS)
        added = next(
            r for r in changes if r["commit_sha"] == head and r["file_path"] == "config.yaml"
        )
        assert added["before_blob_sha"] is None and added["after_blob_sha"]
        added["before_blob_sha"] = (repo.commit(first).tree / "config.yaml").hexsha
        assert any(
            r["field"] == "before_blob_sha"
            for r in reconcile_rows(files, changes, ("commit_sha", "file_path"), CHANGE_FIELDS)
        )


@pytest.mark.counterexample
def test_git_oracle_detects_bot_and_metadata_mutations(tmp_path: Path) -> None:
    repo, _ = synthetic(tmp_path)
    path = Path(str(repo.working_tree_dir))
    bot = change(repo, "bot.py", "x=1", "dependabot[bot]")
    # A bot merge must receive the merge reason first.
    head = repo.index.commit(
        "merge",
        author=Actor("dependabot[bot]", "bot@example.test"),
        parent_commits=[repo.head.commit, repo.commit("HEAD~2")],
    ).hexsha
    cfg = load_config("config/config.yaml")
    expected, files, summary = source_history(
        path,
        head,
        "a/b",
        cfg.model_dump(mode="json"),
        yaml.safe_load(Path("config/file_taxonomy.yaml").read_text()),
    )
    actual, changes, _ = mine_history(
        path, head, "a/b", cfg, load_taxonomy("config/file_taxonomy.yaml"), "fixture"
    )
    assert not reconcile_rows(expected, actual, ("commit_sha",), COMMIT_FIELDS)
    assert not reconcile_rows(files, changes, ("commit_sha", "file_path"), CHANGE_FIELDS)
    assert summary["funnel"] == {"merge": 1, "bot": 1, "included": 5}
    mutant = deepcopy(actual)
    next(r for r in mutant if r["commit_sha"] == bot)["eligibility_status"] = "included"
    assert any(
        r["field"] == "eligibility_status"
        for r in reconcile_rows(expected, mutant, ("commit_sha",), COMMIT_FIELDS)
    )
    mutant[0]["C"] = 1
    assert any(
        r["field"] == "C" for r in reconcile_rows(expected, mutant, ("commit_sha",), COMMIT_FIELDS)
    )
    assert any(
        r["field"] == "membership"
        for r in reconcile_rows(expected, actual[:-1], ("commit_sha",), COMMIT_FIELDS)
    )
    with pytest.raises(ValueError, match="Duplicate source/table identity"):
        reconcile_rows(expected, actual + actual[:1], ("commit_sha",), COMMIT_FIELDS)
    with object_reader(path) as read:
        with pytest.raises(ValueError, match="Full object SHA"):
            read("HEAD", "commit")
        with pytest.raises(ValueError, match="Missing or wrong"):
            read("f" * 40, "commit")
    repo.close()


def test_activity_boundary_aliases_and_large_commit(tmp_path: Path) -> None:
    cfg = load_config("config/config.yaml").model_dump(mode="json")
    cfg["commit_filter"]["large_commit_max_files"] = 1
    with Repo.init(tmp_path) as repo:
        for position, (date, name, email) in enumerate(
            [
                ("2025-08-31 23:59:59 +0000", "Before", "before@example.test"),
                ("2025-09-01 00:00:00 +0000", "Equal", "equal@example.test"),
                ("2025-09-01 00:00:01 +0000", "Alias One", "SAME@example.test"),
                ("2025-09-02 00:00:00 +0000", "Alias Two", "same@example.test"),
            ]
        ):
            for suffix in ("a", "b"):
                (tmp_path / f"{position}{suffix}.py").write_text("x=1")
            repo.git.add(".")
            repo.index.commit("activity", author=Actor(name, email), commit_date=date)
        rows, _, result = source_history(
            tmp_path,
            repo.head.commit.hexsha,
            "a/b",
            cfg,
            yaml.safe_load(Path("config/file_taxonomy.yaml").read_text()),
        )
        assert result["active_contributors_count"] == 1
        assert all(r["eligibility_status"] == "large_commit" for r in rows)


def test_nullable_transport_and_invalid_counts(tmp_path: Path) -> None:
    path = tmp_path / "table.parquet"
    pd.DataFrame(
        [
            dict(changed_key_count=2.0, changed_keys=["x"]),
            dict(changed_key_count=None, changed_keys=[]),
        ]
    ).to_parquet(path)
    assert read_table(path) == [
        dict(changed_key_count=2, changed_keys=["x"]),
        dict(changed_key_count=None, changed_keys=[]),
    ]
    csv = tmp_path / "table.csv"
    csv.write_text("numerator,value\n2,0.5\n,\n")
    assert read_table(csv) == [dict(numerator=2, value=0.5), dict(numerator=None, value=None)]
    for value in (True, 1.5, float("inf")):
        pd.DataFrame([dict(changed_key_count=value)]).to_parquet(path)
        with pytest.raises(ValueError):
            read_table(path)
    csv.write_text("numerator,denominator\n7820.0,276\n")
    assert read_table(csv) == [dict(numerator=7820, denominator=276)]
    csv.write_text("numerator\n1.00000000000000000001\n")
    with pytest.raises(ValueError, match="Noninteger count"):
        read_table(csv)
    csv.write_text("numerator\noops\n")
    with pytest.raises(ValueError, match="Invalid integer count"):
        read_table(csv)
    csv.write_text("value\nnan\n")
    with pytest.raises(ValueError, match="Nonfinite metric"):
        read_table(csv)


def test_descriptive_independent_reference() -> None:
    cfg = load_config("config/config.yaml")
    rows = json.loads(Path("tests/fixtures/verification/four_commits.json").read_text())["commits"]
    for i, row in enumerate(rows):
        row["committed_at_utc"] = "2026-01-31T23:59:59Z" if i < 2 else "2026-04-01T01:00:00+02:00"
    changes = [
        dict(
            repository_id="fixture/four",
            commit_sha=rows[0]["commit_sha"],
            category="CONFIG",
            file_path=path,
            change_type=kind,
            before_blob_sha="same" if kind == "D" else None,
            after_blob_sha="same" if kind == "A" else None,
            changed_key_count=1,
            changed_keys=['["str:names", "int:0"]'],
        )
        for path, kind in (("data/old.yaml", "D"), ("new.yaml", "A"))
    ]
    for state in ("observed", "error", "not_applicable"):
        rows[0]["config_semantic_status"] = state
        result = describe(rows, changes, "fixture/four", cfg.analysis.model_dump())
        assert result["distribution"] == [distribution(rows, "fixture/four", cfg.analysis)]
        assert result["months"] == monthly_series(rows, "fixture/four")
        measured = configuration_sensitivity(rows, changes, "fixture/four", cfg.analysis)
        assert not reconcile_rows(
            result["sensitivity"],
            measured,
            ("variant",),
            tuple(result["sensitivity"][0]),
            tolerance=1e-12,
        )
    assert describe([], [], "a/b", cfg.analysis.model_dump())["months"] == []
    with pytest.raises(ValueError, match="linear"):
        describe([], [], "a/b", {"quantile_method": "nearest"})


def test_incomplete_clones_are_rejected_without_fetching(tmp_path: Path) -> None:
    cfg = load_config("config/config.yaml").model_dump(mode="json")
    taxonomy = yaml.safe_load(Path("config/file_taxonomy.yaml").read_text())
    with Repo.init(tmp_path) as repo:
        sha = change(repo, "train.py", "x=1")
        with pytest.raises(ValueError, match="full SHA"):
            source_history(tmp_path, "HEAD", "a/b", cfg, taxonomy)
        repo.git.config("remote.origin.promisor", "true")
        with pytest.raises(ValueError, match="Partial/promisor"):
            source_history(tmp_path, sha, "a/b", cfg, taxonomy)
        repo.git.config("--unset", "remote.origin.promisor")
        (Path(repo.git_dir) / "shallow").write_text(sha + "\n")
        with pytest.raises(ValueError, match="Shallow source"):
            source_history(tmp_path, sha, "a/b", cfg, taxonomy)
