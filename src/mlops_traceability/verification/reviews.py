"""Import human decisions byte-for-byte, keeping omissions and identity conflicts explicit."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from mlops_traceability.config import ResearchConfig, load_config
from mlops_traceability.manifest import sha256_file
from mlops_traceability.run_storage import portable_path, verified_run
from mlops_traceability.study import load_index
from mlops_traceability.validation.taxonomy_review import evaluate_review, read_csv, valid_utc
from mlops_traceability.verification.oracles import taxonomy_tally

REVIEW_FILES = (
    "taxonomia_revisada.csv",
    "casos_revisados.json",
    "codificacao_revisada.csv",
    "alinhamento_academico.json",
)
CODING_FIELDS = (
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
)


def review_codebook(policy: dict[str, Any], directory: Path) -> dict[str, str]:
    """Add explicitly defined, dated emergent themes without rewriting the policy."""
    result: dict[str, str] = dict(policy["codebook"])
    path = directory / "temas_emergentes.json"
    if path.exists():
        for entry in json.loads(path.read_text()):
            name = entry["theme_id"]
            if (
                not isinstance(name, str)
                or not name.strip()
                or ";" in name
                or name in result
                or not entry.get("definition", "").strip()
                or not entry.get("reviewer", "").strip()
                or not valid_utc(entry.get("registered_at_utc", ""))
            ):
                raise ValueError(
                    "Emergent theme requires a unique name, definition and dated review"
                )
            result[name] = entry["definition"]
    return result


def record_issues(rows: list[dict[str, Any]], fields: tuple[str, ...], kind: str) -> list[str]:
    problems = []
    for position, row in enumerate(rows, 1):
        identity = row.get("unit_id", row.get("event_id", row.get("repository_id", position)))
        for field in fields:
            value = row.get(field)
            if not value or (isinstance(value, str) and not value.strip()):
                problems.append(f"{kind}:{identity}:missing:{field}")
        if not valid_utc(row.get("reviewed_at_utc", "")):
            problems.append(f"{kind}:{identity}:invalid_utc")
    return problems


def validate_decisions(
    index: dict[str, Any],
    cases: list[dict[str, Any]],
    case_original: list[dict[str, Any]],
    coding: list[dict[str, Any]],
    coding_original: list[dict[str, Any]],
    academic: dict[str, Any],
    codebook: dict[str, str],
) -> list[str]:
    problems = []
    case_set = {(c["repository_id"], c["head_commit_sha"]) for c in index["cases"]}
    if (
        len(cases) != len(case_set)
        or {(r.get("repository_id"), r.get("head_commit_sha")) for r in cases} != case_set
    ):
        problems.append("cases:identity_mismatch")
    originals = {r["repository_id"]: r for r in case_original}
    for row in cases:
        source = originals.get(row.get("repository_id", ""), {})
        for field in (
            "repository_id",
            "head_commit_sha",
            "source_run_ids",
            "protocol_version",
            "reachable_commit_count",
            "active_identity_count",
            "stars_at_collection",
            "collection_timestamp",
            "active_after",
        ):
            if field not in row or row[field] != source.get(field):
                problems.append(f"cases:{row.get('repository_id')}:immutable:{field}")
        if row.get("decision") not in {"accepted", "rejected"}:
            problems.append(f"cases:{row.get('repository_id')}:invalid_decision")
    problems += record_issues(
        cases,
        (
            "decision",
            "decision_reason",
            "reviewer",
            "evidence_url",
            "evidence_scope",
        ),
        "cases",
    )

    def immutable(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{k: v for k, v in row.items() if k not in CODING_FIELDS} for row in rows]

    if not coding or immutable(coding) != immutable(coding_original):
        problems.append("coding:identity_or_immutable_mismatch")
    identities = [(r.get("repository_id"), r.get("event_id")) for r in coding]
    if len(set(identities)) != len(identities):
        problems.append("coding:duplicate_event")
    problems += record_issues(coding, CODING_FIELDS, "coding")
    for row in coding:
        themes = str(row.get("themes", "")).split(";")
        for theme in (t.strip() for t in themes if t.strip()):
            if not codebook.get(theme, "").strip():
                problems.append(f"coding:{row.get('event_id')}:undefined_theme:{theme}")
    problems += record_issues(
        [academic],
        (
            "reviewer",
            "evidence",
            "operational_objective",
            "unanswered_questions",
        ),
        "academic",
    )
    if academic.get("status") != "accepted" or any(
        academic.get(field) is not True
        for field in ("mlflow_scope_resolved", "metric_mapping_resolved")
    ):
        problems.append("academic:alignment_not_recorded")
    return sorted(set(problems))


def evaluate_import(
    root: Path,
    index_path: Path,
    directory: Path,
    config: ResearchConfig,
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Resolve registered originals, not paths supplied without manifest verification."""
    index, _ = load_index(root, index_path)
    origins = json.loads((directory / "origens.json").read_text())
    if origins["study_index_sha256"] != sha256_file(index_path):
        raise ValueError("Review belongs to another study index")
    _, index_files, _ = verified_run(root, index_path.parent.name, "study_index")
    _, qualitative_files, execution = verified_run(
        root, origins["qualitative_run_id"], "phase7_select_qualitative"
    )
    expected_ref = {
        "run_id": index_path.parent.name,
        "manifest_sha256": sha256_file(
            root / config.paths.manifests / f"{index_path.parent.name}.json"
        ),
    }
    if expected_ref not in execution.get("sources", []):
        raise ValueError("Qualitative source belongs to another study index")
    originals = {
        "taxonomia_revisada.csv": index_files["amostra_validacao_taxonomia.csv"],
        "casos_revisados.json": index_files["case_review_template.json"],
        "alinhamento_academico.json": index_files["academic_review_template.json"],
        "codificacao_revisada.csv": qualitative_files["codificacao_qualitativa.csv"],
    }
    original_hashes = {}
    for name, path in originals.items():
        declared = origins["originals"][name]
        if portable_path(root, declared["path"]) != path or declared["sha256"] != sha256_file(path):
            raise ValueError(f"Review original mismatch: {name}")
        original_hashes[str(path.relative_to(root))] = sha256_file(path)
    inventory = index_files["taxonomy_inventory.json"]
    if sha256_file(inventory) != index["inventory_sha256"] or (
        sha256_file(originals["taxonomia_revisada.csv"]) != index["sample_sha256"]
    ):
        raise ValueError("Inventory/sample index binding mismatch")
    taxonomy = evaluate_review(
        directory / "taxonomia_revisada.csv",
        config,
        original=originals["taxonomia_revisada.csv"],
        inventory_path=inventory,
    )
    rows = read_csv(directory / "taxonomia_revisada.csv")
    problems = [f"taxonomy:{reason}" for reason in taxonomy["blocking_reasons"]]
    problems += record_issues(
        rows,
        (
            "expected_category",
            "reviewer",
            "justification",
        ),
        "taxonomy",
    )
    cases = json.loads((directory / "casos_revisados.json").read_text())
    coding = read_csv(directory / "codificacao_revisada.csv")
    academic = json.loads((directory / "alinhamento_academico.json").read_text())
    problems += validate_decisions(
        index,
        cases,
        json.loads(originals["casos_revisados.json"].read_text()),
        coding,
        read_csv(originals["codificacao_revisada.csv"]),
        academic,
        review_codebook(policy, directory),
    )
    # Second tally uses raw labels only. It is withheld when any taxonomy record is invalid.
    crosscheck = None
    if rows and not (set(taxonomy["blocking_reasons"]) - {"agreement_below_threshold"}):
        crosscheck = taxonomy_tally(rows)
        if crosscheck["confusion_matrix"] != taxonomy["confusion_matrix"]:
            problems.append("taxonomy:independent_matrix_mismatch")
    return {
        "blocking_reasons": sorted(set(problems)),
        "taxonomy": taxonomy,
        "independent_label_tally": crosscheck,
        "record_counts": {"taxonomy": len(rows), "cases": len(cases), "coding": len(coding)},
        "original_file_hashes": {
            **original_hashes,
            str(inventory.relative_to(root)): sha256_file(inventory),
        },
        "input_manifest_hashes": {
            name: sha256_file(root / config.paths.manifests / f"{name}.json")
            for name in [index_path.parent.name, origins["qualitative_run_id"]]
        },
        "academic_approval_authentication": "not_assessed",
        "evidence_relevance_and_resolution": "NOT_RUN",
    }


