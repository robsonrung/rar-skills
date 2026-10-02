#!/usr/bin/env python3
"""Local cache for capability preflight results, trusted for 24 hours.

Stores the outcome of environment capability probes (CLI presence and version,
supported efforts, tool or image support, ZDR endpoint
checks, browser mechanism readiness) on the user's machine so skills do not
re-run them on every invocation.

The cache covers capability probes only. Serving-model receipts, per-request
privacy controls, live authentication, account entitlement, and quota availability are per-run facts and are never
cached; a fresh cache entry never upgrades an unverified receipt.

Default location: ~/.rar-skills/preflight-cache.json (override with --cache or
RAR_SKILLS_PREFLIGHT_CACHE). Entries are keyed by seat and invalidated by a
caller-supplied fingerprint (for example CLI version plus configuration
digest) and by a 24 hour TTL.

Usage:
    python3 preflight_cache.py get --seat glm --fingerprint FINGERPRINT
    python3 preflight_cache.py set --seat glm --runner pi --fingerprint FINGERPRINT --result '{"available": true}'
    python3 preflight_cache.py fingerprint --probe-cli pi [--config-digest DIGEST]
    python3 preflight_cache.py status
    python3 preflight_cache.py clear [--seat glm]

`get` exits 0 and prints the entry when it is fresh; it exits 1 and prints the
miss reason to stderr otherwise (missing, expired, fingerprint mismatch, or a
corrupt cache file). A miss always means: re-probe, never guess.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from model_routing import CONFIG_PATH
try:
    import fcntl
except ImportError:  # pragma: no cover. The supported runner hosts are POSIX.
    fcntl = None

from runner_preflight import (
    COMPATIBILITY_PATH,
    MODEL_ROUTING_PATH,
    PREFLIGHT_PATH,
    cli_evidence,
    cli_version_probe,
    file_evidence,
    launch_identity,
    resolve_cli,
)

SCHEMA_VERSION = 2
TTL_SECONDS = 24 * 60 * 60

DEFAULT_CACHE_PATH = Path.home() / ".rar-skills" / "preflight-cache.json"


def default_cache_path() -> Path:
    override = os.environ.get("RAR_SKILLS_PREFLIGHT_CACHE")
    return Path(override) if override else DEFAULT_CACHE_PATH


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_cache(path: Path) -> dict:
    """Return the cache mapping, or raise ValueError on a corrupt file."""
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "entries": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"corrupt cache file: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("entries"), dict):
        raise ValueError("corrupt cache file: missing entries object")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("cache schema changed; re-probe capabilities")
    return data


def validate_result(result: dict) -> None:
    """Only stable capability fields belong in this cache."""
    allowed = {"available", "transport", "version", "cli_path", "compatibility", "effort", "config_digest",
               "tools", "images", "capabilities", "zdr_endpoint", "browser", "checks"}
    if set(result) - allowed:
        raise ValueError("result contains fields outside the capability cache contract")
    forbidden = {"auth", "auth_ok", "auth_visibility", "loggedin", "logged_in", "authenticated",
                 "is_authenticated", "authentication", "authentication_state", "model_entitlement",
                 "entitlement", "model_receipt", "receipt", "serving_model", "observed_model",
                 "effective_model", "quota", "quota_remaining", "privacy_controls", "privacy_policy",
                 "request_policy", "tool_policy", "tool_profile", "permissions", "limits", "budget",
                 "launch_context", "installation"}
    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower() in forbidden:
                    raise ValueError("live auth, entitlement, receipts, and request state cannot be cached")
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    visit(result)


def result_digest(result: dict) -> str:
    """Return a stable integrity digest for a validated capability result."""
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


@contextmanager
def cache_lock(path: Path):
    """Serialize cache updates so writers retain entries created by peers."""
    if fcntl is None:
        raise OSError("This host cannot lock the preflight cache safely.")
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f"{path.name}.lock")
    with lock_path.open("a+", encoding="utf-8") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def write_cache(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp_name = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def entry_age_seconds(entry: dict, now: float) -> float | None:
    checked_at = entry.get("checked_at_epoch")
    if isinstance(checked_at, bool) or not isinstance(checked_at, (int, float)):
        return None
    age = now - checked_at
    return age if math.isfinite(age) else None


def lookup(path: Path, seat: str, fingerprint: str | None, *,
           runner: str | None = None) -> tuple[dict | None, str]:
    """Return (entry, reason). Entry is None on any miss; reason explains why."""
    try:
        data = read_cache(path)
    except ValueError as exc:
        return None, str(exc)
    entry = data["entries"].get(seat)
    if entry is None:
        return None, "no cached entry"
    if not isinstance(entry, dict):
        return None, "invalid entry"
    if not isinstance(fingerprint, str) or not fingerprint:
        return None, "current fingerprint required"
    if entry.get("seat") != seat:
        return None, "entry seat mismatch"
    if not isinstance(entry.get("runner"), str) or not entry["runner"]:
        return None, "entry lacks a runner"
    if runner is not None and entry["runner"] != runner:
        return None, "entry runner mismatch"
    if not isinstance(entry.get("fingerprint"), str) or not entry["fingerprint"]:
        return None, "entry lacks a valid fingerprint"
    ttl_seconds = entry.get("ttl_seconds")
    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or ttl_seconds != TTL_SECONDS:
        return None, "entry has an unexpected ttl"
    if entry.get("fingerprint") != fingerprint:
        return None, "fingerprint mismatch"
    try:
        if not isinstance(entry.get("result"), dict):
            raise ValueError("invalid result")
        validate_result(entry["result"])
        digest = entry.get("result_sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("entry lacks a valid result digest")
        if digest != result_digest(entry["result"]):
            raise ValueError("entry result digest mismatch")
    except ValueError as exc:
        return None, str(exc)
    age = entry_age_seconds(entry, time.time())
    if age is None:
        return None, "entry lacks a valid timestamp"
    if age > TTL_SECONDS:
        return None, f"expired ({int(age)}s old, ttl {TTL_SECONDS}s)"
    if age < 0:
        return None, "entry timestamp is in the future"
    return entry, "fresh"


def store(path: Path, seat: str, runner: str, fingerprint: str, result: dict) -> dict:
    """Atomically merge one validated capability result into the cache."""
    if not isinstance(seat, str) or not seat:
        raise ValueError("seat must be a nonempty string")
    if not isinstance(runner, str) or not runner:
        raise ValueError("runner must be a nonempty string")
    if not isinstance(fingerprint, str) or not fingerprint:
        raise ValueError("fingerprint must be a nonempty string")
    validate_result(result)
    digest = result_digest(result)
    entry = {
        "seat": seat,
        "runner": runner,
        "fingerprint": fingerprint,
        "checked_at": utc_now(),
        "checked_at_epoch": time.time(),
        "ttl_seconds": TTL_SECONDS,
        "result": result,
        "result_sha256": digest,
    }
    with cache_lock(path):
        try:
            data = read_cache(path)
        except ValueError:
            data = {"schema_version": SCHEMA_VERSION, "entries": {}}
        data["entries"][seat] = entry
        write_cache(path, data)
    return entry


def clear(path: Path, seat: str | None = None) -> None:
    """Remove one cached result or the cache file while holding the writer lock."""
    with cache_lock(path):
        if not path.exists():
            return
        if seat is None:
            path.unlink()
            return
        try:
            data = read_cache(path)
        except ValueError:
            return
        data["entries"].pop(seat, None)
        write_cache(path, data)


def fingerprint_snapshot(probe_cli: str, config_digest: str | None = None, *,
                         policy_digest: str | None = None,
                         launch_context: dict | str | None = None,
                         working_dir: str | None = None, env: dict | None = None,
                         model: str | None = None, effort: str | None = None) -> dict:
    """Collect one current CLI identity probe and derive its cache fingerprint.

    Callers pass ``version_probe`` to the matching preflight so a cache miss
    does not execute a second version command.
    """
    cli_path = resolve_cli(probe_cli, working_dir=working_dir, env=env)
    identity = cli_evidence(cli_path) if cli_path else {"path": None, "resolved_path": None}
    version_probe = cli_version_probe(cli_path, working_dir=working_dir, env=env) if cli_path else {
        "attempted": False, "return_code": None, "identity": None, "version": None,
    }
    config = file_evidence(CONFIG_PATH)
    policy = file_evidence(COMPATIBILITY_PATH)
    preflight = file_evidence(PREFLIGHT_PATH)
    model_routing = file_evidence(MODEL_ROUTING_PATH)
    material = {
        "schema_version": SCHEMA_VERSION,
        "cli": probe_cli,
        "identity": identity,
        "version": version_probe["identity"],
        "config": config,
        "policy": policy,
        "preflight": preflight,
        "model_routing": model_routing,
        "config_digest": config_digest,
        "policy_digest": policy_digest,
        "launch_context": launch_identity(launch_context, working_dir=working_dir, env=env),
        "model": model,
        "effort": effort,
    }
    fingerprint = hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()
    cacheable = bool(
        cli_path
        and identity.get("stat") != "unavailable"
        and version_probe["version"]
        and config.get("sha256")
        and policy.get("sha256")
        and preflight.get("sha256")
        and model_routing.get("sha256")
    )
    return {
        "fingerprint": fingerprint,
        "cacheable": cacheable,
        "cli_path": cli_path,
        "cli": identity,
        "version_probe": version_probe,
    }


def compute_fingerprint(probe_cli: str, config_digest: str | None = None, *,
                        policy_digest: str | None = None,
                        launch_context: dict | str | None = None,
                        working_dir: str | None = None, env: dict | None = None,
                        model: str | None = None, effort: str | None = None) -> str:
    """Recompute local CLI identity and context before every lookup; never probe inference."""
    return fingerprint_snapshot(
        probe_cli,
        config_digest,
        policy_digest=policy_digest,
        launch_context=launch_context,
        working_dir=working_dir,
        env=env,
        model=model,
        effort=effort,
    )["fingerprint"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=None, help="Cache file path (default: ~/.rar-skills/preflight-cache.json)")
    commands = parser.add_subparsers(dest="command", required=True)

    get_cmd = commands.add_parser("get", help="Print a fresh cached entry; exit 1 on any miss")
    get_cmd.add_argument("--seat", required=True)
    get_cmd.add_argument("--fingerprint", default=None)

    set_cmd = commands.add_parser("set", help="Store a preflight result for a seat")
    set_cmd.add_argument("--seat", required=True)
    set_cmd.add_argument("--runner", required=True)
    set_cmd.add_argument("--fingerprint", required=True)
    set_cmd.add_argument("--result", required=True, help="JSON object with the probe result")

    fp_cmd = commands.add_parser("fingerprint", help="Compute a fingerprint for a probe CLI")
    fp_cmd.add_argument("--probe-cli", required=True)
    fp_cmd.add_argument("--config-digest", default=None)
    fp_cmd.add_argument("--policy-digest", default=None)
    fp_cmd.add_argument("--launch-context", default=None, help="Stable identifier for the actual launch context")

    commands.add_parser("status", help="List cached entries and their freshness")

    clear_cmd = commands.add_parser("clear", help="Remove one entry or the whole cache")
    clear_cmd.add_argument("--seat", default=None)

    args = parser.parse_args(argv)
    path = args.cache or default_cache_path()

    if args.command == "fingerprint":
        print(compute_fingerprint(args.probe_cli, args.config_digest,
                                  policy_digest=args.policy_digest, launch_context=args.launch_context))
        return 0

    if args.command == "get":
        entry, reason = lookup(path, args.seat, args.fingerprint)
        if entry is None:
            print(f"preflight cache miss for {args.seat}: {reason}", file=sys.stderr)
            return 1
        print(json.dumps(entry, indent=2, sort_keys=True))
        return 0

    if args.command == "set":
        try:
            result = json.loads(args.result)
        except ValueError as exc:
            print(f"Invalid --result JSON: {exc}", file=sys.stderr)
            return 2
        if not isinstance(result, dict):
            print("Invalid --result JSON: expected an object", file=sys.stderr)
            return 2
        try:
            validate_result(result)
        except ValueError as exc:
            print(f"Invalid --result: {exc}", file=sys.stderr)
            return 2
        try:
            entry = store(path, args.seat, args.runner, args.fingerprint, result)
        except (OSError, ValueError) as exc:
            print(f"Cannot update preflight cache: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(entry, indent=2, sort_keys=True))
        return 0

    if args.command == "status":
        try:
            data = read_cache(path)
        except ValueError as exc:
            print(f"preflight cache unreadable: {exc}", file=sys.stderr)
            return 1
        now = time.time()
        rows = []
        for seat, entry in sorted(data["entries"].items()):
            age = entry_age_seconds(entry, now)
            fresh = age is not None and 0 <= age <= TTL_SECONDS
            rows.append({
                "seat": seat,
                "runner": entry.get("runner"),
                "checked_at": entry.get("checked_at"),
                "age_seconds": int(age) if age is not None else None,
                "fresh": fresh,
            })
        print(json.dumps({"cache": str(path), "ttl_seconds": TTL_SECONDS, "entries": rows}, indent=2))
        return 0

    if args.command == "clear":
        if args.seat is None:
            try:
                clear(path)
            except OSError as exc:
                print(f"Cannot clear preflight cache: {exc}", file=sys.stderr)
                return 1
            return 0
        try:
            clear(path, args.seat)
        except OSError as exc:
            print(f"Cannot clear preflight cache: {exc}", file=sys.stderr)
            return 1
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
