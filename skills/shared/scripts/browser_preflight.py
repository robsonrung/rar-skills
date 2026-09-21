#!/usr/bin/env python3
"""Bind observed browser capability checks to a driver, workspace, and artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


MECHANISMS = ("playwright-cli", "agent-browser")
CHECKS = ("navigation", "state_inspection", "interaction", "assertions", "evidence_capture")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reference(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": digest(path)}


def verify_reference(ref):
    require(isinstance(ref, dict) and set(ref) == {"path", "sha256"}, "invalid browser evidence reference")
    require(isinstance(ref["path"], str) and Path(ref["path"]).is_absolute(), "browser evidence path must be absolute")
    require(Path(ref["path"]).is_file() and digest(ref["path"]) == ref["sha256"], "browser evidence changed or is missing")


def validate_browser_route(browser):
    require(isinstance(browser, dict) and set(browser) == {"mechanism", "preflight"}, "browser route needs mechanism and preflight")
    require(browser["mechanism"] in MECHANISMS, "unsupported external browser mechanism")
    ref = browser["preflight"]
    require(isinstance(ref, dict) and set(ref) == {"path", "sha256"}, "browser preflight needs a bound file reference")
    require(isinstance(ref["path"], str) and Path(ref["path"]).is_absolute(), "browser preflight path must be absolute")
    value = ref["sha256"]
    require(isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value), "invalid browser preflight digest")


def validate_preflight(record, mechanism, working_dir, *, check_driver=True):
    require(record.get("mechanism") == mechanism and mechanism in MECHANISMS, "browser preflight mechanism mismatch")
    require(record.get("working_dir") == str(Path(working_dir).resolve()), "browser preflight workspace mismatch")
    require(record.get("ready") is True and record.get("status") == "ready", "browser preflight is blocked")
    require(all(record.get("checks", {}).get(k) is True for k in CHECKS), "browser preflight lacks observed capability checks")
    evidence = record.get("evidence")
    require(isinstance(evidence, list) and evidence, "browser preflight requires captured evidence")
    for ref in evidence:
        verify_reference(ref)
    driver = record.get("driver", {})
    require(isinstance(driver, dict) and driver.get("version"), "browser preflight needs driver identity")
    verify_reference({"path": driver.get("path"), "sha256": driver.get("sha256")})
    if check_driver:
        located = shutil.which(mechanism)
        require(located and Path(located).resolve() == Path(driver["path"]).resolve(), "browser driver changed or is unavailable")
    return record


def load_bound_preflight(browser, working_dir):
    validate_browser_route(browser)
    verify_reference(browser["preflight"])
    record = json.loads(Path(browser["preflight"]["path"]).read_text())
    return validate_preflight(record, browser["mechanism"], working_dir)


def record_preflight(mechanism, working_dir, checks, evidence):
    """Record caller-observed checks; a version command alone never marks readiness."""
    require(mechanism in MECHANISMS, "unsupported external browser mechanism")
    require(Path(working_dir).is_dir(), "browser workspace does not exist")
    require(isinstance(checks, dict) and all(type(checks.get(k)) is bool for k in CHECKS), "each browser capability needs an explicit observed boolean")
    require(evidence, "capture browser evidence before recording readiness")
    refs = [reference(path) for path in evidence]
    driver = shutil.which(mechanism)
    result = {"mechanism": mechanism, "working_dir": str(Path(working_dir).resolve()),
              "checks": checks, "evidence": refs, "ready": False, "status": "blocked",
              "reason": "browser driver unavailable"}
    if driver:
        try:
            version = subprocess.run([driver, "--version"], capture_output=True, text=True, timeout=15, check=False)
            result["driver"] = {**reference(driver), "version": version.stdout.strip()[:200]}
            result["reason"] = "browser driver failed readiness" if version.returncode else "required browser capability was not observed"
            if version.returncode == 0 and result["driver"]["version"] and all(checks[k] for k in CHECKS):
                result.update(ready=True, status="ready", reason="driver identity and captured capability checks match")
        except (OSError, subprocess.TimeoutExpired) as error:
            result["reason"] = f"browser driver unavailable: {type(error).__name__}"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    record = sub.add_parser("record", help="Record previously observed capability checks; does not execute a journey")
    record.add_argument("--mechanism", choices=MECHANISMS, required=True)
    record.add_argument("--working-dir", type=Path, required=True)
    record.add_argument("--checks", type=Path, required=True, help="JSON object with an observed boolean for each capability")
    record.add_argument("--evidence", type=Path, action="append", required=True)
    record.add_argument("--output", type=Path, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--route", type=Path, required=True, help="JSON object with mechanism and bound preflight reference")
    verify.add_argument("--working-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "record":
            result = record_preflight(args.mechanism, args.working_dir, json.loads(args.checks.read_text()), args.evidence)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps({"status": result["status"], "reason": result["reason"], "preflight": reference(args.output)}))
            return 0 if result["ready"] else 2
        load_bound_preflight(json.loads(args.route.read_text()), args.working_dir)
        print(json.dumps({"status": "ready"}))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "blocked", "reason": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
