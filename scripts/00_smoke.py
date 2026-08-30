"""Smoke test da fundação técnica e metodológica da pesquisa."""

import argparse
import tempfile
from collections import Counter
from pathlib import Path

from mlops_traceability.config import load_config
from mlops_traceability.manifest import build_artifact, start_run, write_manifest
from mlops_traceability.taxonomy import Category, load_taxonomy
from mlops_traceability.validation.synthetic_repo import (
    build_synthetic_repository,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest-dir",
        type=Path,
        default=Path("tmp/manifests"),
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Permitido apenas para desenvolvimento local da Fase 0.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]

    config_path = root / "config/config.yaml"
    taxonomy_path = root / "config/file_taxonomy.yaml"
    requirements_path = root / "requirements.txt"

    config = load_config(config_path)
    taxonomy = load_taxonomy(taxonomy_path)
    context = start_run(project_root=root, stage="phase0_smoke")

    with tempfile.TemporaryDirectory(prefix="tcc-synthetic-") as directory:
        repository = build_synthetic_repository(Path(directory))
        tracked_files = repository.git.ls_files().splitlines()

        classifications = Counter(taxonomy.classify(file_path) for file_path in tracked_files)

        required_categories = {
            Category.CODE,
            Category.CONFIG,
            Category.DATA_META,
            Category.DOC,
        }

        missing = required_categories - set(classifications)

        if missing:
            raise RuntimeError(f"Fixture sintética não produziu as categorias: {sorted(missing)}")

    if (
        config.reproducibility.require_clean_worktree
        and not args.allow_dirty
        and context.dirty_worktree
    ):
        raise RuntimeError(
            "A execução científica exige um worktree limpo. "
            "Faça commit ou registre explicitamente a alteração antes de executar."
        )

    manifest = write_manifest(
        context=context,
        manifest_directory=root / args.manifest_dir,
        config_path=config_path,
        taxonomy_path=taxonomy_path,
        requirements_path=requirements_path,
        protocol_id=config.protocol.id,
        protocol_version=config.protocol.version,
        status="SUCCESS",
        artifacts=[
            build_artifact(config_path),
            build_artifact(taxonomy_path),
            build_artifact(requirements_path),
        ],
    )

    print("Fase 0 validada com sucesso.")
    print(f"Manifesto: {manifest}")
    print(f"Categorias encontradas: {dict(classifications)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
