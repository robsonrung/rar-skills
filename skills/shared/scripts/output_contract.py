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
import math
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
        "integer": type(value) is int or (type(value) is float and math.isfinite(value) and value.is_integer()),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(schema_type, False)


def validate_schema(schema: dict[str, Any], path: str = "$") -> None:
    """Check every schema branch before validation; unsupported contracts fail closed."""
    if not isinstance(schema, dict):
        raise _SchemaError(f"{path}: schema must be an object")
    unsupported = set(schema) - _SUPPORTED_KEYWORDS
    if unsupported:
        raise _SchemaError(f"{path}: unsupported schema keyword(s): {', '.join(sorted(unsupported))}")
    if "$schema" in schema and schema["$schema"] not in {
        "http://json-schema.org/draft-07/schema#", "https://json-schema.org/draft-07/schema#"
    }:
        raise _SchemaError(f"{path}: only Draft 7 schemas are supported")
    for key in ("$id", "title", "description"):
        if key in schema and not isinstance(schema[key], str):
            raise _SchemaError(f"{path}: {key} must be a string")
    if "type" in schema:
        choices = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        allowed = {"object", "array", "string", "number", "integer", "boolean", "null"}
        if not choices or any(not isinstance(x, str) or x not in allowed for x in choices) or len(set(choices)) != len(choices):
            raise _SchemaError(f"{path}: invalid schema type")
    if "required" in schema:
        value = schema["required"]
        if not isinstance(value, list) or any(not isinstance(x, str) for x in value) or len(set(value)) != len(value):
            raise _SchemaError(f"{path}: required must contain unique strings")
    for key in ("minimum", "maximum"):
        if key in schema and (type(schema[key]) not in (int, float) or (type(schema[key]) is float and not math.isfinite(schema[key]))):
            raise _SchemaError(f"{path}: {key} must be finite numeric")
    for key in ("minItems", "maxItems", "minLength", "maxLength"):
        if key in schema and (type(schema[key]) is not int or schema[key] < 0):
            raise _SchemaError(f"{path}: {key} must be a nonnegative integer")
    if "enum" in schema:
        values = schema["enum"]
        if not isinstance(values, list) or not values:
            raise _SchemaError(f"{path}: enum must be a nonempty array")
        if any(_json_equal(a, b) for i, a in enumerate(values) for b in values[i + 1:]):
            raise _SchemaError(f"{path}: enum values must be unique")
    if "properties" in schema:
        if not isinstance(schema["properties"], dict):
            raise _SchemaError(f"{path}: properties must be an object")
        for name, child in schema["properties"].items():
            validate_schema(child, _pointer(path, name))
    if "items" in schema:
        validate_schema(schema["items"], path + "/items")
    if "additionalProperties" in schema:
        extra = schema["additionalProperties"]
        if not isinstance(extra, bool):
            validate_schema(extra, path + "/additionalProperties")


def _json_equal(left, right):
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_json_equal(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_json_equal(a, b) for a, b in zip(left, right))
    return left == right


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

    if "enum" in schema and not any(_json_equal(value, item) for item in schema["enum"]):
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


def _pairs_unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"invalid JSON constant: {value}")


def _decode_exactly_one_json(text: str, *, allow_prose_fence: bool = False) -> Any:
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("final answer is empty")
    if allow_prose_fence and "```" in cleaned:
        fences = list(re.finditer(r"```(?:json)?[ \t]*\r?\n([\s\S]*?)\r?\n?```", cleaned, re.IGNORECASE))
        if len(fences) != 1 or cleaned.count("```") != 2:
            raise ValueError("expected exactly one JSON fence")
        fence = fences[0]
        outside = cleaned[:fence.start()] + " " + cleaned[fence.end():]
        # Reject structural fragments and standalone scalar candidates outside the fence.
        if re.search(r'[{}\[\]"`]|(?<![\w])(?:-?\d|true\b|false\b|null\b|NaN\b|Infinity\b)', outside):
            raise ValueError("ambiguous JSON outside the fence")
        cleaned = fence.group(1).strip()
    fenced = _CODE_FENCE.fullmatch(cleaned)
    if fenced:
        cleaned = fenced.group(1).strip()
    decoder = json.JSONDecoder(object_pairs_hook=_pairs_unique, parse_constant=_reject_constant)
    try:
        value, end = decoder.raw_decode(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"final answer is not valid JSON: {exc.msg}") from exc
    if cleaned[end:].strip():
        raise ValueError("final answer must contain exactly one JSON value (found trailing content)")
    return value


def validate_document(value: Any, schema: dict[str, Any]) -> ContractResult:
    """Validate against an immutable schema snapshot with a complete branch precheck."""
    try:
        # Also reject non-JSON values passed through the decoded-value API.
        _decode_exactly_one_json(json.dumps(value, allow_nan=False))
        validate_schema(schema)
        _validate(value, schema)
    except (ValueError, TypeError) as exc:
        return ContractResult(False, error_kind="schema_invalid", error=str(exc))
    return ContractResult(True, value=value)


def validate_value(value: Any, schema_path: str | Path) -> ContractResult:
    """Validate an already-decoded value against a local supported schema."""
    try:
        schema = _decode_exactly_one_json(Path(schema_path).expanduser().read_text(encoding="utf-8"))
        if not isinstance(schema, dict):
            raise _SchemaError("schema root must be an object")
        return validate_document(value, schema)
    except (OSError, ValueError) as exc:
        return ContractResult(False, error_kind="schema_invalid", error=str(exc))
    return ContractResult(True, value=value)


def validate_output_contract(message: str | None, schema_path: str | Path, *, allow_prose_fence: bool = False) -> ContractResult:
    """Decode exactly one final JSON value, then validate its output schema."""
    if message is None:
        return ContractResult(False, error_kind="missing_output", error="no final answer was emitted")
    try:
        value = _decode_exactly_one_json(message, allow_prose_fence=allow_prose_fence)
    except ValueError as exc:
        return ContractResult(False, error_kind="invalid_json", error=str(exc))
    return validate_value(value, schema_path)
