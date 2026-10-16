#!/usr/bin/env python3
"""Render task gates from unchanged shared decisions and assessed task differences."""

import argparse
import copy
import json
import re
import sys
from pathlib import Path

from gate_contract import BLOCK, ID, readiness_errors, reject_constant, text, unique_object
from task_queue import canonical_text_sha256


def require(condition, message):
    if not condition:
        raise ValueError(message)


def object_fields(value, fields, label):
    require(isinstance(value, dict) and set(value) == set(fields),
            f"{label} needs exactly: {', '.join(sorted(fields))}")


def read_json(value):
    return json.loads(value, object_pairs_hook=unique_object, parse_constant=reject_constant)


def local_path(root, value):
    require(text(value) and not Path(value).is_absolute() and "://" not in value,
            "planning inputs need relative local paths")
    relative = Path(value)
    require(str(relative) == value and ".." not in relative.parts,
            f"planning input must use a canonical relative path: {value}")
    path = root / relative
    require(not any(candidate.is_symlink() for candidate in (path, *path.parents) if candidate != root),
            f"planning input must not use symlinks: {value}")
    require(path.is_relative_to(root) and path.is_file(), f"missing or outside-root input: {value}")
    return path


def checked_source(root, entry):
    object_fields(entry, {"path", "content_sha256"}, "source input")
    path = local_path(root, entry["path"])
    content = path.read_text(encoding="utf-8")
    require(canonical_text_sha256(content) == entry["content_sha256"],
            f"planning source changed: {entry['path']}; reassess its decisions")
    return content


def gate_section(gate, security):
    decision = gate.get("decision_required")
    decision_id = decision.get("id") if isinstance(decision, dict) else "none"
    return ("## Gates\nVerdict: " + str(gate.get("verdict")) + "\nDecision required: "
            + str(decision_id) + "\n```gate-result\n" + json.dumps(gate, indent=2)
            + "\n```\nSecurity: " + security["level"] + "; trigger: " + security["trigger"] + "\n")


def valid_gate(gate):
    require(isinstance(gate, dict), "gate must be an object")
    errors = readiness_errors(gate_section(gate, {"level": "standard", "trigger": "validation"}))
    require(not errors, "gate is not ready: " + "; ".join(errors))


def selected_gate(content, decision_id, scope):
    require(isinstance(decision_id, str) and ID.fullmatch(decision_id), "invalid decision ID")
    pattern = r"^## " + re.escape(decision_id) + r": [^\n]+\n(.*?)(?=^## |\Z)"
    sections = re.findall(pattern, content, re.M | re.S)
    require(len(sections) == 1, f"decision {decision_id} needs one exact ## {decision_id}: heading")
    section = sections[0]
    scopes = re.findall(r"^Scope: ([^\n]+)$", section, re.M)
    require(scopes == [scope], f"decision {decision_id} scope is missing or changed")
    blocks = BLOCK.findall(section)
    require(len(blocks) == 1, f"decision {decision_id} needs one canonical gate-result")
    gate = read_json(blocks[0])
    valid_gate(gate)
    return gate


def merge_gates(gates):
    merged = copy.deepcopy(gates[0])
    for incoming in gates[1:]:
        for field in ("lenses_run", "blocking_findings", "advisory_findings", "required_changes", "review_focus"):
            for item in incoming[field]:
                if field in ("blocking_findings", "advisory_findings", "required_changes"):
                    matches = [(name, found) for name in ("blocking_findings", "advisory_findings", "required_changes")
                               for found in merged[name] if found["id"] == item["id"]]
                    require(not matches or matches == [(field, item)],
                            f"conflicting shared finding or disposition: {item['id']}")
                if item not in merged[field]:
                    merged[field].append(copy.deepcopy(item))
    valid_gate(merged)
    return merged


