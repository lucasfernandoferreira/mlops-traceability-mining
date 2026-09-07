"""Immutable study deliverables and independent scientific acceptance criteria."""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from mlops_traceability.config import ResearchConfig, load_config
from mlops_traceability.descriptive_analysis import (
    configuration_sensitivity,
    distribution,
    monthly_series,
)
from mlops_traceability.manifest import build_artifact, sha256_file, start_run, write_manifest
from mlops_traceability.pilot import audit_collection, snapshot_source, write_csv, write_json
from mlops_traceability.qualitative_selection import select_events
from mlops_traceability.run_storage import StageName, portable_path, run_directory, verified_run
from mlops_traceability.validation.taxonomy_review import (
    evaluate_review,
    make_sample,
    read_csv,
    valid_utc,
)

STAGES: dict[str, StageName] = {
    "freeze": "phase3_clone_repos",
    "mine": "phase4_mine_commits",
    "metrics": "phase5_compute_metrics",
}


def reference(root: Path, run_id: str, config: ResearchConfig) -> dict[str, str]:
    return {
        "run_id": run_id,
        "manifest_sha256": sha256_file(root / config.paths.manifests / f"{run_id}.json"),
    }


def load_index(root: Path, path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Path]]]:
    _, artifacts, _ = verified_run(root, path.parent.name, "study_index")
    if artifacts["study_index.json"] != path.resolve():
        raise ValueError("Index must be the immutable registered artifact")
    index = json.loads(path.read_text())
    cases = {}
    for case in index["cases"]:
        _, files, _ = verified_run(
            root,
            case["runs"]["mine"]["run_id"],
            "phase4_mine_commits",
            expected_hash=case["runs"]["mine"]["manifest_sha256"],
        )
        cases[case["repository_id"]] = files
    return index, cases


def prepare_case_reviews(
    root: Path,
    cases: list[dict[str, Any]],
    directory: Path,
    config: ResearchConfig,
) -> None:
    """Prepare factual fields and leave human judgment blank, never auto-approve."""
    evidence_path = root / "config/casos.yaml"
    evidence = yaml.safe_load(evidence_path.read_text())["cases"] if evidence_path.exists() else {}
    sample = yaml.safe_load((root / "config/amostra_final.yaml").read_text())
    shortlist_path = (
        root / "data/interim/runs" / sample["source_runs"]["phase2_screen_sample"] / "shortlist.csv"
    )
    shortlist = (
        {r["repository_id"]: r for r in read_csv(shortlist_path)} if shortlist_path.exists() else {}
    )
    reviews = []
    pr_template = {}
    for case in cases:
        repository, sha = case["repository_id"], case["head_commit_sha"]
        _, files, _ = verified_run(root, case["runs"]["mine"]["run_id"], "phase4_mine_commits")
        summary = json.loads(files["mining_summary.json"].read_text())
        observed = shortlist.get(repository, {})
        technical = evidence.get(repository, {})
        reviews.append(
            {
                "repository_id": repository,
                "repository_url": f"https://github.com/{repository}",
                "head_commit_sha": sha,
                **technical,
                "case_boundary": "canonical repository and reachable history at selected SHA",
                "selection_rationale": next(
                    r.get("selection_rationale", "")
                    for r in sample["repositories"]
                    if r["repository_id"] == repository
                ),
                "reachable_commit_count": summary["reachable_commits"],
                "active_after": summary["active_after"],
                "active_identity_count": summary["active_contributors_count"],
                "stars_at_collection": int(observed["stars_count"]) if observed else None,
                "collection_timestamp": observed.get("observed_at_utc", ""),
                "evidence_sha": sha,
                "evidence_url": (
                    f"https://github.com/{repository}/blob/{sha}/"
                    f"{technical.get('integration_component', '')}"
                ),
                "availability_reason": "" if technical else "not_collected",
                "decision": "",
                "decision_reason": "",
                "reviewer": "",
                "reviewed_at_utc": "",
                "source_run_ids": case["runs"],
                "protocol_version": config.protocol.version,
                "preparation_by": "Codex; technical preparation, not human review",
            }
        )
        commits = pd.read_parquet(files["commits.parquet"]).to_dict("records")
        pr_template[repository] = [
            {
                "commit_sha": r["commit_sha"],
                "status": "not_collected",
                "pr_url": "",
                "source_url": "",
                "reviewer": "",
                "checked_at_utc": "",
            }
            for r in commits
            if r["eligibility_status"] == "included"
        ]
    write_json(directory / "case_review_template.json", reviews)
    write_json(directory / "pr_map_template.json", pr_template)
    write_json(
        directory / "academic_review_template.json",
        {
            "status": "pending",
            "reviewer": "",
            "reviewed_at_utc": "",
            "evidence": "",
            "operational_objective": "",
            "unanswered_questions": [],
            "mlflow_scope_resolved": False,
            "metric_mapping_resolved": False,
        },
    )


