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
    for key in ("effort_profiles", "runners", "models", "routes", "policy", "councils"):
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
    for name, route in config["routes"].items():
        require(isinstance(route, dict) and isinstance(route.get("families"), dict) and bool(route["families"]), f"Missing route families for {name}")
        require(route.get("risk_route") in config["routes"], f"Invalid risk route for {name}")
        for family, roles in route["families"].items():
            require(isinstance(roles, dict) and bool(roles), f"Empty roles for {name}/{family}")
            resolved = {key: resolve_role(value, config) for key, value in roles.items()}
            for left, right in (("implementer", "reviewer"), ("interviewer", "respondent")):
                if left in resolved and right in resolved:
                    require(resolved[left]["model"] != resolved[right]["model"], f"Independent roles share a model in {name}/{family}")
            require(family in config["routes"][route["risk_route"]]["families"], f"Missing risk family for {name}/{family}")
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
        for ref in [*council["openings"], council["organizer"], *council["judges"], council["synthesis"]]:
            resolve_reference(ref, config)
        models = [resolve_reference(ref, config)["model"] for ref in council["openings"]]
        require(len(models) >= 3 and len(models) == len(set(models)), f"Council {name} requires distinct opening models")
    for seat, model in config["models"].items():
        if "default_effort" in model:
            validate_selection(model["runner"], model["model"], model["default_effort"], config)
        if "capabilities" in model:
            capabilities = model["capabilities"]
            require(isinstance(capabilities, dict) and all(key in {"tools", "images"} and isinstance(value, bool) for key, value in capabilities.items()), f"Invalid capabilities for {seat}")
    if any(key in config for key in ("profiles", "default_profile", "profile_policy")):
        validate_profiles(config)


def resolve_reference(reference: dict, config: dict) -> dict:
    try:
        selection = config["routes"][reference["route"]]["families"][reference["family"]][reference["role"]]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Invalid route reference: {reference}") from exc
    return resolve_role(selection, config)


def resolve_route(name: str, family: str, *, risk: str = "normal", config: dict | None = None) -> dict:
    config = load_config() if config is None else config
    require(name in config["routes"], f"Unknown task route: {name}")
    require(risk in config["policy"]["risk_levels"], f"Unknown risk level: {risk}")
    selected = config["routes"][name]["risk_route"] if risk == "high" else name
    route = config["routes"][selected]
    require(family in route["families"], f"Unsupported family {family!r} for {selected}")
    return dict(requested_route=name, route=selected, family=family, risk=risk,
                config_digest=config_digest(config), evidence=config["evidence"],
                conditions=route.get("conditions", []),
                roles={key: resolve_role(value, config) for key, value in route["families"][family].items()})


def profile_family(name: str, profile: dict) -> str:
    return profile.get("route_families", {}).get(name, profile["family"])


def validate_profiles(config: dict) -> None:
    profiles = config.get("profiles")
    require(isinstance(profiles, dict) and bool(profiles), "Missing profiles")
    require(config.get("default_profile") in profiles, "Invalid default profile")
    policy = config.get("profile_policy")
    require(isinstance(policy, dict), "Missing profile policy")
    provider = policy.get("provider_routing")
    require(isinstance(provider, dict), "Missing profile provider policy")
    require(set(provider) <= {"gateway", "zdr", "data_collection", "require_parameters", "only", "allow_fallbacks"}, "Unknown profile provider control")
    require(provider.get("gateway") == "openrouter" and provider.get("zdr") is True and provider.get("data_collection") == "deny" and provider.get("require_parameters") is True, "Profile provider policy must require strict privacy and parameter support")
    if "only" in provider:
        require(isinstance(provider["only"], list) and bool(provider["only"]) and all(isinstance(value, str) and value for value in provider["only"]), "Invalid provider allowlist")
    if "allow_fallbacks" in provider:
        require(isinstance(provider["allow_fallbacks"], bool), "Invalid provider fallback control")
    direct = policy.get("direct_execution_routes")
    require(isinstance(direct, list) and all(name in config["routes"] for name in direct), "Invalid direct execution routes")
    for name, profile in profiles.items():
        require(isinstance(profile, dict) and isinstance(profile.get("label"), str) and isinstance(profile.get("family"), str), f"Invalid profile: {name}")
        for field in ("route_families", "role_requirements", "role_candidates", "route_conditions"):
            mapping = profile.get(field, {})
            require(isinstance(mapping, dict) and all(route in config["routes"] for route in mapping), f"Invalid {field} for profile {name}")
        for route, conditions in profile.get("route_conditions", {}).items():
            require(isinstance(conditions, list) and all(isinstance(value, str) and value for value in conditions), f"Invalid conditions for {name}/{route}")
        for field in ("role_requirements", "role_candidates"):
            for route, roles in profile.get(field, {}).items():
                selections = config["routes"][route]["families"].get(profile_family(route, profile), {})
                require(isinstance(roles, dict) and all(role in selections for role in roles), f"Unknown role in {name}/{route}/{field}")
                for role, values in roles.items():
                    require(isinstance(values, list) and bool(values) and all(isinstance(value, str) for value in values), f"Invalid {field} for {name}/{route}/{role}")
                    allowed = {"tools", "images"} if field == "role_requirements" else config["models"]
                    require(all(value in allowed for value in values), f"Unknown {field} for {name}/{route}/{role}")
                    if field == "role_candidates":
                        for seat in values:
                            require("default_effort" in config["models"][seat], f"Missing candidate effort for {seat}")
        for route in config["routes"]:
            for risk in config["policy"]["risk_levels"]:
                resolve_profile(route, name, risk=risk, config=config)


