#!/usr/bin/env python3
"""Read and resolve the collection's model routing configuration without dispatch."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parents[1] / "model-routing.json"

EFFORT_SCALING_VALUES = ("monotonic", "flat", "flat-above-high", "non-monotonic")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def config_digest(config: dict) -> str:
    encoded = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate configuration key: {key}")
        result[key] = value
    return result


def load_config(path: Path | str = CONFIG_PATH) -> dict:
    try:
        config = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot load model routing configuration {path}: {exc}") from exc
    validate_config(config)
    return config


def runner_efforts(runner: str, *, accepted: bool = False, config: dict | None = None) -> tuple[str, ...]:
    config = load_config() if config is None else config
    require(runner in config["runners"], f"Unknown runner: {runner}")
    entry = config["runners"][runner]
    if accepted and "accepted_efforts" in entry:
        return tuple(entry["accepted_efforts"])
    profile = entry.get("accepted_effort_profile", entry["effort_profile"]) if accepted else entry["effort_profile"]
    return tuple(config["effort_profiles"][profile])


def seat_models(runner: str, config: dict | None = None) -> dict[str, str]:
    config = load_config() if config is None else config
    return {seat: item["model"] for seat, item in config["models"].items() if item["runner"] == runner}


def model_aliases(runner: str, config: dict | None = None) -> dict[str, str]:
    config = load_config() if config is None else config
    return {
        alias: entry["model"]
        for seat, entry in config["models"].items() if entry["runner"] == runner
        for alias in [seat, entry["model"], *entry.get("aliases", [])]
    }


def default_model(runner: str, config: dict | None = None) -> str | None:
    config = load_config() if config is None else config
    entry = config["runners"][runner]
    seat = entry.get("default_seat")
    return config["models"][seat]["model"] if seat else entry.get("metadata_model")


def model_efforts(runner: str, config: dict | None = None) -> dict[str, tuple[str, ...]]:
    config = load_config() if config is None else config
    return {
        entry["model"]: tuple(config["effort_profiles"][entry["effort_profile"]])
        for entry in config["models"].values() if entry["runner"] == runner
    }


def validate_selection(runner: str, model: str, effort: str | None, config: dict | None = None) -> None:
    config = load_config() if config is None else config
    require(runner in config["runners"], f"Unknown runner: {runner}")
    adapter = config["runners"][runner]
    supported = model_efforts(runner, config).get(model)
    if supported is None:
        require(not adapter.get("known_model_required"), f"Model {model!r} has no known {runner} effort capability")
        supported = runner_efforts(runner, config=config)
    if adapter["effort_flag"] is None or supported == ():
        require(effort is None, f"{runner}/{model} cannot enforce a selected effort")
    else:
        require(effort in supported and effort in runner_efforts(runner, config=config), f"Effort {effort!r} is not supported by {runner}/{model}")


def resolve_role(selection: dict, config: dict) -> dict:
    require(isinstance(selection, dict), "Role selection must be an object")
    seat = selection.get("seat")
    require(isinstance(seat, str) and seat in config["models"], f"Unknown seat: {seat}")
    entry = config["models"][seat]
    effort = selection.get("effort")
    validate_selection(entry["runner"], entry["model"], effort, config)
    return dict(seat=seat, model=entry["model"], runner=entry["runner"], effort=effort)


def validate_config(config: Any) -> None:
    require(isinstance(config, dict) and config.get("schema_version") == 1, "Unsupported model routing schema")
    for key in ("effort_profiles", "runners", "models", "providers", "routes", "policy", "councils"):
        require(isinstance(config.get(key), dict) and bool(config[key]), f"Missing configuration object: {key}")
    levels = config.get("effort_levels")
    require(isinstance(levels, list) and all(isinstance(v, str) and v for v in levels), "Invalid effort levels")
    require(len(levels) == len(set(levels)), "Duplicate effort level")
    for name, values in config["effort_profiles"].items():
        require(isinstance(values, list) and all(v in levels for v in values), f"Invalid effort profile: {name}")
        require(len(values) == len(set(values)), f"Duplicate effort in {name}")
    aliases: dict[str, str] = {}
    for seat, model in config["models"].items():
        require(isinstance(model, dict) and isinstance(model.get("model"), str) and bool(model["model"]), f"Invalid model for {seat}")
        require(model.get("runner") in config["runners"], f"Invalid runner for {seat}")
        require(model.get("effort_profile") in config["effort_profiles"], f"Invalid effort profile for {seat}")
        require(isinstance(model.get("aliases", []), list), f"Invalid aliases for {seat}")
        for alias in [seat, model["model"], *model.get("aliases", [])]:
            require(isinstance(alias, str) and bool(alias), f"Invalid alias for {seat}")
            require(alias not in aliases or aliases[alias] == seat, f"Duplicate model alias: {alias}")
            aliases[alias] = seat
    for name, runner in config["runners"].items():
        require(isinstance(runner, dict), f"Invalid runner: {name}")
        require(runner.get("effort_profile") in config["effort_profiles"], f"Invalid effort profile for {name}")
        require(runner.get("accepted_effort_profile", runner["effort_profile"]) in config["effort_profiles"], f"Invalid accepted effort profile for {name}")
        require(all(v in levels for v in runner.get("accepted_efforts", [])), f"Invalid accepted effort for {name}")
        require("effort_flag" in runner and "default_effort" in runner, f"Missing effort controls for {name}")
        require(runner["effort_flag"] is None or (isinstance(runner["effort_flag"], str) and runner["effort_flag"].startswith("--")), f"Invalid effort flag for {name}")
        require(runner["effort_flag"] is None or bool(runner_efforts(name, config=config)), f"Empty effort support for {name}")
        default = runner.get("default_seat")
        require(default is None or (default in config["models"] and config["models"][default]["runner"] == name), f"Invalid default seat for {name}")
        require(runner["default_effort"] is None or runner["default_effort"] in runner_efforts(name, config=config), f"Invalid default effort for {name}")
        if default and runner["default_effort"] is not None:
            validate_selection(name, config["models"][default]["model"], runner["default_effort"], config)
        if "fallback_runner" in runner:
            require(runner["fallback_runner"] in config["runners"] and runner["fallback_runner"] != name, f"Invalid fallback runner for {name}")
        require(isinstance(runner.get("fallbacks", []), list), f"Invalid fallbacks for {name}")
        for fallback in runner.get("fallbacks", []):
            require(isinstance(fallback, dict), f"Invalid fallback for {name}")
            target, seat = fallback.get("runner"), fallback.get("seat")
            require(target in config["runners"] and target != name, f"Invalid fallback runner for {name}")
            require(seat is None or (seat in config["models"] and config["models"][seat]["runner"] == target), f"Invalid fallback seat for {name}")
        effort_aliases = runner.get("effort_aliases", {})
        require(isinstance(effort_aliases, dict), f"Invalid effort aliases for {name}")
        for source, target in effort_aliases.items():
            require(source in runner_efforts(name, accepted=True, config=config) and target in runner_efforts(name, config=config), f"Invalid effort alias for {name}")
    validate_routes(config)
    discovery = config.get("discovery")
    require(isinstance(discovery, list), "Missing discovery seats")
    seen = set()
    for spec in discovery:
        require(isinstance(spec, dict), "Invalid discovery entry")
        seat = spec.get("seat")
        require(seat in aliases and seat not in seen, f"Invalid discovery seat: {seat}")
        seen.add(seat)
    for name, seats in config.get("discovery_presets", {}).items():
        require(isinstance(seats, list) and bool(seats) and all(seat in seen for seat in seats), f"Invalid discovery preset: {name}")
    for name, council in config["councils"].items():
        require(
            isinstance(council, dict) and set(council) == {"openings", "organizer", "judges", "synthesis"},
            f"Invalid council: {name}",
        )
        require(isinstance(council["openings"], list) and len(council["openings"]) == 3, f"Council {name} requires three openings")
        require(isinstance(council["judges"], list) and len(council["judges"]) == 2, f"Council {name} requires two judges")
        for selection in [*council["openings"], council["organizer"], *council["judges"], council["synthesis"]]:
            resolve_role(selection, config)
        models = [resolve_role(selection, config)["model"] for selection in council["openings"]]
        require(len(models) == len(set(models)), f"Council {name} requires distinct opening models")
    for seat, model in config["models"].items():
        if "default_effort" in model:
            validate_selection(model["runner"], model["model"], model["default_effort"], config)
        if model["runner"] == "muse":
            require(seat == "muse-wonder-full" and model.get("optional_roles") == ["implementer"]
                    and model.get("model_verification") == "required", "Muse admission requires an optional implementer and exact receipt")
            subscription_privacy(config)
        if "capabilities" in model:
            capabilities = model["capabilities"]
            require(isinstance(capabilities, dict) and all(key in {"tools", "images"} and isinstance(value, bool) for key, value in capabilities.items()), f"Invalid capabilities for {seat}")
        if "effort_scaling" in model:
            require(model["effort_scaling"] in EFFORT_SCALING_VALUES, f"Invalid effort scaling for {seat}")
            evidence = model.get("effort_scaling_evidence")
            require(isinstance(evidence, str) and bool(evidence), f"Missing effort scaling evidence for {seat}")
    admission = config["policy"].get("seat_admission")
    if admission is not None:
        require(isinstance(admission, dict), "Invalid seat admission policy")
        require(admission.get("zdr_required") is True, "Seat admission must require zero data retention")
        require(isinstance(admission.get("rule"), str) and bool(admission["rule"]), "Missing seat admission rule")
        rejected = admission.get("rejected", [])
        require(isinstance(rejected, list), "Invalid seat admission rejections")
        for entry in rejected:
            require(isinstance(entry, dict) and isinstance(entry.get("model"), str) and bool(entry["model"]), "Invalid rejected seat entry")
            require(isinstance(entry.get("reason"), str) and bool(entry["reason"]), "Missing rejected seat reason")
            require(entry["model"] not in aliases, f"Rejected seat is still registered: {entry['model']}")


def resolve_council(name: str, *, config: dict | None = None) -> dict:
    """Resolve a council's default seats without dispatching calls."""
    config = load_config() if config is None else config
    require(name in config["councils"], f"Unknown council: {name}")
    result = {
        key: [resolve_role(selection, config) for selection in value] if isinstance(value, list)
        else resolve_role(value, config)
        for key, value in config["councils"][name].items()
    }
    result["council_name"] = name
    return result