def create_index(
    root: Path, specification: dict[str, Any], directory: Path, config: ResearchConfig
) -> dict[str, Any]:
    selected = yaml.safe_load((root / "config/amostra_final.yaml").read_text())
    expected = {r["repository_id"]: r["head_commit_sha"] for r in selected["repositories"]}
    supplied = specification["cases"]
    if (
        len(supplied) != len(expected)
        or {r["repository_id"]: r["head_commit_sha"] for r in supplied} != expected
    ):
        raise ValueError("Study index must contain exactly the selected cases and SHAs")
    units, cases, sources = [], [], []
    expected_unique_paths = 0
    complete = True
    errors = []
    for case in supplied:
        refs = {}
        executions = {}
        inventories = None
        for name, stage in STAGES.items():
            run_id = case["runs"][name]
            _, artifacts, execution = verified_run(root, run_id, stage)
            if (
                execution["repository_id"] != case["repository_id"]
                or execution["head_commit_sha"] != case["head_commit_sha"]
            ):
                raise ValueError("Case/run repository or SHA mismatch")
            refs[name] = reference(root, run_id, config)
            sources.append(refs[name])
            executions[name] = execution
            if name == "mine":
                inventories = json.loads(artifacts["taxonomy_inventory.json"].read_text())
        if (
            executions["mine"]["source_run_id"] != case["runs"]["freeze"]
            or executions["metrics"]["source_run_id"] != case["runs"]["mine"]
        ):
            raise ValueError("Study source chain mismatch")
        assert inventories is not None
        units.extend(inventories["units"])
        expected_unique_paths += inventories["expected_unique_paths"]
        complete = complete and inventories["complete"]
        errors.extend(inventories["errors"])
        cases.append({**case, "runs": refs})
    assert inventories is not None
    inventory = {
        "schema_version": "2.1.0",
        "complete": complete,
        "errors": errors,
        "cases": [
            {"repository_id": c["repository_id"], "head_commit_sha": c["head_commit_sha"]}
            for c in cases
        ],
        "taxonomy_version": inventories["taxonomy_version"],
        "units": units,
        "expected_unique_paths": expected_unique_paths,
        "scope": "all selected eligible histories and frozen trees",
    }
    write_json(directory / "taxonomy_inventory.json", inventory)
    write_csv(directory / "amostra_validacao_taxonomia.csv", make_sample(inventory, config))
    index = {
        "schema_version": "2.1.0",
        "protocol_version": config.protocol.version,
        "plan_version": config.analysis.plan_version,
        "cases": cases,
        "sources": sources,
        "inventory_sha256": sha256_file(directory / "taxonomy_inventory.json"),
        "sample_sha256": sha256_file(directory / "amostra_validacao_taxonomia.csv"),
        "taxonomy_version": inventories["taxonomy_version"],
    }
    write_json(directory / "study_index.json", index)
    prepare_case_reviews(root, cases, directory, config)
    return index


