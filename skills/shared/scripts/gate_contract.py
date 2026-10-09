#!/usr/bin/env python3
"""Validate versioned planning gates before task approval or dispatch."""

import argparse
import json
import re
from pathlib import Path

FIELDS = {"schema_version", "verdict", "lenses_run", "blocking_findings", "advisory_findings",
          "required_changes", "decision_required", "review_focus"}
NEW_FIELDS = re.compile(r"^\s*(?:\d+\.\s*)?(?:Blocking findings|Advisory findings|Required changes|Review focus):", re.M | re.I)
BLOCK = re.compile(r"^```gate-result\s*\n(.*?)^```\s*$", re.M | re.S)
ID = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*\Z")


def text(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value):
    return isinstance(value, list) and bool(value) and all(text(item) for item in value)


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate gate key: {key}")
        value[key] = item
    return value


def reject_constant(value):
    raise ValueError(f"invalid JSON constant: {value}")


def readiness_errors(task_text) -> list[str]:
    """Return new-format errors; legacy label-only tasks stay with their existing reader."""
    if not isinstance(task_text, str):
        return ["task text must be a string"]
    sections = re.findall(r"^## Gates\s*\n(.*?)(?=^## |\Z)", task_text, re.M | re.S)
    gate_text = "\n".join(sections)
    marked = "gate-result" in task_text or bool(NEW_FIELDS.search(task_text)) or bool(re.search(r'"(?:schema_version|blocking_findings|advisory_findings|required_changes|decision_required|review_focus)"\s*:', gate_text))
    if not marked:
        return []
    if len(sections) != 1:
        return ["new task gate needs exactly one ## Gates section"]
    gates = sections[0]
    blocks = BLOCK.findall(gates)
    if len(blocks) != 1 or task_text.count("```gate-result") != 1:
        return ["new task gate needs exactly one complete gate-result JSON block"]
    try:
        value = json.loads(blocks[0], object_pairs_hook=unique_object,
                           parse_constant=reject_constant)
    except ValueError as error:
        return [f"invalid gate-result JSON: {error}"]
    if not isinstance(value, dict) or set(value) != FIELDS:
        return ["gate-result must contain exactly the versioned required fields"]
    errors = []
    if NEW_FIELDS.search(gates):
        errors.append("new gate details belong only in gate-result JSON, not duplicate prose fields")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        errors.append("unsupported gate-result schema_version; expected 1")
    if value["verdict"] != "proceed":
        errors.append("gate-result verdict must be proceed before approval")
    if value["decision_required"] is not None:
        decision = value["decision_required"]
        if not isinstance(decision, dict) or set(decision) != {"id", "question", "owner"} or not all(text(v) for v in decision.values()) or not ID.fullmatch(decision.get("id", "")):
            errors.append("gate decision needs id, question, and owner, or null")
        errors.append("gate-result has an unresolved decision")
    decision = value["decision_required"]
    decision_label = "none" if decision is None else decision.get("id") if isinstance(decision, dict) else None
    for label, expected in (("Verdict", value["verdict"]), ("Decision required", decision_label)):
        labels = re.findall(r"^\s*(?:\d+\.\s*)?" + label + r":\s*([^\n]+)$", gates, re.M)
        if labels != [expected]:
            errors.append(f"{label}: label must occur once and match gate-result")
    lenses = value["lenses_run"]
    if not isinstance(lenses, list) or any(not isinstance(lens, dict) or set(lens) != {"lens", "risk", "evidence"} or not text(lens["lens"]) or not text(lens["risk"]) or not strings(lens["evidence"]) for lens in lenses):
        errors.append("lenses_run needs lens, risk, and evidence for each entry")
    if not isinstance(value["review_focus"], list) or not all(text(item) for item in value["review_focus"]):
        errors.append("review_focus must be an array of nonempty strings")
    seen = set()
    findings = {}

    def identity(item, fields, kind):
        if not isinstance(item, dict) or set(item) != fields:
            errors.append(f"{kind} has missing or unknown fields")
            return False
        identifier = item["id"]
        if not isinstance(identifier, str) or not ID.fullmatch(identifier) or identifier in seen:
            errors.append(f"{kind} needs a unique stable id")
            return False
        seen.add(identifier)
        return True

    def disposition(item, statuses):
        status = item["status"]
        resolution = item["resolution"]
        if status not in statuses:
            errors.append(f"{item['id']}: invalid status")
        elif status == "open":
            if resolution is not None:
                errors.append(f"{item['id']}: open entries need null resolution")
        elif not isinstance(resolution, dict) or set(resolution) != {"reason", "evidence"} or not text(resolution["reason"]) or not strings(resolution["evidence"]):
            errors.append(f"{item['id']}: closure needs reason and evidence")

    for group in ("blocking_findings", "advisory_findings"):
        if not isinstance(value[group], list):
            errors.append(f"{group} must be an array")
            continue
        for item in value[group]:
            if not identity(item, {"id", "lens", "summary", "evidence", "status", "resolution"}, "finding"):
                continue
            findings[item["id"]] = item
            if not text(item["lens"]) or not text(item["summary"]) or not strings(item["evidence"]):
                errors.append(f"{item['id']}: finding needs lens, summary, and evidence")
            disposition(item, ("open", "resolved", "dismissed"))
            if group == "blocking_findings" and item["status"] == "open":
                errors.append(f"{item['id']}: open blocking finding prevents approval")
    if not isinstance(value["required_changes"], list):
        errors.append("required_changes must be an array")
    else:
        for item in value["required_changes"]:
            if not identity(item, {"id", "finding_id", "summary", "status", "resolution"}, "required change"):
                continue
            if not text(item["summary"]) or not isinstance(item["finding_id"], str) or item["finding_id"] not in findings:
                errors.append(f"{item['id']}: required change needs summary and an existing finding_id")
            disposition(item, ("open", "resolved"))
            if item["status"] == "open":
                errors.append(f"{item['id']}: open required change prevents approval")
            elif isinstance(item["finding_id"], str) and item["finding_id"] in findings and findings[item["finding_id"]]["status"] == "open":
                errors.append(f"{item['id']}: closed change refers to an open finding")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", type=Path, help="Canonical task Markdown file")
    args = parser.parse_args()
    try:
        errors = readiness_errors(args.task.read_text(encoding="utf-8"))
    except OSError as error:
        errors = [str(error)]
    print(json.dumps({"errors": errors}))
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
