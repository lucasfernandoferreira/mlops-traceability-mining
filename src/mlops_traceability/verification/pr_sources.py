"""Reconstruct recorded associations from the frozen collector's GraphQL dialect.

No imports from pr_mapping or the collector. This deliberately accepts only the
preserved query format, not arbitrary GraphQL. Evidence proves the API observation
at collection time, not absence of other PRs or authenticity of a human reviewer.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mlops_traceability.manifest import sha256_file
from mlops_traceability.verification.git_oracle import reconcile_rows


def recorded_query(query: str) -> tuple[str, dict[str, str]]:
    normalized = " ".join(query.split())
    wrapper = re.fullmatch(
        r"query \{ rateLimit \{ remaining resetAt cost \} "
        r'repository\(owner: "([\w.-]+)", name: "([\w.-]+)"\) \{ (.+) \} \}',
        normalized,
    )
    if wrapper is None:
        raise ValueError("Unsupported preserved GraphQL query")
    fields = wrapper[3]
    pattern = re.compile(
        r'(c\d+): object\(oid: "([a-f0-9]{40})"\) \{ \.\.\. on Commit \{ oid '
        r"associatedPullRequests\(first: 100\) \{ totalCount pageInfo \{ hasNextPage \} "
        r"nodes \{ number url repository \{ nameWithOwner \} \} \} \} \}"
    )
    matches = list(pattern.finditer(fields))
    if not matches or " ".join(m[0] for m in matches) != fields or len(matches) > 50:
        raise ValueError("Unsupported preserved GraphQL fields")
    aliases = {m[1]: m[2] for m in matches}
    if len(aliases) != len(matches) or len(set(aliases.values())) != len(matches):
        raise ValueError("Duplicate query alias or commit")
    return f"{wrapper[1]}/{wrapper[2]}", aliases


def association(repository: str, sha: str, node: Any) -> dict[str, Any]:
    result: dict[str, Any] = dict(
        commit_sha=sha,
        status="error",
        pr_url="",
        associated_pr_urls=[],
        error_detail="missing_or_mismatched_commit",
    )
    if not isinstance(node, dict) or node.get("oid") != sha:
        return result
    connection = node.get("associatedPullRequests")
    if not isinstance(connection, dict):
        return {**result, "error_detail": "missing_connection"}
    nodes, page = connection.get("nodes"), connection.get("pageInfo")
    if (
        not isinstance(nodes, list)
        or not isinstance(page, dict)
        or page.get("hasNextPage") is not False
        or type(connection.get("totalCount")) is not int
        or connection["totalCount"] != len(nodes)
    ):
        return {**result, "error_detail": "incomplete_connection"}
    for pr in nodes:
        if (
            not isinstance(pr, dict)
            or not isinstance(pr.get("repository"), dict)
            or str(pr["repository"].get("nameWithOwner", "")).lower() != repository.lower()
            or type(pr.get("number")) is not int
            or pr["number"] <= 0
            or pr.get("url") != f"https://github.com/{repository}/pull/{pr['number']}"
        ):
            return {**result, "error_detail": "foreign_or_invalid_pull_request"}
    result["associated_pr_urls"] = [pr["url"] for pr in nodes]
    if len(nodes) > 1:
        return {**result, "error_detail": "multiple_associations_require_review"}
    return {
        **result,
        "status": "found" if nodes else "pr_not_found",
        "pr_url": nodes[0]["url"] if nodes else "",
        "error_detail": "",
    }


def utc(value: str) -> datetime:
    instant = datetime.fromisoformat(value)
    if instant.utcoffset() != UTC.utcoffset(instant):
        raise ValueError("PR evidence requires a UTC timestamp")
    return instant


def reconstruct_associations(
    collection_path: Path,
    index_path: Path,
    selection_map: Path,
    eligible: dict[str, set[str]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any], list[Path]]:
    """Check snapshot compatibility and every batch, including unselected commits."""
    directory = collection_path.parent
    index = json.loads(index_path.read_text())
    collection = json.loads(collection_path.read_text())
    snapshot_path = directory / "input_study_index.json"
    snapshot = json.loads(snapshot_path.read_text())
    template = index_path.parent / "pr_map_template.json"
    map_path = directory / "mapa_prs.json"
    actual = json.loads(map_path.read_text())
    paths = [collection_path, snapshot_path, template, map_path, selection_map]
    if (
        sha256_file(snapshot_path) != collection["study_index_sha256"]
        or sha256_file(template) != collection["template_sha256"]
        or sha256_file(map_path) != collection["map_sha256"]
        or sha256_file(selection_map) != collection["map_sha256"]
    ):
        raise ValueError("PR collection snapshot/template/map binding mismatch")

    def cases(document: dict[str, Any]) -> list[tuple[str, str]]:
        return sorted((c["repository_id"], c["head_commit_sha"]) for c in document["cases"])

    if cases(snapshot) != cases(index) or len(set(cases(index))) != len(index["cases"]):
        raise ValueError("PR collection frozen cases differ from study index")
    if set(actual) != set(eligible) or set(eligible) != {c[0] for c in cases(index)}:
        raise ValueError("PR collection repository universe mismatch")
    start, finish = utc(collection["started_at_utc"]), utc(collection["finished_at_utc"])
    if finish < start:
        raise ValueError("PR collection time interval is reversed")
    reconstructed: dict[str, list[dict[str, Any]]] = {repo: [] for repo in eligible}
    seen_files: set[str] = set()
    for evidence in collection["evidence"]:
        name = evidence["path"]
        if not re.fullmatch(r"batch_\d{4,}\.json", name) or name in seen_files:
            raise ValueError("Invalid or duplicate PR evidence path")
        seen_files.add(name)
        path = directory / name
        if sha256_file(path) != evidence["sha256"]:
            raise ValueError(f"PR evidence hash mismatch: {name}")
        paths.append(path)
        batch = json.loads(path.read_text())
        repo, aliases = recorded_query(batch["query"])
        if repo not in reconstructed:
            raise ValueError("Query repository outside study")
        if not start <= utc(batch["checked_at_utc"]) <= finish:
            raise ValueError("Batch timestamp outside collection interval")
        response = batch["response"]
        failed = bool(response.get("errors") or response.get("transport_error"))
        nodes = (response.get("data") or {}).get("repository") or {}
        if set(nodes) - set(aliases):
            raise ValueError("Response alias not present in recorded query")
        for alias, sha in aliases.items():
            row = association(repo, sha, None if failed else nodes.get(alias))
            if failed:
                row["error_detail"] = "api_or_transport_error"
            reconstructed[repo].append(
                {
                    **row,
                    "source_url": f"https://github.com/{repo}/commit/{sha}",
                    "checked_at_utc": batch["checked_at_utc"],
                    "method": "GitHub Commit.associatedPullRequests",
                    "evidence_file": name,
                    "evidence_sha256": evidence["sha256"],
                }
            )
    differences: list[Any] = []
    counts: Counter[str] = Counter()
    for repo, expected in reconstructed.items():
        identities = [r["commit_sha"] for r in expected]
        if len(set(identities)) != len(identities) or set(identities) != eligible[repo]:
            raise ValueError(f"PR query coverage differs from eligible Git commits: {repo}")
        # Historical failed mappings may omit associated_pr_urls; absence is explicit [].
        observed = [{"associated_pr_urls": [], **r} for r in actual[repo]]
        differences.extend(
            {"repository_id": repo, **issue}
            for issue in reconcile_rows(
                expected, observed, ("commit_sha",), tuple(expected[0]) if expected else ()
            )
        )
        for row in observed:
            if not isinstance(row.get("reviewer"), str) or not row["reviewer"].strip():
                differences.append(dict(repository_id=repo, field="missing_collection_attribution"))
        counts.update(r["status"] for r in expected)
        for row in expected:
            if row["status"] == "error":
                differences.append(
                    dict(
                        repository_id=repo, commit_sha=row["commit_sha"], error=row["error_detail"]
                    )
                )
    if collection.get("complete") is not True or collection.get("stop_reason"):
        differences.append(dict(field="collection_incomplete"))
    if json.dumps(dict(counts), sort_keys=True) != json.dumps(collection["counts"], sort_keys=True):
        differences.append(dict(field="collection_counts", expected=dict(counts)))
    return (
        reconstructed,
        dict(
            differences=differences,
            counts=dict(counts),
            batches_checked=len(seen_files),
            eligible_commits_checked=sum(len(rows) for rows in reconstructed.values()),
            collection_study_index_sha256=collection["study_index_sha256"],
            verified_study_index_sha256=sha256_file(index_path),
            compatibility="Same frozen cases, exact template bytes, exact Git commit universe",
            scope="Public API associations at the recorded collection times",
        ),
        paths,
    )