def report_tables(
    root: Path,
    index: dict[str, Any],
    inputs: dict[str, dict[str, Path]],
    directory: Path,
    config: ResearchConfig,
) -> None:
    metrics, months, distributions, sensitivity, characterization = [], [], [], [], []
    funnel: list[dict[str, Any]] = []
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    fig_rate, ax_rate = plt.subplots(figsize=(7, 4))
    fig_month, ax_month = plt.subplots(figsize=(9, 4))
    fig_config, ax_config = plt.subplots(figsize=(7, 4))
    for case in index["cases"]:
        repository = case["repository_id"]
        files = inputs[repository]
        commits = pd.read_parquet(files["commits.parquet"]).to_dict("records")
        changes = pd.read_parquet(files["changes.parquet"]).to_dict("records")
        summary = json.loads(files["mining_summary.json"].read_text())
        _, metric_files, _ = verified_run(
            root,
            case["runs"]["metrics"]["run_id"],
            "phase5_compute_metrics",
            expected_hash=case["runs"]["metrics"]["manifest_sha256"],
        )
        case_metrics = read_csv(metric_files["metrics.csv"])
        metrics.extend(case_metrics)
        series = monthly_series(commits, repository)
        months.extend(series)
        dist = distribution(commits, repository, config.analysis)
        distributions.append(dist)
        sensitivity.extend(configuration_sensitivity(commits, changes, repository, config.analysis))
        characterization.append(
            {k: v for k, v in summary.items() if k not in {"funnel", "identity_rule"}}
        )
        funnel.extend(
            {"repository_id": repository, "reason": reason, "count": count}
            for reason, count in summary["funnel"].items()
        )
        rate = next(r for r in case_metrics if r["metric_id"] == "code_config_cochange")
        if sum(r["denominator"] for r in series) != int(rate["denominator"]) or sum(
            r["numerator"] for r in series
        ) != int(rate["numerator"]):
            raise ValueError("Monthly series differs from source metric")
        if rate["status"] == "observed":
            ax_rate.bar(repository, float(rate["value"]))
        ax_month.plot(
            pd.to_datetime([r["month_utc"] + "-01" for r in series]),
            [float("nan") if r["value"] is None else r["value"] for r in series],
            label=repository,
        )
        if dist["status"] == "observed":
            values = sorted(
                r["config_changed_keys"]
                for r in commits
                if r["eligibility_status"] == "included" and r["P"]
            )
            ax_config.step(
                values,
                [(i + 1) / len(values) for i in range(len(values))],
                label=repository,
                where="post",
            )
    for name, rows in (
        ("metricas_consolidadas", metrics),
        ("serie_mensal", months),
        ("distribuicao_configuracao", distributions),
        ("sensibilidade_configuracao", sensitivity),
        ("caracterizacao_casos", characterization),
        ("funil_commits", funnel),
    ):
        write_csv(
            directory / f"{name}.csv", rows, list(rows[0]) if rows else ["repository_id", "status"]
        )
    coverage = [
        {
            k: r[k]
            for k in (
                "repository_id",
                "metric_id",
                "evidence_type",
                "status",
                "availability_reason",
                "evidence_scope",
            )
        }
        for r in metrics
    ]
    write_csv(directory / "cobertura_evidencias.csv", coverage)
    for fig, ax, name, ylabel in (
        (fig_rate, ax_rate, "proporcao_cp", "C∩P / C"),
        (fig_month, ax_month, "serie_mensal", "C∩P / C mensal"),
        (fig_config, ax_config, "distribuicao_magnitude", "Fração acumulada de commits CONFIG"),
    ):
        ax.set_ylabel(ylabel)
        ax.set_title("Descrição por caso — resultados preliminares")
        if ax is ax_month:
            # Matplotlib ships these date helper constructors without typed signatures.
            locator = mdates.AutoDateLocator(minticks=4, maxticks=8)  # type: ignore[no-untyped-call]
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(
                mdates.ConciseDateFormatter(locator)  # type: ignore[no-untyped-call]
            )
            ax.legend(fontsize=7)
        if ax is ax_config:
            ax.set_xlabel("Chaves alteradas por commit CONFIG")
            ax.set_xscale("symlog", linthresh=1)
            ax.legend(fontsize=7)
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(directory / f"{name}.png", dpi=config.analysis.figure_dpi)
        plt.close(fig)
    (directory / "relatorio_preliminar.md").write_text(
        "# Relatório descritivo preliminar\n\n"
        "Protocolo 2.1.0. Tabelas por caso, meses UTC e figuras 300 dpi.\n"
        "Runs e fontes constam no índice imutável.\n"
        "Revisão humana e integração interpretativa pendentes.\n"
        "Chaves CONFIG não equivalem a hiperparâmetros; AST não é execução.\n"
        "Consultar metricas_consolidadas.csv para status, denominadores e perguntas sem fonte.\n"
        "Não há p-valores, causalidade ou representatividade estatística presumida.\n",
        encoding="utf-8",
    )


