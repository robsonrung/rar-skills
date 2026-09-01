#!/usr/bin/env python3
"""Strict, dependency-free output-contract checks shared by runner wrappers.

The model-facing schema prompt and native structured-output switches are useful
guidance, but neither is a receipt.  A consensus vote is usable only when the
final answer contains one JSON value which validates against the requested
schema.  This module deliberately implements the small Draft-7 subset used by
the repository's consensus schemas and rejects unsupported keywords instead of
silently accepting a weaker contract.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_CODE_FENCE = re.compile(r"^```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n?```[ \t]*$", re.IGNORECASE)
_SUPPORTED_KEYWORDS = {
    "$schema", "$id", "title", "description", "type", "required",
    "properties", "additionalProperties", "items", "minimum", "maximum",
    "enum", "minItems", "maxItems", "minLength", "maxLength",
}


@dataclass(frozen=True)
class ContractResult:
    valid: bool
    value: Any = None
    error_kind: str | None = None
    error: str | None = None


class _SchemaError(ValueError):
    pass


def _pointer(path: str, key: str) -> str:
    escaped = key.replace("~", "~0").replace("/", "~1")
    return f"{path}/{escaped}" if path else f"/{escaped}"


def _type_matches(value: Any, schema_type: str) -> bool:
    # bool is a subclass of int in Python, but not in JSON Schema.
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(schema_type, False)


def _validate(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    unsupported = set(schema) - _SUPPORTED_KEYWORDS
    if unsupported:
        names = ", ".join(sorted(unsupported))
        raise _SchemaError(f"{path}: unsupported schema keyword(s): {names}")

    schema_type = schema.get("type")
    if schema_type is not None:
        choices = schema_type if isinstance(schema_type, list) else [schema_type]
        if not all(isinstance(choice, str) for choice in choices):
            raise _SchemaError(f"{path}: schema type must be a string or string array")
        if not any(_type_matches(value, choice) for choice in choices):
            expected = " or ".join(choices)
            actual = "null" if value is None else type(value).__name__
            raise _SchemaError(f"{path}: expected {expected}, got {actual}")

    if "enum" in schema and value not in schema["enum"]:
        raise _SchemaError(f"{path}: value is not one of the allowed enum values")

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            raise _SchemaError(f"{path}: properties must be an object")
        required = schema.get("required", [])
        if not isinstance(required, list) or not all(isinstance(key, str) for key in required):
            raise _SchemaError(f"{path}: required must be a string array")
        for key in required:
            if key not in value:
                raise _SchemaError(f"{_pointer(path, key)}: required property is missing")
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            child_path = _pointer(path, key)
            if key in properties:
                child_schema = properties[key]
                if not isinstance(child_schema, dict):
                    raise _SchemaError(f"{child_path}: property schema must be an object")
                _validate(item, child_schema, child_path)
            elif additional is False:
                raise _SchemaError(f"{child_path}: additional property is not allowed")
            elif isinstance(additional, dict):
                _validate(item, additional, child_path)

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise _SchemaError(f"{path}: expected at least {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise _SchemaError(f"{path}: expected at most {schema['maxItems']} items")
        if "items" in schema:
            item_schema = schema["items"]
            if not isinstance(item_schema, dict):
                raise _SchemaError(f"{path}: items schema must be an object")
            for index, item in enumerate(value):
                _validate(item, item_schema, f"{path}/{index}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise _SchemaError(f"{path}: expected a string of at least {schema['minLength']} characters")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise _SchemaError(f"{path}: expected a string of at most {schema['maxLength']} characters")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise _SchemaError(f"{path}: expected a value >= {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise _SchemaError(f"{path}: expected a value <= {schema['maximum']}")


def _decode_exactly_one_json(text: str) -> Any:
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("final answer is empty")
    fenced = _CODE_FENCE.fullmatch(cleaned)
    if fenced:
        cleaned = fenced.group(1).strip()
    decoder = json.JSONDecoder()
    try:
        value, end = decoder.raw_decode(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"final answer is not valid JSON: {exc.msg}") from exc
    if cleaned[end:].strip():
        raise ValueError("final answer must contain exactly one JSON value (found trailing content)")
    return value


def validate_value(value: Any, schema_path: str | Path) -> ContractResult:
    """Validate an already-decoded value against a local supported schema."""
    try:
        schema = json.loads(Path(schema_path).expanduser().read_text(encoding="utf-8"))
        if not isinstance(schema, dict):
            raise _SchemaError("schema root must be an object")
        _validate(value, schema)
    except (OSError, json.JSONDecodeError, _SchemaError) as exc:
        return ContractResult(False, error_kind="schema_invalid", error=str(exc))
    return ContractResult(True, value=value)


def validate_output_contract(message: str | None, schema_path: str | Path) -> ContractResult:
    """Decode exactly one final JSON value, then validate its output schema."""
    if message is None:
        return ContractResult(False, error_kind="missing_output", error="no final answer was emitted")
    try:
        value = _decode_exactly_one_json(message)
    except ValueError as exc:
        return ContractResult(False, error_kind="invalid_json", error=str(exc))
    return validate_value(value, schema_path)
