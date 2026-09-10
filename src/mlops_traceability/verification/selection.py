"""Reference event selection over Git-derived rows and reconstructed PR evidence.

Grouping uses sorted partitions; sampling uses exact rational interpolation. No
production selection, PR response interpreter or configuration model is imported.
"""

from __future__ import annotations

from datetime import UTC, datetime
from fractions import Fraction
from itertools import groupby
from typing import Any


def spread(size: int, quota: int) -> list[int]:
    count = min(size, max(0, quota))
    if count < 2:
        return list(range(count))
    return [int(Fraction(position, count - 1) * (size - 1)) for position in range(count)]


def select_reference(
    commits: list[dict[str, Any]],
    changes: list[dict[str, Any]],
    repository: str,
    associations: list[dict[str, Any]],
    integration_paths: list[str],
    component: str | None,
    plan: dict[str, Any],
) -> dict[str, Any]:
    if (
        plan["group_order"] != ["Q1", "Q2", "Q3"]
        or type(plan["events_per_group"]) is not int
        or plan["events_per_group"] < 1
        or type(plan["fill_deficits"]) is not bool
    ):
        raise ValueError("Unsupported qualitative selection plan")
    eligible = [c for c in commits if c["eligibility_status"] == "included"]
    by_sha = {c["commit_sha"]: c for c in eligible}
    links = {r["commit_sha"]: r for r in associations}
    if len(by_sha) != len(eligible) or len(links) != len(associations) or set(links) != set(by_sha):
        raise ValueError("Selection requires unique commits and exact association coverage")

    def time_key(sha: str) -> tuple[datetime, str]:
        value = datetime.fromisoformat(by_sha[sha]["committed_at_utc"])
        if value.tzinfo is None:
            raise ValueError("Commit timestamp requires a timezone")
        return value.astimezone(UTC), sha

    def event_key(sha: str) -> str:
        return str(links[sha]["pr_url"]) if links[sha]["status"] == "found" else sha

    integration_shas = {c["commit_sha"] for c in changes if c["file_path"] in integration_paths}
    introductions = {
        c["commit_sha"]
        for c in changes
        if c["file_path"] == component and c["change_type"] == "A" and c["commit_sha"] in by_sha
    }
    first_event = event_key(min(introductions, key=time_key)) if introductions else None
    candidates = []
    for event, partition in groupby(sorted(by_sha, key=event_key), key=event_key):
        shas = sorted(partition, key=time_key)
        configuration = [by_sha[sha] for sha in shas if by_sha[sha]["P"]]
        magnitude = (
            sum(c["config_changed_keys"] for c in configuration)
            if all(c["config_semantic_status"] == "observed" for c in configuration)
            else None
        )
        membership = {
            "Q1": bool(set(shas) & integration_shas),
            "Q2": any(by_sha[sha]["C"] and by_sha[sha]["P"] for sha in shas),
            "Q3": magnitude is not None and magnitude > 0,
        }
        candidates.append(
            dict(
                repository_id=repository,
                event_id=event,
                commit_shas=";".join(shas),
                committed_at_utc=time_key(shas[0])[0].isoformat(),
                tie_sha=shas[0],
                eligible_groups=";".join(k for k in ("Q1", "Q2", "Q3") if membership[k]),
                config_magnitude=magnitude,
                pr_status=";".join(sorted({links[sha]["status"] for sha in shas})),
                pr_source_urls=";".join(sorted({links[sha]["source_url"] for sha in shas})),
                eligibility_rule="eligible commits; PR grouping before Q1/Q2/Q3",
            )
        )
    candidates.sort(key=lambda r: (r["committed_at_utc"], r["tie_sha"]))
    selected: list[dict[str, Any]] = []
    used: set[str] = set()
    groups = []
    quota = plan["events_per_group"]

    def append(pool: list[dict[str, Any]], positions: list[int], group: str) -> None:
        for position in positions:
            row = pool[position]
            if row["event_id"] in used:
                raise ValueError("Reference selection attempted to reuse an event")
            used.add(row["event_id"])
            reason = (
                "documented_deficit_fill"
                if group == "FILL"
                else "first_component_introduction"
                if group == "Q1" and row["event_id"] == first_event
                else "quota"
            )
            selected.append(
                dict(
                    **row,
                    selection_group=group,
                    group_position=position,
                    selection_position=len(selected) + 1,
                    selection_reason=reason,
                )
            )

    for group in ("Q1", "Q2", "Q3"):
        universe = [r for r in candidates if group in r["eligible_groups"].split(";")]
        pool = [r for r in universe if r["event_id"] not in used]
        if group == "Q3":
            pool.sort(key=lambda r: (-r["config_magnitude"], r["committed_at_utc"], r["tie_sha"]))
            positions = list(range(min(quota, len(pool))))
        elif group == "Q1" and first_event:
            reserved = next((i for i, r in enumerate(pool) if r["event_id"] == first_event), None)
            if reserved is None:
                raise ValueError("Integration component introduction is outside Q1 paths")
            remaining = [i for i in range(len(pool)) if i != reserved]
            positions = [reserved, *[remaining[i] for i in spread(len(remaining), quota - 1)]]
        else:
            positions = spread(len(pool), quota)
        append(pool, positions, group)
        groups.append(
            dict(
                group=group,
                quota=quota,
                candidate_count=len(universe),
                overlap_already_selected=len(universe) - len(pool),
                selected_count=len(positions),
                deficit=quota - len(positions),
            )
        )
    if plan["fill_deficits"]:
        pool = [r for r in candidates if r["event_id"] not in used]
        append(pool, spread(len(pool), 3 * quota - len(selected)), "FILL")
    return dict(
        candidates=candidates,
        selected=selected,
        coverage=dict(
            repository_id=repository,
            groups=groups,
            candidate_count=len(candidates),
            selected_count=len(selected),
            total_deficit=3 * quota - len(selected),
            plan_version=plan["plan_version"],
            pr_map_complete=all(r["status"] in {"found", "pr_not_found"} for r in associations),
            pr_errors=sum(r["status"] == "error" for r in associations),
            integration_paths=integration_paths,
            integration_component=component,
            first_integration_event_id=first_event,
        ),
    )
