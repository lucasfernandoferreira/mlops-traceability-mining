"""Deterministic documentary event selection, with explicit PR knowledge and deficits."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from mlops_traceability.config import AnalysisConfig
from mlops_traceability.validation.taxonomy_review import valid_utc


def systematic(rows: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    count = min(count, len(rows))
    if count <= 0:
        return []
    if count == 1:
        return rows[:1]
    return [rows[i * (len(rows) - 1) // (count - 1)] for i in range(count)]


def select_events(
    commits: list[dict[str, Any]],
    changes: list[dict[str, Any]],
    repository: str,
    integration_paths: list[str],
    plan: AnalysisConfig,
    pr_map: list[dict[str, Any]] | None = None,
    integration_component: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    eligible = {r["commit_sha"]: r for r in commits if r["eligibility_status"] == "included"}
    links = {r["commit_sha"]: r for r in pr_map or []}
    if pr_map is not None and (len(links) != len(pr_map) or set(links) != set(eligible)):
        raise ValueError(
            "PR map must cover exactly the eligible commit universe, without duplicates"
        )
    for link in links.values():
        status = link["status"]
        if status not in {"found", "pr_not_found", "error", "not_collected"}:
            raise ValueError("Invalid PR lookup status")
        if status in {"found", "pr_not_found"} and (
            not link.get("reviewer", "").strip()
            or not valid_utc(link.get("checked_at_utc", ""))
            or not link.get("source_url", "").startswith(f"https://github.com/{repository}/")
        ):
            raise ValueError("PR evidence needs a public source, responsible person and UTC")
        prefix = f"https://github.com/{repository}/pull/"
        url = link.get("pr_url", "")
        if status == "found" and (not url.startswith(prefix) or not url[len(prefix) :].isdigit()):
            raise ValueError("Invalid case PR URL")
    paths: dict[str, set[str]] = defaultdict(set)
    for change in changes:
        paths[change["commit_sha"]].add(change["file_path"])
    events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sha, commit in eligible.items():
        link = links.get(sha, {})
        identity = link["pr_url"] if link.get("status") == "found" else sha
        events[identity].append(commit)
    candidates = []
    for identity, rows in events.items():
        rows.sort(
            key=lambda r: (
                datetime.fromisoformat(r["committed_at_utc"]).astimezone(UTC),
                r["commit_sha"],
            )
        )
        q1 = any(paths[r["commit_sha"]] & set(integration_paths) for r in rows)
        q2 = any(r["C"] and r["P"] for r in rows)
        configurations = [r for r in rows if r["P"]]
        valid = all(r["config_semantic_status"] == "observed" for r in configurations)
        magnitude = sum(r["config_changed_keys"] for r in configurations) if valid else None
        groups = [
            name
            for name, flag in (("Q1", q1), ("Q2", q2), ("Q3", valid and bool(magnitude)))
            if flag
        ]
        candidates.append(
            {
                "repository_id": repository,
                "event_id": identity,
                "commit_shas": ";".join(r["commit_sha"] for r in rows),
                "committed_at_utc": datetime.fromisoformat(rows[0]["committed_at_utc"])
                .astimezone(UTC)
                .isoformat(),
                "tie_sha": rows[0]["commit_sha"],
                "eligible_groups": ";".join(groups),
                "config_magnitude": magnitude,
                "pr_status": ";".join(
                    sorted(
                        {
                            links.get(r["commit_sha"], {}).get("status", "not_collected")
                            for r in rows
                        }
                    )
                ),
                "pr_source_urls": ";".join(
                    sorted({links.get(r["commit_sha"], {}).get("source_url", "") for r in rows})
                ),
                "eligibility_rule": "eligible commits; PR grouping before Q1/Q2/Q3",
            }
        )
    candidates.sort(key=lambda r: (r["committed_at_utc"], r["tie_sha"]))
    introductions = [
        c["commit_sha"]
        for c in changes
        if c["file_path"] == integration_component
        and c.get("change_type") == "A"
        and c["commit_sha"] in eligible
    ]
    first_introduction = (
        min(
            introductions,
            key=lambda sha: (
                datetime.fromisoformat(eligible[sha]["committed_at_utc"]).astimezone(UTC),
                sha,
            ),
        )
        if introductions
        else None
    )
    introduction_event = next(
        (r["event_id"] for r in candidates if first_introduction in r["commit_shas"].split(";")),
        None,
    )
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    coverage = []
    for group in plan.group_order:
        universe = [r for r in candidates if group in r["eligible_groups"].split(";")]
        pool = [r for r in universe if r["event_id"] not in selected_ids]
        if group == "Q3":
            pool.sort(key=lambda r: (-r["config_magnitude"], r["committed_at_utc"], r["tie_sha"]))
            chosen = pool[: plan.events_per_group]
        elif group == "Q1" and introduction_event:
            first = next(r for r in pool if r["event_id"] == introduction_event)
            chosen = [
                first,
                *systematic([r for r in pool if r is not first], plan.events_per_group - 1),
            ]
        else:
            chosen = systematic(pool, plan.events_per_group)
        for row in chosen:
            selected.append(
                {
                    **row,
                    "selection_group": group,
                    "group_position": pool.index(row),
                    "selection_position": len(selected) + 1,
                    "selection_reason": "first_component_introduction"
                    if group == "Q1" and row["event_id"] == introduction_event
                    else "quota",
                }
            )
            selected_ids.add(row["event_id"])
        coverage.append(
            {
                "group": group,
                "quota": plan.events_per_group,
                "candidate_count": len(universe),
                "overlap_already_selected": len(universe) - len(pool),
                "selected_count": len(chosen),
                "deficit": plan.events_per_group - len(chosen),
            }
        )
    target = len(plan.group_order) * plan.events_per_group
    if plan.fill_deficits:
        pool = [r for r in candidates if r["event_id"] not in selected_ids]
        for row in systematic(pool, target - len(selected)):
            selected.append(
                {
                    **row,
                    "selection_group": "FILL",
                    "group_position": pool.index(row),
                    "selection_position": len(selected) + 1,
                    "selection_reason": "documented_deficit_fill",
                }
            )
    return (
        candidates,
        selected,
        {
            "repository_id": repository,
            "groups": coverage,
            "candidate_count": len(candidates),
            "selected_count": len(selected),
            "total_deficit": target - len(selected),
            "plan_version": plan.plan_version,
            "pr_map_complete": pr_map is not None
            and all(r["status"] in {"found", "pr_not_found"} for r in links.values()),
            "pr_errors": sum(r["status"] == "error" for r in links.values()),
            "integration_paths": integration_paths,
            "integration_component": integration_component,
            "first_integration_event_id": introduction_event,
        },
    )
