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

import model_routing
from model_routing import CONFIG_PATH, config_digest, load_config, unique_object, validate_selection, runner_efforts

COMPATIBILITY_PATH = Path(__file__).resolve().parents[1] / "runner-compatibility.json"
PREFLIGHT_PATH = Path(__file__).resolve()
MODEL_ROUTING_PATH = Path(model_routing.__file__).resolve()
STATIC_CHECK_NAMES = ("transport", "compatibility", "effort")


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


def cli_version_probe(cli_path: str, *, working_dir: str | None = None,
                      env: dict | None = None) -> dict:
    """Run one local version probe and retain only its compatibility value."""
    result = local_command(cli_path, ["--version"], working_dir=working_dir, env=env)
    version = None
    identity = None
    if result is not None and result.returncode == 0:
        identity = (result.stdout or result.stderr or "").strip()
        output = identity.splitlines()
        candidate = output[0] if output else None
        if parse_version(candidate) is not None:
            version = candidate
    return {
        "attempted": True,
        "return_code": result.returncode if result is not None else None,
        "identity": identity,
        "version": version,
    }


def _capability_evidence(resolved_cli: str | None, version: str | None) -> dict:
    cli = (cli_evidence(resolved_cli) if resolved_cli else
           {"path": None, "resolved_path": None, "sha256": None})
    cli["version"] = version
    return {
        "config": file_evidence(CONFIG_PATH),
        "policy": file_evidence(COMPATIBILITY_PATH),
        "cli": cli,
    }


def probe_claude_capabilities(model: str | None, effort: str | None,
                              cli_path: str | None = None, *,
                              working_dir: str | None = None, env: dict | None = None,
                              version_probe: dict | None = None) -> dict:
    """Probe static Claude transport and compatibility facts without auth checks."""
    checks = {name: check(None, "Not checked.") for name in STATIC_CHECK_NAMES}
    reasons = []
    config = None
    evidence = _capability_evidence(None, None)
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
    if resolved_cli:
        probe = (version_probe if isinstance(version_probe, dict) else
                 cli_version_probe(resolved_cli, working_dir=working_dir, env=env))
        version = probe.get("version") if isinstance(probe.get("version"), str) else None
    else:
        version = None
        reasons.append(checks["transport"]["detail"])
    evidence = _capability_evidence(resolved_cli, version)
    if config is not None:
        evidence["config"]["config_digest"] = config_digest(config)
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
    return {
        "model": model,
        "effort": effort,
        "blocked": bool(reasons),
        "reasons": reasons,
        "checks": checks,
        "evidence": evidence,
        "resolved_cli": resolved_cli,
    }


def cacheable_claude_capabilities(report: dict) -> dict:
    """Extract the exact stable fields allowed in the capability cache."""
    if report.get("blocked"):
        raise ValueError("Blocked Claude capabilities cannot be cached.")
    checks = report.get("checks")
    evidence = report.get("evidence")
    if not isinstance(checks, dict) or not isinstance(evidence, dict):
        raise ValueError("Invalid Claude capability report.")
    if any(not isinstance(checks.get(name), dict) for name in STATIC_CHECK_NAMES):
        raise ValueError("Claude capability report lacks a static check.")
    cli = evidence.get("cli")
    if not isinstance(cli, dict) or not isinstance(cli.get("version"), str):
        raise ValueError("Claude capability report lacks a parsed CLI version.")
    cli_path = cli.get("path")
    if not isinstance(cli_path, str) or not cli_path:
        raise ValueError("Claude capability report lacks a resolved CLI path.")
    config = evidence.get("config")
    if not isinstance(config, dict) or not isinstance(config.get("config_digest"), str):
        raise ValueError("Claude capability report lacks a configuration digest.")
    return {
        "available": True,
        "transport": checks["transport"],
        "compatibility": checks["compatibility"],
        "effort": checks["effort"],
        "version": cli["version"],
        "cli_path": cli_path,
        "config_digest": config["config_digest"],
    }


