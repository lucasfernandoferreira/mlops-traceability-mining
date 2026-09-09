"""Synthetic decisions only. No fixture label is evidence for the empirical study."""

from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml
from test_pilot_pipeline import project as project
from test_study_contracts import review_fixture
from test_study_pipeline import latest_study, setup_case

from mlops_traceability.config import load_config
from mlops_traceability.manifest import sha256_file
from mlops_traceability.pilot import write_csv, write_json
from mlops_traceability.study import run_study
from mlops_traceability.validation.taxonomy_review import evaluate_review, read_csv
from mlops_traceability.verification.reviews import (
    CODING_FIELDS,
    check_import_bindings,
    evaluate_import,
    import_reviews,
    main,
    validate_decisions,
)


@pytest.mark.counterexample
@pytest.mark.parametrize(
    "mutation,reason",
    [
        ("justification", "incomplete_human_review"),
        ("class", "incomplete_human_review"),
        ("timezone", "incomplete_human_review"),
        ("sha", "sample_integrity_mismatch"),
        ("missing", "sample_integrity_mismatch"),
        ("duplicate", "duplicate_sample_units"),
    ],
)
def test_taxonomy_record_mutations(tmp_path: Path, mutation: str, reason: str) -> None:
    original, reviewed, inv, config = review_fixture(tmp_path)
    assert evaluate_review(reviewed, config, original=original, inventory_path=inv)["accepted"]
    rows = read_csv(reviewed)
    if mutation == "justification":
        rows[0]["justification"] = "  "
    elif mutation == "class":
        rows[0]["expected_category"] = "invalid"
    elif mutation == "timezone":
        rows[0]["reviewed_at_utc"] = "2026-09-07T22:00:00-03:00"
    elif mutation == "sha":
        rows[0]["head_commit_sha"] = "b" * 40
    elif mutation == "missing":
        rows.pop()
    else:
        rows.append(rows[0].copy())
    write_csv(reviewed, rows)
    result = evaluate_review(reviewed, config, original=original, inventory_path=inv)
    assert not result["accepted"] and reason in result["blocking_reasons"]