def parse_pick(value: object) -> dict:
    """Read a route pick written as SEAT:EFFORT; runtime selects null effort."""
    require(isinstance(value, str), f"Invalid pick: {value!r}")
    seat, separator, effort = value.partition(":")
    require(bool(seat and separator and effort), f"Write a pick as SEAT:EFFORT: {value!r}")
    return {"seat": seat, "effort": None if effort == "runtime" else effort}


def validate_routes(config: dict) -> None:
    providers = config["providers"]
    for name, entry in providers.items():
        require(isinstance(entry, dict) and entry.get("runner") in config["runners"], f"Invalid runner for provider {name}")
        require(entry.get("cross") in providers and entry["cross"] != name, f"Invalid cross provider for {name}")
    default = config.get("default_provider")
    require(default in providers, "Invalid default provider")
    cross_roles = config.get("cross_provider_roles")
    require(isinstance(cross_roles, list) and all(isinstance(role, str) for role in cross_roles), "Invalid cross provider roles")
    validate_gateway_policy(config.get("gateway_policy"))
    for name, route in config["routes"].items():
        require(isinstance(route, dict) and isinstance(route.get("roles"), dict) and bool(route["roles"]), f"Missing roles for {name}")
        for field in ("purpose", "use_when"):
            require(isinstance(route.get(field), str) and bool(route[field]), f"Missing {field} for {name}")
        require(route.get("risk_route") in config["routes"], f"Invalid risk route for {name}")
        for role, picks in route["roles"].items():
            require(isinstance(picks, dict) and set(picks) <= set(providers), f"Unknown provider in {name}/{role}")
            require(default in picks and providers[default]["cross"] in picks, f"Missing default picks for {name}/{role}")
            for provider, pick in picks.items():
                resolved = resolve_role(parse_pick(pick), config)
                require(resolved["runner"] == providers[provider]["runner"], f"Pick {pick} does not run on {provider} in {name}/{role}")
    for name in config["routes"]:
        for provider in providers:
            for risk in config["policy"]["risk_levels"]:
                resolve_route(name, provider, risk=risk, config=config)