def cached_claude_capabilities(result: dict, *, resolved_cli: str | None,
                               version: str | None, model: str | None,
                               effort: str | None) -> dict:
    """Validate and reconstruct a static report from a narrow cache result."""
    required = {"available", "transport", "compatibility", "effort", "version", "cli_path", "config_digest"}
    if not isinstance(result, dict) or set(result) != required or result.get("available") is not True:
        raise ValueError("Cached Claude capability result has an invalid shape.")
    if result.get("cli_path") != resolved_cli or result.get("version") != version:
        raise ValueError("Cached Claude capability result does not match the current CLI.")
    if not isinstance(version, str) or parse_version(version) is None:
        raise ValueError("Cached Claude capability result lacks a valid CLI version.")
    for name in STATIC_CHECK_NAMES:
        value = result.get(name)
        allowed = {"status", "detail"}
        if name == "compatibility":
            allowed |= {"requirement_seat", "minimum_version", "observed_version", "requirement_evidence"}
        if not isinstance(value, dict) or set(value) - allowed or value.get("status") not in {"true", "false", "unknown"} or not isinstance(value.get("detail"), str):
            raise ValueError("Cached Claude capability result has an invalid check.")
    compatibility = result["compatibility"]
    if result["transport"]["status"] != "true" or result["effort"]["status"] == "false":
        raise ValueError("Cached Claude capability result cannot be nonblocking.")
    if model is not None and effort is not None and result["effort"]["status"] != "true":
        raise ValueError("Cached Claude effort result cannot satisfy explicit controls.")
    if compatibility["status"] == "false":
        raise ValueError("Cached Claude compatibility result cannot be nonblocking.")
    if compatibility["status"] == "unknown":
        if set(compatibility) != {"status", "detail"}:
            raise ValueError("Cached Claude compatibility result has an invalid unknown shape.")
    else:
        compatibility_fields = {
            "status", "detail", "requirement_seat", "minimum_version",
            "observed_version", "requirement_evidence",
        }
        if set(compatibility) != compatibility_fields:
            raise ValueError("Cached Claude compatibility result lacks compatibility evidence.")
        for name in ("requirement_seat", "minimum_version", "observed_version", "requirement_evidence"):
            if not isinstance(compatibility[name], str) or not compatibility[name]:
                raise ValueError("Cached Claude compatibility result has an invalid field.")
        minimum_version = parse_version(compatibility["minimum_version"])
        if minimum_version is None:
            raise ValueError("Cached Claude compatibility result has an invalid minimum version.")
        if compatibility["observed_version"] != version:
            raise ValueError("Cached Claude compatibility result does not match the current CLI version.")
        if parse_version(version) < minimum_version:
            raise ValueError("Cached Claude compatibility result is below its minimum version.")
    config_digest = result.get("config_digest")
    if not isinstance(config_digest, str) or re.fullmatch(r"[0-9a-f]{64}", config_digest) is None:
        raise ValueError("Cached Claude capability result has an invalid configuration digest.")
    evidence = _capability_evidence(resolved_cli, version)
    evidence["config"]["config_digest"] = config_digest
    return {
        "model": model,
        "effort": effort,
        "blocked": False,
        "reasons": [],
        "checks": {name: result[name] for name in STATIC_CHECK_NAMES},
        "evidence": evidence,
        "resolved_cli": resolved_cli,
    }


def claude_cache_key(model: str | None, effort: str | None) -> str:
    """Scope a capability entry to the exact requested Claude controls."""
    return f"claude:{model if model is not None else '<runtime>'}:{effort if effort is not None else '<runtime>'}"


