#!/usr/bin/env python3
"""Capture source state, check results, and structured review evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path


VERSION = 1


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_hash(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def contract_hash(path):
    text = Path(path).read_text().replace("\r\n", "\n").replace("\r", "\n")
    lines = [line for line in text.splitlines() if not re.fullmatch(r"\*\*Status:\*\* (?:ready-for-agent|in-progress|done|blocked)", line)]
    return digest("\n".join(lines))


def read_json(path):
    def unique(pairs):
        value = {}
        for key, entry in pairs:
            require(key not in value, f"duplicate JSON key: {key}")
            value[key] = entry
        return value
    return json.loads(Path(path).read_text(), object_pairs_hook=unique)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write_record(path, payload):
    """Never replace a previous record, including a failed check."""
    path = Path(path)
    record = {"payload": payload, "sha256": digest(payload)}
    if path.exists():
        require(read_json(path) == record, f"record already exists with different content: {path}")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(record, indent=2) + "\n")
    return path


def load_record(path):
    record = read_json(path)
    require(isinstance(record, dict) and set(record) == {"payload", "sha256"}, "invalid record envelope")
    require(record["sha256"] == digest(record["payload"]), f"record checksum mismatch: {path}")
    return record["payload"]


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    require(result.returncode == 0, result.stderr.decode(errors="replace").strip() or "git command failed")
    return result.stdout


def names(data):
    return {item.decode("utf-8", errors="surrogateescape") for item in data.split(b"\0") if item}


def safe_path(root, name):
    require(isinstance(name, str) and name and not Path(name).is_absolute(), "expected a relative path")
    require(".." not in Path(name).parts, "parent traversal is not allowed")
    path = root / name
    require(path == root or path.parent.resolve().is_relative_to(root), f"path parent escapes the source root: {name}")
    return path


def source_state(root, base_ref, artifact_dir):
    root, artifact_dir = Path(root).resolve(), Path(artifact_dir).resolve()
    actual_root = Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel")).strip()).resolve()
    require(root == actual_root, "source root must be the git worktree root")
    base = git(root, "rev-parse", "--verify", f"{base_ref}^{{commit}}").decode().strip()
    tracked = names(git(root, "ls-files", "-z"))
    untracked = names(git(root, "ls-files", "--others", "--exclude-standard", "-z"))
    require(not any((root / p).is_relative_to(artifact_dir) for p in tracked), "artifact directory contains tracked source")
    require(artifact_dir != root and not root.is_relative_to(artifact_dir), "artifact directory contains the source root")
    included = {p for p in tracked | untracked if not (root / p).is_relative_to(artifact_dir)}
    files = {}
    for name in sorted(included):
        path = safe_path(root, name)
        if path.is_symlink():
            require(path.resolve().is_relative_to(root), f"symbolic link target escapes the source root: {name}")
            files[name] = {"kind": "symlink", "target": os.readlink(path)}
        elif not path.exists():
            files[name] = {"kind": "deleted"}
        else:
            require(path.is_file(), f"unsupported source entry (including submodules): {name}")
            files[name] = {"kind": "file", "sha256": file_hash(path), "executable": bool(path.stat().st_mode & stat.S_IXUSR)}
    index = git(root, "ls-files", "--stage", "-z")
    require(not git(root, "ls-files", "--unmerged", "-z"), "unresolved index conflicts prevent source capture")
    require(not any(row.startswith(b"160000 ") for row in index.split(b"\0")), "submodule evidence is not supported")
    changed = names(git(root, "diff", "--no-ext-diff", "--no-renames", "--name-only", "-z", base, "--"))
    changed |= names(git(root, "diff", "--no-ext-diff", "--no-renames", "--cached", "--name-only", "-z", base, "--"))
    changed |= untracked
    changed = sorted(p for p in changed if not (root / p).is_relative_to(artifact_dir))
    return {"root": str(root), "base": base, "files": files, "index_sha256": hashlib.sha256(index).hexdigest(), "changed_paths": changed}


def content_identity(source):
    # A committed deletion no longer has an index entry. Absence represents it.
    return digest({name: value for name, value in source["files"].items() if value["kind"] != "deleted"})


def context_identity(context):
    """Legacy contexts stay strict; version 2 separates notes from identity."""
    if context.get("version") != 2:
        return context
    require(set(context) <= {"version", "identity", "notes"}, "unknown context fields")
    require(isinstance(context.get("identity"), dict) and bool(context["identity"]), "context identity is required")
    require(isinstance(context.get("notes", ""), str), "context notes must be text")
    return {"version": 2, "identity": context["identity"]}


def validate_inputs(paths, root):
    require(isinstance(paths, list) and bool(paths) and all(isinstance(p, str) for p in paths)
            and len(set(paths)) == len(paths), "inputs need unique relative file paths")
    for name in paths:
        path = safe_path(root, name)
        require(name != "." and not path.is_dir(), "inputs must name files, not directories")
        require(not path.is_symlink(), "scoped inputs cannot be symbolic links")
        require(name == Path(name).as_posix(), "inputs must use canonical relative paths")


def input_identity(source, paths):
    return {name: source["files"].get(name, {"kind": "absent"}) for name in paths}


def validate_review_scope(scope, root):
    """Bind a complete dependency declaration and exact prospective changes."""
    require(isinstance(scope, dict) and set(scope) == {"inputs", "complete", "reason", "changes"},
            "review scope needs inputs, complete, reason, and changes")
    validate_inputs(scope["inputs"], root)
    require(scope["complete"] is True, "unknown dependencies cannot use scoped carry forward")
    require(isinstance(scope["reason"], str) and scope["reason"].strip(), "review scope needs a dependency closure assessment")
    changes = scope["changes"]
    require(isinstance(changes, list) and 0 < len(changes) <= 32, "review scope needs 1 to 32 exact changes")
    paths = []
    for row in changes:
        require(isinstance(row, dict) and set(row) == {"path", "content", "reason"}, "invalid scoped change")
        paths.append(row["path"])
        require(isinstance(row["reason"], str) and row["reason"].strip(), "scoped change needs an independence assessment")
        link = row["content"]
        require(isinstance(link, dict) and set(link) == {"path", "sha256"}
                and Path(link["path"]).is_absolute() and file_hash(link["path"]) == link["sha256"],
                "scoped change content checksum mismatch")
    validate_inputs(paths, root)
    require(not set(paths).intersection(scope["inputs"]), "scoped changes overlap review dependencies")


def fresh_observations(old, snapshot):
    before, after = old["requirements"]["value"], snapshot["requirements"]["value"]
    if context_identity(before["context"]) != context_identity(after["context"]):
        return set(after["observations"])
    required = set(after["observations"]) - set(before["observations"])
    for key in after["observations"]:
        previous = before.get("observation_inputs", {}).get(key)
        current = after.get("observation_inputs", {}).get(key)
        if (previous != current or current and input_identity(old["source"], current) != input_identity(snapshot["source"], current)
                or not current and content_identity(old["source"]) != content_identity(snapshot["source"])):
            required.add(key)
    return required


def validate_requirements(value, root):
    require(isinstance(value, dict) and {"context", "checks", "observations", "exclusions"} <= set(value) <= {"context", "checks", "observations", "exclusions", "observation_inputs", "review_scope"}, "requirements need context, checks, observations, and exclusions")
    require(isinstance(value["context"], dict) and bool(value["context"]), "context must describe the current runtime and external state")
    context_identity(value["context"])
    require(isinstance(value["checks"], list), "checks must be a list")
    ids = set()
    for check in value["checks"]:
        require(isinstance(check, dict) and {"id", "command", "cwd", "timeout_seconds"} <= set(check) <= {"id", "command", "cwd", "timeout_seconds", "inputs", "fresh"}, "invalid check definition")
        require(type(check.get("fresh", False)) is bool, "fresh must be a boolean")
        if "inputs" in check:
            validate_inputs(check["inputs"], root)
        key = check["id"]
        require(isinstance(key, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]*", key) and key not in ids, "invalid or duplicate check id")
        ids.add(key)
        require(isinstance(check["command"], list) and bool(check["command"]) and all(isinstance(x, str) and x for x in check["command"]), "command must be a nonempty argument list")
        require(safe_path(root, check["cwd"]).resolve().is_relative_to(root), "check cwd escapes source root")
        require(type(check["timeout_seconds"]) is int and 0 < check["timeout_seconds"] <= 3600, "invalid check timeout")
    observations = value["observations"]
    require(isinstance(observations, list) and all(isinstance(x, str) and x for x in observations), "invalid observation ids")
    require(len(set(observations)) == len(observations), "duplicate observation ids")
    scopes = value.get("observation_inputs", {})
    require(isinstance(scopes, dict) and set(scopes) <= set(observations), "unknown observation input scope")
    for paths in scopes.values():
        validate_inputs(paths, root)
    require(isinstance(value["exclusions"], dict) and all(isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in value["exclusions"].items()), "exclusions need path and reason")
    if "review_scope" in value:
        scope = value["review_scope"]
        validate_review_scope(scope, root)
        declared = {p for check in value["checks"] for p in check.get("inputs", [])}
        declared.update(p for paths in scopes.values() for p in paths)
        require(declared <= set(scope["inputs"]), "review scope omits declared check or observation dependencies")


def prepare(root, base, contract, requirements, output, artifact_dir=None, previous_reviews=()):
    root, output = Path(root).resolve(), Path(output).resolve()
    artifact_dir = Path(artifact_dir or output).resolve()
    require(output.is_relative_to(artifact_dir), "output must be within the artifact directory")
    plan = read_json(requirements)
    validate_requirements(plan, root)
    source = source_state(root, base, artifact_dir)
    scopes = [check["inputs"] for check in plan["checks"] if "inputs" in check]
    scopes.extend(plan.get("observation_inputs", {}).values())
    if "review_scope" in plan:
        scopes.append(plan["review_scope"]["inputs"])
        for row in plan["review_scope"]["changes"]:
            require(not (root / row["path"]).is_relative_to(artifact_dir), "scoped changes cannot be evidence artifacts")
            require(not (root / row["path"]).exists() or row["path"] in source["files"],
                    "scoped changes cannot be ignored source")
    for paths in scopes:
        for name in paths:
            require(not (root / name).exists() or name in source["files"],
                    f"scoped input is outside captured source: {name}")
    require(set(plan["exclusions"]) <= set(source["changed_paths"]), "exclusions contain paths outside the diff")
    payload = {
        "schema_version": VERSION, "source": source, "source_id": digest(source), "content_id": content_identity(source),
        "snapshot_path": str(output / "snapshot.json"),
        "base_ref": base, "artifact_dir": str(artifact_dir),
        "contract": {"path": str(Path(contract).resolve()), "sha256": contract_hash(contract)},
        "requirements": {"path": str(Path(requirements).resolve()), "sha256": file_hash(requirements), "value": plan},
        "previous_reviews": [{"path": str(Path(p).resolve()), "sha256": file_hash(p)} for p in previous_reviews],
    }
    previous_findings(payload)
    require(source == source_state(root, base, artifact_dir), "source changed while preparing the snapshot")
    return write_record(output / "snapshot.json", payload)


def snapshot_record(path):
    """Validate frozen metadata without claiming that historical source is current."""
    snapshot = load_record(path)
    require(snapshot.get("snapshot_path", str(Path(path).resolve())) == str(Path(path).resolve()), "snapshot path differs from its prepared bundle")
    require(snapshot["schema_version"] == VERSION and snapshot["source_id"] == digest(snapshot["source"]), "invalid source snapshot")
    require(snapshot.get("content_id", content_identity(snapshot["source"])) == content_identity(snapshot["source"]), "invalid content identity")
    for key in ("contract", "requirements"):
        observed = contract_hash(snapshot[key]["path"]) if key == "contract" else file_hash(snapshot[key]["path"])
        require(observed == snapshot[key]["sha256"], f"{key} changed since review preparation")
    require(read_json(snapshot["requirements"]["path"]) == snapshot["requirements"]["value"], "captured requirements differ from their source")
    validate_requirements(snapshot["requirements"]["value"], Path(snapshot["source"]["root"]))
    previous_findings(snapshot)
    return snapshot


def current_snapshot(path, base=None):
    snapshot = snapshot_record(path)
    source = source_state(snapshot["source"]["root"], base or snapshot["base_ref"], snapshot["artifact_dir"])
    old = snapshot["source"]
    changed = sorted(p for p in set(old["files"]) | set(source["files"]) if old["files"].get(p) != source["files"].get(p))
    require(source == old, f"source snapshot is stale; changed paths: {changed}; base or index may also differ")
    return snapshot


def check_definition(snapshot, key):
    entries = [x for x in snapshot["requirements"]["value"]["checks"] if x["id"] == key]
    require(len(entries) == 1, f"check id is not in requirements: {key}")
    return entries[0]


def run_check(snapshot_path, key):
    snapshot_path = Path(snapshot_path).resolve()
    snapshot = current_snapshot(snapshot_path)
    definition = check_definition(snapshot, key)
    output = snapshot_path.parent / "checks" / key
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    timed_out = False
    with (output / "stdout.log").open("wb") as stdout, (output / "stderr.log").open("wb") as stderr:
        try:
            process = subprocess.Popen(definition["command"], cwd=safe_path(Path(snapshot["source"]["root"]), definition["cwd"]), stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                code = process.wait(timeout=definition["timeout_seconds"])
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                code = process.wait()
                timed_out = True
        except OSError as error:
            stderr.write(str(error).encode())
            code = 127
    stale = False
    try:
        current_snapshot(snapshot_path)
    except (ValueError, OSError):
        stale = True
    payload = {
        "snapshot_path": str(snapshot_path), "snapshot_sha256": file_hash(snapshot_path), "source_id": snapshot["source_id"],
        "context_id": digest(context_identity(snapshot["requirements"]["value"]["context"])), "definition": definition,
        "exit_code": code, "duration_ms": round((time.monotonic() - started) * 1000),
        "timed_out": timed_out, "source_changed": stale,
        "logs": [{"path": str(output / name), "sha256": file_hash(output / name)} for name in ("stdout.log", "stderr.log")],
    }
    return write_record(output / "result.json", payload)


def validate_check(path, snapshot, definition):
    check = load_record(path)
    require(check["source_id"] == snapshot["source_id"], "check source does not match")
    if "transfer" in check:
        if snapshot.get("snapshot_path"):
            target_path = Path(snapshot["snapshot_path"])
            require(check["snapshot_sha256"] == file_hash(target_path), "transferred check target snapshot differs")
            require(Path(path).resolve() == target_path.parent / "checks" / definition["id"] / "result.json",
                    "transferred check path differs from its target bundle")
        validate_transfer(check, snapshot, definition)
    else:
        captured_path = Path(check.get("snapshot_path", Path(path).resolve().parents[2] / "snapshot.json"))
        require(captured_path.is_absolute() and file_hash(captured_path) == check["snapshot_sha256"], "check capture snapshot mismatch")
        require(Path(path).resolve() == captured_path.parent / "checks" / definition["id"] / "result.json", "check capture path differs from its snapshot bundle")
        captured = load_record(captured_path)
        require(captured.get("snapshot_path", str(captured_path)) == str(captured_path), "captured snapshot path differs")
        require(captured["source_id"] == digest(captured["source"]) == snapshot["source_id"], "invalid check capture source")
        require(check_definition(captured, definition["id"]) == definition, "captured command differs")
        require(captured["contract"]["sha256"] == snapshot["contract"]["sha256"], "check contract does not match")
        require(captured["requirements"]["value"] == snapshot["requirements"]["value"], "check requirements do not match")
        if definition.get("fresh"):
            require(captured == snapshot, "required fresh check belongs to another snapshot")
    require(check["context_id"] == digest(context_identity(snapshot["requirements"]["value"]["context"])), "check context does not match")
    require(check["definition"] == definition, "check command does not match requirements")
    require(type(check["exit_code"]) is int and type(check["duration_ms"]) is int and check["duration_ms"] >= 0, "invalid command result")
    require(type(check["timed_out"]) is bool and type(check["source_changed"]) is bool, "invalid command status")
    require(isinstance(check["logs"], list) and len(check["logs"]) == 2, "command logs are missing")
    expected_names = {"stdout.log", "stderr.log"}
    require({Path(log["path"]).name for log in check["logs"]} == expected_names, "command logs must preserve stdout and stderr")
    for log in check["logs"]:
        require(set(log) == {"path", "sha256"} and Path(log["path"]).is_absolute(), "invalid command log reference")
        capture_result = Path(check["transfer"]["check"]["path"] if "transfer" in check else path).resolve()
        require(Path(log["path"]).parent == capture_result.parent, "command log is outside its capture directory")
        require(file_hash(log["path"]) == log["sha256"], "command log checksum mismatch")
    return check["exit_code"] == 0 and not check["timed_out"] and not check["source_changed"]


def previous_findings(snapshot):
    findings = {}
    paths = set()
    for link in snapshot["previous_reviews"]:
        require(link["path"] not in paths, "duplicate previous review")
        paths.add(link["path"])
        require(file_hash(link["path"]) == link["sha256"], "previous review checksum mismatch")
        record = load_record(link["path"])
        require(record["schema_version"] == VERSION, "unsupported previous review version")
        for finding in record["result"]["findings"]:
            key = finding["id"]
            require(key not in findings or findings[key] == finding, "conflicting prior finding ids; use task-specific ids")
            findings[key] = finding
    return findings


def validate_result(result, snapshot, snapshot_path):
    fields = {"snapshot_sha256", "coverage", "findings", "checks", "observations", "summary"}
    scope = snapshot["requirements"]["value"].get("review_scope")
    if scope:
        fields.add("scope_approval")
    require(isinstance(result, dict) and set(result) == fields, "invalid review result fields")
    if scope:
        require(result["scope_approval"] == digest(scope), "reviewer must approve the exact dependency scope and prospective changes")
    require(result["snapshot_sha256"] == file_hash(snapshot_path), "review is bound to a different snapshot")
    require(isinstance(result["summary"], str) and result["summary"].strip(), "review summary is missing")
    plan = snapshot["requirements"]["value"]
    coverage = result["coverage"]
    require(isinstance(coverage, list), "coverage must be a list")
    seen = set()
    for row in coverage:
        require(isinstance(row, dict) and set(row) == {"path", "outcome", "reason"}, "invalid coverage row")
        require(isinstance(row["path"], str) and row["path"] not in seen, "duplicate coverage path")
        seen.add(row["path"])
        require(row["outcome"] in {"reviewed", "excluded"} and isinstance(row["reason"], str) and row["reason"].strip(), "coverage needs an outcome and reason")
        expected = plan["exclusions"].get(row["path"])
        require((row["outcome"] == "excluded") == (expected is not None), "coverage exclusion differs from requirements")
        if expected:
            require(row["reason"] == expected, "exclusion reason differs from requirements")
    require(seen == set(snapshot["source"]["changed_paths"]), "review coverage is incomplete or outside the diff")
    require(isinstance(result["findings"], list), "findings must be a list")
    previous = previous_findings(snapshot)
    finding_paths = seen | {f["path"] for f in previous.values()}
    ids = set()
    for finding in result["findings"]:
        require(isinstance(finding, dict) and set(finding) == {"id", "path", "severity", "status", "evidence"}, "invalid finding fields")
        require(isinstance(finding["id"], str) and finding["id"] and finding["id"] not in ids, "invalid or duplicate finding id")
        ids.add(finding["id"])
        require(finding["path"] in finding_paths, "finding path is outside review scope")
        require(finding["severity"] in {"P0", "P1", "P2", "P3"}, "unknown finding severity")
        require(finding["status"] in {"open", "fixed", "rejected", "deferred", "disputed"}, "unknown finding status")
        require(isinstance(finding["evidence"], str) and finding["evidence"].strip(), "finding evidence is missing")
        if finding["id"] in previous:
            old = previous[finding["id"]]
            require((finding["path"], finding["severity"]) == (old["path"], old["severity"]), "prior finding path or severity changed; retain its identity and record resolution")
    require(set(previous) <= ids, "prior findings were dropped from the recheck")
    require(isinstance(result["checks"], dict), "checks must map ids to captured result paths")
    require(set(result["checks"]) == {c["id"] for c in plan["checks"]}, "required checks are missing or unknown")
    require(isinstance(result["observations"], list), "observations must be a list")
    observed = set()
    for observation in result["observations"]:
        require(isinstance(observation, dict) and set(observation) == {"id", "result", "evidence"}, "invalid observation fields")
        require(isinstance(observation["id"], str) and observation["id"] not in observed, "duplicate observation")
        observed.add(observation["id"])
        require(observation["result"] in {"pass", "fail", "skipped"}, "unknown observation result")
        require(isinstance(observation["evidence"], list) and bool(observation["evidence"]), "observation needs captured evidence files")
        for entry in observation["evidence"]:
            require(isinstance(entry, dict) and set(entry) == {"path", "sha256"} and Path(entry["path"]).is_absolute()
                    and file_hash(entry["path"]) == entry["sha256"], "observation evidence checksum mismatch")
    require(observed == set(plan["observations"]), "required observations are missing or unknown")


def prior_review(link, depth=0):
    require(depth < 100, "review reference chain is too deep")
    require(set(link) == {"path", "sha256"} and file_hash(link["path"]) == link["sha256"], "prior review checksum mismatch")
    record = load_record(link["path"])
    snapshot_path = Path(record.get("snapshot_path", Path(link["path"]).parent / "snapshot.json"))
    require(file_hash(snapshot_path) == record["snapshot_sha256"], "prior review snapshot mismatch")
    snapshot = load_record(snapshot_path)
    raw = json.loads(record["execution"].get("agent_message", ""))
    require(record["execution"].get("success") is True, "prior review execution failed")
    require(expand_response(raw, snapshot, snapshot_path, depth + 1) == record["result"], "prior review result differs from execution")
    validate_result(record["result"], snapshot, snapshot_path)
    return record, snapshot


def expand_response(raw, snapshot, snapshot_path, depth=0):
    has_packet = isinstance(raw, dict) and "evidence_packet" in raw
    if has_packet:
        require("checks" not in raw and "observations" not in raw, "packet replaces checks and observations")
        packet = load_packet(raw["evidence_packet"], snapshot, snapshot_path)
        raw = {key: value for key, value in raw.items() if key != "evidence_packet"}
        raw.update(checks=packet["checks"], observations=packet["observations"])
    if not isinstance(raw, dict) or "mode" not in raw:
        return raw
    fields = {"mode", "snapshot_sha256", "previous_review", "reuse_assessment", "affected_paths",
              "coverage", "findings", "checks", "observations", "summary"}
    scope = snapshot["requirements"]["value"].get("review_scope")
    if scope:
        fields.add("scope_approval")
    require(set(raw) == fields and raw["mode"] in {"recheck", "addendum"}, "invalid incremental review fields")
    require(raw["snapshot_sha256"] == file_hash(snapshot_path), "review is bound to a different snapshot")
    require(raw["previous_review"] in snapshot["previous_reviews"], "incremental review must reference a bound prior review")
    require(isinstance(raw["reuse_assessment"], str) and raw["reuse_assessment"].strip(), "reviewer must assess retained coverage and evidence")
    previous, old = prior_review(raw["previous_review"], depth)
    require(old["contract"]["sha256"] == snapshot["contract"]["sha256"], "changed contract requires a full review")
    affected = raw["affected_paths"]
    require(isinstance(affected, list) and all(isinstance(x, str) for x in affected) and len(set(affected)) == len(affected), "invalid affected paths")
    allowed = set(snapshot["source"]["changed_paths"])
    require(set(affected) <= allowed, "affected paths are outside the review scope")
    changed = {name for name in set(old["source"]["files"]) | set(snapshot["source"]["files"])
               if old["source"]["files"].get(name) != snapshot["source"]["files"].get(name)}
    prior = previous["result"]
    result = copy.deepcopy(prior)
    result.update(snapshot_sha256=raw["snapshot_sha256"], summary=raw["summary"])
    if scope:
        result["scope_approval"] = raw["scope_approval"]
    else:
        result.pop("scope_approval", None)
    rows = {row["path"]: row for row in prior["coverage"] if row["path"] in allowed}
    require(isinstance(raw["coverage"], list), "coverage must be a list")
    updates = {}
    for row in raw["coverage"]:
        require(isinstance(row, dict) and isinstance(row.get("path"), str) and row["path"] not in updates, "invalid or duplicate coverage update")
        updates[row["path"]] = row
    exclusion_changes = {name for name in allowed if old["requirements"]["value"]["exclusions"].get(name)
                         != snapshot["requirements"]["value"]["exclusions"].get(name)}
    require(((changed & allowed) | set(affected) | (allowed - set(rows)) | exclusion_changes) <= set(updates),
            "changed or affected paths need fresh coverage")
    rows.update(updates)
    result["coverage"] = list(rows.values())
    findings = {finding["id"]: finding for finding in prior["findings"]}
    require(isinstance(raw["findings"], list), "findings must be a list")
    seen = set()
    for finding in raw["findings"]:
        require(isinstance(finding, dict) and isinstance(finding.get("id"), str) and finding["id"] not in seen, "invalid or duplicate finding update")
        seen.add(finding["id"])
        if raw["mode"] == "addendum":
            before = findings.get(finding["id"], {})
            require(all(finding.get(key) == before.get(key) for key in ("id", "path", "severity", "status")), "addendum cannot change finding disposition")
        findings[finding["id"]] = finding
    result["findings"] = list(findings.values())
    require(isinstance(raw["checks"], dict) and isinstance(raw["observations"], list), "invalid evidence updates")
    result["checks"] = {**({} if has_packet else prior["checks"]), **raw["checks"]}
    observations = {} if has_packet else {row["id"]: row for row in prior["observations"]}
    seen = set()
    for row in raw["observations"]:
        require(isinstance(row, dict) and isinstance(row.get("id"), str) and row["id"] not in seen, "invalid or duplicate observation update")
        seen.add(row["id"])
        observations[row["id"]] = row
    result["observations"] = list(observations.values())
    require(fresh_observations(old, snapshot) <= seen, "changed context or inputs require fresh observations")
    if raw["mode"] == "addendum":
        require(old["source_id"] == snapshot["source_id"] and old["requirements"]["value"] == snapshot["requirements"]["value"],
                "addendum requires unchanged source and requirements")
        require(not affected and not raw["coverage"] and not raw["checks"] and not raw["observations"], "addendum may only correct review prose")
    return result


def transfer_check(from_snapshot, to_snapshot, check_path, assessment_path):
    """Copy no command output; bind an identical-content check through explicit provenance."""
    old = load_record(from_snapshot)
    target = current_snapshot(to_snapshot)
    check = load_record(check_path)
    require("transfer" not in check, "transfer directly from the original captured check")
    definition = check_definition(target, check["definition"]["id"])
    require(validate_check(check_path, old, definition), "only a passing captured check can transfer")
    transfer = {"snapshot": {"path": str(Path(from_snapshot).resolve()), "sha256": file_hash(from_snapshot)},
                "check": {"path": str(Path(check_path).resolve()), "sha256": file_hash(check_path)},
                "assessment": {"path": str(Path(assessment_path).resolve()), "sha256": file_hash(assessment_path)}}
    payload = {**check, "snapshot_path": str(Path(to_snapshot).resolve()), "snapshot_sha256": file_hash(to_snapshot), "source_id": target["source_id"], "transfer": transfer}
    validate_transfer(payload, target, definition)
    return write_record(Path(to_snapshot).parent / "checks" / definition["id"] / "result.json", payload)


def validate_transfer(check, target, definition):
    require(not definition.get("fresh"), "required fresh checks cannot transfer")
    links = check["transfer"]
    require(set(links) == {"snapshot", "check", "assessment"}, "invalid transfer links")
    for link in links.values():
        require(set(link) == {"path", "sha256"} and file_hash(link["path"]) == link["sha256"], "transfer evidence checksum mismatch")
    old = load_record(links["snapshot"]["path"])
    original = load_record(links["check"]["path"])
    require("transfer" not in original, "nested transfer is not permitted")
    require(old["source_id"] == digest(old["source"]), "invalid transfer source")
    require(original["snapshot_sha256"] == links["snapshot"]["sha256"], "original check snapshot differs")
    if "inputs" in definition:
        require(input_identity(old["source"], definition["inputs"]) == input_identity(target["source"], definition["inputs"]),
                "transfer check inputs differ")
    else:
        require(content_identity(old["source"]) == content_identity(target["source"]), "transfer source content differs")
    require(old["contract"]["sha256"] == target["contract"]["sha256"], "transfer contract differs")
    require(context_identity(old["requirements"]["value"]["context"]) == context_identity(target["requirements"]["value"]["context"]), "transfer context differs")
    require(check_definition(old, definition["id"]) == definition, "transfer command definition differs")
    require(validate_check(links["check"]["path"], old, definition), "original check did not pass")
    for key in ("definition", "exit_code", "duration_ms", "timed_out", "source_changed", "logs", "context_id"):
        require(check[key] == original[key], "transferred check changed captured facts")
    assessment = read_json(links["assessment"]["path"])
    require(isinstance(assessment, dict), "environment assessment must be an object")
    require(assessment.get("from_snapshot_sha256") == links["snapshot"]["sha256"]
            and assessment.get("to_source_id") == target["source_id"], "transfer assessment binding differs")
    validate_environment_assessment(assessment)


def validate_environment_assessment(assessment):
    for key in ("runtime", "dependencies", "external_state", "base_interactions"):
        row = assessment.get(key)
        require(isinstance(row, dict) and set(row) == {"reason", "evidence"}
                and isinstance(row["reason"], str) and row["reason"].strip()
                and isinstance(row["evidence"], list) and row["evidence"], f"transfer needs fresh {key} evidence")
        for entry in row["evidence"]:
            require(set(entry) == {"path", "sha256"} and file_hash(entry["path"]) == entry["sha256"], "transfer assessment evidence changed")


def select_checks(snapshot_path, from_snapshot=None, checks=None, fresh=()):
    """Select actual commands from captured inputs; never infer dependency independence."""
    target = current_snapshot(snapshot_path)
    definitions = target["requirements"]["value"]["checks"]
    ids = {row["id"] for row in definitions}
    require(set(fresh) <= ids, "unknown required fresh check")
    checks = checks or {}
    require(isinstance(checks, dict) and set(checks) <= ids, "unknown supplied check")
    old = load_record(from_snapshot) if from_snapshot else None
    if old:
        require(old["source_id"] == digest(old["source"]), "invalid prior source")
    changed = sorted(name for name in set(old["source"]["files"]) | set(target["source"]["files"])
                     if old["source"]["files"].get(name) != target["source"]["files"].get(name)) if old else target["source"]["changed_paths"]
    rows = []
    for definition in definitions:
        key = definition["id"]
        action, reason = "run", "no passing captured check supplied"
        if key in fresh or definition.get("fresh"):
            reason = "fresh execution required"
        elif old and key in checks:
            try:
                require(validate_check(checks[key], old, check_definition(old, key)), "prior check failed")
                require(check_definition(old, key) == definition, "command or inputs declaration changed")
                require(old["contract"]["sha256"] == target["contract"]["sha256"], "acceptance contract changed")
                require(context_identity(old["requirements"]["value"]["context"]) == context_identity(target["requirements"]["value"]["context"]), "environment identity changed")
                if "inputs" in definition:
                    require(not set(changed).intersection(definition["inputs"]), "declared check inputs changed")
                else:
                    require(content_identity(old["source"]) == content_identity(target["source"]), "unknown dependencies require whole source scope")
                if old["source_id"] == target["source_id"] and old["requirements"]["value"] == target["requirements"]["value"]:
                    action, reason = "reuse", "passing capture matches source, requirements, and environment"
                else:
                    require("transfer" not in load_record(checks[key]), "transfer from the original capture only")
                    action, reason = "transfer", "unchanged declared inputs; fresh environment and base assessment required"
            except (ValueError, OSError, KeyError, TypeError) as error:
                reason = str(error)
        rows.append({"id": key, "action": action, "reason": reason, "inputs": definition.get("inputs", "whole-source"),
                     **({"check": evidence_link(checks[key])} if action in {"reuse", "transfer"} else {})})
    return {"snapshot": evidence_link(snapshot_path), "changed_paths": changed, "checks": rows}


def evidence_link(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": file_hash(path)}


def prepare_packet(snapshot_path, output, checks=None, observations=None, scope=None):
    """Hash captured artifacts; never infer a result or review judgment."""
    snapshot_path = Path(snapshot_path).resolve()
    snapshot = current_snapshot(snapshot_path)
    plan = snapshot["requirements"]["value"]
    if checks is None:
        checks = {row["id"]: str(snapshot_path.parent / "checks" / row["id"] / "result.json") for row in plan["checks"]
                  if scope is None or row["id"] in scope}
    require(isinstance(checks, dict), "checks must map ids to captured results")
    require(isinstance(observations, list), "observations must explicitly state captured results")
    captured = []
    for row in observations:
        require(isinstance(row, dict) and set(row) == {"id", "result", "evidence"}, "invalid observation fields")
        links = []
        require(isinstance(row["evidence"], list), "observation evidence must be a list")
        for entry in row["evidence"]:
            if isinstance(entry, dict):
                require(set(entry) == {"path", "sha256"} and evidence_link(entry["path"]) == entry,
                        "supplied evidence checksum differs")
                links.append(entry)
            else:
                require(isinstance(entry, str) and Path(entry).is_absolute(), "captured evidence needs absolute paths")
                links.append(evidence_link(entry))
        captured.append({**row, "evidence": links})
    packet = {"snapshot_sha256": file_hash(snapshot_path),
              "checks": {key: str(Path(path).resolve()) for key, path in checks.items()},
              "check_hashes": {key: file_hash(path) for key, path in checks.items()}, "observations": captured}
    if scope is not None:
        packet["scope"] = scope
    validate_packet(packet, snapshot, snapshot_path)
    return write_record(output, packet)


def validate_packet(packet, snapshot, snapshot_path):
    fields = {"snapshot_sha256", "checks", "check_hashes", "observations"}
    require(isinstance(packet, dict) and fields <= set(packet) <= fields | {"scope"}, "invalid evidence packet")
    require(isinstance(packet["checks"], dict) and isinstance(packet["check_hashes"], dict)
            and isinstance(packet["observations"], list), "invalid evidence packet values")
    require(packet["snapshot_sha256"] == file_hash(snapshot_path), "packet belongs to another snapshot")
    plan = snapshot["requirements"]["value"]
    check_ids, observation_ids = {c["id"] for c in plan["checks"]}, set(plan["observations"])
    scope = packet.get("scope", sorted(check_ids | observation_ids))
    require(isinstance(scope, list) and all(isinstance(key, str) for key in scope) and len(set(scope)) == len(scope)
            and set(scope) <= check_ids | observation_ids and (bool(scope) or not (check_ids | observation_ids)), "invalid packet scope")
    expected = check_ids & set(scope)
    require(set(packet["checks"]) == set(packet["check_hashes"]) == expected, "packet checks are incomplete")
    for definition in plan["checks"]:
        key = definition["id"]
        if key not in expected:
            continue
        require(file_hash(packet["checks"][key]) == packet["check_hashes"][key], "packet check checksum mismatch")
        validate_check(packet["checks"][key], snapshot, definition)
    # Validate captured observations without supplying any review conclusions.
    observed = set()
    for row in packet["observations"]:
        require(isinstance(row, dict) and set(row) == {"id", "result", "evidence"} and isinstance(row["id"], str) and row["id"] not in observed, "invalid or duplicate observation")
        observed.add(row["id"])
        require(row["result"] in {"pass", "fail", "skipped"}, "unknown observation result")
        require(isinstance(row["evidence"], list) and bool(row["evidence"]), "observation needs captured evidence files")
        for link in row["evidence"]:
            require(isinstance(link, dict) and set(link) == {"path", "sha256"} and Path(link["path"]).is_absolute()
                    and file_hash(link["path"]) == link["sha256"], "observation evidence checksum mismatch")
    require(observed == observation_ids & set(scope), "packet observations are missing or unknown")


def load_packet(link, snapshot, snapshot_path, allow_partial=False):
    require(isinstance(link, dict) and set(link) == {"path", "sha256"} and Path(link["path"]).is_absolute() and file_hash(link["path"]) == link["sha256"], "evidence packet checksum mismatch")
    packet = load_record(link["path"])
    validate_packet(packet, snapshot, snapshot_path)
    if not allow_partial:
        plan = snapshot["requirements"]["value"]
        require(set(packet["checks"]) == {row["id"] for row in plan["checks"]}
                and {row["id"] for row in packet["observations"]} == set(plan["observations"]),
                "review packet is incomplete; combine scoped unit captures before dispatch")
    return packet


def response_contract(snapshot_path):
    snapshot = current_snapshot(snapshot_path)
    fresh = set(snapshot["requirements"]["value"]["observations"])
    if len(snapshot["previous_reviews"]) == 1:
        _, old = prior_review(snapshot["previous_reviews"][0])
        fresh = fresh_observations(old, snapshot)
    scope = snapshot["requirements"]["value"].get("review_scope")
    return {"snapshot_sha256": file_hash(snapshot_path), "previous_reviews": snapshot["previous_reviews"],
            **({"scope_approval": digest(scope), "review_scope": scope} if scope else {}),
            "coverage_paths": snapshot["source"]["changed_paths"],
            "check_ids": [c["id"] for c in snapshot["requirements"]["value"]["checks"]],
            "observation_ids": snapshot["requirements"]["value"]["observations"],
            "fresh_observation_ids": sorted(fresh), "prior_findings": previous_findings(snapshot)}


def record_review(snapshot_path, result, execution):
    snapshot_path = Path(snapshot_path).resolve()
    snapshot = current_snapshot(snapshot_path)
    raw = result
    result = expand_response(raw, snapshot, snapshot_path)
    validate_result(result, snapshot, snapshot_path)
    require(isinstance(execution, dict) and execution.get("success") is True, "review execution did not succeed")
    require(json.loads(execution.get("agent_message", "")) == raw, "result differs from the recorded reviewer response")
    checks = []
    for definition in snapshot["requirements"]["value"]["checks"]:
        path = Path(result["checks"][definition["id"]]).resolve()
        validate_check(path, snapshot, definition)
        checks.append({"id": definition["id"], "path": str(path), "sha256": file_hash(path)})
    payload = {"schema_version": VERSION, "snapshot_path": str(snapshot_path), "snapshot_sha256": file_hash(snapshot_path), "result": result, "execution": execution, "checks": checks}
    return write_record(snapshot_path.parent / "review.json", payload)


def assess(snapshot_path, base):
    snapshot_path = Path(snapshot_path).resolve()
    snapshot = current_snapshot(snapshot_path, base)
    return assess_record(snapshot_path, snapshot)


def assess_record(snapshot_path, snapshot):
    """Check a review's original evidence; callers enforce current source separately."""
    record = load_record(snapshot_path.parent / "review.json")
    require(record["schema_version"] == VERSION and record["snapshot_sha256"] == file_hash(snapshot_path), "review snapshot mismatch")
    result = record["result"]
    validate_result(result, snapshot, snapshot_path)
    require(record["execution"].get("success") is True and expand_response(json.loads(record["execution"].get("agent_message", "")), snapshot, snapshot_path) == result, "review execution result mismatch")
    plan = snapshot["requirements"]["value"]
    links = record["checks"]
    require(len(links) == len(plan["checks"]) and {x["id"] for x in links} == {x["id"] for x in plan["checks"]}, "check references are incomplete")
    failed_checks = []
    for link in links:
        require(file_hash(link["path"]) == link["sha256"], "check result checksum mismatch")
        require(str(Path(result["checks"][link["id"]]).resolve()) == link["path"], "check result path mismatch")
        if not validate_check(link["path"], snapshot, check_definition(snapshot, link["id"])):
            failed_checks.append(link["id"])
    open_findings = [f["id"] for f in result["findings"] if f["status"] in {"open", "disputed"} or (f["status"] == "deferred" and f["severity"] != "P3")]
    failed_observations = [x["id"] for x in result["observations"] if x["result"] != "pass"]
    status = "needs-work" if open_findings or failed_checks or failed_observations else "ready"
    return {"status": status, "snapshot_sha256": file_hash(snapshot_path), "open_findings": open_findings, "failed_checks": failed_checks, "failed_observations": failed_observations}