def check_import_bindings(
    receipt_path: Path, root: Path, index_path: Path, review_dir: Path
) -> None:
    """Reject changed originals, policies, reviews, or archive; this alone is not acceptance."""
    receipt = json.loads(receipt_path.read_text())
    if receipt["study_index_sha256"] != sha256_file(index_path):
        raise ValueError("Study index hash mismatch")
    for name, digest in receipt["review_file_hashes"].items():
        if sha256_file(review_dir / name) != digest or (
            sha256_file(receipt_path.parent / "original_reviews" / name) != digest
        ):
            raise ValueError(f"Review hash mismatch: {name}")
    for name, digest in receipt["bound_file_hashes"].items():
        if sha256_file(portable_path(root, name)) != digest:
            raise ValueError(f"Bound source hash mismatch: {name}")
    if (
        sha256_file(receipt_path.parent / "verification_source.tar.gz")
        != receipt["source_archive_sha256"]
    ):
        raise ValueError("Verification source archive mismatch")


def import_reviews(
    root: Path,
    index_path: Path,
    review_dir: Path,
    output: Path,
    *,
    scope: str = "empirical",
) -> int:
    """Write once; report missing/incompatible inputs with exit 2, invalid decisions with 1."""
    if scope not in {"synthetic", "empirical"}:
        raise ValueError("Invalid scope")
    root, index_path, review_dir = root.resolve(), index_path.resolve(), review_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    preserved = output / "original_reviews"
    preserved.mkdir()
    receipt: dict[str, Any] = {
        "review_import_schema_version": "1.0.0",
        "scope": scope,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "scientific_result_accepted": False,
        "review_import_status": "FAIL",
        "review_file_hashes": {},
        "bound_file_hashes": {},
        "transformations": [],
        "blocking_reasons": [],
        "limitations": [
            "Record validation does not authenticate reviewers or academic approval.",
            "G00-G15 verification, evidence relevance and restoration remain separate gates.",
            "No judgments, dates or labels are inferred; no normalization was performed.",
        ],
    }
    code = 2
    try:
        # Preserve every available input before validating any of them, including refusals.
        for name in (*REVIEW_FILES, "origens.json", "temas_emergentes.json"):
            source = review_dir / name
            if source.is_file():
                shutil.copyfile(source, preserved / name)
                receipt["review_file_hashes"][name] = sha256_file(preserved / name)
            elif name != "temas_emergentes.json":
                receipt["blocking_reasons"].append(f"missing_input:{name}")
        receipt["verification_code_sha"] = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            text=True,
        ).strip()
        receipt["dirty_worktree"] = bool(
            subprocess.check_output(
                ["git", "-C", str(root), "status", "--porcelain"],
                text=True,
            ).strip()
        )
        paths = {
            p
            for base in ("src", "scripts", "tests", "config")
            for p in (root / base).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        }
        paths.update(
            root / p
            for p in (
                "Makefile",
                "pyproject.toml",
                "requirements.txt",
                "requirements-dev.txt",
                "docs/DECISOES_METODOLOGICAS.md",
            )
            if (root / p).is_file()
        )
        with tarfile.open(output / "verification_source.tar.gz", "w:gz") as archive:
            for path in sorted(paths):
                archive.add(path, arcname=path.relative_to(root), recursive=False)
        receipt["source_archive_sha256"] = sha256_file(output / "verification_source.tar.gz")
        receipt["study_index_sha256"] = sha256_file(index_path)
        policy_path = root / "config/verification.yaml"
        policy = yaml.safe_load(policy_path.read_text())
        receipt["verification_policy_version"] = policy["verification_policy_version"]
        receipt["bound_file_hashes"] = {
            p: sha256_file(root / p)
            for p in (
                "config/verification.yaml",
                "config/config.yaml",
                "config/file_taxonomy.yaml",
                "requirements.txt",
                "docs/DECISOES_METODOLOGICAS.md",
            )
        }
        if not receipt["blocking_reasons"]:
            result = evaluate_import(
                root, index_path, preserved, load_config(root / "config/config.yaml"), policy
            )
            receipt.update(result)
            receipt["bound_file_hashes"].update(result["original_file_hashes"])
            receipt["bound_file_hashes"].update(
                {
                    f"data/processed/manifests/{run}.json": digest
                    for run, digest in result["input_manifest_hashes"].items()
                }
            )
            code = 1 if result["blocking_reasons"] else 0
            receipt["review_import_status"] = "PASS" if code == 0 else "FAIL"
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        yaml.YAMLError,
        subprocess.CalledProcessError,
    ) as error:
        receipt["blocking_reasons"].append(f"incompatible_input:{type(error).__name__}:{error}")
    receipt["exit_code"] = code
    with (output / "review_import.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-index", required=True, type=Path)
    parser.add_argument("--review-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[3]
    try:
        return import_reviews(root, args.study_index, args.review_dir, args.output_dir)
    except OSError as error:
        print(f"Cannot create immutable import: {error}")
        return 2
