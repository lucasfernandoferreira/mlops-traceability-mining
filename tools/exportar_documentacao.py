"""Exporta a versão documental vigente sem históricos de execução ou de controle de versão."""

from __future__ import annotations

import argparse
import json
import subprocess
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from mlops_traceability.manifest import sha256_file


def export(root: Path, destination: Path) -> None:
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    allowed = {"docs", "src", "scripts", "tests", "tools", "config"}
    paths = {
        root / name
        for name in tracked
        if name and (Path(name).parts[0] in allowed or len(Path(name).parts) == 1)
    }
    paths.update((root / "data/interim/fechamento_dm027/revisoes").iterdir())
    paths.update(
        root / name for name in ("RELATORIO_FECHAMENTO_DM027.md", "PENDENCIAS_TECNICAS.md")
    )
    # Narrative execution logs and historical command transcripts belong to the archive.
    paths = {
        path
        for path in paths
        if path.is_file() and not path.name.startswith(("log_", "comandos_", "validacao_"))
    }
    entries = [
        {"path": p.relative_to(root).as_posix(), "sha256": sha256_file(p)} for p in sorted(paths)
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            archive.write(path, path.relative_to(root).as_posix())
        archive.writestr(
            "DOCUMENTATION_MANIFEST.json",
            json.dumps(
                {
                    "created_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "code_sha": subprocess.check_output(
                        ["git", "rev-parse", "HEAD"], cwd=root, text=True
                    ).strip(),
                    "package_status": "documentation_review",
                    "scientific_result_accepted": False,
                    "scope": (
                        "Documentos e código vigentes; fontes empíricas e recibos "
                        "são dependências externas."
                    ),
                    "files": entries,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
    print(
        json.dumps(
            {
                "package": str(destination),
                "files": len(entries),
                "sha256": sha256_file(destination),
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    export(Path(__file__).resolve().parents[1], args.output)


if __name__ == "__main__":
    main()