def validate_gateway_policy(policy: object) -> None:
    require(isinstance(policy, dict), "Missing gateway policy")
    require(set(policy) <= {"gateway", "zdr", "data_collection", "require_parameters", "only", "allow_fallbacks"}, "Unknown gateway control")
    require(policy.get("gateway") == "openrouter" and policy.get("zdr") is True and policy.get("data_collection") == "deny"
            and policy.get("require_parameters") is True, "Gateway policy must require strict privacy and parameter support")
    if "only" in policy:
        require(isinstance(policy["only"], list) and bool(policy["only"]) and all(isinstance(value, str) and value for value in policy["only"]), "Invalid provider allowlist")
    if "allow_fallbacks" in policy:
        require(isinstance(policy["allow_fallbacks"], bool), "Invalid provider fallback control")


def subscription_privacy(config: dict | None = None) -> dict:
    """Return scoped user evidence without asserting independent verification."""
    config = load_config() if config is None else config
    privacy = config["models"]["muse-wonder-full"].get("privacy", {})
    require(privacy.get("gateway") == "meta-subscription" and privacy.get("zdr_available") is True
            and privacy.get("evidence_type") == "user_confirmed"
            and privacy.get("scope") == "current_user_subscription"
            and privacy.get("independently_verified") is False
            and isinstance(privacy.get("confirmed_at"), str) and bool(privacy["confirmed_at"])
            and isinstance(privacy.get("reference"), str) and bool(privacy["reference"]),
            "Muse requires account scoped subscription ZDR confirmation from the user")
    return copy.deepcopy(privacy)


