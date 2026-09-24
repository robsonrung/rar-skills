#!/usr/bin/env python3
"""Local runner checks. No inference requests, credential output, or installation changes."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from model_routing import CONFIG_PATH, config_digest, load_config, unique_object, validate_selection, runner_efforts

COMPATIBILITY_PATH = Path(__file__).resolve().parents[1] / "runner-compatibility.json"


def file_evidence(path: Path | str) -> dict:
    path = Path(path).expanduser().absolute()
    result = {"path": str(path), "resolved_path": str(path.resolve()), "sha256": None}
    try:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        result["sha256"] = digest.hexdigest()
    except OSError:
        pass
    return result


def cli_evidence(path: Path | str) -> dict:
    path = Path(path).expanduser().absolute()
    result = {"path": str(path), "resolved_path": str(path.resolve())}
    try:
        info = path.stat()
        result.update(size=info.st_size, mtime_ns=info.st_mtime_ns, inode=info.st_ino)
    except OSError:
        result["stat"] = "unavailable"
    return result


def resolve_cli(requested_cli: str, *, working_dir: str | None = None,
                env: dict | None = None) -> str | None:
    """Resolve relative executable and PATH entries in the child's working directory."""
    base = Path(working_dir).absolute() if working_dir else Path.cwd()
    environment = os.environ if env is None else env
    search_path = os.pathsep.join(
        str(base / part) if not Path(part).is_absolute() else part
        for part in environment.get("PATH", os.defpath).split(os.pathsep)
    )
    if os.path.dirname(requested_cli) and not Path(requested_cli).is_absolute():
        requested_cli = str(base / requested_cli)
    resolved = shutil.which(requested_cli, path=search_path)
    return str(Path(resolved).absolute()) if resolved else None


def launch_identity(launch_context: dict | str | None = None, *,
                    working_dir: str | None = None, env: dict | None = None) -> dict:
    """Record context identity without reading tokens or credential stores."""
    environment = os.environ if env is None else env
    return {
        "platform": os.name,
        "uid": os.getuid() if hasattr(os, "getuid") else None,
        "cwd": str(Path(working_dir).absolute()) if working_dir else str(Path.cwd()),
        "environment_digest": config_digest({key: environment.get(key) for key in (
            "PATH", "HOME", "SHELL", "CLAUDE_CONFIG_DIR", "XDG_CONFIG_HOME",
            "SSH_CONNECTION", "SANDBOX_PROFILE",
        )}),
        "declared_context_digest": config_digest(launch_context),
    }


def check(status: bool | None, detail: str) -> dict:
    return {"status": "unknown" if status is None else "true" if status else "false", "detail": detail}


def parse_version(value: str | None) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"(?:v)?(\d+)\.(\d+)\.(\d+)(?:\s+\([^\n]*\))?", (value or "").strip())
    return tuple(map(int, match.groups())) if match else None