def qualitative_tables(
    index: dict[str, Any],
    inputs: dict[str, dict[str, Path]],
    directory: Path,
    config: ResearchConfig,
    maps: dict[str, Any],
    case_records: list[dict[str, Any]],
) -> None:
    candidates, selected, coverage = [], [], []
    for case in index["cases"]:
        repository = case["repository_id"]
        files = inputs[repository]
        commits = pd.read_parquet(files["commits.parquet"]).to_dict("records")
        changes = pd.read_parquet(files["changes.parquet"]).to_dict("records")
        pool, chosen, report = select_events(
            commits,
            changes,
            repository,
            case.get("integration_paths", []),
            config.analysis,
            maps.get(repository),
            next(
                (
                    r.get("integration_component")
                    for r in case_records
                    if r["repository_id"] == repository
                ),
                None,
            ),
        )
        candidates.extend(pool)
        selected.extend(chosen)
        coverage.append(report)
    for name, rows in (("eventos_candidatos", candidates), ("eventos_selecionados", selected)):
        write_csv(
            directory / f"{name}.csv",
            rows,
            list(rows[0]) if rows else ["repository_id", "event_id"],
        )
    write_json(
        directory / "cobertura_qualitativa.json",
        {"cases": coverage, "plan": config.analysis.model_dump(mode="json")},
    )
    coding = [
        {
            "repository_id": r["repository_id"],
            "event_id": r["event_id"],
            "commit_shas": r["commit_shas"],
            **dict.fromkeys(
                (
                    "themes",
                    "evidence",
                    "interpretation",
                    "justification",
                    "ambiguity",
                    "metric_id",
                    "quantitative_pattern",
                    "contrary_evidence",
                    "conclusion_limit",
                    "reviewer",
                    "reviewed_at_utc",
                ),
                "",
            ),
        }
        for r in selected
    ]
    write_csv(
        directory / "codificacao_qualitativa.csv",
        coding,
        list(coding[0]) if coding else ["repository_id", "event_id"],
    )