def profile_role(selection: dict, provider_routing: dict, requirements: list[str], config: dict) -> dict:
    result = resolve_role(selection, config)
    entry = config["models"][result["seat"]]
    required = list(dict.fromkeys([*requirements, *(["tools"] if result["runner"] == "pi" else [])]))
    capabilities = entry.get("capabilities", {})
    for capability in required:
        require(capabilities.get(capability) is True, f"Seat {result['seat']} lacks recorded {capability} support")
    if result["runner"] == "pi":
        privacy = entry.get("privacy", {})
        require(privacy.get("gateway") == provider_routing["gateway"] and privacy.get("zdr_available") is True, f"Seat {result['seat']} has no verified strict privacy route")
        result["provider_routing"] = copy.deepcopy(provider_routing)
    result["effort_control"] = "runtime" if result["effort"] is None else "runner"
    if capabilities:
        result["capabilities"] = copy.deepcopy(capabilities)
    if required:
        result["required_capabilities"] = required
    return result


def override_selection(base: dict, override: dict, config: dict) -> dict:
    require(isinstance(override, dict) and bool(override) and set(override) <= {"seat", "effort"}, "Role overrides accept only seat and effort")
    selection = {key: base[key] for key in ("seat", "effort")}
    if "seat" in override and override["seat"] != base["seat"]:
        seat = override["seat"]
        require(isinstance(seat, str) and seat in config["models"], f"Unknown seat: {seat}")
        entry = config["models"][seat]
        require("effort" in override or "default_effort" in entry, f"Select an explicit effort for {seat}")
        selection = {"seat": seat, "effort": entry.get("default_effort")}
    selection.update(override)
    return selection


def resolve_profile(name: str, profile: str | None = None, *, local_profile: str | None = None,
                    role_overrides: dict | None = None, risk: str = "normal", config: dict | None = None) -> dict:
    """Build a preview before approval. Saved route snapshots bypass this function."""
    config = load_config() if config is None else config
    selected_profile = profile if profile is not None else local_profile if local_profile is not None else config.get("default_profile")
    require(isinstance(selected_profile, str) and selected_profile in config.get("profiles", {}), f"Unknown profile: {selected_profile}")
    entry = config["profiles"][selected_profile]
    policy = config["profile_policy"]
    require(name in config["routes"], f"Unknown task route: {name}")
    require(risk in config["policy"]["risk_levels"], f"Unknown risk level: {risk}")
    direct = name in policy["direct_execution_routes"]
    if direct:
        result = dict(requested_route=name, route=name, family=profile_family(name, entry),
                      config_digest=config_digest(config), evidence=config["evidence"],
                      conditions=copy.deepcopy(config["routes"][name].get("conditions", [])))
    else:
        result = resolve_route(name, profile_family(name, entry), risk=risk, config=config)
    result.update(profile=selected_profile, profile_label=entry["label"], risk=risk,
                  selection_source="explicit" if profile is not None else "local" if local_profile is not None else "central",
                  execution="repository-commands" if direct else "model-roles")
    overrides = {} if role_overrides is None else role_overrides
    require(isinstance(overrides, dict), "Role overrides must be an object")
    if direct:
        require(not overrides, f"{name} runs repository commands and accepts no model overrides")
        result.update(roles={}, alternatives={})
        return result
    require(set(overrides) <= set(result["roles"]), f"Unknown role override for {result['route']}")
    requirements = entry.get("role_requirements", {}).get(result["route"], {})
    result["roles"] = {
        role: profile_role(override_selection(selection, overrides[role], config) if role in overrides else selection,
                           policy["provider_routing"], requirements.get(role, []), config)
        for role, selection in result["roles"].items()
    }
    for left, right in (("implementer", "reviewer"), ("interviewer", "respondent")):
        if left in result["roles"] and right in result["roles"]:
            require(result["roles"][left]["model"] != result["roles"][right]["model"], "Independent roles must use distinct models")
    result["conditions"] = [*result["conditions"], *entry.get("route_conditions", {}).get(result["route"], [])]
    result["alternatives"] = {}
    for role, seats in entry.get("role_candidates", {}).get(result["route"], {}).items():
        eligible = []
        for seat in seats:
            selection = {"seat": seat, "effort": config["models"][seat]["default_effort"]}
            try:
                candidate = profile_role(selection, policy["provider_routing"], requirements.get(role, []), config)
            except ValueError:
                continue
            other_models = {value["model"] for other, value in result["roles"].items() if other != role}
            if candidate["model"] not in other_models:
                eligible.append(candidate)
        result["alternatives"][role] = eligible
    return result


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