def claude_compatibility(model: str, version: str | None, *, config: dict | None = None) -> dict:
    policy = json.loads(COMPATIBILITY_PATH.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    if not isinstance(policy, dict) or policy.get("schema_version") != 1 or not isinstance(policy.get("claude"), dict):
        raise ValueError("Invalid compatibility policy")
    config = load_config() if config is None else config
    requirements = {}
    for seat, requirement in policy["claude"].items():
        entry = config["models"].get(seat)
        if not isinstance(entry, dict) or entry.get("runner") != "claude":
            raise ValueError(f"Compatibility seat {seat!r} is not a registered Claude seat")
        requirements[entry["model"]] = (seat, requirement)
    selection = requirements.get(model)
    if selection is None:
        return check(None, "No minimum CLI version is recorded for this exact model.")
    seat, requirement = selection
    if not isinstance(requirement, dict) or not isinstance(requirement.get("minimum_version"), str):
        raise ValueError("Invalid model compatibility requirement")
    minimum = parse_version(requirement["minimum_version"])
    if minimum is None:
        raise ValueError("Invalid minimum CLI version in compatibility policy")
    observed = parse_version(version)
    result = check(None if observed is None else observed >= minimum,
                   f"This model requires CLI {requirement['minimum_version']} or later.")
    result.update(requirement_seat=seat, minimum_version=requirement["minimum_version"], observed_version=version,
                  requirement_evidence=requirement["evidence"])
    return result


def local_command(cli_path: str, args: list[str], *, working_dir: str | None = None, env: dict | None = None) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run([cli_path, *args], capture_output=True, text=True, timeout=10, check=False, cwd=working_dir, env=env)
    except (OSError, subprocess.TimeoutExpired):
        return None


def check_claude(model: str | None, effort: str | None, cli_path: str | None = None,
                 launch_context: dict | str | None = None, *,
                 working_dir: str | None = None, env: dict | None = None) -> dict:
    """Check supplied controls in this process context; omitted controls stay unknown.

    launch_context may name the context or provide {"auth_visibility": "full"}.
    Use full only when the caller confirms credential visibility matches execution.
    A local loggedIn result is visibility evidence, never proof of live authentication.
    """
    checks = {name: check(None, "Not checked.") for name in (
        "transport", "compatibility", "auth_visibility", "model_entitlement", "effort", "tools",
    )}
    evidence = {"config": file_evidence(CONFIG_PATH), "policy": file_evidence(COMPATIBILITY_PATH),
                "launch_context": launch_identity(launch_context, working_dir=working_dir, env=env), "provider_calls": 0}
    reasons = []
    config = None
    try:
        config = load_config()
        evidence["config"]["config_digest"] = config_digest(config)
        if model is None or effort is None:
            if effort is not None and effort not in runner_efforts("claude", config=config):
                raise ValueError(f"Effort {effort!r} is not supported by the runner.")
            checks["effort"] = check(None, "Model or effort was omitted; runtime defaults are unverified.")
        else:
            validate_selection("claude", model, effort, config)
            checks["effort"] = check(True, "Exact model and effort are accepted by the loaded routing configuration.")
    except (ValueError, KeyError, TypeError) as exc:
        checks["effort"] = check(False, str(exc))
        reasons.append(str(exc))

    resolved_cli = resolve_cli(str(cli_path or "claude"), working_dir=working_dir, env=env)
    checks["transport"] = check(resolved_cli is not None, "CLI found." if resolved_cli else "CLI not found or not executable.")
    evidence["cli"] = cli_evidence(resolved_cli) if resolved_cli else {"path": None, "resolved_path": None, "sha256": None}
    version = None
    if resolved_cli:
        result = local_command(resolved_cli, ["--version"], working_dir=working_dir, env=env)
        if result is not None and result.returncode == 0:
            output = (result.stdout or result.stderr or "").strip().splitlines()
            candidate = output[0] if output else None
            if parse_version(candidate) is not None:
                version = candidate
    else:
        reasons.append(checks["transport"]["detail"])
    evidence["cli"]["version"] = version
    try:
        checks["compatibility"] = (check(None, "Model was omitted; runtime model compatibility is unverified.")
                                   if model is None else claude_compatibility(model, version, config=config))
        if checks["compatibility"]["status"] == "false":
            reasons.append(checks["compatibility"]["detail"])
        elif checks["compatibility"]["status"] == "unknown" and "minimum_version" in checks["compatibility"]:
            reasons.append("Cannot establish the required minimum CLI version.")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        checks["compatibility"] = check(None, "Compatibility policy could not be loaded.")
        reasons.append("Compatibility policy could not be loaded.")
        evidence["policy_error"] = type(exc).__name__
    checks["model_entitlement"] = check(None, "Local metadata cannot prove account access to this model.")
    checks["tools"] = check(None, "Tool access depends on the execution context and selected tool policy.")
    checks["auth_visibility"] = check(None, "Credential visibility has not been established in this launch context.")
    if resolved_cli and not reasons:
        result = local_command(resolved_cli, ["auth", "status", "--json"], working_dir=working_dir, env=env)
        evidence["auth_status"] = {"return_code": result.returncode if result is not None else None}
        try:
            auth = json.loads(result.stdout) if result is not None else {}
        except (ValueError, TypeError):
            auth = {}
        logged_in = auth.get("loggedIn") if isinstance(auth, dict) else None
        # Discard raw auth output, which can include account details.
        if result is not None and result.returncode == 0 and logged_in is True:
            checks["auth_visibility"] = check(True, "Local CLI reports visible credentials; live authentication is untested.")
        elif logged_in is False:
            full = isinstance(launch_context, dict) and launch_context.get("auth_visibility") == "full"
            checks["auth_visibility"] = check(False if full else None,
                "Local CLI reports no login; credential visibility is confirmed." if full else
                "Local CLI reports no login, but restricted or unknown visibility cannot prove host logout.")
            if full:
                reasons.append(checks["auth_visibility"]["detail"])
    from install_drift import check_loaded_install
    installation = check_loaded_install()
    evidence["installation"] = installation
    reasons.extend(installation["reasons"])
    return {"schema_version": 1, "model": model, "effort": effort, "blocked": bool(reasons),
            "reasons": reasons, "checks": checks, "evidence": evidence}
