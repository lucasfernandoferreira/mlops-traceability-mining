"""History at a fixed SHA, with an auditable exclusion funnel and file evidence."""

from __future__ import annotations

import ast
import hashlib
from collections import Counter
from datetime import UTC
from pathlib import Path
from typing import Any

from git import Blob, Repo

from mlops_traceability.config import ResearchConfig
from mlops_traceability.config_diff import changed_keys
from mlops_traceability.taxonomy import Category, FileTaxonomy

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def is_bot(identity: str, config: ResearchConfig) -> bool:
    return any(pattern.lower() in identity.lower() for pattern in config.commit_filter.bot_patterns)


def read_blob(repo: Repo, revision: str | None, path: str) -> bytes | None:
    if revision is None:
        return None
    try:
        blob = repo.commit(revision).tree / path
    except KeyError:
        return None
    return bytes(blob.data_stream.read())


def mine_history(
    path: Path,
    sha: str,
    repository_id: str,
    config: ResearchConfig,
    taxonomy: FileTaxonomy,
    run_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    repo = Repo(path)
    commits: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    active_authors: set[str] = set()
    # Full reachable DAG, one entry per SHA. No --first-parent or wall-clock cutoff.
    for index, commit in enumerate(repo.iter_commits(sha, reverse=True, topo_order=True), 1):
        parent = commit.parents[0].hexsha if commit.parents else None
        tokens = repo.git.diff_tree(
            "--no-commit-id",
            "--name-status",
            "--no-renames",
            "-r",
            "-z",
            parent or EMPTY_TREE,
            commit.hexsha,
        ).split("\0")
        tokens = [token for token in tokens if token]
        if len(tokens) % 2:
            raise ValueError("Malformed Git name-status output")
        statuses = dict(zip(tokens[1::2], tokens[0::2], strict=True))
        paths = list(statuses)
        bot = is_bot(f"{commit.author.name} {commit.author.email}", config)
        if (
            not bot
            and len(commit.parents) <= 1
            and commit.committed_datetime > config.selection.active_after
        ):
            active_authors.add((commit.author.email or commit.author.name or "").lower())
        reason = "included"
        if config.commit_filter.exclude_merges and len(commit.parents) > 1:
            reason = "merge"
        elif config.commit_filter.exclude_bots and bot:
            reason = "bot"
        elif (
            len(paths) > config.commit_filter.large_commit_max_files
            and config.commit_filter.large_commit_action == "flag_and_skip"
        ):
            reason = "large_commit"
        categories: set[str] = set()
        key_count = 0
        semantic_status = "observed"
        if reason == "included":
            for file_path in paths:
                category = taxonomy.classify(file_path)
                categories.add(category.value)
                row: dict[str, Any] = {
                    "repository_id": repository_id,
                    "commit_sha": commit.hexsha,
                    "parent_sha": parent,
                    "file_path": file_path,
                    "category": category.value,
                    "change_type": statuses[file_path],
                    "run_id": run_id,
                    "semantic_status": "not_applicable",
                    "semantic_detail": "",
                    "changed_keys": [],
                    "changed_key_count": None,
                }
                if category == Category.CONFIG:
                    try:
                        keys = changed_keys(
                            read_blob(repo, parent, file_path),
                            read_blob(repo, commit.hexsha, file_path),
                            file_path,
                        )
                        row.update(
                            semantic_status="observed",
                            changed_keys=keys,
                            changed_key_count=len(keys),
                        )
                        key_count += len(keys)
                    except NotImplementedError as error:
                        row.update(semantic_status="not_applicable", semantic_detail=str(error))
                    except Exception as error:
                        row.update(semantic_status="error", semantic_detail=str(error)[:500])
                    if row["semantic_status"] == "error":
                        semantic_status = "error"
                    elif row["semantic_status"] != "observed" and semantic_status != "error":
                        semantic_status = "not_applicable"
                changes.append(row)
        commits.append(
            {
                "repository_id": repository_id,
                "commit_sha": commit.hexsha,
                "parent_sha": parent,
                "committed_at_utc": commit.committed_datetime.astimezone(UTC).isoformat(),
                "parent_count": len(commit.parents),
                "is_bot": bot,
                "files_changed_count": len(paths),
                "large_commit": len(paths) > config.commit_filter.large_commit_max_files,
                "eligibility_status": reason,
                "C": bool(categories & {"CODE", "NOTEBOOK"}),
                "D": "DATA_META" in categories,
                "P": "CONFIG" in categories,
                "config_changed_keys": key_count if semantic_status == "observed" else None,
                "config_semantic_status": semantic_status,
                "run_id": run_id,
            }
        )
        if index % 250 == 0:
            print(f"{repository_id}: {index} commits processados", flush=True)
    summary = {
        "repository_id": repository_id,
        "head_commit_sha": sha,
        "reachable_commits": len(commits),
        "funnel": dict(Counter(row["eligibility_status"] for row in commits)),
        "active_contributors_count": len(active_authors),
        "active_contributors_gate": len(active_authors) >= config.selection.min_contributors,
        "active_after": config.selection.active_after.isoformat(),
        "identity_rule": "lowercase author email, fallback author name; no mailmap",
        "period_start_utc": min(row["committed_at_utc"] for row in commits),
        "period_end_utc": max(row["committed_at_utc"] for row in commits),
        "semantic_errors": sum(row["semantic_status"] == "error" for row in changes),
    }
    repo.close()
    return commits, changes, summary


def static_calls(source: bytes) -> list[dict[str, Any]]:
    """Syntactic candidates: imported aliases only; no execution or data-flow inference."""
    tree = ast.parse(source)
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "mlflow" or alias.name.startswith("mlflow."):
                    aliases[alias.asname or alias.name.split(".")[0]] = (
                        alias.name if alias.asname else "mlflow"
                    )
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and (node.module == "mlflow" or node.module.startswith("mlflow."))
        ):
            for alias in node.names:
                aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"

    def qualified(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return aliases.get(node.id, "")
        if isinstance(node, ast.Attribute):
            prefix = qualified(node.value)
            return f"{prefix}.{node.attr}" if prefix else ""
        return ""

    result = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and (name := qualified(node.func)):
            result.append(
                {
                    "line": node.lineno,
                    "call": name,
                    "operation": name.rsplit(".", 1)[-1],
                    "status": "static_candidate",
                }
            )
    return sorted(result, key=lambda row: (row["line"], row["call"]))


def inspect_tree(
    path: Path, sha: str, repository_id: str, taxonomy: FileTaxonomy
) -> dict[str, Any]:
    repo = Repo(path)
    files = []
    calls = []
    errors = []
    mlruns = []
    for blob in repo.commit(sha).tree.traverse():
        if not isinstance(blob, Blob):
            continue
        category = taxonomy.classify(str(blob.path)).value
        files.append(
            {
                "repository_id": repository_id,
                "head_commit_sha": sha,
                "file_path": blob.path,
                "category": category,
                "blob_sha": blob.hexsha,
            }
        )
        if "mlruns" in Path(blob.path).parts[:-1]:
            mlruns.append(blob.path)
        if str(blob.path).endswith(".py"):
            source = bytes(blob.data_stream.read())
            try:
                candidates = static_calls(source)
            except (SyntaxError, ValueError) as error:
                errors.append({"file_path": blob.path, "error": str(error)})
                continue
            for row in candidates:
                calls.append(
                    {
                        **row,
                        "repository_id": repository_id,
                        "head_commit_sha": sha,
                        "file_path": blob.path,
                        "category": category,
                        "blob_sha": blob.hexsha,
                        "source_sha256": hashlib.sha256(source).hexdigest(),
                        "url": f"https://github.com/{repository_id}/blob/{sha}/{blob.path}#L{row['line']}",
                    }
                )
    repo.close()
    return {
        "files": files,
        "calls": calls,
        "parse_errors": errors,
        "mlruns_paths": mlruns,
        "runtime_evidence_status": "not_available",
        "runtime_evidence_detail": (
            "No runs/registry source ingested; tree scan is not a runtime census."
        ),
    }
