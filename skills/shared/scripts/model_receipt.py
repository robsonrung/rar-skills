"""Keep runner model provenance truthful.

Wrappers can always report what the caller requested and what they forwarded.
They must not present either value as the model that served a run unless the
native CLI or provider response includes that model identifier.
"""

from __future__ import annotations

from typing import Any


VERIFIED_SOURCES = frozenset({"native_event", "provider_event"})


def _model_id(value: object) -> str | None:
    """Return a nonempty model id or None."""
    return value.strip() if isinstance(value, str) and value.strip() and value.strip() != "<synthetic>" else None


def attach_claude_model_receipt(
    result: dict[str, Any], events: list[dict[str, Any]], requested_model: str | None,
) -> dict[str, Any]:
    """Use primary assistant events as serving evidence; keep usage labels separate."""
    primary, auxiliary = set(), set()
    usage = {}
    for event in events:
        message = event.get("message")
        if event.get("type") == "assistant" and isinstance(message, dict):
            model = _model_id(message.get("model"))
            if model:
                target = auxiliary if event.get("parent_tool_use_id") else primary
                target.add(model)
        if event.get("type") == "result" and isinstance(event.get("modelUsage"), dict):
            usage = event["modelUsage"]
    result["primary_model_ids"] = sorted(primary)
    result["auxiliary_model_ids"] = sorted(auxiliary)
    # This breakdown is already included in the terminal total, not an extra cost.
    result["model_usage"] = usage
    result["auxiliary_model_usage"] = {key: value for key, value in usage.items() if key not in primary}
    result.pop("native_model_id", None)
    result.pop("model_receipt", None)
    if len(primary) == 1:
        result["native_model_id"] = next(iter(primary))
    requested = _model_id(requested_model)
    # An alias does not identify an exact serving version.
    exact_request = bool(requested and requested.startswith("claude-"))
    result["model_matches_requested"] = (
        next(iter(primary)) == requested if len(primary) == 1 and exact_request else None
    )
    result["model_identity_error"] = (
        "Multiple primary serving models observed." if len(primary) > 1 else
        "Serving model differs from the requested model." if result["model_matches_requested"] is False else None
    )
    return attach_model_receipt(result, requested_model, observed_source="native_event")


def attach_model_receipt(
    result: dict[str, Any],
    requested_model: str | None,
    *,
    observed_source: str = "not_observed",
) -> dict[str, Any]:
    """Add requested, configured, and observed model fields to an envelope.

    `native_model_id` is the only generic proof available to wrappers. A
    wrapper may use ``provider_event`` when it parsed the same information from
    a provider result instead. Existing receipt data is preserved only when it
    is already marked verified and carries an observed model id.
    """
    requested = _model_id(result.get("requested_model")) or _model_id(requested_model)
    if requested is not None:
        result["requested_model"] = requested
    else:
        result["requested_model"] = None

    configured = _model_id(result.get("configured_model"))
    if configured is None and result.get("model_forwarded") is not False:
        configured = _model_id(result.get("model"))
    result["configured_model"] = configured

    native_model = _model_id(result.get("native_model_id"))
    previous = result.get("model_receipt")
    if isinstance(previous, dict):
        if previous.get("status") == "verified" and previous.get("source") in VERIFIED_SOURCES:
            previous_model = _model_id(previous.get("observed_model"))
            if previous_model is not None and native_model in (None, previous_model):
                native_model = previous_model
                observed_source = str(previous["source"])

    if native_model is not None and observed_source in VERIFIED_SOURCES:
        result["effective_model"] = native_model
        result["model_receipt"] = {
            "status": "verified",
            "source": observed_source,
            "observed_model": native_model,
        }
        return result

    # `effective_model` means an observed serving model. Do not fill it from a
    # requested or configured value: a CLI can accept a model flag yet route a
    # run elsewhere, and some CLIs expose no serving identifier at all.
    result["effective_model"] = None
    result["model_receipt"] = {
        "status": "unverified",
        "source": "configured_model" if configured is not None else "not_observed",
        "observed_model": None,
    }
    return result
