"""Normalize per-call usage without treating missing measurements as zero."""

import math

FIELDS = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens",
          "reasoning_output_tokens", "duration_ms", "reported_cost_usd")


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def normalize_metrics(result):
    if isinstance(result.get("metrics"), dict):
        return {key: number(result["metrics"].get(key)) for key in FIELDS}
    usage = result.get("usage") or {}
    if not isinstance(usage, dict):
        usage = {}
    provider_cache = "cache_read_input_tokens" in usage or "cache_creation_input_tokens" in usage
    cached = number(usage.get("cache_read_input_tokens" if provider_cache else "cached_input_tokens"))
    written = number(usage.get("cache_creation_input_tokens" if provider_cache else "cache_write_input_tokens"))
    inputs = number(usage.get("input_tokens"))
    if provider_cache:
        inputs = inputs + cached + written if all(x is not None for x in (inputs, cached, written)) else None
    details = usage.get("output_tokens_details") or {}
    if not isinstance(details, dict):
        details = {}
    return dict(zip(FIELDS, (inputs, cached, written, number(usage.get("output_tokens")),
                            number(usage.get("reasoning_output_tokens", details.get("thinking_tokens"))),
                            number(result.get("duration_ms")), number(result.get("total_cost_usd")))))


def aggregate_metrics(calls):
    """Report partial measured sums and counts; no invented total for unknown calls."""
    rows = [normalize_metrics(call.get("receipt", {})) for call in calls]
    return {key: {"measured_sum": sum(row[key] for row in rows if row[key] is not None),
                  "measured_calls": sum(row[key] is not None for row in rows),
                  "unknown_calls": sum(row[key] is None for row in rows)} for key in FIELDS}