def render(request_path, root):
    root = Path(root).resolve()
    request_path = Path(request_path)
    if request_path.is_absolute():
        require(request_path.is_relative_to(root), "request must be inside root")
        request_path = request_path.relative_to(root)
    request_path = local_path(root, str(request_path))
    request_text = request_path.read_text(encoding="utf-8")
    request = read_json(request_text)
    object_fields(request, {"schema_version", "shared", "sources", "task"}, "render request")
    require(type(request["schema_version"]) is int and request["schema_version"] == 1,
            "unsupported planning render request version")
    require(isinstance(request["shared"], list) and request["shared"], "select at least one shared decision")
    require(isinstance(request["sources"], list), "sources must list checked source revisions")
    source_paths = set()
    for entry in request["sources"]:
        checked_source(root, entry)
        path = local_path(root, entry["path"])
        require(path not in source_paths, "duplicate source input")
        source_paths.add(path)
    task = request["task"]
    object_fields(task, {"id", "surfaces", "assessment", "security", "gate"}, "task assessment")
    require(isinstance(task["id"], str) and re.fullmatch(r"T[1-9][0-9]*", task["id"]), "invalid task ID")
    require(text(task["assessment"]), "task risk assessment is required")
    security = task["security"]
    object_fields(security, {"level", "trigger"}, "task security")
    require(security["level"] in ("deep", "standard") and text(security["trigger"])
            and "\n" not in security["trigger"] and "\r" not in security["trigger"],
            "task security needs deep or standard and one explicit trigger line")
    valid_gate(task["gate"])
    inputs = {request_path: canonical_text_sha256(request_text)}
    decisions = {}
    gates = []
    for entry in request["shared"]:
        object_fields(entry, {"decision_id", "path", "content_sha256", "scope"}, "shared decision")
        require(text(entry["scope"]), "shared decision needs explicit scope")
        decision_id = entry["decision_id"]
        require(isinstance(decision_id, str) and decision_id not in decisions, "duplicate or invalid decision ID")
        content = checked_source(root, {key: entry[key] for key in ("path", "content_sha256")})
        gate = selected_gate(content, decision_id, entry["scope"])
        decisions[decision_id] = entry["scope"]
        path = local_path(root, entry["path"])
        inputs[path] = entry["content_sha256"]
        gate["review_focus"].append(f"Shared decision {decision_id}: {entry['path']}#{decision_id}")
        gates.append(gate)
    require(isinstance(task["surfaces"], list) and task["surfaces"], "task surfaces must be explicitly assessed")
    reused = set()
    surfaces = set()
    for surface in task["surfaces"]:
        object_fields(surface, {"scope", "decision_id", "status"}, "task surface")
        require(text(surface["scope"]) and surface["scope"] not in surfaces, "duplicate or missing task scope")
        surfaces.add(surface["scope"])
        if surface["status"] == "unchanged":
            identifier = surface["decision_id"]
            require(isinstance(identifier, str) and decisions.get(identifier) == surface["scope"],
                    "unchanged task scope must match a selected shared decision")
            reused.add(identifier)
        else:
            require(surface["status"] == "assessed" and surface["decision_id"] is None,
                    "unknown or changed scope cannot reuse a shared decision; assess the affected scope")
    require(reused == set(decisions), "every selected decision needs an unchanged task scope match")
    task["gate"]["review_focus"].append("Task risk assessment: " + task["assessment"])
    gates.append(task["gate"])
    merged = merge_gates(gates)
    for entry in request["sources"]:
        checked_source(root, entry)
    for path, digest in inputs.items():
        checked_source(root, {"path": str(path.relative_to(root)), "content_sha256": digest})
    return {"task_id": task["id"], "gate_section": gate_section(merged, security),
            "scope_inputs": [{"path": str(path.relative_to(root)), "content_sha256": digest}
                             for path, digest in sorted(inputs.items())],
            "checked_sources": request["sources"], "approval_granted": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--request", type=Path, help="Saved task render request inside the project")
    mode.add_argument("--hash-input", action="append", help="Print canonical source input identity; repeat for each path")
    parser.add_argument("--root", type=Path, required=True, help="Project root; source paths resolve here")
    args = parser.parse_args()
    try:
        if args.hash_input:
            root = args.root.resolve()
            result = [{"path": str(local_path(root, value).relative_to(root)),
                       "content_sha256": canonical_text_sha256(local_path(root, value).read_text(encoding="utf-8"))}
                      for value in args.hash_input]
        else:
            result = render(args.request, args.root)
        print(json.dumps(result, indent=2))
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
