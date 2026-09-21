"""Validate request routing policy and compute its immutable identity."""

import hashlib
import json


def validate_provider_routing(policy: object) -> None:
    if not isinstance(policy, dict):
        raise ValueError("Provider routing must be an object")
    required = {"gateway", "zdr", "data_collection", "require_parameters"}
    if not required <= policy.keys() or policy.keys() - required - {"only", "allow_fallbacks"}:
        raise ValueError("Provider routing has missing or unsupported fields")
    if policy["gateway"] != "openrouter":
        raise ValueError("Strict provider routing requires the openrouter gateway")
    if policy["zdr"] is not True or policy["data_collection"] != "deny" or policy["require_parameters"] is not True:
        raise ValueError("Provider routing requires ZDR, denied collection, and supported parameters")
    if "only" in policy:
        providers = policy["only"]
        if (not isinstance(providers, list) or not providers
                or any(not isinstance(p, str) or not p.strip() or p != p.strip() for p in providers)
                or len(providers) != len(set(providers))):
            raise ValueError("Provider allowlist requires unique nonempty provider ids")
    if "allow_fallbacks" in policy and type(policy["allow_fallbacks"]) is not bool:
        raise ValueError("Provider allow_fallbacks must be boolean")


def provider_policy_digest(policy: dict) -> str:
    validate_provider_routing(policy)
    canonical = json.dumps(policy, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_provider_policy_receipt(receipt: object, policy: dict) -> None:
    if (not isinstance(receipt, dict) or receipt.get("status") != "enforced"
            or receipt.get("gateway") != policy["gateway"]
            or receipt.get("policy_sha256") != provider_policy_digest(policy)
            or type(receipt.get("request_count")) is not int or receipt["request_count"] < 1):
        raise ValueError("Missing or mismatched provider policy receipt")


def provider_receipt_error(policy: dict | None, result: object) -> str | None:
    """Check a full runner result before accepting it into the run ledger."""
    if policy is None:
        return None
    try:
        validate_provider_routing(policy)
        if not isinstance(result, dict):
            raise ValueError("Missing runner result for provider policy receipt")
        validate_provider_policy_receipt(result.get("provider_policy_receipt"), policy)
    except ValueError as exc:
        return str(exc)
    return None
