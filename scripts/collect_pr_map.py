"""Collect and preserve public commit–PR associations for one immutable study index."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from git import Repo

from mlops_traceability.manifest import sha256_file
from mlops_traceability.pilot import write_json
from mlops_traceability.pr_mapping import build_query, response_link
from mlops_traceability.study import load_index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-index", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    with Repo(root) as repo:
        if repo.is_dirty(untracked_files=True):
            parser.error("Commit the instrument before collecting the study PR map")
        code_sha = repo.head.commit.hexsha
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        parser.error("GITHUB_TOKEN is required")
    load_index(root, args.study_index)
    template = args.study_index.parent / "pr_map_template.json"
    mapping = json.loads(template.read_text())
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=False)
    (output / "input_study_index.json").write_bytes(args.study_index.read_bytes())
    started = datetime.now(UTC).isoformat()
    evidence: list[dict[str, str]] = []
    stop_reason = ""
    try:
        for repository, rows in mapping.items():
            for offset in range(0, len(rows), 50):
                batch = rows[offset : offset + 50]
                query = build_query(repository, [r["commit_sha"] for r in batch])
                request = urllib.request.Request(
                    "https://api.github.com/graphql",
                    data=json.dumps({"query": query}).encode(),
                    headers={
                        "Authorization": "Bearer " + token,
                        "Content-Type": "application/json",
                        "User-Agent": "mlops-traceability-mining",
                    },
                )
                payload: dict[str, Any]
                try:
                    with urllib.request.urlopen(request, timeout=30) as response:
                        payload = json.loads(response.read())
                except (urllib.error.URLError, TimeoutError, ValueError) as error:
                    # Persist diagnostics without headers or the credential-bearing request.
                    payload = {"transport_error": type(error).__name__}
                    if isinstance(error, urllib.error.HTTPError):
                        payload["http_status"] = error.code
                        payload["retry_after"] = error.headers.get("Retry-After")
                checked = datetime.now(UTC).isoformat()
                path = output / f"batch_{len(evidence):04d}.json"
                write_json(path, {"query": query, "checked_at_utc": checked, "response": payload})
                digest = sha256_file(path)
                evidence.append({"path": path.name, "sha256": digest})
                failed = bool(payload.get("errors") or payload.get("transport_error"))
                data = payload.get("data") or {}
                nodes = data.get("repository") or {}
                for i, original in enumerate(batch):
                    link = response_link(
                        repository,
                        original["commit_sha"],
                        None if failed else nodes.get(f"c{i}"),
                        checked,
                    )
                    if failed:
                        link["error_detail"] = "api_or_transport_error"
                    original.update(link, evidence_file=path.name, evidence_sha256=digest)
                write_json(output / "mapa_prs.json", mapping)
                case_counts = Counter(r["status"] for r in rows)
                print(
                    f"{repository}: {min(offset + 50, len(rows))}/{len(rows)} {dict(case_counts)}",
                    flush=True,
                )
                remaining = data.get("rateLimit", {}).get("remaining", 0)
                if failed or remaining < 50:
                    stop_reason = "api_error_or_rate_limit_reserve; retry in a new directory"
                    break
                time.sleep(1)
            if stop_reason:
                break
    except KeyboardInterrupt:
        stop_reason = "interrupted; partial evidence preserved"
    finally:
        write_json(output / "mapa_prs.json", mapping)
        counts = dict(Counter(r["status"] for rows in mapping.values() for r in rows))
        complete = not stop_reason and all(k in {"found", "pr_not_found"} for k in counts)
        write_json(
            output / "collection.json",
            {
                "schema_version": "1.0.0",
                "code_commit_sha": code_sha,
                "dirty_worktree": False,
                "started_at_utc": started,
                "finished_at_utc": datetime.now(UTC).isoformat(),
                "study_index_sha256": sha256_file(args.study_index),
                "template_sha256": sha256_file(template),
                "map_sha256": sha256_file(output / "mapa_prs.json"),
                "method": "GitHub Commit.associatedPullRequests; complete unique association only",
                "scope": "Public associations at collection time for every eligible study commit",
                "documentation": "https://docs.github.com/en/graphql/reference/commits#commit",
                "counts": counts,
                "complete": complete,
                "stop_reason": stop_reason,
                "evidence": evidence,
            },
        )
    print(f"PR map complete={complete}: {output / 'mapa_prs.json'}")
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
