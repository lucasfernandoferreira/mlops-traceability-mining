"""Frozen Git source recount using raw objects and raw diffs, without GitPython/mining.

The Git object engine, Python regex and policy rules are shared dependencies.
Author identities are used only in memory; no names/emails are written to reports.
"""

from __future__ import annotations

import hashlib
import math
import re
import subprocess
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from mlops_traceability.verification.semantics import reference_keys

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def git(clone: Path, *args: str) -> bytes:
    return subprocess.check_output(
        ["git", "--no-replace-objects", "-C", str(clone), *args],
        stderr=subprocess.PIPE,
    )


@contextmanager
def object_reader(clone: Path) -> Iterator[Any]:
    process = subprocess.Popen(
        ["git", "--no-replace-objects", "-C", str(clone), "cat-file", "--batch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert process.stdin is not None and process.stdout is not None

    def read(oid: str, kind: str) -> bytes:
        if not re.fullmatch(r"[0-9a-f]{40}", oid):
            raise ValueError("Full object SHA required")
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(oid.encode() + b"\n")
        process.stdin.flush()
        header = process.stdout.readline().split()
        if len(header) != 3 or header[0].decode() != oid or header[1].decode() != kind:
            raise ValueError(f"Missing or wrong Git object: {oid}")
        content = process.stdout.read(int(header[2]))
        if len(content) != int(header[2]) or process.stdout.read(1) != b"\n":
            raise ValueError("Truncated Git object")
        digest = hashlib.sha1(
            kind.encode() + b" " + str(len(content)).encode() + b"\0" + content
        ).hexdigest()
        if digest != oid:
            raise ValueError("Git object content hash mismatch")
        return content

    try:
        yield read
    finally:
        process.stdin.close()
        process.stdout.close()
        process.wait()


def classify(path: str, taxonomy: dict[str, Any]) -> str:
    normalized = path.replace("\\", "/").removeprefix("./")
    for rule in taxonomy["rules"]:
        if any(re.search(pattern, normalized, re.I) for pattern in rule["patterns"]):
            return str(rule["category"])
    return str(taxonomy["default_category"])


def raw_changes(clone: Path, parent: str | None, sha: str) -> list[dict[str, Any]]:
    raw = git(
        clone,
        "diff-tree",
        "--no-commit-id",
        "--raw",
        "--no-abbrev",
        "--no-renames",
        "-r",
        "-z",
        parent or EMPTY_TREE,
        sha,
    )
    tokens = raw.split(b"\0")
    if tokens[-1] != b"" or (len(tokens) - 1) % 2:
        raise ValueError("Malformed raw Git diff")
    result = []
    for position in range(0, len(tokens) - 1, 2):
        metadata = tokens[position].decode("ascii").split()
        if len(metadata) != 5 or metadata[4] not in {"A", "D", "M", "T"}:
            raise ValueError("Unsupported raw Git diff record")
        result.append(
            {
                "file_path": tokens[position + 1].decode("utf-8"),
                "change_type": metadata[4],
                "before_blob_sha": None if metadata[2] == "0" * 40 else metadata[2],
                "after_blob_sha": None if metadata[3] == "0" * 40 else metadata[3],
            }
        )
    return result


def source_history(
    clone: Path,
    sha: str,
    repository: str,
    config: dict[str, Any],
    taxonomy: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Frozen full SHA required")
    if git(clone, "rev-parse", "--is-shallow-repository").strip() != b"false":
        raise ValueError("Shallow source cannot establish the full history")
    local_config = git(clone, "config", "--local", "--list", "-z").decode().split("\0")
    keys = [entry.split("\n", 1)[0].lower() for entry in local_config]
    if any(key.endswith(".promisor") or key == "extensions.partialclone" for key in keys):
        raise ValueError("Partial/promisor clones are not offline complete sources")
    shas = git(clone, "rev-list", sha).decode().splitlines()
    commits, changes = [], []
    active: set[str] = set()
    filters = config["commit_filter"]
    cutoff = datetime.fromisoformat(config["selection"]["active_after"]).timestamp()
    cache: dict[tuple[str | None, str | None, str], dict[str, Any]] = {}
    with object_reader(clone) as read:
        for position, oid in enumerate(shas, 1):
            headers = read(oid, "commit").split(b"\n\n", 1)[0].splitlines()
            parents = [line[7:].decode("ascii") for line in headers if line.startswith(b"parent ")]
            author = next(line[7:] for line in headers if line.startswith(b"author "))
            match = re.fullmatch(rb"(.*) <(.*)> (-?\d+) [+-]\d{4}", author)
            if not match:
                raise ValueError("Malformed Git author")
            name, email = match[1].decode("utf-8"), match[2].decode("utf-8")
            is_bot = any(p.lower() in f"{name} {email}".lower() for p in filters["bot_patterns"])
            committer = next(line for line in headers if line.startswith(b"committer "))
            instant = int(committer.rsplit(b" ", 2)[1])
            if len(parents) <= 1 and not is_bot and instant > cutoff:
                active.add((email or name).lower())
            parent = parents[0] if parents else None
            files = raw_changes(clone, parent, oid)
            large = len(files) > filters["large_commit_max_files"]
            reason = (
                "merge"
                if len(parents) > 1 and filters["exclude_merges"]
                else "bot"
                if is_bot and filters["exclude_bots"]
                else "large_commit"
                if large and filters["large_commit_action"] == "flag_and_skip"
                else "included"
            )
            categories: set[str] = set()
            key_count = 0
            statuses: set[str] = set()
            if reason == "included":
                for entry in files:
                    category = classify(entry["file_path"], taxonomy)
                    categories.add(category)
                    change = {
                        **entry,
                        "repository_id": repository,
                        "commit_sha": oid,
                        "parent_sha": parent,
                        "category": category,
                        "semantic_status": "not_applicable",
                        "changed_keys": [],
                        "changed_key_count": None,
                    }
                    if category == "CONFIG":
                        path = entry["file_path"]
                        parser = (
                            "MLproject"
                            if Path(path).name == "MLproject"
                            else Path(path).suffix.lower()
                        )
                        pair = (entry["before_blob_sha"], entry["after_blob_sha"], parser)
                        if pair not in cache:
                            # Missing Git objects are input failures, never parser-error matches.
                            old = read(pair[0], "blob") if pair[0] else None
                            new = read(pair[1], "blob") if pair[1] else None
                            try:
                                keys = reference_keys(old, new, path)
                                cache[pair] = dict(
                                    semantic_status="observed",
                                    changed_keys=keys,
                                    changed_key_count=len(keys),
                                )
                            except NotImplementedError:
                                cache[pair] = dict(
                                    semantic_status="not_applicable",
                                    changed_keys=[],
                                    changed_key_count=None,
                                )
                            except (ValueError, TypeError, RecursionError, yaml.YAMLError) as error:
                                cache[pair] = dict(
                                    semantic_status="error",
                                    changed_keys=[],
                                    changed_key_count=None,
                                    error_type=type(error).__name__,
                                )
                        change.update(cache[pair])
                        statuses.add(change["semantic_status"])
                        key_count += change["changed_key_count"] or 0
                    changes.append(change)
            state = (
                "error"
                if "error" in statuses
                else "not_applicable"
                if "not_applicable" in statuses
                else "observed"
            )
            commits.append(
                {
                    "repository_id": repository,
                    "commit_sha": oid,
                    "parent_sha": parent,
                    "parent_count": len(parents),
                    "committed_at_utc": datetime.fromtimestamp(instant, UTC).isoformat(),
                    "is_bot": is_bot,
                    "files_changed_count": len(files),
                    "large_commit": large,
                    "eligibility_status": reason,
                    "C": bool(categories & {"CODE", "NOTEBOOK"}),
                    "D": "DATA_META" in categories,
                    "P": "CONFIG" in categories,
                    "config_semantic_status": state,
                    "config_changed_keys": key_count if state == "observed" else None,
                }
            )
            if position % 250 == 0:
                print(f"Git oracle {repository}: {position}/{len(shas)}", flush=True)
    return (
        commits,
        changes,
        {
            "repository_id": repository,
            "head_commit_sha": sha,
            "reachable_commits": len(shas),
            "active_contributors_count": len(active),
            "funnel": dict(Counter(r["eligibility_status"] for r in commits)),
            "config_blob_pairs_checked": len(cache),
            "identity_rule": "lowercase email or name; no mailmap; identities are not persons",
            "shared_dependencies": [
                "Git object engine",
                "Python regex",
                "PyYAML parser",
                "JSON scalar serialization",
            ],
        },
    )


def reconcile_rows(
    expected: list[dict[str, Any]],
    actual: list[dict[str, Any]],
    identity: tuple[str, ...],
    fields: tuple[str, ...],
    *,
    tolerance: float = 0.0,
) -> list[dict[str, Any]]:
    """Compare the full universe; reject duplicates rather than silently overwriting them."""

    def indexed(rows: list[dict[str, Any]]) -> dict[tuple[Any, ...], dict[str, Any]]:
        result = {tuple(r[k] for k in identity): r for r in rows}
        if len(result) != len(rows):
            raise ValueError("Duplicate source/table identity")
        return result

    left, right = indexed(expected), indexed(actual)
    problems = []
    for key in sorted(left.keys() | right.keys()):
        if key not in left or key not in right:
            problems.append(
                dict(identity=key, field="membership", expected=key in left, observed=key in right)
            )
        else:
            for field in fields:
                a, b = left[key][field], right[key][field]
                matches = type(a) is type(b) and a == b
                if isinstance(a, float) and isinstance(b, float):
                    matches = math.isclose(a, b, rel_tol=0, abs_tol=tolerance)
                if not matches:
                    problems.append(
                        dict(
                            identity=key,
                            field=field,
                            expected=left[key][field],
                            observed=right[key][field],
                        )
                    )
    return problems
