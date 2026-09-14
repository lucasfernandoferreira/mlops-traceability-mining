"""Confirmação única pelo pesquisador; preserva rascunhos e executa o fechamento."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from mlops_traceability.study import run_study
from mlops_traceability.verification.release import confirm_reviews, final_receipt, restore_study
from mlops_traceability.verification.runner import verify_study


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--responsavel", required=True)
    parser.add_argument("--assumo-revisao", action="store_true")
    parser.add_argument(
        "--lock", type=Path, default=root / "data/interim/fechamento_dm027/confirmation_lock.json"
    )
    args = parser.parse_args()
    work = root / "data/interim/fechamento_dm027"
    try:
        reviews = confirm_reviews(
            root, work / "revisoes", args.lock, args.responsavel, args.assumo_revisao
        )
        origins = json.loads((reviews / "origens.json").read_text())
        index = (
            root / "data/interim/runs/20260911T204432183508Z_1ce60b65_study_index/study_index.json"
        )
        runs = root / "data/interim/runs"
        before = set(runs.iterdir())
        if run_study(
            "phase6_validate_taxonomy",
            [
                "--study-index",
                str(index),
                "--sample",
                str(reviews / "taxonomia_revisada.csv"),
                "--inventory",
                str(index.parent / "taxonomy_inventory.json"),
            ],
            root,
        ):
            raise ValueError(
                "A avaliação taxonômica confirmada foi recusada; consulte o novo recibo."
            )
        validation = list(set(runs.iterdir()) - before)
        if len(validation) != 1:
            raise ValueError("Não foi possível identificar univocamente o run criado.")
        output = work / ("fechamento_confirmado_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
        output.mkdir()
        empirical = output / "empirical"
        if verify_study(root, index, reviews, empirical):
            raise ValueError(f"Verificação recusada: {empirical / 'verification_receipt.json'}")
        receipt = empirical / "verification_receipt.json"
        before = set(runs.iterdir())
        code = run_study(
            "phase9_finalize_study",
            [
                "--study-index",
                str(index),
                "--validation-run-id",
                validation[0].name,
                "--verification-receipt",
                str(receipt),
                "--qualitative-run-id",
                origins["qualitative_run_id"],
                "--report-run-id",
                origins["report_run_id"],
                "--case-review",
                str(reviews / "casos_revisados.json"),
                "--academic-review",
                str(reviews / "alinhamento_academico.json"),
                "--qualitative-review",
                str(reviews / "codificacao_revisada.csv"),
            ],
            root,
        )
        finalized = list(set(runs.iterdir()) - before)
        if len(finalized) != 1 or code not in {0, 1}:
            raise ValueError("Falha técnica do finalizador; recibos preservados.")
        candidate = finalized[0] / "reproduction.zip"
        if not candidate.is_file():
            raise ValueError("O finalizador não autorizou pacote candidato.")
        restoration = output / "restoration"
        restore_study(root, index, receipt, candidate, reviews, restoration)
        final = final_receipt(
            root,
            index,
            receipt,
            candidate,
            restoration / "restoration_report.json",
            reviews,
            output / "recibo_final.json",
        )
        print(json.dumps(final, ensure_ascii=False, indent=2))
        print(f"Recibo final: {output / 'recibo_final.json'}")
        return 0 if final["scientific_result_accepted"] else 1
    except (OSError, ValueError, KeyError) as error:
        print(f"Fechamento recusado: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