def validate_carry_forward(payload, from_snapshot, base):
    require(isinstance(payload, dict) and set(payload) == {"schema_version", "snapshot", "review", "target", "assessment", "evidence_packet"}
            and payload["schema_version"] == VERSION, "invalid carry forward checkpoint")
    for key in ("snapshot", "review", "target", "assessment", "evidence_packet"):
        link = payload[key]
        require(isinstance(link, dict) and set(link) == {"path", "sha256"}
                and Path(link["path"]).is_absolute() and file_hash(link["path"]) == link["sha256"],
                f"carry forward {key} checksum mismatch")
    from_snapshot = Path(from_snapshot).resolve()
    require(payload["snapshot"] == evidence_link(from_snapshot), "carry forward belongs to another original snapshot")
    require(payload["review"] == evidence_link(from_snapshot.parent / "review.json"), "carry forward review binding differs")
    old = snapshot_record(from_snapshot)
    require(assess_record(from_snapshot, old)["status"] == "ready", "original review is not ready")
    scope = old["requirements"]["value"].get("review_scope")
    require(scope is not None, "original review has no approved carry forward scope")
    target_path = Path(payload["target"]["path"])
    target = current_snapshot(target_path, base)
    require(old["contract"] == target["contract"] and old["requirements"] == target["requirements"],
            "carry forward contract or requirements changed")
    require(target["previous_reviews"] == [payload["review"]], "carry forward must retain its original findings")
    before, after = old["source"], target["source"]
    require(all(before[key] == after[key] for key in ("root", "base", "index_sha256"))
            and old["artifact_dir"] == target["artifact_dir"], "carry forward root, base, index, or artifact directory changed")
    require(input_identity(before, scope["inputs"]) == input_identity(after, scope["inputs"]),
            "carry forward dependency inputs changed")
    changed = {name for name in set(before["files"]) | set(after["files"])
               if before["files"].get(name) != after["files"].get(name)}
    allowed = {row["path"]: row for row in scope["changes"]}
    require(changed and changed <= set(allowed), "carry forward contains changes outside the approved scope")
    for name in changed:
        expected = {"kind": "file", "sha256": allowed[name]["content"]["sha256"], "executable": False}
        require(after["files"].get(name) == expected, "carry forward content differs from the exact approved change")
        require(before["files"].get(name, {}).get("kind") not in {"symlink", "deleted"},
                "carry forward cannot replace symbolic links or deleted entries")
    assessment = read_json(payload["assessment"]["path"])
    require(isinstance(assessment, dict), "environment assessment must be an object")
    require(assessment.get("from_snapshot_sha256") == payload["snapshot"]["sha256"]
            and assessment.get("to_source_id") == target["source_id"], "carry forward environment assessment binding differs")
    validate_environment_assessment(assessment)
    packet = load_packet(payload["evidence_packet"], target, target_path)
    for definition in target["requirements"]["value"]["checks"]:
        require(validate_check(packet["checks"][definition["id"]], target, definition), "carry forward check did not pass")
    require(all(row["result"] == "pass" for row in packet["observations"]), "carry forward observation did not pass")
    prior_observations = {row["id"]: row for row in load_record(payload["review"]["path"])["result"]["observations"]}
    fresh = fresh_observations(old, target)
    for row in packet["observations"]:
        if row["id"] in fresh:
            prior_paths = {link["path"] for link in prior_observations[row["id"]]["evidence"]}
            require(all(link["path"] not in prior_paths for link in row["evidence"]),
                    "carry forward requires fresh observation captures")
    current_snapshot(target_path, base)
    return {"status": "ready", "snapshot_sha256": payload["snapshot"]["sha256"],
            "target": payload["target"], "changed_paths": sorted(changed), "scope": "dependency-release-only"}


