"""Guard against false negative or ambiguous public PR evidence."""

from __future__ import annotations

from typing import Any

import pytest

from mlops_traceability.pr_mapping import build_query, response_link

SHA = "a" * 40
STAMP = "2026-09-08T00:00:00Z"


def node(prs: list[Any], **overrides: Any) -> dict[str, Any]:
    return {
        "oid": SHA,
        "associatedPullRequests": {
            "nodes": prs,
            "totalCount": len(prs),
            "pageInfo": {"hasNextPage": False},
            **overrides,
        },
    }


def pr(number: int = 1) -> dict[str, Any]:
    return {
        "number": number,
        "url": f"https://github.com/a/b/pull/{number}",
        "repository": {"nameWithOwner": "a/b"},
    }


def test_verified_absence_and_unique_association() -> None:
    absent = response_link("a/b", SHA, node([]), STAMP)
    assert absent["status"] == "pr_not_found" and absent["pr_url"] == ""
    found = response_link("a/b", SHA, node([pr()]), STAMP)
    assert found["status"] == "found" and found["pr_url"].endswith("/pull/1")
    assert found["checked_at_utc"] == STAMP
    assert "automated" in found["reviewer"].lower()
    assert "human review pending" in found["reviewer"]


@pytest.mark.parametrize(
    "response",
    [
        None,
        {},
        {"oid": "b" * 40},
        {"oid": SHA},
        node([], pageInfo={"hasNextPage": True}),
        node([], totalCount=1),
        node([], nodes=None),
        node([pr(), pr(2)]),
        node([None]),
        node([{**pr(), "url": "https://github.com/foreign/repo/pull/1"}]),
        node([{**pr(), "repository": {"nameWithOwner": "foreign/repo"}}]),
        node([pr(0)]),
        node([{**pr(), "number": "1"}]),
    ],
)
def test_incomplete_or_ambiguous_evidence_never_becomes_absence(
    response: dict[str, Any] | None,
) -> None:
    result = response_link("a/b", SHA, response, STAMP)
    assert result["status"] == "error" and result["error_detail"]


def test_query_uses_full_shas_and_explicit_completeness_fields() -> None:
    query = build_query("a/b", [SHA, "b" * 40])
    assert f'c0: object(oid: "{SHA}")' in query and "c1:" in query
    assert "totalCount" in query and "hasNextPage" in query
    for repository, shas in [("bad", [SHA]), ("a/b", []), ("a/b", ["short"]), ("a/b", [SHA] * 51)]:
        with pytest.raises(ValueError):
            build_query(repository, shas)
