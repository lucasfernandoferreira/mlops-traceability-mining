"""Observabilidade local para as etapas executáveis da pesquisa."""

from __future__ import annotations

import json
import sys
import threading
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Any, TextIO


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "calculando"
    rounded = max(0, round(seconds))
    hours, remainder = divmod(rounded, 3600)
    minutes, seconds_part = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds_part:02d}"
    return f"{minutes:02d}:{seconds_part:02d}"


class ExecutionObserver:
    """Emite eventos legíveis no terminal e JSONL para diagnóstico posterior."""

    def __init__(
        self,
        *,
        stage: str,
        run_id: str,
        log_directory: Path,
        stream: TextIO = sys.stdout,
        now_func: Any = _utc_now,
    ) -> None:
        self.stage = stage
        self.run_id = run_id
        self.log_path = log_directory / f"{run_id}.jsonl"
        self._stream = stream
        self._now_func = now_func
        self._lock = threading.Lock()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def event(self, name: str, message: str, **details: Any) -> None:
        timestamp = self._now_func().astimezone(UTC)
        payload = {
            "timestamp_utc": timestamp.isoformat().replace("+00:00", "Z"),
            "stage": self.stage,
            "run_id": self.run_id,
            "event": name,
            "message": message,
            **details,
        }
        detail_text = " ".join(
            f"{key}={value}" for key, value in details.items() if value is not None
        )
        console_line = f"[{payload['timestamp_utc']}] {self.stage} | {message}"
        if detail_text:
            console_line = f"{console_line} | {detail_text}"

        with self._lock:
            print(console_line, file=self._stream, flush=True)
            with self.log_path.open("a", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, default=str)
                handle.write("\n")

    def progress(
        self,
        *,
        name: str,
        total: int,
        initial_completed: int = 0,
        interval_seconds: float = 10,
    ) -> ProgressTask:
        return ProgressTask(
            observer=self,
            name=name,
            total=total,
            initial_completed=initial_completed,
            interval_seconds=interval_seconds,
        )


class ProgressTask:
    """Mantém heartbeat, taxa e ETA de uma coleção de trabalho."""

    def __init__(
        self,
        *,
        observer: ExecutionObserver,
        name: str,
        total: int,
        initial_completed: int,
        interval_seconds: float,
    ) -> None:
        if total < 0:
            raise ValueError("total não pode ser negativo")
        if not 0 <= initial_completed <= total:
            raise ValueError("initial_completed precisa estar entre zero e total")
        if interval_seconds <= 0:
            raise ValueError("interval_seconds precisa ser positivo")

        self._observer = observer
        self._name = name
        self._total = total
        self._initial_completed = initial_completed
        self._completed = initial_completed
        self._current_item: str | None = None
        self._counts: dict[str, int] = {}
        self._interval_seconds = interval_seconds
        self._started_at = time.monotonic()
        self._last_emitted_at = 0.0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._heartbeat = threading.Thread(
            target=self._heartbeat_loop,
            name=f"progress-{name}",
            daemon=True,
        )

    def __enter__(self) -> ProgressTask:
        self._emit(force=True)
        self._heartbeat.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_value, traceback
        self._stop.set()
        self._heartbeat.join(timeout=self._interval_seconds + 1)
        self._emit(force=True, status="failed" if exc_type is not None else "finished")

    def update(
        self,
        completed: int,
        *,
        current_item: str | None = None,
        counts: Mapping[str, int] | None = None,
        force: bool = False,
    ) -> None:
        if not 0 <= completed <= self._total:
            raise ValueError("completed precisa estar entre zero e total")
        with self._lock:
            self._completed = completed
            self._current_item = current_item
            if counts is not None:
                self._counts = dict(counts)
        self._emit(force=force or completed == self._total)

    def _heartbeat_loop(self) -> None:
        while not self._stop.wait(self._interval_seconds):
            self._emit(force=True, status="running")

    def _emit(self, *, force: bool, status: str = "running") -> None:
        now = time.monotonic()
        with self._lock:
            if not force and now - self._last_emitted_at < self._interval_seconds:
                return
            self._last_emitted_at = now
            completed = self._completed
            current_item = self._current_item
            counts = dict(self._counts)

        elapsed = max(0.0, now - self._started_at)
        newly_completed = completed - self._initial_completed
        rate = newly_completed / elapsed if elapsed > 0 and newly_completed > 0 else 0.0
        eta_seconds = (self._total - completed) / rate if rate > 0 else None
        percentage = 100.0 if self._total == 0 else completed / self._total * 100
        self._observer.event(
            f"{self._name}_progress",
            f"{self._name}: {completed}/{self._total} ({percentage:.1f}%)",
            status=status,
            elapsed=_format_duration(elapsed),
            eta=_format_duration(eta_seconds),
            items_per_minute=round(rate * 60, 2),
            current_item=current_item,
            **counts,
        )
