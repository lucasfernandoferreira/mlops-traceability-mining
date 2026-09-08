"""Interpret GitHub commit associations without turning incomplete evidence into absence."""

from __future__ import annotations

import json
import re
from typing import Any


def build_query(repository: str, shas: list[str]) -> str:
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository) or not shas:
        raise ValueError("Repository and commits are required")
    if len(shas) > 50 or any(not re.fullmatch(r"[0-9a-f]{40}", sha) for sha in shas):
        raise ValueError("Expected at most 50 full commit SHAs")
    owner, name = repository.split("/")
    fields = " ".join(
        f'c{i}: object(oid: "{sha}") {{ ... on Commit {{ oid '
        "associatedPullRequests(first: 100) { totalCount pageInfo { hasNextPage } "
        "nodes { number url repository { nameWithOwner } } } } }"
        for i, sha in enumerate(shas)
    )
    return (
        "query { rateLimit { remaining resetAt cost } "
        f"repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{ {fields} }} }}"
    )


def response_link(
    repository: str, sha: str, node: dict[str, Any] | None, checked_at: str
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "commit_sha": sha,
        "status": "error",
        "pr_url": "",
        "source_url": f"https://github.com/{repository}/commit/{sha}",
        "reviewer": "Automated GitHub GraphQL collection; human review pending",
        "checked_at_utc": checked_at,
        "method": "GitHub Commit.associatedPullRequests",
        "error_detail": "missing_or_mismatched_commit",
    }
    if not node or node.get("oid") != sha:
        return row
    connection = node.get("associatedPullRequests")
    if not isinstance(connection, dict):
        return {**row, "error_detail": "missing_connection"}
    nodes = connection.get("nodes")
    if (
        not isinstance(nodes, list)
        or connection.get("pageInfo", {}).get("hasNextPage") is not False
        or connection.get("totalCount") != len(nodes)
    ):
        return {**row, "error_detail": "incomplete_connection"}
    if any(
        not isinstance(pr, dict)
        or pr.get("repository", {}).get("nameWithOwner", "").lower() != repository.lower()
        or not isinstance(pr.get("number"), int)
        or pr["number"] <= 0
        or pr.get("url") != f"https://github.com/{repository}/pull/{pr['number']}"
        for pr in nodes
    ):
        return {**row, "error_detail": "foreign_or_invalid_pull_request"}
    row["associated_pr_urls"] = [pr["url"] for pr in nodes]
    if len(nodes) > 1:
        return {**row, "error_detail": "multiple_associations_require_review"}
    return {
        **row,
        "status": "found" if nodes else "pr_not_found",
        "pr_url": nodes[0]["url"] if nodes else "",
        "error_detail": "",
    }
