"""Execute preservation, claims, fixture, relevance and alignment gates offline."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mlops_traceability.manifest import sha256_file
from mlops_traceability.verification.evidence import Evidence, resolve_evidence
from mlops_traceability.verification.finalization import checked_path
from mlops_traceability.verification.provenance import assess_provenance

# Each entry names executable assertions, including the expected refusal where applicable.
SCENARIOS = {
    "four_commit_arithmetic": (
        "test_oracles",
        "test_known_arithmetic_and_ordering",
        "known answers",
    ),
    "excluded_bot_and_merge": ("test_oracles", "test_git_fixture_with_bot_and_merge", "bot;merge"),
    "zero_config_magnitude": (
        "test_oracles",
        "test_git_fixture_with_bot_and_merge",
        "P true and keys zero",
    ),
    "undefined_denominator": (
        "test_oracles",
        "test_zero_denominator_and_comparison_boundaries",
        "undefined",
    ),
    "unavailable_is_null": (
        "test_oracles",
        "test_arithmetic_mutations",
        "provenance_coverage:value",
    ),
    "duplicate_sha": ("test_oracles", "test_duplicate_sha_mutation", "Duplicate commit SHA"),
    "historical_blob": (
        "test_contracts",
        "test_historical_deletion_and_swapped_blob",
        "Evidence blob SHA mismatch",
    ),
    "review_identity_and_justification": (
        "test_reviews",
        "test_taxonomy_record_mutations",
        "sample_integrity_mismatch;incomplete_human_review",
    ),
    "review_source_hash": (
        "test_reviews",
        "test_review_round_and_hash_mutations",
        "Review original mismatch",
    ),
    "incomplete_criteria": (
        "test_finalization",
        "test_incomplete_claim_cannot_authorize_candidate",
        "incomplete or failed",
    ),
    "wrong_code_denominator": (
        "test_oracles",
        "test_arithmetic_mutations",
        "code_config_cochange:denominator",
    ),
    "omit_zero_magnitude_config": (
        "test_oracles",
        "test_arithmetic_mutations",
        "config_magnitude:denominator",
    ),
    "unavailable_to_zero": (
        "test_oracles",
        "test_arithmetic_mutations",
        "provenance_coverage:value",
    ),
    "duplicate_commit": ("test_oracles", "test_duplicate_sha_mutation", "Duplicate commit SHA"),
    "swap_evidence_blob": (
        "test_contracts",
        "test_historical_deletion_and_swapped_blob",
        "Evidence blob SHA mismatch",
    ),
    "mutate_review_after_import": ("test_reviews", "test_review_round_and_hash_mutations", "hash"),
    "replace_review_round": (
        "test_reviews",
        "test_review_round_and_hash_mutations",
        "another study index",
    ),
    "force_partial_pass": (
        "test_contracts",
        "test_force_partial_pass_does_not_cover_missing_criteria",
        "NOT_RUN",
    ),
    "include_bot_in_eligible_table": (
        "test_source_oracles",
        "test_git_oracle_detects_bot_and_metadata_mutations",
        "eligibility_status",
    ),
    "directory_sha_mislabeled_as_blob": (
        "test_source_oracles",
        "test_directory_to_symlink_does_not_record_tree_as_blob",
        "blob",
    ),
    "missing_source_commit": (
        "test_source_oracles",
        "test_incomplete_clones_are_rejected_without_fetching",
        "Missing",
    ),
    "boolean_flag_replaced_by_integer": (
        "test_source_oracles",
        "test_git_oracle_detects_bot_and_metadata_mutations",
        "C",
    ),
    "incomplete_pr_response_to_absence": (
        "test_selection_oracle",
        "test_incomplete_or_invalid_observation_never_becomes_absence",
        "incomplete_connection",
    ),
    "duplicate_pr_query_commit": (
        "test_selection_oracle",
        "test_recorded_query_rejects_unparsed_fields_and_duplicates",
        "duplicate",
    ),
    "swapped_pr_response_oid": (
        "test_selection_oracle",
        "test_incomplete_or_invalid_observation_never_becomes_absence",
        "missing_or_mismatched_commit",
    ),
    "changed_pr_association": (
        "test_selection_oracle",
        "test_map_forgery_is_detected_even_with_matching_file_hashes",
        "differences",
    ),
    "changed_event_order_or_quota": (
        "test_selection_oracle",
        "test_selection_mutations_have_specific_reasons",
        "event_order;selection_group",
    ),
    "duplicated_selected_event": (
        "test_selection_oracle",
        "test_duplicate_selected_event_is_rejected",
        "Duplicate",
    ),
    "missing_or_duplicate_case_template": (
        "test_selection_oracle",
        "test_missing_or_duplicate_case_template_is_rejected",
        "case",
    ),
}


def fixtures(root: Path, output: Path, policy: dict[str, Any], code_sha: str) -> dict[str, Any]:
    names: list[str] = sum(
        (
            policy[k]
            for k in ("required_scenarios", "initial_counterexamples", "additional_counterexamples")
        ),
        [],
    )
    unknown = set(names) - SCENARIOS.keys()
    if unknown:
        raise ValueError(f"Unmapped required scenarios: {sorted(unknown)}")
    selected = sorted(
        {f"tests/verification/{SCENARIOS[n][0]}.py::{SCENARIOS[n][1]}" for n in names}
    )
    command = [
        sys.executable,
        "-m",
        "pytest",
        *selected,
        "--no-cov",
        "-q",
        f"--junitxml={output / 'fixtures.xml'}",
    ]
    with (output / "fixtures.log").open("x") as stream:
        result = subprocess.run(
            command, cwd=root, stdout=stream, stderr=subprocess.STDOUT, check=False
        )
    tests = list(ET.parse(output / "fixtures.xml").iter("testcase"))
    mapping = []
    differences = []
    for name in names:
        module, function, refusal = SCENARIOS[name]
        matched = [
            t
            for t in tests
            if t.attrib.get("classname", "").endswith(module)
            and t.attrib["name"].split("[")[0] == function
        ]
        valid = bool(matched) and all(
            not any(t.find(k) is not None for k in ("failure", "error", "skipped")) for t in matched
        )
        mapping.append(
            dict(
                scenario=name,
                test=f"{module}.py::{function}",
                expected_assertion=refusal,
                executed=[t.attrib["name"] for t in matched],
                passed=valid,
            )
        )
        if not valid:
            differences.append(f"scenario_not_passed:{name}")
    if result.returncode:
        differences.append(f"pytest_exit:{result.returncode}")
    return dict(code_sha=code_sha, command=command, mapping=mapping, differences=differences)


def catalog_check(data: dict[str, Any], root: Path, bind: Callable[[Path], None]) -> dict[str, Any]:
    """Resolve bytes separately from the recorded content relevance judgment."""
    claims = data["claims"]
    if not claims or len({c["claim_id"] for c in claims}) != len(claims):
        raise ValueError("Empty or duplicate claims")
    resolutions, issues, relevance = [], [], []
    for claim in claims:
        cid = claim["claim_id"]
        for field in (
            "statement",
            "method",
            "result",
            "limitation",
            "allowed_conclusion",
            "relevance",
        ):
            if not claim.get(field):
                issues.append(f"{cid}:missing:{field}")
        if claim.get("status") not in {"sustentada_no_escopo", "contradita", "nao_resolvida"}:
            issues.append(f"{cid}:invalid_status")
        if not claim.get("sources"):
            issues.append(f"{cid}:missing_sources")
        for source in claim.get("sources", []):
            try:
                evidence = Evidence.model_validate(source)
                if evidence.kind != "file":
                    raise ValueError("Closure sources must be preserved files")
                result = resolve_evidence(evidence, root, {})
                bind(checked_path(root, evidence.path))
                resolutions.append(dict(claim_id=cid, **result))
                if Path(evidence.path).name == "metrics.csv":
                    with (root / evidence.path).open() as stream:
                        rows = list(csv.DictReader(stream))
                    matched = [
                        r
                        for r in rows
                        if cid == r["repository_id"].split("/")[-1] + ":" + r["metric_id"]
                    ]
                    if len(matched) != 1 or any(
                        claim["result"].get(k) != matched[0][k]
                        for k in ("value", "numerator", "denominator", "status")
                    ):
                        issues.append(f"{cid}:numeric_result_mismatch")
            except (OSError, ValueError, KeyError) as error:
                issues.append(f"{cid}:source:{error}")
        relevance.append(
            dict(
                claim_id=cid,
                status=claim["status"],
                assessment=claim.get("relevance"),
                allowed_conclusion=claim.get("allowed_conclusion"),
            )
        )
    return dict(
        claim_count=len(claims),
        identity_results=resolutions,
        identity_errors=issues,
        relevance_results=relevance,
    )


def run_closure_checks(
    root: Path,
    index_path: Path,
    reviews: Path,
    output: Path,
    policy: dict[str, Any],
    code_sha: str,
    bind: Callable[[Path], None],
) -> dict[str, tuple[str, list[Any], list[str]]]:
    """Return the runner's existing method/differences/proof contract for each gate."""
    results: dict[str, tuple[str, list[Any], list[str]]] = {}
    directory = output / "closure"
    directory.mkdir()

    def save(key: str, data: dict[str, Any], differences: list[Any], method: str) -> None:
        path = directory / f"{key}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        proofs = [path.relative_to(output).as_posix()]
        if key == "G04":
            proofs += [p.relative_to(output).as_posix() for p in directory.glob("fixtures.*")]
        results[key] = method, differences, proofs

    def load(name: str) -> dict[str, Any]:
        path = checked_path(reviews, name)
        return json.loads(path.read_text())  # type: ignore[no-any-return]

    try:
        inputs = load("closure_inputs.json")
        if inputs["study_index_sha256"] != sha256_file(index_path):
            raise ValueError("Closure index mismatch")
        inv_path = checked_path(root, inputs["inventory_path"])
        if sha256_file(inv_path) != inputs["inventory_sha256"]:
            raise ValueError("Preservation inventory changed")
        bind(inv_path)
        inventory = json.loads(inv_path.read_text())["files"]
        for extra in inputs.get("additional_inventories", []):
            extra_path = checked_path(root, extra["path"])
            if sha256_file(extra_path) != extra["sha256"]:
                raise ValueError("Additional preservation inventory changed")
            bind(extra_path)
            extra_entries = json.loads(extra_path.read_text())["files"]
            inventory += extra_entries
            for entry in extra_entries:
                bind(checked_path(root, entry["path"]))
        errors = []
        if not inventory:
            raise ValueError("Empty preservation inventory")
        for entry in inventory:
            path = checked_path(root, entry["path"])
            if path.stat().st_size != entry["size"] or sha256_file(path) != entry["sha256"]:
                errors.append(f"preserved_input_changed:{entry['path']}")
            # The bundle/clone recovery hashes are independently checked by G14.
        save(
            "G00",
            dict(
                files_checked=len(inventory),
                inventory_sha256=sha256_file(inv_path),
                code_sha=code_sha,
                differences=errors,
            ),
            errors,
            "Inventory hashes and sizes; instrument bundle; explicit frozen input roots",
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        save("G00", dict(error=str(error)), [str(error)], "Preservation inputs")
    try:
        result = catalog_check(load("claims_catalog.json"), root, bind)
        save(
            "G02",
            result,
            result["identity_errors"],
            "Explicit claim states, method, evidence identity, scope and limitations",
        )
        provenance = assess_provenance(reviews, "claims_catalog.json")
        if provenance["mode"] == "legacy_unspecified":
            provenance["errors"].append("claims_provenance_missing")
        missing = [r["claim_id"] for r in result["relevance_results"] if not r["assessment"]]
        save(
            "G11",
            dict(**result, provenance=provenance),
            result["identity_errors"] + missing + provenance["errors"],
            "Separate source identity from attributed content relevance judgment",
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        for key in ("G02", "G11"):
            save(key, dict(error=str(error)), [str(error)], "Claim catalog and relevance")
    try:
        result = fixtures(root, directory, policy, code_sha)
        save(
            "G04",
            result,
            result["differences"],
            "Execute mapped known answers and counterexamples at verifier revision",
        )
    except (OSError, ValueError, KeyError, ET.ParseError) as error:
        save("G04", dict(error=str(error)), [str(error)], "Required fixture execution")
    try:
        academic = load("alinhamento_academico.json")
        inputs = load("closure_inputs.json")
        evidence = Evidence.model_validate(inputs["alignment_evidence"])
        resolve_evidence(evidence, root, {})
        bind(checked_path(root, evidence.path))
        errors = []
        required = {
            "provenance_coverage",
            "data_code_ratio_original",
            "data_code_cochange",
            "cace_index",
            "env_versioning_rate",
            "experiment_redundancy",
        }
        if not required <= set(academic["unanswered_questions"]):
            errors.append("unanswered_metrics_missing")
        if (
            not academic["operational_objective"]
            or academic["status"] != "accepted"
            or any(
                academic.get(k) is not True
                for k in ("mlflow_scope_resolved", "metric_mapping_resolved")
            )
        ):
            errors.append("academic_scope_unresolved")
        provenance = assess_provenance(reviews, "alinhamento_academico.json")
        errors += provenance["errors"]
        if provenance["mode"] == "legacy_unspecified":
            errors.append("academic_provenance_missing")
        save(
            "G12",
            dict(academic=academic, alignment_source=evidence.model_dump(), provenance=provenance),
            errors,
            "Documented operational objective, six open questions, scope and decision authorship",
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        save("G12", dict(error=str(error)), [str(error)], "Academic scope and source alignment")
    return results
