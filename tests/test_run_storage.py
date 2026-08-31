from __future__ import annotations

from pathlib import Path

import pytest

from mlops_traceability.run_storage import (
    build_run_pointer,
    load_latest_pointer,
    preserve_legacy_run,
    resolve_artifact,
    run_directory,
    write_latest_pointer,
)


def test_pointer_round_trip_and_artifact_resolution(tmp_path: Path) -> None:
    interim = tmp_path / "data/interim"
    directory = run_directory(interim, "run-1")
    directory.mkdir(parents=True)
    artifact = directory / "result.csv"
    artifact.write_text("header\nvalue\n", encoding="utf-8")
    pointer = build_run_pointer(
        interim_directory=interim,
        stage="phase1_search_candidates",
        status="SUCCESS",
        run_id="run-1",
        artifacts={"result": artifact},
    )

    write_latest_pointer(interim, pointer)
    loaded = load_latest_pointer(interim, "phase1_search_candidates")

    assert loaded == pointer
    assert loaded is not None
    assert resolve_artifact(interim, loaded, "result") == artifact.resolve()


def test_preserve_legacy_run_is_idempotent(tmp_path: Path) -> None:
    interim = tmp_path / "data/interim"
    interim.mkdir(parents=True)
    legacy = interim / "legacy.csv"
    legacy.write_text("original\n", encoding="utf-8")

    first = preserve_legacy_run(
        interim_directory=interim,
        stage="phase2_screen_sample",
        status="FAILED",
        run_id="screen-run",
        source_run_id="source-run",
        legacy_artifacts={"funnel": legacy},
    )
    legacy.write_text("changed\n", encoding="utf-8")
    second = preserve_legacy_run(
        interim_directory=interim,
        stage="phase2_screen_sample",
        status="FAILED",
        run_id="screen-run",
        source_run_id="source-run",
        legacy_artifacts={"funnel": legacy},
    )

    archived = resolve_artifact(interim, second, "funnel")
    assert first == second
    assert archived.read_text(encoding="utf-8") == "original\n"


def test_resolve_artifact_rejects_unknown_name(tmp_path: Path) -> None:
    interim = tmp_path / "interim"
    directory = run_directory(interim, "run-1")
    directory.mkdir(parents=True)
    artifact = directory / "result.csv"
    artifact.touch()
    pointer = build_run_pointer(
        interim_directory=interim,
        stage="phase1_search_candidates",
        status="SUCCESS",
        run_id="run-1",
        artifacts={"result": artifact},
    )

    with pytest.raises(KeyError):
        resolve_artifact(interim, pointer, "missing")
