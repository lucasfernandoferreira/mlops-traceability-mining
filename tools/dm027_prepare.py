# ruff: noqa: E501
"""Consolida fontes já registradas sem refazer coleta ou alterar runs."""

import csv
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from mlops_traceability.run_storage import verified_run

ROOT = Path(__file__).resolve().parents[1]
INDEX_ID = "20260911T204432183508Z_1ce60b65_study_index"
QUAL_ID = "20260911T204444532841Z_1ce60b65_phase7_select_qualitative"
REPORT_ID = "20260911T204458152055Z_1ce60b65_phase8_report"
WORK = ROOT / "data/interim/fechamento_dm027"
REVIEW = WORK / "revisoes"
EVID = ROOT / "docs/evidencias"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    if path.exists():
        if path.read_text() != content:
            raise ValueError(f"Destino existente diferente: {path}")
    else:
        path.write_text(content)


def main():
    REVIEW.mkdir(parents=True, exist_ok=True)
    index_path = ROOT / "data/interim/runs" / INDEX_ID / "study_index.json"
    index = json.loads(index_path.read_text())
    ids = [
        (ref["run_id"], case["repository_id"])
        for case in index["cases"]
        for ref in case["runs"].values()
    ]
    ids += [(INDEX_ID, "conjunto"), (QUAL_ID, "conjunto"), (REPORT_ID, "conjunto")]
    rows, objects = [], {}
    for rid, case in ids:
        manifest, artifacts, execution = verified_run(ROOT, rid, scientific=True)
        objects[rid] = artifacts
        for path in [ROOT / f"data/processed/manifests/{rid}.json", *artifacts.values()]:
            rows.append(
                {
                    "run_id": rid,
                    "case": case,
                    "path": path.relative_to(ROOT).as_posix(),
                    "sha256": sha(path),
                    "date_utc": manifest["finished_at_utc"],
                    "code_commit_sha": manifest["code_commit_sha"],
                }
            )
    write(EVID / "rodada_referencia_1_2_0.json", {"index": INDEX_ID, "artifacts": rows})
    (EVID / "rodada_referencia_1_2_0.md").write_text(
        "# Rodada de referência da taxonomia 1.2.0\n\n"
        "Gerado por `tools/dm027_prepare.py`; hashes reconferidos nesta sessão. "
        "Elegibilidade técnica não equivale a aceite científico.\n\n"
        "| Run | Caso | Artefato | SHA-256 | Encerramento UTC |\n|---|---|---|---|---|\n"
        + "\n".join(
            "| " + " | ".join(r[k] for k in ("run_id", "case", "path", "sha256", "date_utc")) + " |"
            for r in rows
        )
        + "\n"
    )
    spec = EVID / "runs_dm027.json"
    data = json.loads(spec.read_text())
    for case in data["cases"]:
        original = next(c for c in index["cases"] if c["repository_id"] == case["repository_id"])
        assert case["head_commit_sha"] == original["head_commit_sha"]
        assert case["runs"] == {k: v["run_id"] for k, v in original["runs"].items()}
    if "schema_version" not in data:
        shutil.copy2(spec, WORK / "runs_dm027_recebido.json")
        data["schema_version"] = "1.0.0"
        data["study_index_run_id"] = INDEX_ID
        data["qualitative_run_id"] = QUAL_ID
        data["report_run_id"] = REPORT_ID
        spec.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    template = {
        "taxonomia_revisada.csv": objects[INDEX_ID]["amostra_validacao_taxonomia.csv"],
        "casos_revisados.json": objects[INDEX_ID]["case_review_template.json"],
        "alinhamento_academico.json": objects[INDEX_ID]["academic_review_template.json"],
        "codificacao_revisada.csv": objects[QUAL_ID]["codificacao_qualitativa.csv"],
    }
    origins = {
        "study_index": index_path.relative_to(ROOT).as_posix(),
        "study_index_sha256": sha(index_path),
        "qualitative_run_id": QUAL_ID,
        "report_run_id": REPORT_ID,
        "originals": {},
    }
    for name, path in template.items():
        origins["originals"][name] = {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha(path),
            "source_mtime_utc": datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(),
        }
        if not (REVIEW / name).exists():
            shutil.copy2(path, REVIEW / name)
    write(REVIEW / "origens.json", origins)
    old = ROOT / "data/interim/reviews/avaliacao_taxonomia_1_2_0_20260911/origem_taxonomia.json"
    previous = json.loads(old.read_text())
    compare = {
        k: {"previous": previous[k], "registered": index[k], "equal": previous[k] == index[k]}
        for k in ("sample_sha256", "inventory_sha256")
    }
    write(
        EVID / "correspondencia_previa_definitiva.json",
        {
            "source": str(old.relative_to(ROOT)),
            "source_sha256": sha(old),
            "index": origins["study_index"],
            "index_sha256": sha(index_path),
            "comparison": compare,
            "original_preserved": True,
        },
    )
    (EVID / "correspondencia_previa_definitiva.md").write_text(
        "# Correspondência da prévia com a rodada registrada\n\n"
        "Origem anterior preservada. A cópia de revisão atual usa os modelos do índice registrado.\n\n"
        "| Conteúdo | SHA-256 anterior | SHA-256 registrado | Igualdade |\n|---|---|---|---|\n"
        + "\n".join(
            f"| {k} | {v['previous']} | {v['registered']} | {v['equal']} |"
            for k, v in compare.items()
        )
        + "\n"
    )
    sample = list(csv.DictReader(template["taxonomia_revisada.csv"].open()))
    blind = WORK / "taxonomia_cega.csv"
    if not blind.exists():
        fields = [
            k for k in sample[0] if k not in {"category", "calibration_used", "taxonomy_version"}
        ]
        with blind.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows({k: r[k] for k in fields} for r in sample)
    write(
        WORK / "protocolo_cego.json",
        {
            "path": str(blind.relative_to(ROOT)),
            "sha256": sha(blind),
            "source_sha256": sha(template["taxonomia_revisada.csv"]),
            "rows": len(sample),
            "removed_fields": ["category", "calibration_used", "taxonomy_version"],
            "limitation": "Ordem original preservada; agrupamento estratificado e conhecimento prévio das regras limitam o cegamento. Rascunho de IA não mede concordância humana independente.",
        },
    )
    manifest_entries = []
    for base in ["data/interim", "data/processed/manifests", "data/raw/repos"]:
        for p in sorted((ROOT / base).rglob("*")):
            if not p.is_file() or p.is_symlink() or WORK in p.parents:
                continue
            rel = p.relative_to(ROOT).as_posix()
            if "/restored_instrument.git/" in rel or "/.git/" in rel:
                continue
            role = (
                "fonte_git_recuperavel"
                if base.endswith("repos")
                else "manifesto"
                if "manifests" in base
                else "insumo_ou_evidencia_preservada"
            )
            manifest_entries.append(
                {
                    "path": rel,
                    "sha256": sha(p),
                    "size": p.stat().st_size,
                    "origin": base,
                    "role": role,
                    "recovery": "cópia local preservada; referência em inventário",
                }
            )
    write(
        EVID / "inventario_insumos.json",
        {
            "schema_version": "1.0.0",
            "scope": "inventário de preservação anterior às novas revisões; exclui a pasta mutável desta tarefa",
            "files": manifest_entries,
        },
    )
    print(
        json.dumps(
            {
                "runs": len(ids),
                "artifacts": len(rows),
                "inventory_files": len(manifest_entries),
                "sample_rows": len(sample),
                "blind_sha256": sha(blind),
                "comparison": compare,
            },
            indent=2,
        )
    )
    for filename in ["DM027_TAXONOMIA_1_2_0.md", "INSPECAO_MANUAL_AMOSTRA.md"]:
        p = ROOT / "docs" / filename
        txt = p.read_text()
        notice = "## Estado consolidado da rodada\n\nA cadeia registrada está identificada em [rodada de referência](evidencias/rodada_referencia_1_2_0.md). "
        notice += "Mineração, métricas, índice, seleção e relatório já foram executados. "
        notice += "As passagens abaixo sobre prévia e registro futuro são históricas. O fechamento e a autoria das novas análises estão em `RELATORIO_FECHAMENTO_DM027.md`.\n\n[HISTÓRICO — rodada anterior]\n\n"
        if "## Estado consolidado da rodada" not in txt:
            first, rest = txt.split("\n", 1)
            p.write_text(first + "\n\n" + notice + rest)
    log = EVID / "log_fechamento_dm027.md"
    log.write_text(
        "# Log do fechamento DM-027\n\n"
        "Solicitação original preservada em `data/interim/fechamento_dm027/prompt_recebido.txt`.\n"
        "Reconhecimento: `pwd`, `git status --short`, leitura integral dos cinco documentos, Makefile, pyproject.toml e CLIs; "
        "`git branch -a`, `git tag`, `git stash list`, `git log --all`, `git reflog --all`, `git fsck --full --no-reflogs --unreachable`.\n"
        "Branch `feat/dm027-fechamento` criada com escalonamento de sandbox porque `.git` é somente leitura no sandbox.\n"
        "Comandos seguintes, saídas, códigos e hashes preservados em `data/interim/fechamento_dm027/comandos/`. "
        "A atualização deste log ocorre entre execuções, para manter worktree limpo nas verificações.\n\n"
        "Bloco 1: `python tools/dm027_prepare.py`. Fontes verificadas por `verified_run(scientific=True)`; "
        "especificação confrontada com o índice; origens mantidas; cópia cega sem predições; inventário calculado por leitura dos bytes. "
        "Nenhuma consulta ao GitHub ou alteração da taxonomia.\n"
    )


if __name__ == "__main__":
    main()