def finish_role(role: str, selection: dict, provider: str | None, config: dict) -> dict:
    """Resolve one role and attach the controls its runner requires."""
    result = resolve_role(selection, config)
    entry = config["models"][result["seat"]]
    allowed = entry.get("optional_roles")
    require(allowed is None or role in allowed, f"Seat {result['seat']} is not admitted for role {role}")
    result["provider"] = provider
    result["effort_control"] = "runtime" if result["effort"] is None else "runner"
    if result["runner"] == "pi":
        policy = config["gateway_policy"]
        privacy = entry.get("privacy", {})
        require(entry.get("capabilities", {}).get("tools") is True, f"Seat {result['seat']} lacks recorded tools support")
        require(privacy.get("gateway") == policy["gateway"] and privacy.get("zdr_available") is True, f"Seat {result['seat']} has no verified strict privacy route")
        result["provider_routing"] = copy.deepcopy(policy)
    if result["runner"] == "muse":
        result.update(privacy_evidence=subscription_privacy(config), model_verification="required")
    return result


def override_selection(base: dict, override: dict, config: dict) -> dict:
    require(isinstance(override, dict) and bool(override) and set(override) <= {"seat", "effort"}, "Role overrides accept only seat and effort")
    selection = dict(base)
    if "seat" in override and override["seat"] != base["seat"]:
        seat = override["seat"]
        require(isinstance(seat, str) and seat in config["models"], f"Unknown seat: {seat}")
        entry = config["models"][seat]
        require("effort" in override or "default_effort" in entry, f"Select an explicit effort for {seat}")
        selection = {"seat": seat, "effort": entry.get("default_effort")}
    selection.update(override)
    return selection


def seat_provider(seat: str, config: dict) -> str | None:
    runner = config["models"][seat]["runner"]
    return next((name for name, entry in config["providers"].items() if entry["runner"] == runner), None)


