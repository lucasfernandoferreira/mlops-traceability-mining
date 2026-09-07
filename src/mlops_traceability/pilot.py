"""Reusable stage plumbing, frozen inputs and immutable pilot provenance."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import tarfile
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from git import Repo

from mlops_traceability.config import load_config
from mlops_traceability.manifest import build_artifact, sha256_file, start_run, write_manifest
from mlops_traceability.metrics_gqm import compute_metrics
from mlops_traceability.mining import inspect_tree, mine_history
from mlops_traceability.run_storage import (
    RunStatus,
    StageName,
    build_run_pointer,
    load_latest_pointer,
    run_directory,
    verified_run,
    write_latest_pointer,
)
from mlops_traceability.taxonomy import load_taxonomy


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: str(value).lower() if isinstance(value, bool) else value
                    for key, value in row.items()
                }
            )


def audit_collection(root: Path, sample: dict[str, Any]) -> dict[str, Any]:
    """Verify original artifacts/config bytes, never reinterpret old runs as protocol 2."""
    results = []
    repo = Repo(root)
    for stage, run_id in sample["source_runs"].items():
        path = root / "data/processed/manifests" / f"{run_id}.json"
        manifest = json.loads(path.read_text())
        if manifest["status"] != "SUCCESS" or manifest["dirty_worktree"]:
            raise ValueError(f"Unaccepted original collection: {run_id}")
        verified = []
        for artifact in manifest["artifacts"]:
            old_path = Path(artifact["path"])
            if old_path.name in {"config.yaml", "file_taxonomy.yaml", "requirements.txt"}:
                rel = f"config/{old_path.name}" if old_path.suffix == ".yaml" else old_path.name
                content = (repo.commit(manifest["code_commit_sha"]).tree / rel).data_stream.read()
            else:
                relative = old_path.as_posix().split("/data/", 1)[-1]
                content = (root / "data" / relative).read_bytes()
            if hashlib.sha256(content).hexdigest() != artifact["sha256"]:
                raise ValueError(f"Original artifact hash mismatch: {old_path.name}")
            verified.append({"name": old_path.name, "sha256": artifact["sha256"]})
        # Fase 2 did not include original config among artifacts; verify its top-level hashes too.
        for field, rel in (
            ("config_sha256", "config/config.yaml"),
            ("taxonomy_sha256", "config/file_taxonomy.yaml"),
            ("requirements_sha256", "requirements.txt"),
        ):
            content = (repo.commit(manifest["code_commit_sha"]).tree / rel).data_stream.read()
            if hashlib.sha256(content).hexdigest() != manifest[field]:
                raise ValueError(f"Original instrument hash mismatch: {run_id}/{rel}")
        results.append(
            {
                "stage": stage,
                "run_id": run_id,
                "protocol_version": manifest["protocol_version"],
                "manifest_sha256": sha256_file(path),
                "artifacts": verified,
            }
        )
    repo.close()
    shortlist = (
        root / "data/interim/runs" / sample["source_runs"]["phase2_screen_sample"] / "shortlist.csv"
    )
    if sha256_file(shortlist) != sample["source_shortlist_sha256"]:
        raise ValueError("Shortlist hash mismatch")
    with shortlist.open() as stream:
        rows = {row["repository_id"]: row for row in csv.DictReader(stream)}
    for selected in sample["repositories"]:
        original = rows[selected["repository_id"]]
        if (
            original["decision"] != "eligible"
            or original["head_commit_sha"] != selected["head_commit_sha"]
        ):
            raise ValueError("Selection does not match original shortlist")
    return {"verified": True, "sources": results}


def freeze_repository(root: Path, selected: dict[str, Any], raw_directory: Path) -> dict[str, Any]:
    repository_id, sha = selected["repository_id"], selected["head_commit_sha"]
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository_id) or not re.fullmatch(
        r"[0-9a-f]{40}", sha
    ):
        raise ValueError("Invalid repository ID or SHA")
    url = f"https://github.com/{repository_id}.git"
    target = root / raw_directory / (repository_id.replace("/", "__") + ".git")
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"Congelando {repository_id} em {sha}", flush=True)
    if not target.exists():
        repo = Repo.clone_from(url, target, bare=True)
    else:
        repo = Repo(target)
        if not repo.bare or repo.remotes.origin.url != url:
            raise ValueError("Existing clone must be bare and match selected origin")
    if repo.git.rev_parse("--is-shallow-repository") != "false":
        raise ValueError("Shallow clone is not a complete history")
    if repo.config_reader().has_option('remote "origin"', "promisor"):
        raise ValueError("Partial clone is not a complete history")
    try:
        actual = repo.commit(sha).hexsha
    except ValueError:
        repo.remotes.origin.fetch(sha)
        actual = repo.commit(sha).hexsha
    if actual != sha:
        raise ValueError("Selected SHA mismatch")
    # Read every reachable object; missing blobs/parents fail before acceptance.
    repo.git.fsck("--connectivity-only", "--no-dangling", sha)
    repo.git.update_ref(f"refs/tcc/frozen/{sha}", sha)
    result = {
        "repository_id": repository_id,
        "repository_url": url.removesuffix(".git"),
        "head_commit_sha": sha,
        "clone_path": target.relative_to(root).as_posix(),
        "stratum": selected["stratum"],
        "reachable_commits": int(repo.git.rev_list("--count", sha)),
        "shallow": False,
        "clone_bytes": sum(p.stat().st_size for p in target.rglob("*") if p.is_file()),
    }
    repo.close()
    return result


def source_artifact(
    root: Path,
    stage: StageName,
    name: str,
    source_run_id: str | None = None,
) -> tuple[Path, str]:
    config = load_config(root / "config/config.yaml")
    if source_run_id is None:
        pointer = load_latest_pointer(root / config.paths.interim, stage)
        if pointer is None or pointer.status != "SUCCESS":
            raise ValueError(f"Missing successful source stage: {stage}")
        source_run_id = pointer.run_id
    _, artifacts, execution = verified_run(root, source_run_id, stage)
    filename = execution["artifact_names"][name]
    return artifacts[filename], source_run_id


def snapshot_source(root: Path, target: Path) -> None:
    """Preserve exact work-in-progress code used by a development pilot."""
    with tarfile.open(target, "w:gz") as archive:
        files = [root / "pyproject.toml", root / "requirements.txt", root / "requirements-dev.txt"]
        for directory in ("src", "scripts", "config", "docs"):
            if not (root / directory).exists():
                continue
            files.extend(
                p
                for p in (root / directory).rglob("*")
                if p.is_file() and "__pycache__" not in p.parts and not p.name.endswith(".pyc")
            )
        for path in sorted(files):
            archive.add(path, arcname=path.relative_to(root))


def run_stage(stage: StageName, argv: list[str] | None = None, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-dirty", action="store_true", help="Piloto preliminar com snapshot do código."
    )
    parser.add_argument("--repository", default="ultralytics/ultralytics")
    parser.add_argument("--source-run-id")
    args = parser.parse_args(argv)
    root = root or Path(__file__).resolve().parents[2]
    config_path, taxonomy_path = root / "config/config.yaml", root / "config/file_taxonomy.yaml"
    config, taxonomy = load_config(config_path), load_taxonomy(taxonomy_path)
    context = start_run(project_root=root, stage=stage)
    directory = run_directory(root / config.paths.interim, context.run_id)
    directory.mkdir(parents=True, exist_ok=False)
    artifacts: dict[str, Path] = {}
    source_run_id = None
    sources: list[dict[str, str]] = []
    scientific_eligible = not context.dirty_worktree
    frozen: dict[str, Any] = {}
    error = None
    status: RunStatus = "SUCCESS"
    try:
        if (
            context.dirty_worktree
            and config.reproducibility.require_clean_worktree
            and not args.allow_dirty
        ):
            raise ValueError(
                "Scientific run requires clean worktree; use --allow-dirty for preliminary pilot."
            )
        artifacts["source_snapshot"] = directory / "source_snapshot.tar.gz"
        snapshot_source(root, artifacts["source_snapshot"])
        sample_path = root / "config/amostra_final.yaml"
        sample = yaml.safe_load(sample_path.read_text())
        if sample["protocol_version"] != config.protocol.version:
            raise ValueError("Sample protocol mismatch")
        selected = [r for r in sample["repositories"] if r["repository_id"] == args.repository]
        if len(selected) != 1 or sample["status"] not in {"pilot", "final"}:
            raise ValueError("Repository not authorized for pilot/final selection")
        expected_sha = selected[0]["head_commit_sha"]
        if stage == "phase3_clone_repos":
            if args.source_run_id:
                raise ValueError("Clone stage does not accept source-run-id")
            audit = audit_collection(root, sample)
            artifacts["source_audit"] = directory / "source_audit.json"
            write_json(artifacts["source_audit"], audit)
            frozen = freeze_repository(root, selected[0], config.paths.raw_repositories)
            frozen["run_id"] = context.run_id
            artifacts["frozen_sample"] = directory / "amostra_congelada.csv"
            write_csv(artifacts["frozen_sample"], [frozen])
            source_run_id = sample["source_runs"]["phase2_screen_sample"]
        elif stage == "phase4_mine_commits":
            source, source_run_id = source_artifact(
                root, "phase3_clone_repos", "frozen_sample", args.source_run_id
            )
            with source.open() as stream:
                frozen_rows = list(csv.DictReader(stream))
            if len(frozen_rows) != 1 or frozen_rows[0]["repository_id"] != args.repository:
                raise ValueError("Frozen source repository mismatch")
            frozen = frozen_rows[0]
            if frozen["head_commit_sha"] != expected_sha:
                raise ValueError("Frozen source SHA differs from selected case")
            clone = (root / frozen["clone_path"]).resolve()
            if not clone.is_relative_to((root / config.paths.raw_repositories).resolve()):
                raise ValueError("Clone outside configured raw repositories")
            commits, changes, summary = mine_history(
                clone, frozen["head_commit_sha"], args.repository, config, taxonomy, context.run_id
            )
            inspection = inspect_tree(clone, frozen["head_commit_sha"], args.repository, taxonomy)
            if len(commits) != int(frozen["reachable_commits"]):
                raise ValueError("Reachable commit count mismatch")
            for name, value in (("commits", commits), ("changes", changes)):
                artifacts[name] = directory / f"{name}.parquet"
                pd.DataFrame(value).to_parquet(artifacts[name], index=False)
            for name, document in (("mining_summary", summary), ("tree_inspection", inspection)):
                artifacts[name] = directory / f"{name}.json"
                write_json(artifacts[name], document)
            from mlops_traceability.validation.taxonomy_review import build_inventory, make_sample

            inventory = build_inventory(clone, changes, inspection, summary, taxonomy, config)
            artifacts["taxonomy_inventory"] = directory / "taxonomy_inventory.json"
            write_json(artifacts["taxonomy_inventory"], inventory)
            sample_rows = make_sample(inventory, config)
            artifacts["manual_sample"] = directory / "amostra_validacao_taxonomia.csv"
            write_csv(artifacts["manual_sample"], sample_rows)
        elif stage == "phase5_compute_metrics":
            inputs = {}
            for name in ("commits", "changes", "mining_summary", "tree_inspection"):
                source, upstream = source_artifact(
                    root, "phase4_mine_commits", name, args.source_run_id
                )
                if source_run_id is not None and upstream != source_run_id:
                    raise ValueError("Mixed mining source runs")
                source_run_id = upstream
                inputs[name] = source
            commits = pd.read_parquet(inputs["commits"]).to_dict("records")
            summary = json.loads(inputs["mining_summary"].read_text())
            inspection = json.loads(inputs["tree_inspection"].read_text())
            frozen = summary
            if summary["head_commit_sha"] != expected_sha:
                raise ValueError("Mining source SHA differs from selected case")
            if summary["repository_id"] != args.repository:
                raise ValueError("Mining source repository mismatch")
            rows = compute_metrics(
                commits,
                summary,
                inspection,
                protocol_version=config.protocol.version,
                taxonomy_version=taxonomy.config.version,
                run_id=context.run_id,
            )
            artifacts["metrics"] = directory / "metrics.csv"
            write_csv(artifacts["metrics"], rows)
            # Membership table permits reproducing both numerator and denominator by SHA.
            members = [
                {
                    "metric_id": metric,
                    "commit_sha": row["commit_sha"],
                    "in_numerator": row["P"] if metric == "code_config_cochange" else True,
                    "numerator_contribution": int(row["P"])
                    if metric == "code_config_cochange"
                    else row["config_changed_keys"],
                }
                for metric in ("code_config_cochange", "config_magnitude")
                for row in commits
                if row["eligibility_status"] == "included"
                and row["C" if metric == "code_config_cochange" else "P"]
            ]
            artifacts["metric_membership"] = directory / "metric_membership.csv"
            write_csv(
                artifacts["metric_membership"],
                members,
                ["metric_id", "commit_sha", "in_numerator", "numerator_contribution"],
            )
            artifacts["report"] = directory / "piloto.md"
            lines = [
                f"# Piloto {args.repository}",
                "",
                f"SHA: `{summary['head_commit_sha']}`.",
                "",
                "Resultados preliminares; validação humana da taxonomia pendente.",
                f"Commits alcançáveis: {summary['reachable_commits']}. "
                f"Funil: `{summary['funnel']}`.",
                f"Contribuidores ativos: {summary['active_contributors_count']}; "
                f"gate: {summary['active_contributors_gate']}.",
                "",
                "| Métrica | Numerador | Denominador | Valor | Status |",
                "|---|---:|---:|---:|---|",
            ]
            for row in rows:
                lines.append(
                    f"| {row['metric_id']} | {row['numerator']} | {row['denominator']} | "
                    f"{row['value']} | {row['status']} |"
                )
            lines += [
                "",
                f"Fonte da mineração: `{source_run_id}`.",
                "`metric_membership.csv` identifica os commits; "
                "`changes.parquet` identifica arquivos e chaves.",
                "`tree_inspection.json` contém linhas, URLs e hashes das chamadas estáticas.",
                "DATA_META não valida a dimensão de dados MLflow. "
                "Nenhuma fonte de runs/registry foi ingerida.",
            ]
            artifacts["report"].write_text("\n".join(lines) + "\n", encoding="utf-8")
            if any(row["status"] == "error" for row in rows):
                raise ValueError("Processing failed: metric errors")
        else:
            raise ValueError(f"Unsupported pilot stage: {stage}")
        if stage != "phase3_clone_repos" and source_run_id:
            upstream_manifest, _, upstream_execution = verified_run(root, source_run_id)
            if (
                upstream_execution["repository_id"] != args.repository
                or upstream_execution["head_commit_sha"] != frozen["head_commit_sha"]
            ):
                raise ValueError("Source repository/SHA mismatch")
            scientific_eligible = scientific_eligible and upstream_execution["scientific_eligible"]
            sources.append(
                {
                    "run_id": source_run_id,
                    "manifest_sha256": sha256_file(
                        root / config.paths.manifests / f"{source_run_id}.json"
                    ),
                }
            )
    except Exception as exception:
        status, error = "FAILED", f"{type(exception).__name__}: {exception}"
    artifacts = {name: path for name, path in artifacts.items() if path.is_file()}
    metadata = directory / "execution.json"
    write_json(
        metadata,
        {
            "run_id": context.run_id,
            "source_run_id": source_run_id,
            "repository_id": args.repository,
            "status": status,
            "error": error,
            "preliminary": True,
            "contract_version": "2.1.0",
            "head_commit_sha": frozen.get("head_commit_sha"),
            "processing_status": status,
            "sample_status": "pilot",
            "measurement_validation_status": "pending",
            "academic_alignment_status": "pending",
            "scientific_eligible": scientific_eligible,
            "sources": sources,
            "artifact_names": {name: path.name for name, path in artifacts.items()},
            "dirty_worktree": context.dirty_worktree,
        },
    )
    artifacts["execution"] = metadata
    manifest = write_manifest(
        context=context,
        manifest_directory=root / config.paths.manifests,
        config_path=config_path,
        taxonomy_path=taxonomy_path,
        requirements_path=root / "requirements.txt",
        protocol_id=config.protocol.id,
        protocol_version=config.protocol.version,
        status=status,
        artifacts=[
            build_artifact(p).model_copy(update={"path": p.relative_to(root).as_posix()})
            for p in artifacts.values()
        ],
        error=error,
    )
    pointer = build_run_pointer(
        interim_directory=root / config.paths.interim,
        stage=stage,
        status=status,
        run_id=context.run_id,
        artifacts=artifacts,
        source_run_id=source_run_id,
        manifest_path=manifest,
    )
    write_latest_pointer(root / config.paths.interim, pointer)
    print(f"{status}: {directory}", flush=True)
    if error:
        print(error, flush=True)
    return 0 if status == "SUCCESS" else 1