def carry_forward(from_snapshot, to_snapshot, assessment, packet, output):
    """Keep original review approval separate from current dependency-release evidence."""
    payload = {"schema_version": VERSION, "snapshot": evidence_link(from_snapshot),
               "review": evidence_link(Path(from_snapshot).parent / "review.json"),
               "target": evidence_link(to_snapshot), "assessment": evidence_link(assessment),
               "evidence_packet": evidence_link(packet)}
    validate_carry_forward(payload, from_snapshot, load_record(to_snapshot)["base_ref"])
    return write_record(output, payload)


def assess_carry_forward(link, from_snapshot, base):
    require(isinstance(link, dict) and set(link) == {"path", "sha256"}
            and Path(link["path"]).is_absolute() and file_hash(link["path"]) == link["sha256"],
            "carry forward checkpoint checksum mismatch")
    return validate_carry_forward(load_record(link["path"]), from_snapshot, base)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    prepare_parser = commands.add_parser("prepare", help="freeze source and required evidence before review")
    for name in ("root", "base", "contract", "requirements", "output"):
        prepare_parser.add_argument("--" + name, required=True)
    prepare_parser.add_argument("--artifact-dir")
    prepare_parser.add_argument("--previous-review", action="append", default=[], help="prior review.json; repeat for independent task records")
    check_parser = commands.add_parser("run-check", help="execute one declared command and capture its result")
    check_parser.add_argument("--snapshot", required=True)
    check_parser.add_argument("--id", required=True)
    record_parser = commands.add_parser("record", help="store the structured response from a completed reviewer")
    record_parser.add_argument("--snapshot", required=True)
    record_parser.add_argument("--execution", required=True)
    verify_parser = commands.add_parser("verify", help="check current source, evidence integrity, and readiness")
    verify_parser.add_argument("--snapshot", required=True)
    verify_parser.add_argument("--base", required=True)
    transfer_parser = commands.add_parser("transfer-check", help="reuse a passing check on identical content with explicit environment evidence")
    for name in ("from-snapshot", "to-snapshot", "check", "assessment"):
        transfer_parser.add_argument("--" + name, required=True)
    carry_parser = commands.add_parser("carry-forward", help="capture dependency release for exact changes approved by the original reviewer")
    for name in ("from-snapshot", "to-snapshot", "assessment", "packet", "output"):
        carry_parser.add_argument("--" + name, required=True)
    packet_parser = commands.add_parser("prepare-packet", help="validate and hash all captured evidence before reviewer dispatch")
    for name in ("snapshot", "output", "observations"):
        packet_parser.add_argument("--" + name, required=True)
    packet_parser.add_argument("--checks", help="JSON map of check ids to captured result paths; defaults to snapshot checks")
    packet_parser.add_argument("--id", action="append", help="declared unit check or observation id; repeat for a scoped unit packet")
    contract_parser = commands.add_parser("response-contract", help="show exact response requirements before dispatch")
    contract_parser.add_argument("--snapshot", required=True)
    selection_parser = commands.add_parser("select-checks", help="select affected commands and checked reuse from declared inputs")
    selection_parser.add_argument("--snapshot", required=True)
    selection_parser.add_argument("--from-snapshot")
    selection_parser.add_argument("--checks", help="JSON map of check ids to original captured result paths")
    selection_parser.add_argument("--fresh", action="append", default=[], help="required fresh check id; repeat for multiple checks")
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            result = {"snapshot": str(prepare(args.root, args.base, args.contract, args.requirements, args.output, args.artifact_dir, args.previous_review))}
        elif args.action == "run-check":
            path = run_check(args.snapshot, args.id)
            result = {"check": str(path), "passed": validate_check(path, load_record(args.snapshot), check_definition(load_record(args.snapshot), args.id))}
        elif args.action == "response-contract":
            result = response_contract(args.snapshot)
        elif args.action == "select-checks":
            result = select_checks(args.snapshot, args.from_snapshot, read_json(args.checks) if args.checks else None, args.fresh)
        elif args.action == "prepare-packet":
            path = prepare_packet(args.snapshot, args.output, read_json(args.checks) if args.checks else None, read_json(args.observations), args.id)
            result = {"evidence_packet": evidence_link(path)}
        elif args.action == "record":
            execution = read_json(args.execution)
            result = {"review": str(record_review(args.snapshot, json.loads(execution.get("agent_message", "")), execution))}
        elif args.action == "transfer-check":
            result = {"check": str(transfer_check(args.from_snapshot, args.to_snapshot, args.check, args.assessment))}
        elif args.action == "carry-forward":
            result = {"carry_forward": evidence_link(carry_forward(args.from_snapshot, args.to_snapshot, args.assessment, args.packet, args.output))}
        else:
            result = assess(args.snapshot, args.base)
        print(json.dumps(result))
        return 1 if result.get("status") == "needs-work" or result.get("passed") is False else 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