def resolve_panel_providers(panel: dict, config: dict | None = None) -> dict:
    """Expand semantic references; leave explicit approved snapshots unchanged."""
    config = load_config() if config is None else config
    result = copy.deepcopy(panel)
    used_reference = False
    for name, provider in result.get("providers", {}).items():
        if "route" not in provider:
            continue
        used_reference = True
        for key in ("model", "effort", "runner", "provider", "transport", "effort_control", "effort_flag"):
            require(key not in provider, f"Panel provider {name} must not override resolved {key}")
        for arg in provider.get("runner_args", []):
            arg = str(arg)
            override = arg.split("=", 1)[0] in {"--model", "-m", "--effort", "-e", "--thinking", "--seat"}
            override = override or (arg.startswith(("-m", "-e")) and not arg.startswith("--"))
            require(not override, f"Panel provider {name} must not override its route in runner_args")
        selection = resolve_reference(dict(route=provider["route"], family=provider.get("family"), role=provider.get("route_role")), config)
        provider.update(selection)
        provider["provider"] = config["runners"][selection["runner"]]["provider"]
        provider["effort_flag"] = config["runners"][selection["runner"]]["effort_flag"]
        native = provider.get("kind") in {"native", "native_codex"}
        provider["effort_control"] = "native" if native else ("runner" if config["runners"][selection["runner"]]["effort_flag"] else "runtime")
        provider["transport"] = "native" if native else f"{selection['runner']}-runner"
    if used_reference:
        result["model_routing_digest"] = config_digest(config)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH, help="Configuration to inspect; never dispatches a model")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="Check identities, capabilities, routes, and council references")
    commands.add_parser("show", help="Print the full configuration")
    resolve = commands.add_parser("resolve", help="Resolve a task into exact role selections")
    resolve.add_argument("route")
    selection = resolve.add_mutually_exclusive_group()
    selection.add_argument("--family", help="Legacy family; defaults to gpt without a profile")
    selection.add_argument("--profile", help="Preview profile; use default for the configured preference")
    resolve.add_argument("--local-profile", help="Local preview preference, below an explicit profile")
    resolve.add_argument("--role", action="append", default=[], metavar="ROLE=SEAT[:EFFORT]", help="Change one preview role; use runtime for a model without effort control")
    resolve.add_argument("--risk", default="normal")
    council = commands.add_parser("council", help="Resolve a council preview without starting any calls")
    council.add_argument("name")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        if args.command == "validate":
            output = dict(valid=True, models=len(config["models"]), routes=len(config["routes"]), config_digest=config_digest(config))
        elif args.command == "resolve":
            use_profile = args.profile is not None or args.local_profile is not None
            require(not (args.family is not None and use_profile), "Select either a family or a profile")
            require(use_profile or not args.role, "Role overrides require a profile")
            if use_profile:
                output = resolve_profile(args.route, None if args.profile == "default" else args.profile,
                                         local_profile=args.local_profile, role_overrides=parse_role_overrides(args.role),
                                         risk=args.risk, config=config)
            else:
                output = resolve_route(args.route, args.family or "gpt", risk=args.risk, config=config)
        elif args.command == "council":
            require(args.name in config["councils"], f"Unknown council: {args.name}")
            output = {key: [resolve_reference(ref, config) for ref in value] if isinstance(value, list) else resolve_reference(value, config) for key, value in config["councils"][args.name].items()}
        else:
            output = config
        print(json.dumps(output, indent=2))
        return 0
    except (ValueError, KeyError, TypeError) as exc:
        print(f"Model routing error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