def cached_or_fresh_claude_capabilities(model: str | None, effort: str | None,
                                        cli_path: str | None, launch_context: dict | str | None,
                                        *, working_dir: str | None = None,
                                        env: dict | None = None) -> tuple[dict, dict]:
    """Use a validated static cache entry, or refresh it without weakening preflight."""
    try:
        from preflight_cache import fingerprint_snapshot, lookup, store
        snapshot = fingerprint_snapshot(
            str(cli_path or "claude"),
            launch_context=launch_context,
            working_dir=working_dir,
            env=env,
            model=model,
            effort=effort,
        )
    except Exception as exc:  # Cache support must not weaken a fresh preflight.
        return (
            probe_claude_capabilities(model, effort, cli_path, working_dir=working_dir, env=env),
            {"status": "unavailable", "reason": type(exc).__name__},
        )

    probe_cli = snapshot.get("cli_path") or cli_path
    version_probe = snapshot.get("version_probe")
    if not snapshot.get("cacheable") or not isinstance(snapshot.get("fingerprint"), str):
        return (
            probe_claude_capabilities(model, effort, probe_cli, working_dir=working_dir,
                                      env=env, version_probe=version_probe),
            {"status": "miss", "reason": "fingerprint incomplete"},
        )

    key = claude_cache_key(model, effort)
    try:
        entry, reason = lookup(preflight_cache_path(), key, snapshot["fingerprint"], runner="claude")
    except Exception as exc:  # Cache I/O must not prevent a fresh local probe.
        entry, reason = None, f"cache lookup failed: {type(exc).__name__}"
    if entry is not None:
        try:
            return (
                cached_claude_capabilities(
                    entry["result"],
                    resolved_cli=snapshot["cli_path"],
                    version=snapshot["version_probe"]["version"],
                    model=model,
                    effort=effort,
                ),
                {"status": "hit"},
            )
        except (KeyError, TypeError, ValueError):
            reason = "invalid cached capability result"

    fresh = probe_claude_capabilities(model, effort, probe_cli, working_dir=working_dir,
                                      env=env, version_probe=version_probe)
    cache_status = {"status": "miss", "reason": reason}
    if not fresh["blocked"]:
        try:
            result = cacheable_claude_capabilities(fresh)
            store(preflight_cache_path(), key, "claude", snapshot["fingerprint"], result)
            cache_status["stored"] = True
        except Exception:  # Cache I/O must not prevent the already fresh preflight from running.
            cache_status["stored"] = False
    return fresh, cache_status


def preflight_cache_path() -> Path:
    """Resolve the cache location lazily so direct preflight has no cache dependency."""
    from preflight_cache import default_cache_path
    return default_cache_path()


def check_claude(model: str | None, effort: str | None, cli_path: str | None = None,
                 launch_context: dict | str | None = None, *,
                 working_dir: str | None = None, env: dict | None = None,
                 use_capability_cache: bool = False) -> dict:
    """Check supplied controls in this process context; omitted controls stay unknown.

    launch_context may name the context or provide {"auth_visibility": "full"}.
    Use full only when the caller confirms credential visibility matches execution.
    A local loggedIn result is visibility evidence, never proof of live authentication.
    ``use_capability_cache`` reuses only static transport, compatibility, and
    effort checks. Authentication and installation checks always run live.
    """
    cache = None
    if use_capability_cache:
        static, cache = cached_or_fresh_claude_capabilities(
            model, effort, cli_path, launch_context, working_dir=working_dir, env=env,
        )
    else:
        static = probe_claude_capabilities(model, effort, cli_path, working_dir=working_dir, env=env)

    checks = {name: static["checks"][name] for name in STATIC_CHECK_NAMES}
    checks["model_entitlement"] = check(None, "Local metadata cannot prove account access to this model.")
    checks["tools"] = check(None, "Tool access depends on the execution context and selected tool policy.")
    checks["auth_visibility"] = check(None, "Credential visibility has not been established in this launch context.")
    evidence = static["evidence"]
    evidence["launch_context"] = launch_identity(launch_context, working_dir=working_dir, env=env)
    evidence["provider_calls"] = 0
    if cache is not None:
        evidence["capability_cache"] = cache
    reasons = list(static["reasons"])
    resolved_cli = static["resolved_cli"]
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
