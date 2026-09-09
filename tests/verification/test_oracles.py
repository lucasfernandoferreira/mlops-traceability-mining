"""Known answers and deliberate counterexamples; all inputs here are synthetic."""

from __future__ import annotations

import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from git import Actor, Repo
from test_pilot_metrics import calculate

from mlops_traceability.config import load_config
from mlops_traceability.mining import mine_history
from mlops_traceability.taxonomy import load_taxonomy
from mlops_traceability.verification.oracles import arithmetic, compare_metrics

FIXTURE = Path("tests/fixtures/verification/four_commits.json")


def fixture() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text())  # type: ignore[no-any-return]


def test_known_arithmetic_and_ordering() -> None:
    data = fixture()
    assert arithmetic(data["commits"]) == data["expected"]
    assert arithmetic(data["commits"][::-1]) == data["expected"]
    measured = list(calculate(data["commits"]).values())
    assert compare_metrics(data["expected"], measured) == []


def test_git_fixture_with_bot_and_merge(tmp_path: Path) -> None:
    with Repo.init(tmp_path) as repo:
        actor = Actor("fixture", "fixture@example.test")
        bot = Actor("dependabot[bot]", "bot@example.test")
        shas = []
        for label, files in (
            ("A", {"train.py": "x = 1\n", "config.yaml": "x: 1\ny: 2\n"}),
            ("B", {"train.py": "x = 2\n"}),
            ("C", {"config.yaml": "# comment only\nx: 1\ny: 2\n"}),
            ("D", {"README.md": "documentation\n"}),
            ("bot", {"train.py": "x = 3\n", "config.yaml": "x: 2\ny: 2\n"}),
        ):
            for name, text in files.items():
                (tmp_path / name).write_text(text)
            repo.index.add(list(files))
            shas.append(repo.index.commit(label, author=bot if label == "bot" else actor).hexsha)
        merge = repo.index.commit(
            "merge", author=bot, parent_commits=[repo.commit(shas[-1]), repo.commit(shas[1])]
        )
        rows, _, _ = mine_history(
            tmp_path,
            merge.hexsha,
            "fixture/four",
            load_config("config/config.yaml"),
            load_taxonomy("config/file_taxonomy.yaml"),
            "synthetic",
        )
    expected = fixture()["expected"]
    expected.update(reachable=6, funnel={"included": 4, "bot": 1, "merge": 1})
    assert arithmetic(rows) == expected
    assert compare_metrics(expected, list(calculate(rows).values())) == []
    by_sha = {r["commit_sha"]: r for r in rows}
    assert by_sha[shas[2]]["P"] and by_sha[shas[2]]["config_changed_keys"] == 0
    assert by_sha[merge.hexsha]["eligibility_status"] == "merge"


@pytest.mark.parametrize("state", ["error", "not_applicable"])
def test_no_partial_mean(state: str) -> None:
    rows = fixture()["commits"]
    rows[0]["config_semantic_status"] = state
    result = arithmetic(rows)
    assert result["metrics"]["config_magnitude"]["value"] is None
    assert result["metrics"]["config_magnitude"]["status"] == state
    assert not compare_metrics(result, list(calculate(rows).values()))


def test_zero_denominator_and_comparison_boundaries() -> None:
    expected = arithmetic([])
    assert expected["metrics"]["config_magnitude"]["status"] == "undefined"
    assert not compare_metrics(expected, list(calculate([]).values()))
    data = fixture()
    measured = list(calculate(data["commits"]).values())
    measured[0]["value"] += 5e-13
    assert not compare_metrics(data["expected"], measured)
    measured[0]["value"] += 2e-12
    assert "code_config_cochange:value" in compare_metrics(data["expected"], measured)
    measured[0]["value"] = float("nan")
    assert "code_config_cochange:value" in compare_metrics(data["expected"], measured)
    assert "code_config_cochange:missing" in compare_metrics(data["expected"], measured[1:])
    unavailable = next(r for r in measured if r["metric_id"] == "provenance_coverage")
    del unavailable["value"]
    assert "provenance_coverage:value:missing" in compare_metrics(data["expected"], measured)
    with pytest.raises(ValueError, match="Duplicate metric"):
        compare_metrics(data["expected"], measured + measured[:1])
    for tolerance in (-1, math.inf, math.nan):
        with pytest.raises(ValueError, match="Invalid tolerance"):
            compare_metrics(data["expected"], measured, tolerance=tolerance)


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("eligibility_status", "unknown", "Unknown eligibility"),
        ("C", "false", "booleans"),
        ("config_changed_keys", -1, "nonnegative integer"),
        ("config_changed_keys", 0.5, "nonnegative integer"),
        ("config_semantic_status", "not_available", "Unknown CONFIG"),
        ("repository_id", "other/case", "per case"),
    ],
)
def test_invalid_inputs_rejected(field: str, value: Any, message: str) -> None:
    rows = fixture()["commits"]
    rows[0][field] = value
    with pytest.raises(ValueError, match=message):
        arithmetic(rows)


@pytest.mark.counterexample
@pytest.mark.parametrize(
    "mutation,expected_reason",
    [
        ("denominator", "code_config_cochange:denominator"),
        ("omit_zero", "config_magnitude:denominator"),
        ("unavailable_zero", "provenance_coverage:value"),
    ],
)
def test_arithmetic_mutations(mutation: str, expected_reason: str) -> None:
    data = fixture()
    actual = list(calculate(data["commits"]).values())
    assert not compare_metrics(data["expected"], actual)  # Setup must pass first.
    if mutation == "denominator":
        actual[0].update(denominator=4, value=0.25)
    elif mutation == "omit_zero":
        actual = list(calculate([r for r in data["commits"] if r != data["commits"][2]]).values())
    else:
        next(r for r in actual if r["metric_id"] == "provenance_coverage")["value"] = 0
    assert expected_reason in compare_metrics(data["expected"], actual)


@pytest.mark.counterexample
def test_duplicate_sha_mutation() -> None:
    rows = fixture()["commits"]
    assert arithmetic(rows)["reachable"] == 4
    with pytest.raises(ValueError, match="Duplicate commit SHA"):
        arithmetic(rows + [deepcopy(rows[0])])


def test_sql_label_matrix_keeps_disagreement_and_absent_categories() -> None:
    from mlops_traceability.verification.oracles import taxonomy_tally

    rows = [
        dict(repository_id="a/b", expected_category="CODE", category="CODE"),
        dict(repository_id="a/b", expected_category="DOC", category="CODE"),
        dict(repository_id="c/d", expected_category="DOC", category="DOC"),
    ]
    result = taxonomy_tally(rows)
    assert result["agreement_numerator"] == 2 and result["agreement_denominator"] == 3
    assert result["confusion_matrix"] == [
        dict(expected_category="CODE", predicted_category="CODE", count=1),
        dict(expected_category="DOC", predicted_category="CODE", count=1),
        dict(expected_category="DOC", predicted_category="DOC", count=1),
    ]
    assert len(result["by_case"]) == 3
    assert taxonomy_tally(rows[::-1]) == result
    assert taxonomy_tally([])["agreement_denominator"] == 0
