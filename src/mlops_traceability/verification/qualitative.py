"""Bind the reference selection to registered runs and the freshly checked Git rows."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from mlops_traceability.manifest import sha256_file
from mlops_traceability.run_storage import portable_path, verified_run
from mlops_traceability.verification.git_oracle import reconcile_rows
from mlops_traceability.verification.pr_sources import reconstruct_associations
from mlops_traceability.verification.selection import select_reference
from mlops_traceability.verification.tables import read_table


def compare_selection(
    expected: list[dict[str, Any]], measured: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    identity = ("repository_id", "event_id")
    differences = reconcile_rows(
        expected, measured, identity, tuple(expected[0]) if expected else ()
    )
    if [(r["repository_id"], r["event_id"]) for r in expected] != [
        (r["repository_id"], r["event_id"]) for r in measured
    ]:
        differences.append(dict(field="event_order"))
    return differences


def declared_components(
    rows: list[dict[str, Any]], repositories: set[str]
) -> dict[str, str | None]:
    declarations = {row["repository_id"]: row.get("integration_component") for row in rows}
    if len(declarations) != len(rows) or set(declarations) != repositories:
        raise ValueError("Case template must contain exactly the study repositories")
    return declarations


def verify_qualitative(
    root: Path,
    index_path: Path,
    origins: dict[str, Any],
    output: Path,
    plan: dict[str, Any],
    *,
    scientific: bool,
) -> tuple[dict[str, Any], list[Path]]:
    index = json.loads(index_path.read_text())
    run_id = origins["qualitative_run_id"]
    manifest, files, execution = verified_run(
        root, run_id, "phase7_select_qualitative", scientific=scientific
    )
    reference = dict(
        run_id=index_path.parent.name,
        manifest_sha256=sha256_file(
            root / "data/processed/manifests" / f"{index_path.parent.name}.json"
        ),
    )
    if execution["sources"] != [reference]:
        raise ValueError("Qualitative source uses another index")
    collection = portable_path(root, origins["pr_collection"])
    source = {
        case["repository_id"]: json.loads(
            (output / case["repository_id"].replace("/", "__") / "source_commits.json").read_text()
        )
        for case in index["cases"]
    }
    eligible = {
        repo: {r["commit_sha"] for r in rows if r["eligibility_status"] == "included"}
        for repo, rows in source.items()
    }
    associations, pr_check, bound = reconstruct_associations(
        collection, index_path, files["input_pr_map.json"], eligible
    )
    bound += [root / "data/processed/manifests" / f"{manifest['run_id']}.json", *files.values()]
    candidates, selected, coverage = [], [], []
    components = declared_components(
        json.loads((index_path.parent / "case_review_template.json").read_text()), set(source)
    )
    for case in index["cases"]:
        repo = case["repository_id"]
        changes = json.loads((output / repo.replace("/", "__") / "source_changes.json").read_text())
        result = select_reference(
            source[repo],
            changes,
            repo,
            associations[repo],
            case["integration_paths"],
            components[repo],
            plan,
        )
        candidates.extend(result["candidates"])
        selected.extend(result["selected"])
        coverage.append(result["coverage"])
    differences = list(pr_check["differences"])
    for expected, name in (
        (candidates, "eventos_candidatos.csv"),
        (selected, "eventos_selecionados.csv"),
    ):
        differences.extend(
            {"table": name, **issue}
            for issue in compare_selection(expected, read_table(files[name]))
        )
    actual_coverage = json.loads(files["cobertura_qualitativa.json"].read_text())
    actual_plan = actual_coverage["plan"]
    if datetime.fromisoformat(actual_plan["planned_at_utc"]) != datetime.fromisoformat(
        plan["planned_at_utc"]
    ) or json.dumps(
        {k: v for k, v in actual_plan.items() if k != "planned_at_utc"}, sort_keys=True
    ) != json.dumps({k: v for k, v in plan.items() if k != "planned_at_utc"}, sort_keys=True):
        differences.append(dict(field="analysis_plan"))
    if json.dumps(coverage, sort_keys=True) != json.dumps(actual_coverage["cases"], sort_keys=True):
        differences.append(
            dict(field="coverage", expected=coverage, observed=actual_coverage["cases"])
        )
    identities = [
        {k: row[k] for k in ("repository_id", "event_id", "commit_shas")} for row in selected
    ]
    differences.extend(
        {"table": "codificacao_qualitativa.csv", **issue}
        for issue in compare_selection(identities, read_table(files["codificacao_qualitativa.csv"]))
    )
    directory = output / "qualitative"
    directory.mkdir(exist_ok=False)
    result = dict(
        differences=differences,
        pr_sources=pr_check,
        candidate_count=len(candidates),
        selected_count=len(selected),
        coverage=coverage,
        dependencies="Git rows, recorded GraphQL JSON, integration paths and analysis plan",
        limitations=[
            "No production selection or PR interpreter is called by the reference implementation.",
            "Hashes bind recorded observations, without authenticating GitHub or human authorship.",
            "Integration meaning and qualitative interpretations remain G11/G12 human evidence.",
        ],
    )
    for name, value in (
        ("associations.json", associations),
        ("candidates.json", candidates),
        ("selected.json", selected),
        ("crosscheck.json", result),
    ):
        with (directory / name).open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
    return result, bound
