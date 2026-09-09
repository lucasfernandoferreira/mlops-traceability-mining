"""Synthetic end-to-end receipts and source-chain rejection, never human study data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from git import Repo
from test_pilot_pipeline import project as project
from test_pilot_pipeline import synthetic

from mlops_traceability.config import load_config
from mlops_traceability.manifest import sha256_file
from mlops_traceability.mining import inspect_tree, mine_history
from mlops_traceability.pilot import run_stage, source_artifact, write_csv, write_json
from mlops_traceability.run_storage import StageName, verified_run
from mlops_traceability.study import create_index, load_index, run_study
from mlops_traceability.taxonomy import load_taxonomy
from mlops_traceability.validation.taxonomy_review import build_inventory, read_csv


def latest_study(root: Path, stage: str) -> Path:
    return sorted((root / "data/interim/runs").glob(f"*_{stage}"))[-1]


def setup_case(project: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, dict[str, str]]:
    repo, sha = synthetic(project)
    target = project / "data/raw/repos/test__case.git"
    Repo.clone_from(str(repo.working_tree_dir), target, bare=True).close()
    with Repo(target) as bare:
        bare.remotes.origin.set_url("https://github.com/test/case.git")
    sample_path = project / "config/amostra_final.yaml"
    sample = yaml.safe_load(sample_path.read_text())
    sample["repositories"] = [
        {"repository_id": "test/case", "head_commit_sha": sha, "stratum": "apenas_mlflow"}
    ]
    sample_path.write_text(yaml.safe_dump(sample))
    monkeypatch.setattr("mlops_traceability.pilot.audit_collection", lambda *_: {"verified": True})
    runs: dict[str, str] = {}
    args = ["--allow-dirty", "--repository", "test/case"]
    stages: list[tuple[str, StageName, str]] = [
        ("freeze", "phase3_clone_repos", "frozen_sample"),
        ("mine", "phase4_mine_commits", "commits"),
        ("metrics", "phase5_compute_metrics", "metrics"),
    ]
    for short, stage, artifact in stages:
        extra = (
            []
            if short == "freeze"
            else ["--source-run-id", runs["freeze" if short == "mine" else "mine"]]
        )
        assert run_stage(stage, args + extra, project) == 0
        _, runs[short] = source_artifact(project, stage, artifact)
    repo.close()
    return sha, runs


def test_explicit_source_stages_inventory_and_wrong_identity(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sha, runs = setup_case(project, monkeypatch)
    before, _ = source_artifact(project, "phase4_mine_commits", "commits", runs["mine"])
    sample_path = project / "config/amostra_final.yaml"
    sample = yaml.safe_load(sample_path.read_text())
    original_sample = sample_path.read_text()
    sample["repositories"].append({"repository_id": "wrong/case", "head_commit_sha": sha})
    sample_path.write_text(yaml.safe_dump(sample))
    assert (
        run_stage(
            "phase4_mine_commits",
            ["--allow-dirty", "--repository", "wrong/case", "--source-run-id", runs["freeze"]],
            project,
        )
        == 1
    )
    sample["repositories"][0]["head_commit_sha"] = "b" * 40
    sample_path.write_text(yaml.safe_dump(sample))
    mismatched_sources: list[tuple[StageName, str]] = [
        ("phase4_mine_commits", runs["freeze"]),
        ("phase5_compute_metrics", runs["mine"]),
    ]
    for stage, source in mismatched_sources:
        assert (
            run_stage(
                stage,
                [
                    "--allow-dirty",
                    "--repository",
                    "test/case",
                    "--source-run-id",
                    source,
                ],
                project,
            )
            == 1
        )
    sample_path.write_text(original_sample)
    # A failed global latest never replaces the explicitly requested valid source.
    assert source_artifact(project, "phase4_mine_commits", "commits", runs["mine"])[0] == before
    with pytest.raises(ValueError, match="run/stage"):
        verified_run(project, runs["mine"], "phase3_clone_repos")
    with pytest.raises(ValueError, match="manifest hash"):
        verified_run(project, runs["mine"], expected_hash="tampered")
    with pytest.raises(ValueError, match="Development"):
        verified_run(project, runs["mine"], scientific=True)
    with pytest.raises(FileNotFoundError):
        source_artifact(project, "phase4_mine_commits", "commits", "missing")
    directory = project / "test-index"
    directory.mkdir()
    case = {"repository_id": "test/case", "head_commit_sha": sha, "runs": runs}
    config = load_config(project / "config/config.yaml")
    for corrupted in (
        {**case, "head_commit_sha": "b" * 40},
        {**case, "runs": {**runs, "mine": runs["metrics"]}},
    ):
        with pytest.raises(ValueError):
            create_index(project, {"cases": [corrupted]}, directory, config)
    manifest_path = project / "data/processed/manifests" / f"{runs['mine']}.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["protocol_version"] = "old"
    write_json(manifest_path, manifest)
    with pytest.raises(ValueError, match="protocol"):
        verified_run(project, runs["mine"])


def test_historical_deletion_and_incomplete_inventory(tmp_path: Path) -> None:
    repo, _ = synthetic(tmp_path)
    root = Path(str(repo.working_tree_dir))
    repo.index.remove(["cfg/model.yaml"], working_tree=True)
    sha = repo.index.commit("synthetic deletion").hexsha
    config, taxonomy = load_config("config/config.yaml"), load_taxonomy("config/file_taxonomy.yaml")
    commits, changes, summary = mine_history(root, sha, "a/b", config, taxonomy, "synthetic")
    inspection = inspect_tree(root, sha, "a/b", taxonomy)
    deletion = [r for r in changes if r["change_type"] == "D"]
    inventory = build_inventory(root, deletion, inspection, summary, taxonomy, config)
    row = next(r for r in inventory["units"] if r["file_path"] == "cfg/model.yaml")
    assert row["blob_revision"] == deletion[0]["parent_sha"]
    assert row["commit_sha"] == sha and inventory["complete"]
    deletion[0]["file_path"] = "nonexistent"
    assert not build_inventory(root, deletion, inspection, summary, taxonomy, config)["complete"]
    deletion[0]["file_path"] = "../escape"
    with pytest.raises(ValueError, match="Noncanonical"):
        build_inventory(root, deletion, inspection, summary, taxonomy, config)
    repo.close()


def test_full_derived_pipeline_blank_review_and_tampering(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    index_path = latest_study(project, "study_index") / "study_index.json"
    index, inputs = load_index(project, index_path)
    assert len(inputs) == 1
    common = ["--study-index", str(index_path), "--allow-dirty"]
    original = index_path.parent / "amostra_validacao_taxonomia.csv"
    assert run_study("phase6_validate_taxonomy", common + ["--sample", str(original)], project) == 1
    blank_receipt_dir = latest_study(project, "phase6_validate_taxonomy")
    assert not json.loads((blank_receipt_dir / "taxonomy_validation.json").read_text())["accepted"]
    reviewed = project / "review.csv"
    rows = read_csv(original)
    for row in rows:
        row.update(
            expected_category=row["category"],
            reviewer="synthetic evaluator",
            justification="Synthetic fixture: explicit known CODE role.",
            reviewed_at_utc="2026-09-07T00:00:00Z",
            role_change_review="synthetic role checked",
        )
    write_csv(reviewed, rows)
    assert (
        run_study(
            "phase6_validate_taxonomy",
            common
            + [
                "--sample",
                str(reviewed),
                "--inventory",
                str(index_path.parent / "taxonomy_inventory.json"),
            ],
            project,
        )
        == 0
    )
    validation = latest_study(project, "phase6_validate_taxonomy")
    receipt = json.loads((validation / "taxonomy_validation.json").read_text())
    assert receipt["accepted"] and receipt["input_hashes"]["inventory"] == index["inventory_sha256"]
    assert run_study("phase7_select_qualitative", common, project) == 0
    qualitative = latest_study(project, "phase7_select_qualitative")
    assert run_study("phase8_report", common, project) == 0
    report = latest_study(project, "phase8_report")
    assert len(list(report.glob("*.png"))) == 3
    assert (
        run_study(
            "phase9_finalize_study",
            common
            + [
                "--validation-run-id",
                validation.name,
                "--qualitative-run-id",
                qualitative.name,
                "--report-run-id",
                report.name,
            ],
            project,
        )
        == 1
    )
    final = json.loads(
        (latest_study(project, "phase9_finalize_study") / "study_acceptance.json").read_text()
    )
    assert (
        not final["scientific_result_accepted"]
        and "development_or_invalid_source_chain" in final["blocking_reasons"]
    )
    assert "academic_alignment_pending" in final["blocking_reasons"]
    assert (
        run_study(
            "phase6_validate_taxonomy",
            common + ["--sample", str(reviewed), "--inventory", str(reviewed)],
            project,
        )
        == 1
    )
    assert run_study("phase8_report", ["--study-index", str(index_path)], project) == 1
    manifest_path = project / "data/processed/manifests" / f"{runs['mine']}.json"
    manifest = json.loads(manifest_path.read_text())
    before_hash = sha256_file(manifest_path)
    manifest["dirty_worktree"] = False
    write_json(manifest_path, manifest)
    assert sha256_file(manifest_path) != before_hash
    # The immutable index pins the original upstream manifest, so even metadata edits fail.
    with pytest.raises(ValueError, match="manifest hash"):
        load_index(project, index_path)


def test_case_measurements_cannot_be_filled_with_invented_counts(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import zipfile

    from mlops_traceability.study import verify_case_measurements, write_results_packet

    config = load_config(project / "config/config.yaml")
    sample = yaml.safe_load((project / "config/amostra_final.yaml").read_text())
    shortlist = (
        project
        / "data/interim/runs"
        / sample["source_runs"]["phase2_screen_sample"]
        / "shortlist.csv"
    )
    shortlist.parent.mkdir(parents=True)
    write_csv(
        shortlist,
        [
            {
                "repository_id": "test/case",
                "stars_count": 100,
                "observed_at_utc": "2026-09-01T00:00:00Z",
            }
        ],
    )
    monkeypatch.setattr("mlops_traceability.study.audit_collection", lambda *_: {"verified": True})
    summary_path = project / "summary.json"
    write_json(
        summary_path,
        {
            "reachable_commits": 300,
            "active_contributors_count": 5,
            "active_after": "2025-09-01T00:00:00Z",
        },
    )
    index = {"cases": [{"repository_id": "test/case", "head_commit_sha": "a" * 40}]}
    inputs = {"test/case": {"mining_summary.json": summary_path}}
    review: dict[str, Any] = {
        "repository_id": "test/case",
        "reachable_commit_count": 300,
        "active_identity_count": 5,
        "stars_at_collection": 100,
        "collection_timestamp": "2026-09-01T00:00:00Z",
        "active_after": "2025-09-01T00:00:00Z",
        "evidence_type": "structural",
        "evidence_url": f"https://github.com/test/case/blob/{'a' * 40}/train.py",
    }
    assert verify_case_measurements(project, index, inputs, [review])
    review["active_identity_count"] = 6
    assert not verify_case_measurements(project, index, inputs, [review])
    review["active_identity_count"] = 5
    review["evidence_type"] = "proxy"
    assert not verify_case_measurements(project, index, inputs, [review])
    review["repository_id"] = "unknown/case"
    assert not verify_case_measurements(project, index, inputs, [review])
    output = project / "packet"
    output.mkdir()
    metrics = [
        {
            "repository_id": "test/case",
            "metric_id": "cochange",
            "numerator": 1,
            "denominator": 2,
            "value": 0.5,
            "status": "observed",
        }
    ]
    coding = [
        {
            "repository_id": "test/case",
            "event_id": "synthetic",
            "quantitative_pattern": "synthetic pattern",
            "interpretation": "synthetic interpretation",
            "evidence": "synthetic source",
            "contrary_evidence": "synthetic contrary",
            "conclusion_limit": "synthetic limit",
        }
    ]
    write_results_packet(
        project,
        output,
        [],
        metrics,
        coding,
        {"operational_objective": "synthetic test", "unanswered_questions": ["runtime"]},
        config,
    )
    with zipfile.ZipFile(output / "reproduction.zip") as archive:
        manifest = json.loads(archive.read("PACKAGE_MANIFEST.json"))
        assert manifest["files"]
        assert not any("data/raw/repos" in name for name in archive.namelist())
        assert "synthetic interpretation" in archive.read("packet/resultados_discussao.md").decode()