def resolve_route(name: str, provider: str | None = None, *, risk: str = "normal",
                  role_overrides: dict | None = None, config: dict | None = None) -> dict:
    """Resolve a route to one exact model and effort per role, before approval.

    A role runs on the given provider. A role in cross_provider_roles runs on that
    provider's cross provider, so a reviewer never shares its author's provider.
    A provider with no pick for a role uses the default provider's pick.
    """
    config = load_config() if config is None else config
    provider = config["default_provider"] if provider is None else provider
    require(provider in config["providers"], f"Unknown provider: {provider}")
    require(name in config["routes"], f"Unknown task route: {name}")
    require(risk in config["policy"]["risk_levels"], f"Unknown risk level: {risk}")
    selected = config["routes"][name]["risk_route"] if risk == "high" else name
    route = config["routes"][selected]
    overrides = {} if role_overrides is None else role_overrides
    require(isinstance(overrides, dict) and set(overrides) <= set(route["roles"]), f"Unknown role override for {selected}")
    cross = config["providers"][provider]["cross"]
    roles = {}
    for role, picks in route["roles"].items():
        wanted = cross if role in config["cross_provider_roles"] else provider
        if wanted not in picks:
            wanted = config["default_provider"]
            if role in config["cross_provider_roles"] and wanted == provider:
                wanted = cross
        selection = parse_pick(picks[wanted])
        if role in overrides:
            selection = override_selection(selection, overrides[role], config)
            wanted = seat_provider(selection["seat"], config)
        roles[role] = finish_role(role, selection, wanted, config)
    for left, right in (("implementer", "reviewer"), ("interviewer", "respondent")):
        if left in roles and right in roles:
            require(roles[left]["model"] != roles[right]["model"], "Independent roles must use distinct models")
    return dict(requested_route=name, route=selected, risk=risk, provider=provider,
                config_digest=config_digest(config), evidence=config["evidence"],
                purpose=route["purpose"], use_when=route["use_when"], roles=roles)


def list_routes(config: dict) -> dict:
    return {name: {key: route[key] for key in ("purpose", "use_when", "risk_route")} | {"roles": list(route["roles"])}
            for name, route in config["routes"].items()}


def parse_role_overrides(values: list[str]) -> dict:
    result = {}
    for value in values:
        role, separator, choice = value.partition("=")
        seat, effort_separator, effort = choice.partition(":")
        require(bool(separator and role and seat), "Use --role ROLE=SEAT[:EFFORT]")
        require(role not in result, f"Duplicate role override: {role}")
        selection = {"seat": seat}
        if effort_separator:
            require(bool(effort), f"Missing effort for {role}")
            selection["effort"] = None if effort == "runtime" else effort
        result[role] = selection
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH, help="Configuration to inspect; never dispatches a model")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="Check identities, capabilities, routes, and council references")
    commands.add_parser("show", help="Print the full configuration")
    commands.add_parser("routes", help="List each route with its purpose and when to use it")
    resolve = commands.add_parser("resolve", help="Resolve a route into one exact model and effort per role")
    resolve.add_argument("route")
    resolve.add_argument("--provider", help="Provider the work runs on: the current host. Omitted uses the default provider")
    resolve.add_argument("--role", action="append", default=[], metavar="ROLE=SEAT[:EFFORT]", help="Change one role; use runtime for a model without effort control")
    resolve.add_argument("--risk", default="normal")
    council = commands.add_parser("council", help="Resolve a council's default seats without starting any calls")
    council.add_argument("name")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        if args.command == "validate":
            output = dict(valid=True, models=len(config["models"]), routes=len(config["routes"]), config_digest=config_digest(config))
        elif args.command == "resolve":
            output = resolve_route(args.route, args.provider, risk=args.risk,
                                   role_overrides=parse_role_overrides(args.role), config=config)
        elif args.command == "routes":
            output = list_routes(config)
        elif args.command == "council":
            output = resolve_council(args.name, config=config)
        else:
            output = config
        print(json.dumps(output, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Model routing error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
