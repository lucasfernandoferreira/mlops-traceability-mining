"""Paired-tree CONFIG reference; no production flattening/diff imports.

PyYAML parsing and JSON scalar serialization are declared shared dependencies.
Mappings are compared recursively as pairs, not flattened into two leaf tables.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import PurePosixPath
from typing import Any

import yaml

MISSING = object()


def unique_pairs(pairs: list[tuple[Any, Any]]) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate configuration key")
        result[key] = value
    return result


class ReferenceLoader(yaml.SafeLoader):
    """Separate duplicate-key implementation, with the protocol's SafeLoader types."""


def mapping(loader: ReferenceLoader, node: yaml.MappingNode) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    return unique_pairs(loader.construct_pairs(node, deep=True))


ReferenceLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def parse(content: bytes | None, path: str) -> Any:
    if content is None:
        return MISSING
    text = content.decode("utf-8")
    suffix = PurePosixPath(path).suffix.lower()
    if suffix in {".yaml", ".yml"} or PurePosixPath(path).name == "MLproject":
        value = yaml.load(text, Loader=ReferenceLoader)
    elif suffix == ".json":
        value = json.loads(text, object_pairs_hook=unique_pairs)
    elif suffix == ".toml":
        value = tomllib.loads(text)
    else:
        raise NotImplementedError(f"Unsupported CONFIG format: {path}")
    return MISSING if value is None else value


def reference_keys(before: bytes | None, after: bytes | None, path: str) -> list[str]:
    differences: set[str] = set()

    def visit(old: Any, new: Any, parts: tuple[str, ...], ancestors: frozenset[int]) -> None:
        for value in (old, new):
            if isinstance(value, dict) and id(value) in ancestors:
                raise ValueError("Recursive configuration alias")
        old_map = (
            {f"{type(k).__name__}:{k}": v for k, v in old.items()}
            if isinstance(old, dict) and old
            else {}
        )
        new_map = (
            {f"{type(k).__name__}:{k}": v for k, v in new.items()}
            if isinstance(new, dict) and new
            else {}
        )
        if old_map or new_map:
            # Replacing a leaf by a mapping removes its old path and adds child paths.
            if (not old_map and old is not MISSING) or (not new_map and new is not MISSING):
                differences.add(json.dumps(parts, ensure_ascii=False))
            for key in old_map.keys() | new_map.keys():
                visit(
                    old_map.get(key, MISSING),
                    new_map.get(key, MISSING),
                    (*parts, key),
                    ancestors | {id(old), id(new)},
                )
        elif old is MISSING or new is MISSING:
            if old is not new:
                differences.add(json.dumps(parts, ensure_ascii=False))
        elif json.dumps(old, sort_keys=True, default=str, ensure_ascii=False) != json.dumps(
            new, sort_keys=True, default=str, ensure_ascii=False
        ):
            differences.add(json.dumps(parts, ensure_ascii=False))

    visit(parse(before, path), parse(after, path), (), frozenset())
    return sorted(differences)
