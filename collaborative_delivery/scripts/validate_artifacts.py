#!/usr/bin/env python3
"""Validate required artifacts and real panel participation for a skill run.

This script is intentionally duplicated byte-identically across the sibling skills
collaborative_delivery, collaborative_discovery, collaborative_specification, and
collaborative_task_design to honor each skill's self-containment contract. When
changing it, apply the same change to all four copies.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import tomllib
except Exception:  # pragma: no cover
    tomllib = None


OK_STATUSES = {"ok", "native_response_recorded"}


def load_toml(path: Path) -> dict[str, Any]:
    if tomllib is None:
        raise RuntimeError("Python 3.11 or newer is required")
    with path.open("rb") as fh:
        return tomllib.load(fh)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_error": str(exc)}


def phase_run_is_complete(run: dict[str, Any], required_roles: list[str]) -> bool:
    results = run.get("results") or []
    by_role = {str(item.get("role")): item for item in results if isinstance(item, dict)}
    for role in required_roles:
        if by_role.get(role, {}).get("status") not in OK_STATUSES:
            return False
    for item in results:
        if isinstance(item, dict) and item.get("required", True) and item.get("status") not in OK_STATUSES:
            return False
    return True


def validate_panel_summary(
    summary_path: Path,
    required_phases: list[str],
    phase_required_roles: dict[str, list[str]],
) -> dict[str, Any]:
    if not summary_path.exists():
        return {
            "ok": False,
            "missing_panel_summary": True,
            "missing_required_phases": required_phases,
            "incomplete_phase_runs": [],
        }

    summary = load_json(summary_path)
    if "_error" in summary:
        return {
            "ok": False,
            "panel_summary_error": summary["_error"],
            "missing_required_phases": required_phases,
            "incomplete_phase_runs": [],
        }

    phase_runs = summary.get("phase_runs")
    if not isinstance(phase_runs, list):
        latest = summary.get("latest_run") or summary
        phase_runs = [latest] if isinstance(latest, dict) else []

    complete_phases: set[str] = set()
    incomplete_phase_runs: list[dict[str, Any]] = []
    for run in phase_runs:
        if not isinstance(run, dict):
            continue
        phase = str(run.get("phase") or "")
        expected_roles = phase_required_roles.get(phase) or list(run.get("required_roles") or [])
        complete = bool(run.get("complete")) and phase_run_is_complete(run, expected_roles)
        if complete:
            complete_phases.add(phase)
        elif phase:
            incomplete_phase_runs.append(
                {
                    "phase": phase,
                    "created_at": run.get("created_at"),
                    "statuses": {
                        str(item.get("role")): item.get("status")
                        for item in (run.get("results") or [])
                        if isinstance(item, dict)
                    },
                }
            )

    missing_required_phases = [phase for phase in required_phases if phase not in complete_phases]
    return {
        "ok": not missing_required_phases,
        "missing_panel_summary": False,
        "required_phases": required_phases,
        "complete_phases": sorted(complete_phases),
        "missing_required_phases": missing_required_phases,
        "incomplete_phase_runs": incomplete_phase_runs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir")
    parser.add_argument(
        "--allow-missing-phases",
        action="store_true",
        help="Only validate required files. Use for partial in-progress runs.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    cfg = load_toml(root / "assets" / "routing.toml")
    skill = cfg.get("skill", {})
    artifact_dir = Path(args.artifact_dir or skill.get("artifact_dir") or ".")
    required_outputs = list(skill.get("required_outputs", []))
    missing_outputs = [name for name in required_outputs if not (artifact_dir / name).exists()]
    required_phases = list(skill.get("required_phases") or cfg.get("phases", {}).keys())
    mandatory = list(skill.get("mandatory_presence", []))
    phase_required_roles = {
        phase: list(dict.fromkeys(list(phase_cfg.get("roles", [])) + mandatory))
        for phase, phase_cfg in cfg.get("phases", {}).items()
    }
    panel_result = validate_panel_summary(
        artifact_dir / "panel_summary.json",
        required_phases,
        phase_required_roles,
    )
    if args.allow_missing_phases:
        panel_ok = not panel_result.get("missing_panel_summary")
    else:
        panel_ok = bool(panel_result.get("ok"))

    result = {
        "skill": skill.get("name"),
        "artifact_dir": str(artifact_dir),
        "required_outputs": required_outputs,
        "missing_outputs": missing_outputs,
        "panel": panel_result,
        "ok": not missing_outputs and panel_ok,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