def write_results_packet(
    root: Path,
    directory: Path,
    sources: list[dict[str, str]],
    metrics: list[dict[str, Any]],
    coding: list[dict[str, str]],
    academic: dict[str, Any],
    config: ResearchConfig,
) -> None:
    """Assemble accepted evidence and a manuscript draft, without cloning/training."""
    lines = [
        "# Resultados e Discussão — rascunho derivado",
        "",
        "Objetivo operacional: " + academic["operational_objective"],
        "",
        "## Resultados",
        "",
        "| Caso | Métrica | Numerador | Denominador | Valor | Status |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in metrics:
        lines.append(
            "| "
            + " | ".join(
                str(row[k])
                for k in (
                    "repository_id",
                    "metric_id",
                    "numerator",
                    "denominator",
                    "value",
                    "status",
                )
            )
            + " |"
        )
    lines += ["", "## Discussão integrada", ""]
    for row in coding:
        lines += [
            f"### {row['repository_id']} — {row['event_id']}",
            "",
            row["quantitative_pattern"],
            "",
            row["interpretation"],
            "",
            "Evidência: " + row["evidence"],
            "",
            "Evidência contrária: " + row["contrary_evidence"],
            "",
            "Limite: " + row["conclusion_limit"],
            "",
        ]
    lines += [
        "## Limitações e perguntas pendentes",
        "",
        "A seleção é intencional; commits são dependentes. AST não mede execução.",
        "Chaves de configuração incluem mapas de classes e definições de datasets.",
        "Fontes públicas não certificam práticas das organizações usuárias.",
        "Perguntas não respondidas: " + str(academic["unanswered_questions"]),
        "",
        "## Conclusão",
        "",
        "Este rascunho reúne medidas validadas e interpretações documentais assinadas.",
        "A conclusão autoral deve responder ao objetivo operacional respeitando esses limites.",
        "Não é uma declaração de revisão ou aprovação da redação pela orientadora.",
    ]
    (directory / "resultados_discussao.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    files: set[Path] = set()
    pending = list(sources)
    visited = set()
    while pending:
        source = pending.pop()
        if source["run_id"] in visited:
            continue
        visited.add(source["run_id"])
        _, artifacts, execution = verified_run(
            root, source["run_id"], expected_hash=source["manifest_sha256"]
        )
        files.update(artifacts.values())
        files.add(root / config.paths.manifests / f"{source['run_id']}.json")
        pending.extend(execution["sources"])
        if "source_audit.json" in artifacts:
            audit = json.loads(artifacts["source_audit.json"].read_text())
            for historical in audit.get("sources", []):
                manifest_path = root / config.paths.manifests / f"{historical['run_id']}.json"
                if sha256_file(manifest_path) != historical["manifest_sha256"]:
                    raise ValueError("Historical collection manifest changed")
                files.add(manifest_path)
                for artifact in json.loads(manifest_path.read_text())["artifacts"]:
                    if Path(artifact["path"]).name in {
                        "config.yaml",
                        "file_taxonomy.yaml",
                        "requirements.txt",
                    }:
                        continue  # Original instrument is recoverable from its Git code_commit_sha.
                    files.add(portable_path(root, artifact["path"]))
    files.update(p for p in directory.iterdir() if p.is_file())
    files.update(
        p for folder in ("config", "docs") for p in (root / folder).rglob("*") if p.is_file()
    )
    with zipfile.ZipFile(
        directory / "reproduction.zip", "x", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        entries = []
        for path in sorted(files):
            relative = path.relative_to(root).as_posix()
            archive.write(path, relative)
            entries.append({"path": relative, "sha256": sha256_file(path)})
        archive.writestr(
            "PACKAGE_MANIFEST.json",
            json.dumps({"files": entries, "protocol_version": config.protocol.version}, indent=2),
        )
        archive.writestr(
            "REPRODUCTION.md",
            "Instrumento e fontes por run preservados. Clones externos não incluídos.\n"
            "Os Parquets não contêm nomes/emails dos autores. Veja docs/PLANO_ANALISE.md.\n"
            "A redação é rascunho para revisão autoral, não aprovação acadêmica da redação.\n",
        )


def verify_case_measurements(
    root: Path,
    index: dict[str, Any],
    inputs: dict[str, dict[str, Path]],
    reviews: list[dict[str, Any]],
) -> bool:
    """Human approval cannot replace measured maturity or the original collection."""
    if not reviews:
        return False
    sample = yaml.safe_load((root / "config/amostra_final.yaml").read_text())
    audit_collection(root, sample)
    shortlist_path = (
        root / "data/interim/runs" / sample["source_runs"]["phase2_screen_sample"] / "shortlist.csv"
    )
    shortlist = {r["repository_id"]: r for r in read_csv(shortlist_path)}
    selected = {c["repository_id"]: c for c in index["cases"]}
    for review in reviews:
        repository = review.get("repository_id")
        if not isinstance(repository, str) or repository not in selected:
            return False
        summary = json.loads(inputs[repository]["mining_summary.json"].read_text())
        observed = shortlist[repository]
        for key, expected in (
            ("reachable_commit_count", summary["reachable_commits"]),
            ("active_identity_count", summary["active_contributors_count"]),
            ("stars_at_collection", int(observed["stars_count"])),
            ("collection_timestamp", observed["observed_at_utc"]),
            ("active_after", summary["active_after"]),
        ):
            if review.get(key) != expected:
                return False
        if review.get("evidence_type") not in {"structural", "direct"} or not review.get(
            "evidence_url", ""
        ).startswith(
            f"https://github.com/{repository}/blob/{selected[repository]['head_commit_sha']}/"
        ):
            return False
    return True


def acceptance(
    index: dict[str, Any],
    receipt: dict[str, Any],
    case_reviews: list[dict[str, Any]],
    academic: dict[str, Any],
    coding: list[dict[str, str]],
    original_coding: list[dict[str, str]],
    config: ResearchConfig,
    *,
    chain_eligible: bool,
    metrics_valid: bool,
    qualitative_valid: bool,
    case_measurements_valid: bool = False,
    unanswered_metric_ids: set[str] | None = None,
) -> dict[str, Any]:
    case_set = {(c["repository_id"], c["head_commit_sha"]) for c in index["cases"]}
    reasons = []
    sample_ok = (
        case_measurements_valid
        and config.selection.final_sample_min <= len(case_set) <= config.selection.final_sample_max
        and len(case_reviews) == len(case_set)
        and {(r.get("repository_id"), r.get("head_commit_sha")) for r in case_reviews} == case_set
    )
    for row in case_reviews:
        sample_ok = sample_ok and (
            row.get("decision") == "accepted"
            and bool(row.get("reviewer", "").strip())
            and valid_utc(row.get("reviewed_at_utc", ""))
            and row.get("integration_evidence_status")
            in {"functional_integration_observed", "execution_publicly_verified"}
            and all(
                row.get(k)
                for k in (
                    "integration_entrypoint",
                    "integration_component",
                    "operation",
                    "evidence_url",
                    "evidence_scope",
                    "decision_reason",
                )
            )
            and row.get("evidence_sha") == row.get("head_commit_sha")
            and row.get("reachable_commit_count", 0) >= config.selection.min_commits
            and row.get("active_identity_count", 0) >= config.selection.min_contributors
            and row.get("stars_at_collection", 0) >= config.selection.min_stars
        )
    receipt_ok = (
        receipt.get("accepted") is True
        and bool(index.get("taxonomy_version"))
        and receipt.get("taxonomy_version") == index.get("taxonomy_version")
        and receipt.get("input_hashes", {}).get("inventory") == index["inventory_sha256"]
        and receipt.get("input_hashes", {}).get("original") == index["sample_sha256"]
        and {(c["repository_id"], c["head_commit_sha"]) for c in receipt.get("cases", [])}
        == case_set
    )
    academic_ok = (
        academic.get("status") == "accepted"
        and all(
            academic.get(k)
            for k in ("reviewer", "evidence", "operational_objective", "unanswered_questions")
        )
        and valid_utc(academic.get("reviewed_at_utc", ""))
        and academic.get("mlflow_scope_resolved") is True
        and academic.get("metric_mapping_resolved") is True
        and (unanswered_metric_ids or set()) <= set(academic.get("unanswered_questions", []))
    )

    def identity(row: dict[str, str]) -> tuple[str | None, ...]:
        return (row.get("repository_id"), row.get("event_id"), row.get("commit_shas"))

    coding_ok = (
        bool(coding)
        and [identity(r) for r in coding] == [identity(r) for r in original_coding]
        and all(
            all(
                r.get(k, "").strip()
                for k in (
                    "themes",
                    "evidence",
                    "interpretation",
                    "justification",
                    "ambiguity",
                    "metric_id",
                    "quantitative_pattern",
                    "contrary_evidence",
                    "conclusion_limit",
                    "reviewer",
                )
            )
            and valid_utc(r.get("reviewed_at_utc", ""))
            for r in coding
        )
    )
    for flag, reason in (
        (chain_eligible, "development_or_invalid_source_chain"),
        (sample_ok, "case_selection_pending_or_ineligible"),
        (receipt_ok, "taxonomy_receipt_incompatible_or_unaccepted"),
        (academic_ok, "academic_alignment_pending"),
        (metrics_valid, "metric_error_or_missing_scope"),
        (coding_ok and qualitative_valid, "qualitative_review_or_selection_pending"),
    ):
        if not flag:
            reasons.append(reason)
    return {
        "scientific_result_accepted": not reasons,
        "blocking_reasons": reasons,
        "processing_status": "SUCCESS",
        "sample_status": "accepted" if sample_ok else "pending",
        "measurement_validation_status": "accepted" if receipt_ok and metrics_valid else "pending",
        "academic_alignment_status": "accepted" if academic_ok else "pending",
        "qualitative_status": "accepted" if coding_ok and qualitative_valid else "pending",
    }


def run_study(stage: StageName, argv: list[str] | None = None, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--study-index", type=Path, required=stage != "study_index")
    parser.add_argument("--runs-file", type=Path, required=stage == "study_index")
    parser.add_argument("--sample", type=Path, required=stage == "phase6_validate_taxonomy")
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--pr-map", type=Path)
    parser.add_argument("--validation-run-id")
    parser.add_argument("--qualitative-run-id")
    parser.add_argument("--report-run-id")
    parser.add_argument("--case-review", type=Path)
    parser.add_argument("--academic-review", type=Path)
    parser.add_argument("--qualitative-review", type=Path)
    args = parser.parse_args(argv)
    root = (root or Path(__file__).resolve().parents[2]).resolve()
    config = load_config(root / "config/config.yaml")
    context = start_run(project_root=root, stage=stage)
    directory = run_directory(root / config.paths.interim, context.run_id)
    directory.mkdir(parents=True, exist_ok=False)
    sources: list[dict[str, str]] = []
    status: Any = "SUCCESS"
    error = None
    accepted = True
    scientific = not context.dirty_worktree
    try:
        if context.dirty_worktree and not args.allow_dirty:
            raise ValueError(
                "Scientific run requires clean worktree; use --allow-dirty for development"
            )
        snapshot_source(root, directory / "source_snapshot.tar.gz")
        # Preserve every external review/map/specification as an input artifact.
        for name in (
            "runs_file",
            "sample",
            "pr_map",
            "case_review",
            "academic_review",
            "qualitative_review",
        ):
            path = getattr(args, name)
            if path:
                copied = directory / f"input_{name}{path.suffix}"
                shutil.copyfile(path, copied)
                setattr(args, name, copied)
        if stage == "study_index":
            index = create_index(
                root, yaml.safe_load(args.runs_file.read_text()), directory, config
            )
            sources = index["sources"]
        else:
            index, inputs = load_index(root, args.study_index)
            sources = [reference(root, args.study_index.parent.name, config)]
            if stage == "phase6_validate_taxonomy":
                inventory_path = args.study_index.parent / "taxonomy_inventory.json"
                if args.inventory and args.inventory.resolve() != inventory_path.resolve():
                    raise ValueError("Inventory must belong to study index")
                receipt = evaluate_review(
                    args.sample,
                    config,
                    original=args.study_index.parent / "amostra_validacao_taxonomia.csv",
                    inventory_path=inventory_path,
                )
                receipt["study_index_sha256"] = sha256_file(args.study_index)
                write_json(directory / "taxonomy_validation.json", receipt)
                write_csv(
                    directory / "confusion_matrix.csv",
                    receipt["confusion_matrix"],
                    ["expected_category", "predicted_category", "count"],
                )
                write_csv(directory / "category_coverage.csv", receipt["coverage"])
                write_csv(directory / "case_agreement.csv", receipt["by_case"])
                accepted = receipt["accepted"]
            elif stage == "phase7_select_qualitative":
                maps = json.loads(args.pr_map.read_text()) if args.pr_map else {}
                qualitative_tables(
                    index,
                    inputs,
                    directory,
                    config,
                    maps,
                    json.loads((args.study_index.parent / "case_review_template.json").read_text()),
                )
            elif stage == "phase8_report":
                report_tables(root, index, inputs, directory, config)
            elif stage == "phase9_finalize_study":
                receipt, coding, original_coding, case_reviews, academic = {}, [], [], [], {}
                metrics: list[dict[str, Any]] = []
                if args.validation_run_id:
                    _, files, execution = verified_run(
                        root, args.validation_run_id, "phase6_validate_taxonomy"
                    )
                    sources.append(reference(root, args.validation_run_id, config))
                    if execution["sources"][0] != sources[0]:
                        raise ValueError("Validation uses a different study index")
                    receipt = json.loads(files["taxonomy_validation.json"].read_text())
                    reevaluated = evaluate_review(
                        files["input_sample.csv"],
                        config,
                        original=args.study_index.parent / "amostra_validacao_taxonomia.csv",
                        inventory_path=args.study_index.parent / "taxonomy_inventory.json",
                    )
                    if any(receipt[key] != value for key, value in reevaluated.items()):
                        raise ValueError("Validation receipt differs from human labels")
                qualitative_valid = False
                if args.qualitative_run_id:
                    _, files, execution = verified_run(
                        root, args.qualitative_run_id, "phase7_select_qualitative"
                    )
                    sources.append(reference(root, args.qualitative_run_id, config))
                    if execution["sources"][0] != sources[0]:
                        raise ValueError("Qualitative selection uses a different index")
                    original_coding = read_csv(files["codificacao_qualitativa.csv"])
                    coverage = json.loads(files["cobertura_qualitativa.json"].read_text())
                    qualitative_valid = all(
                        c["pr_map_complete"]
                        and not c["pr_errors"]
                        and c["integration_paths"]
                        and c.get("first_integration_event_id")
                        for c in coverage["cases"]
                    )
                metrics_valid = False
                if args.report_run_id:
                    _, files, execution = verified_run(root, args.report_run_id, "phase8_report")
                    sources.append(reference(root, args.report_run_id, config))
                    if execution["sources"][0] != sources[0]:
                        raise ValueError("Report uses a different index")
                    metrics = read_csv(files["metricas_consolidadas.csv"])
                    metrics_valid = all(
                        r["status"] != "error"
                        and r["evidence_scope"]
                        and (
                            r["status"] not in {"not_available", "not_applicable"}
                            or r["availability_reason"]
                        )
                        for r in metrics
                    )
                    write_csv(
                        directory / "metricas_consolidadas.csv",
                        [
                            {**r, "validation_receipt_run_id": args.validation_run_id or ""}
                            for r in metrics
                        ],
                    )
                if args.case_review:
                    case_reviews = json.loads(args.case_review.read_text())
                case_measurements_valid = verify_case_measurements(
                    root, index, inputs, case_reviews
                )
                if args.academic_review:
                    academic = json.loads(args.academic_review.read_text())
                if args.qualitative_review:
                    coding = read_csv(args.qualitative_review)
                metric_identities = {(r["repository_id"], r["metric_id"]) for r in metrics}
                qualitative_valid = qualitative_valid and all(
                    (row["repository_id"], row["metric_id"]) in metric_identities for row in coding
                )
                chain_eligible = not context.dirty_worktree
                for source in sources:
                    try:
                        verified_run(
                            root,
                            source["run_id"],
                            expected_hash=source["manifest_sha256"],
                            scientific=True,
                        )
                    except ValueError:
                        chain_eligible = False
                result = acceptance(
                    index,
                    receipt,
                    case_reviews,
                    academic,
                    coding,
                    original_coding,
                    config,
                    chain_eligible=chain_eligible,
                    metrics_valid=metrics_valid,
                    qualitative_valid=qualitative_valid,
                    case_measurements_valid=case_measurements_valid,
                    unanswered_metric_ids={
                        r["metric_id"] for r in metrics if r["status"] == "not_available"
                    },
                )
                result["sources"] = sources
                result["study_index_sha256"] = sha256_file(args.study_index)
                write_json(directory / "study_acceptance.json", result)
                accepted = result["scientific_result_accepted"]
                write_csv(
                    directory / "metricas_consolidadas.csv",
                    [
                        {
                            **row,
                            "validation_receipt_run_id": args.validation_run_id or "",
                            "validation_status": "scientifically_validated"
                            if accepted
                            else "pending",
                            "scientific_result_accepted": accepted,
                        }
                        for row in metrics
                    ],
                    list(metrics[0]) + ["validation_receipt_run_id", "scientific_result_accepted"]
                    if metrics
                    else ["metric_id", "validation_status", "scientific_result_accepted"],
                )
                if accepted:
                    write_csv(directory / "integracao_resultados.csv", coding)
                    write_results_packet(
                        root, directory, sources, metrics, coding, academic, config
                    )
            else:
                raise ValueError("Unsupported study stage")
        for source in sources:
            _, _, execution = verified_run(
                root, source["run_id"], expected_hash=source["manifest_sha256"]
            )
            scientific = scientific and execution["scientific_eligible"]
    except Exception as exception:
        status, error, accepted = "FAILED", f"{type(exception).__name__}: {exception}", False
        if stage == "phase9_finalize_study":
            write_json(
                directory / "study_acceptance.json",
                {
                    "scientific_result_accepted": False,
                    "processing_status": "FAILED",
                    "sample_status": "pending",
                    "measurement_validation_status": "pending",
                    "academic_alignment_status": "pending",
                    "blocking_reasons": [error],
                },
            )
    write_json(
        directory / "execution.json",
        {
            "run_id": context.run_id,
            "status": status,
            "contract_version": "2.1.0",
            "sources": sources,
            "scientific_eligible": scientific,
            "scientific_result_accepted": accepted if stage == "phase9_finalize_study" else False,
            "artifact_names": {p.stem: p.name for p in directory.iterdir() if p.is_file()},
            "error": error,
        },
    )
    write_manifest(
        context=context,
        manifest_directory=root / config.paths.manifests,
        config_path=root / "config/config.yaml",
        taxonomy_path=root / "config/file_taxonomy.yaml",
        requirements_path=root / "requirements.txt",
        protocol_id=config.protocol.id,
        protocol_version=config.protocol.version,
        status=status,
        error=error,
        artifacts=[
            build_artifact(p).model_copy(update={"path": p.relative_to(root).as_posix()})
            for p in sorted(directory.iterdir())
            if p.is_file()
        ],
    )
    print(f"{status}: {directory}")
    if error:
        print(error)
    elif not accepted:
        print("Processing complete; scientific acceptance blocked. See receipt.")
    return 0 if accepted else 1
