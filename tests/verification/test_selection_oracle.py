"""Known PR observations and hand-calculated event selection; synthetic evidence only."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from mlops_traceability.manifest import sha256_file
from mlops_traceability.pilot import write_json
from mlops_traceability.verification.pr_sources import (
    association,
    reconstruct_associations,
    recorded_query,
    utc,
)
from mlops_traceability.verification.qualitative import compare_selection, declared_components
from mlops_traceability.verification.selection import select_reference, spread

REPO = "test/case"
STAMP = "2026-09-08T00:00:00Z"


def oid(number: int) -> str:
    return f"{number:040x}"


def query(repo: str, shas: list[str]) -> str:
    owner, name = repo.split("/")
    fields = " ".join(
        f'c{i}: object(oid: "{sha}") {{ ... on Commit {{ oid '
        "associatedPullRequests(first: 100) { totalCount pageInfo { hasNextPage } "
        "nodes { number url repository { nameWithOwner } } } } }"
        for i, sha in enumerate(shas)
    )
    return (
        "query { rateLimit { remaining resetAt cost } "
        f'repository(owner: "{owner}", name: "{name}") {{ {fields} }} }}'
    )


def node(sha: str, prs: tuple[int, ...] = (), **connection: Any) -> dict[str, Any]:
    return {
        "oid": sha,
        "associatedPullRequests": {
            "totalCount": len(prs),
            "pageInfo": {"hasNextPage": False},
            "nodes": [
                {
                    "number": n,
                    "url": f"https://github.com/{REPO}/pull/{n}",
                    "repository": {"nameWithOwner": REPO},
                }
                for n in prs
            ],
            **connection,
        },
    }


def preserve_collection(directory: Path, index: Path, shas: list[str]) -> Path:
    """Build complete zero-association observations without using the production collector."""
    directory.mkdir()
    (directory / "input_study_index.json").write_bytes(index.read_bytes())
    evidence = directory / "batch_0000.json"
    write_json(
        evidence,
        {
            "query": query(REPO, shas),
            "checked_at_utc": STAMP,
            "response": {
                "data": {"repository": {f"c{i}": node(sha) for i, sha in enumerate(shas)}}
            },
        },
    )
    rows = [
        {
            "commit_sha": sha,
            "status": "pr_not_found",
            "pr_url": "",
            "source_url": f"https://github.com/{REPO}/commit/{sha}",
            "checked_at_utc": STAMP,
            "reviewer": "synthetic collector",
            "method": "GitHub Commit.associatedPullRequests",
            "error_detail": "",
            "associated_pr_urls": [],
            "evidence_file": evidence.name,
            "evidence_sha256": sha256_file(evidence),
        }
        for sha in shas
    ]
    write_json(directory / "mapa_prs.json", {REPO: rows})
    write_json(
        directory / "collection.json",
        {
            "study_index_sha256": sha256_file(index),
            "template_sha256": sha256_file(index.parent / "pr_map_template.json"),
            "map_sha256": sha256_file(directory / "mapa_prs.json"),
            "started_at_utc": STAMP,
            "finished_at_utc": STAMP,
            "complete": True,
            "stop_reason": "",
            "counts": {"pr_not_found": len(shas)},
            "evidence": [{"path": evidence.name, "sha256": sha256_file(evidence)}],
        },
    )
    return directory / "collection.json"


@pytest.fixture
def collection(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, set[str]]]:
    index = tmp_path / "study_index.json"
    write_json(index, {"cases": [{"repository_id": REPO, "head_commit_sha": oid(99)}]})
    write_json(tmp_path / "pr_map_template.json", {REPO: [{"commit_sha": oid(1)}]})
    record = preserve_collection(tmp_path / "collection", index, [oid(1)])
    selected = tmp_path / "selected_map.json"
    selected.write_bytes((record.parent / "mapa_prs.json").read_bytes())
    return record, index, selected, {REPO: {oid(1)}}


def test_recorded_query_rejects_unparsed_fields_and_duplicates() -> None:
    text = query(REPO, [oid(1), oid(2)])
    assert recorded_query(text) == (REPO, {"c0": oid(1), "c1": oid(2)})
    for bad in (
        text + " garbage",
        text.replace("first: 100", "first: 1"),
        query(REPO, [oid(1), oid(1)]),
        text.replace("c1:", "c0:"),
    ):
        with pytest.raises(ValueError, match="Unsupported|Duplicate"):
            recorded_query(bad)
    with pytest.raises(ValueError, match="UTC"):
        utc("2026-09-08T00:00:00-03:00")


@pytest.mark.parametrize(
    "prs,status,url",
    [
        ((), "pr_not_found", ""),
        ((7,), "found", f"https://github.com/{REPO}/pull/7"),
        ((7, 8), "error", ""),
    ],
)
def test_known_associations(prs: tuple[int, ...], status: str, url: str) -> None:
    result = association(REPO, oid(1), node(oid(1), prs))
    assert result["status"] == status and result["pr_url"] == url


@pytest.mark.counterexample
@pytest.mark.parametrize(
    "mutation,reason",
    [
        ("pagination", "incomplete_connection"),
        ("count", "incomplete_connection"),
        ("oid", "missing_or_mismatched_commit"),
        ("missing", "missing_connection"),
        ("foreign", "foreign_or_invalid_pull_request"),
        ("boolean_number", "foreign_or_invalid_pull_request"),
    ],
)
def test_incomplete_or_invalid_observation_never_becomes_absence(
    mutation: str, reason: str
) -> None:
    observed = node(oid(1))
    if mutation == "pagination":
        observed["associatedPullRequests"]["pageInfo"]["hasNextPage"] = True
    elif mutation == "count":
        observed["associatedPullRequests"]["totalCount"] = 1
    elif mutation == "oid":
        observed["oid"] = oid(2)
    elif mutation == "missing":
        del observed["associatedPullRequests"]
    else:
        observed = node(oid(1), (7,))
        pr = observed["associatedPullRequests"]["nodes"][0]
        if mutation == "foreign":
            pr["repository"]["nameWithOwner"] = "other/case"
        else:
            pr["number"] = True
    assert association(REPO, oid(1), observed)["error_detail"] == reason
    assert association(REPO, oid(1), observed)["status"] == "error"


def test_complete_collection_and_compatible_reprocessed_index(collection: Any) -> None:
    record, index, selected, universe = collection
    mapping, check, paths = reconstruct_associations(*collection)
    assert check["differences"] == [] and len(paths) == 6
    assert mapping[REPO][0]["status"] == "pr_not_found"
    document = json.loads(index.read_text())
    document["new_run_metadata"] = "same cases, template and eligible universe"
    write_json(index, document)
    _, check, _ = reconstruct_associations(record, index, selected, universe)
    assert check["collection_study_index_sha256"] != check["verified_study_index_sha256"]
    assert check["differences"] == []


@pytest.mark.counterexample
@pytest.mark.parametrize(
    "mutation,reason",
    [
        ("hash", "hash mismatch"),
        ("duplicate_batch", "duplicate PR evidence"),
        ("query_universe", "query coverage"),
        ("different_head", "frozen cases"),
        ("map_binding", "binding mismatch"),
    ],
)
def test_collection_binding_mutations(collection: Any, mutation: str, reason: str) -> None:
    record, index, selected, universe = collection
    document = json.loads(record.read_text())
    if mutation == "hash":
        (record.parent / "batch_0000.json").write_text("{}")
    elif mutation == "duplicate_batch":
        document["evidence"] *= 2
        write_json(record, document)
    elif mutation == "query_universe":
        universe[REPO].add(oid(2))
    elif mutation == "different_head":
        write_json(index, {"cases": [{"repository_id": REPO, "head_commit_sha": oid(98)}]})
    else:
        selected.write_text("{}")
    with pytest.raises(ValueError, match=reason):
        reconstruct_associations(record, index, selected, universe)


@pytest.mark.counterexample
def test_map_forgery_is_detected_even_with_matching_file_hashes(collection: Any) -> None:
    record, index, selected, universe = collection
    path = record.parent / "mapa_prs.json"
    mapping = json.loads(path.read_text())
    mapping[REPO][0].update(status="found", pr_url=f"https://github.com/{REPO}/pull/99")
    write_json(path, mapping)
    selected.write_bytes(path.read_bytes())
    document = json.loads(record.read_text())
    document["map_sha256"] = sha256_file(path)
    write_json(record, document)
    _, check, _ = reconstruct_associations(record, index, selected, universe)
    assert {d["field"] for d in check["differences"]} >= {"status", "pr_url"}


def selection_fixture() -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]
]:
    commits, changes, links = [], [], []
    for i in range(1, 11):
        commits.append(
            dict(
                commit_sha=oid(i),
                eligibility_status="included",
                C=i in range(2, 7),
                P=i in (2, 4, 5, 6, 7),
                config_changed_keys={2: 2, 4: 3, 5: 10, 6: 10, 7: 20}.get(i, 0),
                config_semantic_status="observed",
                committed_at_utc=f"2026-01-{i:02}T00:00:00Z",
            )
        )
        links.append(
            dict(
                commit_sha=oid(i),
                status="found" if i in (1, 2) else "pr_not_found",
                pr_url=f"https://github.com/{REPO}/pull/7" if i in (1, 2) else "",
                source_url=f"https://github.com/{REPO}/commit/{oid(i)}",
            )
        )
        changes.append(
            dict(
                commit_sha=oid(i),
                file_path="integration.py" if i in (2, 3, 4) else "doc.md",
                change_type="A" if i == 2 else "M",
            )
        )
    return (
        commits,
        changes,
        links,
        dict(
            plan_version="1.0.0",
            group_order=["Q1", "Q2", "Q3"],
            events_per_group=2,
            fill_deficits=True,
        ),
    )


def selected_reference() -> dict[str, Any]:
    commits, changes, links, plan = selection_fixture()
    return select_reference(
        commits, changes, REPO, links, ["integration.py"], "integration.py", plan
    )


def test_hand_calculated_grouping_introduction_overlap_and_quota() -> None:
    result = selected_reference()
    assert len(result["candidates"]) == 9  # Two commits belong to one PR before sampling.
    assert result["candidates"][0]["commit_shas"] == f"{oid(1)};{oid(2)}"
    assert [r["event_id"] for r in result["selected"]] == [
        f"https://github.com/{REPO}/pull/7",
        oid(3),
        oid(4),
        oid(6),
        oid(7),
        oid(5),
    ]
    assert [r["group_position"] for r in result["selected"]] == [0, 1, 0, 2, 0, 1]
    assert [r["overlap_already_selected"] for r in result["coverage"]["groups"]] == [0, 1, 3]
    assert result["selected"][0]["selection_reason"] == "first_component_introduction"
    assert result["coverage"]["total_deficit"] == 0


@pytest.mark.parametrize("fill,count", [(True, 3), (False, 0)])
def test_documentary_deficit_does_not_manufacture_group_membership(fill: bool, count: int) -> None:
    commits, changes, links, plan = selection_fixture()
    plan["fill_deficits"] = fill
    result = select_reference(
        commits[-3:], changes[-3:], REPO, links[-3:], ["integration.py"], "integration.py", plan
    )
    assert len(result["selected"]) == count
    assert result["coverage"]["total_deficit"] == 6 - count
    assert all(
        r["selection_group"] == "FILL" and r["eligible_groups"] == "" for r in result["selected"]
    )
    assert all(r["deficit"] == 2 for r in result["coverage"]["groups"])


@pytest.mark.parametrize(
    "size,quota,expected", [(0, 5, []), (1, 1, [0]), (6, 3, [0, 2, 5]), (9, 4, [0, 2, 5, 8])]
)
def test_rational_positions(size: int, quota: int, expected: list[int]) -> None:
    assert spread(size, quota) == expected


@pytest.mark.counterexample
@pytest.mark.parametrize(
    "mutation,reason",
    [
        ("order", "event_order"),
        ("quota", "selection_group"),
        ("member", "commit_shas"),
        ("magnitude", "config_magnitude"),
    ],
)
def test_selection_mutations_have_specific_reasons(mutation: str, reason: str) -> None:
    expected = selected_reference()["selected"]
    measured = deepcopy(expected)
    if mutation == "order":
        measured.reverse()
    elif mutation == "quota":
        measured[0]["selection_group"] = "Q3"
    elif mutation == "member":
        measured[0]["commit_shas"] = oid(1)
    else:
        measured[-1]["config_magnitude"] += 1
    assert reason in {d["field"] for d in compare_selection(expected, measured)}


@pytest.mark.counterexample
def test_duplicate_selected_event_is_rejected() -> None:
    expected = selected_reference()["selected"]
    with pytest.raises(ValueError, match="Duplicate"):
        compare_selection(expected, [*expected, expected[0]])


@pytest.mark.counterexample
@pytest.mark.parametrize("rows", [[], [{"repository_id": REPO}] * 2])
def test_missing_or_duplicate_case_template_is_rejected(rows: list[dict[str, Any]]) -> None:
    with pytest.raises(ValueError, match="exactly the study repositories"):
        declared_components(rows, {REPO})


@pytest.mark.counterexample
@pytest.mark.parametrize("mutation", ["pagination", "api_error", "missing_node"])
def test_response_failures_block_collection_without_inventing_absence(
    collection: Any, mutation: str
) -> None:
    record, index, selected, universe = collection
    evidence = record.parent / "batch_0000.json"
    batch = json.loads(evidence.read_text())
    if mutation == "pagination":
        batch["response"]["data"]["repository"]["c0"]["associatedPullRequests"]["pageInfo"][
            "hasNextPage"
        ] = True
    elif mutation == "api_error":
        batch["response"]["errors"] = [{"message": "synthetic error"}]
    else:
        batch["response"]["data"]["repository"] = {}
    write_json(evidence, batch)
    document = json.loads(record.read_text())
    document["evidence"][0]["sha256"] = sha256_file(evidence)
    write_json(record, document)
    mapping, check, _ = reconstruct_associations(record, index, selected, universe)
    assert mapping[REPO][0]["status"] == "error"
    assert any(d.get("error") for d in check["differences"])


@pytest.mark.counterexample
def test_same_commit_in_two_batches_is_not_double_counted(collection: Any) -> None:
    record, _, _, _ = collection
    duplicate = record.parent / "batch_0001.json"
    duplicate.write_bytes((record.parent / "batch_0000.json").read_bytes())
    document = json.loads(record.read_text())
    document["evidence"].append({"path": duplicate.name, "sha256": sha256_file(duplicate)})
    write_json(record, document)
    with pytest.raises(ValueError, match="query coverage"):
        reconstruct_associations(*collection)


def test_grouping_does_not_invent_same_commit_cochange() -> None:
    commits, changes, links, plan = selection_fixture()
    commits[0].update(C=True, P=False)
    commits[1].update(C=False, P=True)
    result = select_reference(
        commits, changes, REPO, links, ["integration.py"], "integration.py", plan
    )
    assert result["candidates"][0]["eligible_groups"] == "Q1;Q3"


def test_utc_sha_tie_and_unknown_or_zero_magnitude() -> None:
    commits, changes, links, plan = selection_fixture()
    commits[5]["committed_at_utc"] = commits[4]["committed_at_utc"]
    commits[6]["config_semantic_status"] = "error"
    commits[3]["config_changed_keys"] = 0
    result = select_reference(
        commits, changes, REPO, links, ["integration.py"], "integration.py", plan
    )
    candidates = {r["event_id"]: r for r in result["candidates"]}
    assert candidates[oid(7)]["config_magnitude"] is None
    assert "Q3" not in candidates[oid(7)]["eligible_groups"]
    assert "Q3" not in candidates[oid(4)]["eligible_groups"]
    ordered = [r["event_id"] for r in result["candidates"]]
    assert ordered.index(oid(5)) < ordered.index(oid(6))
    # A timezone spelling change preserves the UTC order inside one PR.
    commits[1]["committed_at_utc"] = "2025-12-31T21:00:00-03:00"
    result = select_reference(
        commits, changes, REPO, links, ["integration.py"], "integration.py", plan
    )
    assert result["candidates"][0]["commit_shas"] == f"{oid(1)};{oid(2)}"


@pytest.mark.parametrize(
    "mutation,reason",
    [
        ("plan", "Unsupported"),
        ("duplicate", "unique"),
        ("time", "timezone"),
        ("component", "outside Q1"),
    ],
)
def test_invalid_reference_inputs_are_refused(mutation: str, reason: str) -> None:
    commits, changes, links, plan = selection_fixture()
    paths = ["integration.py"]
    if mutation == "plan":
        plan["group_order"] = ["Q3", "Q2", "Q1"]
    elif mutation == "duplicate":
        commits.append(commits[0])
    elif mutation == "time":
        commits[0]["committed_at_utc"] = "2026-01-01T00:00:00"
    else:
        paths = []
    with pytest.raises(ValueError, match=reason):
        select_reference(commits, changes, REPO, links, paths, "integration.py", plan)


def test_q3_equal_magnitudes_use_utc_then_sha() -> None:
    commits, changes, links, plan = selection_fixture()
    for row in commits:
        row["C"] = False
    commits[5]["committed_at_utc"] = commits[4]["committed_at_utc"]
    result = select_reference(commits, changes, REPO, links, [], None, plan)
    q3 = [r["event_id"] for r in result["selected"] if r["selection_group"] == "Q3"]
    assert q3 == [oid(7), oid(5)]
