"""Safe semantic differences; repository content is parsed, never executed."""

from __future__ import annotations

import json
import tomllib
from pathlib import PurePosixPath
from typing import Any

import yaml


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject ambiguous mappings instead of silently keeping the last key."""


def _mapping(loader: UniqueKeyLoader, node: yaml.MappingNode) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in result:
            raise ValueError(f"Duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=True)
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _json_mapping(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def config_keys(content: bytes | None, path: str) -> dict[str, str]:
    """Flatten leaves with typed keys; lists count atomically and empty maps as leaves."""
    if content is None:
        return {}
    text = content.decode("utf-8")
    suffix = PurePosixPath(path).suffix.lower()
    if suffix in {".yaml", ".yml"} or PurePosixPath(path).name == "MLproject":
        value = yaml.load(text, Loader=UniqueKeyLoader)
    elif suffix == ".json":
        value = json.loads(text, object_pairs_hook=_json_mapping)
    elif suffix == ".toml":
        value = tomllib.loads(text)
    else:
        raise NotImplementedError(f"Unsupported config format: {path}")
    result: dict[str, str] = {}

    def visit(item: Any, parts: list[str], ancestors: set[int]) -> None:
        if id(item) in ancestors:
            raise ValueError("Recursive YAML alias")
        if isinstance(item, dict) and item:
            for key, child in item.items():
                visit(child, [*parts, f"{type(key).__name__}:{key}"], ancestors | {id(item)})
        else:
            # JSON preserves bool/int distinctions; YAML dates are serialized explicitly.
            result[json.dumps(parts, ensure_ascii=False)] = json.dumps(
                item, sort_keys=True, default=str, ensure_ascii=False
            )

    if value is not None:
        visit(value, [], set())
    return result


def changed_keys(before: bytes | None, after: bytes | None, path: str) -> list[str]:
    old, new = config_keys(before, path), config_keys(after, path)
    return sorted(key for key in old.keys() | new.keys() if old.get(key) != new.get(key))
