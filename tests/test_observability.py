from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mlops_traceability.observability import ExecutionObserver


def test_observer_emits_console_jsonl_progress_and_eta(tmp_path: Path) -> None:
    stream = io.StringIO()
    observer = ExecutionObserver(
        stage="phase-test",
        run_id="run-test",
        log_directory=tmp_path,
        stream=stream,
    )

    observer.event("input_loaded", "Entrada carregada", candidates=2)
    with observer.progress(
        name="items",
        total=2,
        interval_seconds=60,
    ) as progress:
        progress.update(1, current_item="owner/one", counts={"eligible": 1}, force=True)
        progress.update(2, current_item="owner/two", counts={"eligible": 2})

    console = stream.getvalue()
    assert "Entrada carregada" in console
    assert "items: 2/2 (100.0%)" in console
    assert "eta=00:00" in console
    assert "eligible=2" in console

    records = [
        json.loads(line) for line in observer.log_path.read_text(encoding="utf-8").splitlines()
    ]
    assert records[0]["event"] == "input_loaded"
    assert records[-1]["status"] == "finished"
    assert all(record["run_id"] == "run-test" for record in records)


@pytest.mark.parametrize(
    ("total", "initial_completed", "interval_seconds"),
    [(-1, 0, 1), (1, 2, 1), (1, 0, 0)],
)
def test_progress_rejects_invalid_bounds(
    tmp_path: Path,
    total: int,
    initial_completed: int,
    interval_seconds: float,
) -> None:
    observer = ExecutionObserver(
        stage="phase-test",
        run_id="run-test",
        log_directory=tmp_path,
        stream=io.StringIO(),
    )

    with pytest.raises(ValueError):
        observer.progress(
            name="items",
            total=total,
            initial_completed=initial_completed,
            interval_seconds=interval_seconds,
        )


def test_progress_marks_stall_and_invalidates_eta(tmp_path: Path) -> None:
    stream = io.StringIO()
    observer = ExecutionObserver(
        stage="phase-test",
        run_id="run-stalled",
        log_directory=tmp_path,
        stream=stream,
    )

    with patch(
        "mlops_traceability.observability.time.monotonic",
        side_effect=[0.0, 61.0],
    ):
        progress = observer.progress(
            name="items",
            total=10,
            initial_completed=5,
            interval_seconds=10,
            stall_threshold_seconds=60,
            details_provider=lambda: {
                "github_rate_limit_state": "cooldown",
                "blocked_workers": 4,
            },
        )
        progress._emit(force=True)

    record = json.loads(observer.log_path.read_text(encoding="utf-8"))
    assert record["status"] == "waiting"
    assert record["eta"] == "indisponivel"
    assert record["last_progress_ago"] == "01:01"
    assert record["stalled"] is True
    assert record["github_rate_limit_state"] == "cooldown"
    assert record["blocked_workers"] == 4


def test_progress_rejects_invalid_stall_threshold(tmp_path: Path) -> None:
    observer = ExecutionObserver(
        stage="phase-test",
        run_id="run-test",
        log_directory=tmp_path,
        stream=io.StringIO(),
    )

    with pytest.raises(ValueError):
        observer.progress(name="items", total=1, stall_threshold_seconds=0)
