"""Separate role context from dispatch records and measure adapter text."""
from contextvars import ContextVar
from functools import wraps
import hashlib
import inspect
import json

from context_packet import ContextBudgetError, measure_rendered

BOOKKEEPING_FIELDS = frozenset({
    "execution_provenance", "input_measurement", "adapter_input_measurement",
    "input_revision", "route_digest", "call_id", "request_receipt", "request_receipts",
    "provider_policy_receipt", "continuation_proof",
})

_measurement = ContextVar("adapter_input_measurement", default=None)
_metadata = ContextVar("dispatch_metadata", default=None)


def prompt_context(metadata_json):
    """Preserve legacy user context; explicit context excludes envelope-only fields."""
    if not metadata_json:
        return None
    try:
        value = json.loads(metadata_json)
    except (TypeError, ValueError):
        return metadata_json
    if isinstance(value, dict) and "prompt_context" in value:
        value = value["prompt_context"]
        return None if value is None or value == {} else json.dumps(value, ensure_ascii=False)
    if isinstance(value, dict):
        context = {key: item for key, item in value.items() if key not in BOOKKEEPING_FIELDS}
        return json.dumps(context, ensure_ascii=False) if context else None
    return metadata_json


def record_input(text):
    encoded = text.encode("utf-8")
    measurement = {"scope": "adapter_rendered_input", "utf8_bytes": len(encoded),
                   "sha256": hashlib.sha256(encoded).hexdigest(), "token_count": None,
                   "unmeasured": ["host_instructions", "tool_schemas", "role_history", "later_reads", "images"]}
    _measurement.set(measurement)
    metadata = _metadata.get()
    budget = metadata.get("input_measurement") if isinstance(metadata, dict) else None
    if isinstance(budget, dict):
        limit = {key: budget[key] for key in ("max_bytes", "reason") if key in budget}
        measure_rendered(text, limit)
    return measurement


def measured_run(function):
    """Attach complete text measurement and dispatch data on success or failure."""
    @wraps(function)
    def run(*args, **kwargs):
        implementation = function.__globals__.get("_" + function.__name__) or function
        values = inspect.signature(implementation).bind_partial(*args, **kwargs).arguments
        raw = values.get("metadata_json")
        try:
            metadata = json.loads(raw) if raw else None
        except (TypeError, ValueError):
            metadata = None
        token = _metadata.set(metadata)
        measured = _measurement.set(None)
        try:
            try:
                result = function(*args, **kwargs)
            except ContextBudgetError as error:
                result = function.__globals__["normalize_envelope"](
                    {"success": False, "return_code": -3, "stdout": "", "stderr": str(error),
                     "status": "invalid_input", "print_invocation_started": False},
                    requested_runner=function.__name__.removeprefix("run_"),
                    requested_model=values.get("model"))
            if isinstance(metadata, dict):
                result["dispatch_metadata"] = metadata
            if _measurement.get() is not None:
                result.setdefault("adapter_input_measurement", _measurement.get())
            return result
        finally:
            _metadata.reset(token)
            _measurement.reset(measured)
    return run
