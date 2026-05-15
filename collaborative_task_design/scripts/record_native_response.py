#!/usr/bin/env python3
"""Record a native Codex role response for a collaborative skill phase."""
from __future__ import annotations

import argparse
import datetime as _dt
import json
from pathlib import Path
import sys
from typing import Any

try:
    import tomllib
except Exception:  # pragma: no cover
    tomllib = None


OK_STATUSES = {"ok", "native_response_recorded"}


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def get_skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_toml(path: Path) -> dict[str, Any]:
    if tomllib is None:
        raise RuntimeError("Python 3.11 or newer is required for TOML parsing")
    with path.open("rb") as handle:
        return tomllib.load(handle)


def read_content(args: argparse.Namespace) -> tuple[str, str]:
    sources = [bool(args.text), bool(args.from_file)]
    if sum(sources) > 1:
        raise ValueError("Use only one input source: --text, --from-file, or stdin.")
    if args.text:
        return args.text, "text"
    if args.from_file:
        path = Path(args.from_file).expanduser()
        if not path.exists():
            raise FileNotFoundError(str(path))
        return path.read_text(encoding="utf-8"), str(path)
    if not sys.stdin.isatty():
        return sys.stdin.read(), "stdin"
    raise ValueError("Provide response content with --text, --from-file, or stdin.")


def required_roles_for_phase(cfg: dict[str, Any], phase: str) -> list[str]:
    skill = cfg.get("skill", {})
    phase_cfg = cfg.get("phases", {}).get(phase, {})
    roles = list(phase_cfg.get("roles", [])) + list(skill.get("mandatory_presence", []))
    return list(dict.fromkeys(roles))


def role_is_native(cfg: dict[str, Any], role: str) -> bool:
    role_cfg = cfg.get("roles", {}).get(role, {})
    provider_key = role_cfg.get("provider") or role
    provider = cfg.get("providers", {}).get(provider_key, {})
    return provider.get("kind") == "native_codex"


def phase_run_is_complete(run: dict[str, Any]) -> bool:
    required_roles = list(run.get("required_roles") or [])
    results = [item for item in run.get("results", []) if isinstance(item, dict)]
    by_role = {str(item.get("role")): item for item in results}
    for role in required_roles:
        if by_role.get(role, {}).get("status") not in OK_STATUSES:
            return False
    for item in results:
        if item.get("required", True) and item.get("status") not in OK_STATUSES:
            return False
    return True


def write_text(path: Path, content: str, replace: bool, dry_run: bool) -> None:
    if path.exists() and path.read_text(encoding="utf-8").strip() and not replace:
        raise FileExistsError(f"{path} already exists. Use --replace to overwrite it.")
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def update_summary(summary_path: Path, phase: str, role: str, response_path: Path, dry_run: bool) -> dict[str, Any]:
    if not summary_path.exists():
        return {"updated": False, "reason": "panel_summary.json not found"}
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"updated": False, "reason": f"panel_summary.json is invalid JSON: {exc}"}

    phase_runs = summary.get("phase_runs")
    if not isinstance(phase_runs, list):
        return {"updated": False, "reason": "panel_summary.json has no phase_runs list"}

    updated_run = None
    updated_result = None
    for run in reversed(phase_runs):
        if not isinstance(run, dict) or run.get("phase") != phase:
            continue
        for result in run.get("results", []):
            if isinstance(result, dict) and result.get("role") == role:
                result.update(
                    {
                        "status": "ok",
                        "participation": "native_response_recorded",
                        "response_path": str(response_path),
                    }
                )
                result.pop("instruction", None)
                updated_run = run
                updated_result = result
                break
        if updated_result:
            break

    if not updated_result:
        return {"updated": False, "reason": f"no panel result found for {phase}/{role}"}

    updated_run["complete"] = phase_run_is_complete(updated_run)
    complete_phases = sorted(
        {
            str(run.get("phase"))
            for run in phase_runs
            if isinstance(run, dict) and run.get("complete") and run.get("phase")
        }
    )
    required_phases = list(summary.get("required_phases") or [])
    missing_required_phases = [phase_name for phase_name in required_phases if phase_name not in complete_phases]
    summary.update(
        {
            "updated_at": now_iso(),
            "complete_phases": complete_phases,
            "missing_required_phases": missing_required_phases,
            "complete": not missing_required_phases if required_phases else summary.get("complete", False),
            "latest_run": phase_runs[-1] if phase_runs else summary.get("latest_run"),
        }
    )
    if not dry_run:
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"updated": True, "phase_complete": updated_run["complete"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a native Codex role response.")
    parser.add_argument("--phase", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--artifact-dir")
    parser.add_argument("--from-file")
    parser.add_argument("--text")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-unconfigured", action="store_true")
    args = parser.parse_args()

    skill_root = get_skill_root()
    cfg = load_toml(skill_root / "assets" / "routing.toml")
    skill = cfg.get("skill", {})
    artifact_dir = Path(args.artifact_dir or skill.get("artifact_dir") or ".codex_workflow/panel")
    try:
        content, source = read_content(args)
    except Exception as exc:
        raise SystemExit(str(exc))
    if not content.strip():
        raise SystemExit("Native response content is empty.")

    required_roles = required_roles_for_phase(cfg, args.phase)
    if args.role not in required_roles and not args.allow_unconfigured:
        raise SystemExit(f"Role {args.role!r} is not configured for phase {args.phase!r}.")
    if not role_is_native(cfg, args.role) and not args.allow_unconfigured:
        raise SystemExit(f"Role {args.role!r} is not routed to a native_codex provider.")

    response_path = artifact_dir / "native_responses" / f"{args.phase}_{args.role}.md"
    try:
        write_text(response_path, content, replace=args.replace, dry_run=args.dry_run)
    except Exception as exc:
        raise SystemExit(str(exc))
    summary_update = update_summary(artifact_dir / "panel_summary.json", args.phase, args.role, response_path, args.dry_run)
    result = {
        "skill": skill.get("name"),
        "phase": args.phase,
        "role": args.role,
        "response_path": str(response_path),
        "source": source,
        "dry_run": args.dry_run,
        "summary_update": summary_update,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
