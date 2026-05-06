#!/usr/bin/env python3
"""Validate program records in the open workspace data directory."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml


PLUGIN_SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA_PATH = PLUGIN_SKILL_ROOT / "references" / "program-scope.v1.schema.json"


class ValidationError(Exception):
    pass


def type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return True


def check_format(value: str, fmt: str, path: str) -> None:
    if fmt == "uri":
        parsed = urlparse(value)
        if not parsed.scheme or not parsed.netloc:
            raise ValidationError(f"{path}: expected absolute URI")
    elif fmt == "date":
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValidationError(f"{path}: expected YYYY-MM-DD date")


def validate_value(value: Any, schema: dict[str, Any], path: str) -> None:
    if "const" in schema and value != schema["const"]:
        raise ValidationError(f"{path}: expected {schema['const']!r}")

    if "enum" in schema and value not in schema["enum"]:
        raise ValidationError(f"{path}: expected one of {schema['enum']!r}")

    expected_type = schema.get("type")
    if expected_type and not type_matches(value, expected_type):
        raise ValidationError(f"{path}: expected {expected_type}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ValidationError(f"{path}: shorter than minLength")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            raise ValidationError(f"{path}: does not match pattern {schema['pattern']!r}")
        if "format" in schema:
            check_format(value, schema["format"], path)

    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ValidationError(f"{path}: below minimum {schema['minimum']}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise ValidationError(f"{path}: fewer than minItems")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                validate_value(item, item_schema, f"{path}[{index}]")

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                raise ValidationError(f"{path}: missing required key {key!r}")

        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extras = sorted(set(value) - set(properties))
            if extras:
                raise ValidationError(f"{path}: unexpected keys {extras!r}")

        for key, child in value.items():
            if key in properties:
                validate_value(child, properties[key], f"{path}.{key}")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: expected YAML mapping")
    return data


def program_records(data_root: Path) -> list[Path]:
    program_root = data_root
    records = [
        path
        for path in program_root.rglob("*.yaml")
        if path.name != "sources.yaml" and ".cache" not in path.parts
    ]
    return sorted(records)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate program YAML records in a workspace data directory."
    )
    parser.add_argument(
        "--data-dir",
        default=str(Path.cwd() / "data"),
        help="workspace data directory; defaults to ./data",
    )
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA_PATH),
        help="program-scope v1 JSON schema path",
    )
    args = parser.parse_args()

    workspace_root = Path.cwd()
    data_root = Path(args.data_dir).expanduser().resolve()
    schema_path = Path(args.schema).expanduser().resolve()

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    records = program_records(data_root)
    if not records:
        print(f"No program records found under {data_root}.", file=sys.stderr)
        return 1

    failures: list[str] = []
    for record_path in records:
        try:
            try:
                display_path = str(record_path.relative_to(workspace_root))
            except ValueError:
                display_path = str(record_path)
            validate_value(load_yaml(record_path), schema, display_path)
        except Exception as exc:
            failures.append(f"{display_path}: {exc}")

    if failures:
        print("Program record validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    try:
        display_schema = schema_path.relative_to(workspace_root)
    except ValueError:
        display_schema = schema_path
    print(f"Validated {len(records)} program record(s) against {display_schema}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
