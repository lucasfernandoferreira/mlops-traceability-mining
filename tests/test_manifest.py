import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from mlops_traceability.config import load_config
from mlops_traceability.manifest import RunManifest, sha256_file, write_manifest


def test_hash_is_deterministic(tmp_path: Path) -> None:
    target = tmp_path / "input.txt"
    target.write_text("conteúdo controlado", encoding="utf-8")

    assert sha256_file(target) == sha256_file(target)


def test_write_manifest(tmp_path: Path) -> None:
    root = Path.cwd()
    config = load_config(root / "config/config.yaml")
    started_at_utc = datetime.now(UTC)

    output = write_manifest(
        project_root=root,
        manifest_directory=tmp_path,
        config_path=root / "config/config.yaml",
        taxonomy_path=root / "config/file_taxonomy.yaml",
        requirements_path=root / "requirements.txt",
        protocol_id=config.protocol.id,
        protocol_version=config.protocol.version,
        stage="phase0_test",
        status="SUCCESS",
        started_at_utc=started_at_utc,
        require_clean_worktree=False,
    )

    assert output.is_file()
    assert output.suffix == ".json"
    manifest = RunManifest.model_validate_json(output.read_text(encoding="utf-8"))
    assert manifest.started_at_utc == started_at_utc
    assert manifest.finished_at_utc >= manifest.started_at_utc
    assert manifest.run_id == output.stem
    assert manifest.status == "SUCCESS"


def test_write_manifest_never_overwrites_a_run(tmp_path: Path) -> None:
    root = Path.cwd()
    config = load_config(root / "config/config.yaml")
    instant = datetime(2026, 1, 2, 3, 4, 5, 678901, tzinfo=UTC)

    arguments = {
        "project_root": root,
        "manifest_directory": tmp_path,
        "config_path": root / "config/config.yaml",
        "taxonomy_path": root / "config/file_taxonomy.yaml",
        "requirements_path": root / "requirements.txt",
        "protocol_id": config.protocol.id,
        "protocol_version": config.protocol.version,
        "stage": "phase0_collision_test",
        "status": "SUCCESS",
        "started_at_utc": instant,
        "require_clean_worktree": False,
    }

    with patch("mlops_traceability.manifest.datetime") as mocked_datetime:
        mocked_datetime.now.return_value = instant
        first_output = write_manifest(**arguments)  # type: ignore[arg-type]
        original_content = first_output.read_text(encoding="utf-8")

        with pytest.raises(FileExistsError):
            write_manifest(**arguments)  # type: ignore[arg-type]

    assert first_output.read_text(encoding="utf-8") == original_content
    assert json.loads(original_content)["run_id"] == first_output.stem
