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
    return value.strip() if isinstance(value, str) and value.strip() else None


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
    if native_model is None and isinstance(previous, dict):
        if previous.get("status") == "verified" and previous.get("source") in VERIFIED_SOURCES:
            native_model = _model_id(previous.get("observed_model"))
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
