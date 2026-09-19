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
    if adapter["effort_flag"] is None:
        require(effort is None, f"{runner} cannot enforce a selected effort")
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
    resolve.add_argument("--family", default="gpt")
    resolve.add_argument("--risk", default="normal")
    council = commands.add_parser("council", help="Resolve a council preview without starting any calls")
    council.add_argument("name")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        if args.command == "validate":
            output = dict(valid=True, models=len(config["models"]), routes=len(config["routes"]), config_digest=config_digest(config))
        elif args.command == "resolve":
            output = resolve_route(args.route, args.family, risk=args.risk, config=config)
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
