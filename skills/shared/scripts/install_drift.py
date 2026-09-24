#!/usr/bin/env python3
"""Compare source and installed routing data without installing or dispatching."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from skill_paths import runner_script

from model_routing import config_digest, load_config, unique_object, validate_selection
from runner_preflight import file_evidence


def shared_root(root: Path | str) -> Path:
    root = Path(root).expanduser().absolute()
    if (root / "skills" / "shared").is_dir():
        return root / "skills" / "shared"
    return root / "shared"


def verify_route(approved: dict, config: dict) -> dict:
    """Compare exact approved fields; never re-resolve or mutate the approved route."""
    reasons = []
    digest = approved.get("config_digest", approved.get("model_routing_digest"))
    if digest is not None and digest != config_digest(config):
        reasons.append("Approved configuration digest differs from the loaded configuration.")
    roles = approved.get("roles")
    if not isinstance(roles, dict) or not roles:
        return {"blocked": True, "reasons": ["Approved route must contain exact roles."]}
    for name, role in roles.items():
        if not isinstance(role, dict) or not all(key in role for key in ("seat", "model", "runner", "effort")):
            reasons.append(f"Role {name} lacks an exact seat, model, runner, or effort.")
            continue
        entry = config["models"].get(role["seat"])
        if entry is None or (role["model"], role["runner"]) != (entry["model"], entry["runner"]):
            reasons.append(f"Role {name} differs from the loaded seat mapping.")
            continue
        try:
            validate_selection(role["runner"], role["model"], role["effort"], config)
        except ValueError as exc:
            reasons.append(f"Role {name}: {exc}")
        if "provider_routing" in role:
            current = config.get("profile_policy", {}).get("provider_routing")
            if role["provider_routing"] != current:
                reasons.append(f"Role {name} provider policy differs from the loaded policy.")
    return {"blocked": bool(reasons), "reasons": reasons}


def compare_install(source_root: Path | str, installed_root: Path | str, *,
                    seat: str | None = None, effort: str | None = None,
                    approved_route: dict | None = None) -> dict:
    roots = {"source": shared_root(source_root), "installed": shared_root(installed_root)}
    evidence = {name: {filename: file_evidence(root / filename) for filename in (
        "model-routing.json", "runner-compatibility.json",
    )} for name, root in roots.items()}
    reasons = []
    configs = {}
    for name, root in roots.items():
        try:
            configs[name] = load_config(root / "model-routing.json")
            evidence[name]["model-routing.json"]["config_digest"] = config_digest(configs[name])
        except (ValueError, KeyError, TypeError) as exc:
            reasons.append(f"Cannot validate {name} routing configuration: {exc}")
    for filename in ("model-routing.json", "runner-compatibility.json"):
        left, right = (evidence[name][filename]["sha256"] for name in roots)
        if left is None or right is None:
            reasons.append(f"Missing or unreadable {filename}.")
        elif left != right:
            reasons.append(f"Installed {filename} differs from source.")
    route = approved_route
    if seat is not None:
        if approved_route is not None:
            reasons.append("Choose a seat or an approved route, not both.")
        elif "source" in configs:
            entry = configs["source"]["models"].get(seat)
            if entry is None:
                reasons.append(f"Unknown source seat: {seat}")
            else:
                route = {"roles": {"selected": {"seat": seat, "model": entry["model"],
                                               "runner": entry["runner"], "effort": effort}}}
    route_checks = {}
    if route is not None:
        for name, config in configs.items():
            route_checks[name] = verify_route(route, config)
            reasons.extend(f"{name}: {reason}" for reason in route_checks[name]["reasons"])
    return {"schema_version": 1, "blocked": bool(reasons), "reasons": reasons,
            "evidence": evidence, "route_checks": route_checks}


MANIFEST_NAME = ".rar-skills-install.json"
CRITICAL_FILES = (
    "shared/model-routing.json", "shared/runner-compatibility.json",
    "shared/scripts/model_routing.py", "shared/scripts/runner_preflight.py",
    "shared/scripts/preflight_cache.py", "shared/scripts/discover_runners.py",
    "shared/scripts/install_drift.py", "shared/scripts/model_receipt.py",
    "claude-runner/scripts/run_claude.py",
)


def critical_path(root: Path | str, relative: str) -> Path:
    skills = shared_root(root).parent
    if relative == "claude-runner/scripts/run_claude.py":
        return runner_script("claude", root=skills)
    return skills / relative


def write_manifest(source_root: Path | str, installed_root: Path | str) -> Path:
    """Called by the installer after copying/linking. Store outside symlinked shared/."""
    files = {}
    for relative in CRITICAL_FILES:
        source = file_evidence(critical_path(source_root, relative))
        installed = file_evidence(critical_path(installed_root, relative))
        if source["sha256"] is None or installed["sha256"] != source["sha256"]:
            raise ValueError(f"Cannot record an install with missing or changed file: {relative}")
        files[relative] = {"source_path": source["path"], "sha256": source["sha256"]}
    manifest = {"schema_version": 1, "source_root": str(Path(source_root).absolute()), "files": files}
    path = shared_root(installed_root).parent / MANIFEST_NAME
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def check_loaded_install(installed_root: Path | str | None = None, *,
                         source_root: Path | str | None = None,
                         approved_route: dict | None = None) -> dict:
    """Read provenance beside the loaded tree; never search other installations.

    Without a manifest, provenance is unknown. An explicit source comparison or
    exact approved route can still prove a mismatch. This never updates a route.
    """
    installed_root = installed_root or Path(__file__).absolute().parents[2]
    path = shared_root(installed_root).parent / MANIFEST_NAME
    report = {"blocked": False, "status": "unknown", "reasons": [],
              "evidence": {"manifest": file_evidence(path)}, "source_status": "unknown"}
    if path.exists():
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
            if not isinstance(manifest, dict) or manifest.get("schema_version") != 1 or not isinstance(manifest.get("files"), dict) or set(manifest["files"]) != set(CRITICAL_FILES):
                raise ValueError("Unsupported or incomplete install manifest")
            source_available = True
            files = {}
            for relative in CRITICAL_FILES:
                saved = manifest["files"][relative]
                if not isinstance(saved, dict) or not isinstance(saved.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", saved["sha256"]):
                    raise ValueError("Invalid manifest digest")
                loaded = file_evidence(critical_path(installed_root, relative))
                source = file_evidence(critical_path(manifest["source_root"], relative))
                files[relative] = {"loaded": loaded, "source": source, "installed_sha256": saved["sha256"]}
                if loaded["sha256"] != saved["sha256"]:
                    report["reasons"].append(f"Loaded file differs from the install manifest: {relative}")
                if source["sha256"] is None:
                    source_available = False
                elif source["sha256"] != saved["sha256"]:
                    report["reasons"].append(f"Source file changed since installation: {relative}")
            report["evidence"]["files"] = files
            report["source_status"] = "available" if source_available else "unknown"
            report["status"] = "match" if source_available else "unknown"
        except (OSError, ValueError, KeyError, TypeError) as exc:
            report["reasons"].append(f"Cannot validate install manifest: {exc}")
    else:
        report["evidence"]["provenance"] = "No install manifest; source provenance is unknown."
    if source_root is not None:
        comparison = compare_install(source_root, installed_root, approved_route=approved_route)
        report["comparison"] = comparison
        report["reasons"].extend(comparison["reasons"])
    elif approved_route is not None:
        try:
            config = load_config(shared_root(installed_root) / "model-routing.json")
            report["route_check"] = verify_route(approved_route, config)
            report["reasons"].extend(report["route_check"]["reasons"])
        except (ValueError, KeyError, TypeError) as exc:
            report["reasons"].append(f"Cannot validate loaded route: {exc}")
    report["blocked"] = bool(report["reasons"])
    if report["blocked"]:
        report["status"] = "drift"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True, help="Checkout root or skills directory")
    parser.add_argument("--installed-root", type=Path, required=True, help="Installed skills directory")
    route = parser.add_mutually_exclusive_group()
    route.add_argument("--seat", help="Verify this seat against its source model and supplied effort")
    route.add_argument("--approved-route", type=Path, help="Saved JSON with exact roles and optional config_digest")
    parser.add_argument("--effort", help="Required for seats with an effort control")
    parser.add_argument("--write-manifest", action="store_true", help="Record a completed install; used by the installer")
    args = parser.parse_args(argv)
    try:
        if args.write_manifest:
            path = write_manifest(args.source_root, args.installed_root)
            print(json.dumps({"manifest": str(path)}))
            return 0
        approved = json.loads(args.approved_route.read_text(encoding="utf-8"), object_pairs_hook=unique_object) if args.approved_route else None
        if args.approved_route is not None and not isinstance(approved, dict):
            raise ValueError("Approved route must be an object")
        report = compare_install(args.source_root, args.installed_root, seat=args.seat,
                                 effort=args.effort, approved_route=approved)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        report = {"blocked": True, "reasons": [str(exc)]}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["blocked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