@pytest.fixture
def imported_sources(project: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    (project / "docs").mkdir()
    shutil.copyfile("docs/DECISOES_METODOLOGICAS.md", project / "docs/DECISOES_METODOLOGICAS.md")
    sha, runs = setup_case(project, monkeypatch)
    specification = project / "runs.yaml"
    specification.write_text(
        yaml.safe_dump(
            {
                "cases": [
                    {
                        "repository_id": "test/case",
                        "head_commit_sha": sha,
                        "runs": runs,
                        "integration_paths": ["train.py"],
                    }
                ]
            }
        )
    )
    assert (
        run_study("study_index", ["--runs-file", str(specification), "--allow-dirty"], project) == 0
    )
    index = latest_study(project, "study_index") / "study_index.json"
    assert (
        run_study(
            "phase7_select_qualitative", ["--study-index", str(index), "--allow-dirty"], project
        )
        == 0
    )
    qualitative = latest_study(project, "phase7_select_qualitative")
    review = project / "reviews"
    review.mkdir()
    sources = {
        "taxonomia_revisada.csv": index.parent / "amostra_validacao_taxonomia.csv",
        "casos_revisados.json": index.parent / "case_review_template.json",
        "alinhamento_academico.json": index.parent / "academic_review_template.json",
        "codificacao_revisada.csv": qualitative / "codificacao_qualitativa.csv",
    }
    for name, source in sources.items():
        shutil.copyfile(source, review / name)
    write_json(
        review / "origens.json",
        {
            "study_index_sha256": sha256_file(index),
            "qualitative_run_id": qualitative.name,
            "originals": {
                name: {"path": str(path.relative_to(project)), "sha256": sha256_file(path)}
                for name, path in sources.items()
            },
        },
    )
    rows = read_csv(review / "taxonomia_revisada.csv")
    for row in rows:
        row.update(
            expected_category=row["category"],
            reviewer="synthetic",
            reviewed_at_utc="2026-09-08T00:00:00Z",
            justification="Known fixture role",
            role_change_review="All historical fixture versions inspected",
        )
    write_csv(review / "taxonomia_revisada.csv", rows)
    cases = json.loads((review / "casos_revisados.json").read_text())
    for case in cases:
        case.update(
            decision="accepted",
            decision_reason="Synthetic decision",
            reviewer="synthetic",
            reviewed_at_utc="2026-09-08T00:00:00Z",
            evidence_url="synthetic",
            evidence_scope="synthetic",
        )
    write_json(review / "casos_revisados.json", cases)
    coding = read_csv(review / "codificacao_revisada.csv")
    for row in coding:
        row.update(dict.fromkeys(CODING_FIELDS, "synthetic"))
        row.update(
            themes="training_integration;parameter_logging",
            reviewed_at_utc="2026-09-08T00:00:00Z",
            ambiguity="None found within synthetic fixture",
            contrary_evidence="None found within synthetic fixture",
        )
    write_csv(review / "codificacao_revisada.csv", coding)
    write_json(
        review / "alinhamento_academico.json",
        {
            "reviewer": "synthetic",
            "reviewed_at_utc": "2026-09-08T00:00:00Z",
            "status": "accepted",
            "evidence": "Synthetic academic decision",
            "operational_objective": "Synthetic objective",
            "unanswered_questions": ["runtime"],
            "mlflow_scope_resolved": True,
            "metric_mapping_resolved": True,
        },
    )
    return project, index, review


def test_import_preserves_bytes_without_scientific_acceptance(
    imported_sources: tuple[Path, Path, Path],
) -> None:
    root, index, review = imported_sources
    output = root / "imported"
    assert import_reviews(root, index, review, output, scope="synthetic") == 0
    receipt = json.loads((output / "review_import.json").read_text())
    assert receipt["review_import_status"] == "PASS"
    assert not receipt["scientific_result_accepted"] and receipt["scope"] == "synthetic"
    assert (
        receipt["independent_label_tally"]["agreement_numerator"]
        == receipt["taxonomy"]["sample_count"]
    )
    assert receipt["transformations"] == []
    for name in receipt["review_file_hashes"]:
        assert (output / "original_reviews" / name).read_bytes() == (review / name).read_bytes()
    check_import_bindings(output / "review_import.json", root, index, review)
    with pytest.raises(FileExistsError):
        import_reviews(root, index, review, output, scope="synthetic")
    # Rejected or incomplete records are preserved too, with exit 1.
    taxonomy = read_csv(review / "taxonomia_revisada.csv")
    taxonomy[0]["justification"] = ""
    write_csv(review / "taxonomia_revisada.csv", taxonomy)
    assert import_reviews(root, index, review, root / "invalid", scope="synthetic") == 1
    # Missing inputs produce a receipt and exit 2, never skip.
    (review / "casos_revisados.json").unlink()
    assert import_reviews(root, index, review, root / "missing", scope="synthetic") == 2
    missing = json.loads((root / "missing/review_import.json").read_text())
    assert "missing_input:casos_revisados.json" in missing["blocking_reasons"]
    assert import_reviews(root, root / "missing_index", review, root / "missing_index_result") == 2
    write_json(review / "casos_revisados.json", {"unexpected": True})
    assert import_reviews(root, index, review, root / "wrong_shape", scope="synthetic") == 2
    (root / "config/verification.yaml").write_text("broken: [")
    assert import_reviews(root, index, review, root / "invalid_policy", scope="synthetic") == 2
    with pytest.raises(ValueError, match="Invalid scope"):
        import_reviews(root, index, review, root / "bad_scope", scope="unknown")


@pytest.mark.counterexample
def test_review_round_and_hash_mutations(imported_sources: tuple[Path, Path, Path]) -> None:
    root, index, review = imported_sources
    output = root / "imported"
    assert import_reviews(root, index, review, output, scope="synthetic") == 0
    receipt = output / "review_import.json"
    check_import_bindings(receipt, root, index, review)
    for path, message in (
        (review / "taxonomia_revisada.csv", "Review hash mismatch"),
        (output / "original_reviews/casos_revisados.json", "Review hash mismatch"),
        (root / "config/verification.yaml", "Bound source hash mismatch"),
        (output / "verification_source.tar.gz", "source archive mismatch"),
        (index, "Study index hash mismatch"),
    ):
        original = path.read_bytes()
        path.write_bytes(original + b"\n")
        with pytest.raises(ValueError, match=message):
            check_import_bindings(receipt, root, index, review)
        path.write_bytes(original)
    origins_path = review / "origens.json"
    origins = json.loads(origins_path.read_text())
    wrong = deepcopy(origins)
    wrong["study_index_sha256"] = "f" * 64
    write_json(origins_path, wrong)
    assert import_reviews(root, index, review, root / "wrong_round", scope="synthetic") == 2
    result = json.loads((root / "wrong_round/review_import.json").read_text())
    assert any("another study index" in r for r in result["blocking_reasons"])
    wrong = deepcopy(origins)
    wrong["originals"]["taxonomia_revisada.csv"]["sha256"] = "f" * 64
    write_json(origins_path, wrong)
    policy = yaml.safe_load((root / "config/verification.yaml").read_text())
    with pytest.raises(ValueError, match="Review original mismatch"):
        evaluate_import(root, index, review, load_config(root / "config/config.yaml"), policy)


def test_invalid_decisions_are_discriminated() -> None:
    index = {"cases": [{"repository_id": "a/b", "head_commit_sha": "a" * 40}]}
    coding: list[dict[str, Any]] = [
        {"repository_id": "other/case", "event_id": "wrong", "themes": "undefined"}
    ] * 2
    problems = validate_decisions(index, [{"repository_id": "other/case"}], [], coding, [], {}, {})
    assert "cases:identity_mismatch" in problems
    assert "coding:duplicate_event" in problems
    assert "coding:identity_or_immutable_mismatch" in problems
    assert "coding:wrong:undefined_theme:undefined" in problems
    assert "academic:alignment_not_recorded" in problems


def test_cli_existing_destination(tmp_path: Path) -> None:
    assert (
        main(
            [
                "--study-index",
                str(tmp_path / "missing"),
                "--review-dir",
                str(tmp_path),
                "--output-dir",
                str(tmp_path),
            ]
        )
        == 2
    )


def test_emergent_themes_require_definition_and_dated_registration(tmp_path: Path) -> None:
    from mlops_traceability.verification.reviews import review_codebook

    policy = {"codebook": {"existing": "Existing definition"}}
    assert review_codebook(policy, tmp_path) == policy["codebook"]
    entry = {
        "theme_id": "new_theme",
        "definition": "Explicit emergent definition",
        "reviewer": "synthetic",
        "registered_at_utc": "2026-09-08T00:00:00Z",
    }
    path = tmp_path / "temas_emergentes.json"
    write_json(path, [entry])
    assert review_codebook(policy, tmp_path)["new_theme"] == entry["definition"]
    for update in (
        {"theme_id": "existing"},
        {"definition": ""},
        {"reviewer": ""},
        {"registered_at_utc": "2026-09-08"},
        {"theme_id": "a;b"},
    ):
        write_json(path, [{**entry, **update}])
        with pytest.raises(ValueError, match="Emergent theme requires"):
            review_codebook(policy, tmp_path)
