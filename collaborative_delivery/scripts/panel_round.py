#!/usr/bin/env python3
"""Run one role-panel phase for a collaborative portable skill.

The runner is deliberately honest about model participation:

* external seats use repo-local runner wrappers with fallback disabled when configured
* native Codex seats produce prompts and require a recorded native response artifact
* panel_summary.json accumulates phase runs instead of overwriting earlier evidence

The script does not pretend that a handoff prompt equals model execution.

This script is intentionally duplicated byte-identically across the sibling skills
collaborative_delivery, collaborative_discovery, collaborative_specification, and
collaborative_task_design to honor each skill's self-containment contract. When
changing it, apply the same change to all four copies.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import textwrap
import time
import traceback
from typing import Any

try:
    import tomllib
except Exception:  # pragma: no cover
    tomllib = None


OK_STATUSES = {"ok", "native_response_recorded"}


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def stamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in value)


def load_toml(path: Path) -> dict[str, Any]:
    if tomllib is None:
        raise RuntimeError("Python 3.11 or newer is required for TOML parsing")
    with path.open("rb") as fh:
        return tomllib.load(fh)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_context(paths: list[str]) -> str:
    sections: list[str] = []
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(raw_path)
        sections.append(f"## Context file: {path}\n\n{read_text(path)}")
    return "\n\n---\n\n".join(sections)


def get_skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(raw_path: str, working_dir: Path, skill_root: Path) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path
    candidates = [
        working_dir / path,
        skill_root / path,
        Path.cwd() / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def template(value: str, variables: dict[str, Any]) -> str:
    out = value
    for key, val in variables.items():
        out = out.replace("{" + key + "}", str(val))
    return out


def parse_native_response_args(items: list[str]) -> dict[str, Path]:
    responses: dict[str, Path] = {}
    for item in items:
        if "=" not in item:
            raise ValueError("--native-response must use ROLE=PATH")
        role, path = item.split("=", 1)
        responses[role.strip()] = Path(path).expanduser()
    return responses


def build_prompt(
    skill: dict[str, Any],
    role_name: str,
    role_cfg: dict[str, Any],
    provider_cfg: dict[str, Any],
    phase: str,
    goal: str,
    context: str,
) -> str:
    skill_name = skill.get("name", "portable skill")
    workflow = skill.get("workflow", "")
    duty = role_cfg.get("duty") or provider_cfg.get("duty") or "Contribute to this phase."
    mandatory = ", ".join(skill.get("mandatory_presence", []))
    return textwrap.dedent(
        f"""
        You are a real participant in a role-based model panel for a Codex skill.

        Skill: {skill_name}
        Phase: {phase}
        Role: {role_name}
        Duty: {duty}
        Mandatory anchor roles for every phase: {mandatory}

        User goal:
        {goal}

        Context:
        {context or "(No additional context file was provided.)"}

        Workflow contract:
        {workflow}

        Return concise Markdown with these sections:
        1. Position
        2. Evidence from context
        3. Risks and contradictions
        4. Recommended decision
        5. Tests or validation needed
        6. Open questions

        Work independently. Do not assume another role will cover your duty.
        Do not claim consensus when there is meaningful disagreement.
        """
    ).strip()


def write_prompt(prompts_dir: Path, phase: str, role: str, prompt: str) -> Path:
    prompts_dir.mkdir(parents=True, exist_ok=True)
    path = prompts_dir / f"{stamp()}_{safe_name(phase)}_{safe_name(role)}.md"
    path.write_text(prompt, encoding="utf-8")
    return path


def record_native_role(
    *,
    provider_cfg: dict[str, Any],
    role: str,
    phase: str,
    prompt_path: Path,
    native_responses_dir: Path,
    native_response_overrides: dict[str, Path],
) -> dict[str, Any]:
    expected_path = native_response_overrides.get(role) or native_responses_dir / f"{phase}_{role}.md"
    result: dict[str, Any] = {
        "role": role,
        "kind": "native_codex",
        "provider": provider_cfg.get("provider", "codex"),
        "model": provider_cfg.get("model"),
        "model_label": provider_cfg.get("model_label"),
        "prompt_path": str(prompt_path),
        "expected_response_path": str(expected_path),
        "required": True,
    }
    if expected_path.exists() and expected_path.read_text(encoding="utf-8").strip():
        result.update(
            {
                "status": "ok",
                "participation": "native_response_recorded",
                "response_path": str(expected_path),
            }
        )
    else:
        result.update(
            {
                "status": "awaiting_native_execution",
                "participation": "prompt_only",
                "instruction": (
                    "Run this native Codex role through the host agent or an allowed "
                    "native Codex subagent, write the response to expected_response_path, "
                    "then rerun this phase or pass --native-response role=path."
                ),
            }
        )
    return result


def load_runner_payload(output_file: Path, stdout: str) -> dict[str, Any]:
    if output_file.exists() and output_file.read_text(encoding="utf-8").strip():
        try:
            return json.loads(output_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return {"success": False, "return_code": -3, "stderr": f"Invalid runner JSON: {exc}"}
    try:
        return json.loads(stdout) if stdout.strip() else {}
    except json.JSONDecodeError:
        return {"success": False, "return_code": -3, "stdout": stdout, "stderr": "Runner did not emit JSON"}


def run_runner_role(
    *,
    provider_cfg: dict[str, Any],
    role_cfg: dict[str, Any],
    role: str,
    phase: str,
    prompt_path: Path,
    output_file: Path,
    stdout_path: Path,
    stderr_path: Path,
    working_dir: Path,
    skill_root: Path,
    dry_run: bool,
) -> dict[str, Any]:
    script_raw = provider_cfg.get("script")
    if not script_raw:
        return {
            "role": role,
            "kind": "runner",
            "provider": provider_cfg.get("provider"),
            "model": provider_cfg.get("model"),
            "status": "missing_runner_script",
            "required": True,
        }

    script = resolve_path(str(script_raw), working_dir, skill_root)
    metadata = {
        "skill": skill_root.name,
        "phase": phase,
        "role": role,
        "provider": provider_cfg.get("provider"),
        "model": provider_cfg.get("model"),
    }
    variables = {
        "phase": phase,
        "role": role,
        "model": provider_cfg.get("model", ""),
        "prompt_file": str(prompt_path),
        "output_file": str(output_file),
        "working_dir": str(working_dir),
    }

    cmd = [
        sys.executable,
        str(script),
        "--prompt-file",
        str(prompt_path),
        "--timeout",
        str(int(provider_cfg.get("timeout_seconds", 900))),
        "--working-dir",
        str(working_dir),
        "--json",
        "--disable-fallback",
        "--output-file",
        str(output_file),
        "--metadata-json",
        json.dumps(metadata, ensure_ascii=False),
    ]
    model = provider_cfg.get("model")
    if model:
        cmd.extend(["--model", str(model)])
    runner_role = role_cfg.get("runner_role") or provider_cfg.get("runner_role")
    if runner_role:
        cmd.extend(["--role", str(runner_role)])
    for arg in provider_cfg.get("runner_args", []):
        cmd.append(template(str(arg), variables))

    command_preview = " ".join(shlex.quote(part) for part in cmd)
    result: dict[str, Any] = {
        "role": role,
        "kind": "runner",
        "provider": provider_cfg.get("provider"),
        "model": provider_cfg.get("model"),
        "model_label": provider_cfg.get("model_label"),
        "runner_script": str(script),
        "prompt_path": str(prompt_path),
        "output_file": str(output_file),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "command_preview": command_preview,
        "required": True,
    }
    if dry_run:
        result["status"] = "dry_run"
        return result
    if not script.exists():
        result.update({"status": "runner_unavailable", "blocked_reason": "missing_runner_script"})
        return result

    started = time.time()
    try:
        completed = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=int(provider_cfg.get("timeout_seconds", 900)) + 30,
        )
        stdout_path.write_text(completed.stdout or "", encoding="utf-8")
        stderr_path.write_text(completed.stderr or "", encoding="utf-8")
        payload = load_runner_payload(output_file, completed.stdout or "")
        success = bool(payload.get("success")) and int(payload.get("return_code", completed.returncode)) == 0
        fallback_reason = payload.get("fallback_reason")
        effective_runner = payload.get("effective_runner")
        requested_runner = provider_cfg.get("runner") or provider_cfg.get("provider")
        lost_independence = bool(fallback_reason) or (
            effective_runner is not None and requested_runner is not None and str(effective_runner) != str(requested_runner)
        )
        status = "ok" if success and not lost_independence else "error"
        if lost_independence:
            status = "fallback_used"
        result.update(
            {
                "status": status,
                "success": success,
                "return_code": payload.get("return_code", completed.returncode),
                "auth_ok": payload.get("auth_ok"),
                "effective_runner": effective_runner,
                "effective_model": payload.get("effective_model"),
                "effective_provider": payload.get("effective_provider"),
                "fallback_reason": fallback_reason,
                "blocked_reason": payload.get("blocked_reason"),
                "elapsed_seconds": round(time.time() - started, 3),
            }
        )
    except Exception as exc:
        stderr_path.write_text(traceback.format_exc(), encoding="utf-8")
        result.update(
            {
                "status": "exception",
                "success": False,
                "return_code": -3,
                "error": repr(exc),
                "elapsed_seconds": round(time.time() - started, 3),
            }
        )
    return result


def run_direct_cli_role(
    *,
    provider_cfg: dict[str, Any],
    role: str,
    phase: str,
    prompt: str,
    prompt_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    variables = {
        "prompt": prompt,
        "phase": phase,
        "role": role,
        "model": provider_cfg.get("model", ""),
        "prompt_file": str(prompt_path),
    }
    cmd = [template(provider_cfg["command"], variables)]
    for arg in provider_cfg.get("args", []):
        cmd.append(template(str(arg), variables))

    result: dict[str, Any] = {
        "role": role,
        "kind": "cli",
        "provider": provider_cfg.get("provider", "cli"),
        "model": provider_cfg.get("model"),
        "prompt_path": str(prompt_path),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "command_preview": " ".join(shlex.quote(part) for part in cmd),
        "required": True,
    }
    if dry_run:
        result["status"] = "dry_run"
        return result

    timeout = int(provider_cfg.get("timeout_seconds", 900))
    started = time.time()
    try:
        completed = subprocess.run(
            cmd,
            input=prompt if provider_cfg.get("prompt_transport") == "stdin" else None,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=os.environ.copy(),
        )
        stdout_path.write_text(completed.stdout or "", encoding="utf-8")
        stderr_path.write_text(completed.stderr or "", encoding="utf-8")
        result.update(
            {
                "status": "ok" if completed.returncode == 0 else "error",
                "success": completed.returncode == 0,
                "return_code": completed.returncode,
                "elapsed_seconds": round(time.time() - started, 3),
            }
        )
    except Exception as exc:
        stderr_path.write_text(traceback.format_exc(), encoding="utf-8")
        result.update(
            {
                "status": "exception",
                "success": False,
                "return_code": -3,
                "error": repr(exc),
                "elapsed_seconds": round(time.time() - started, 3),
            }
        )
    return result


def phase_is_complete(results: list[dict[str, Any]], required_roles: list[str]) -> bool:
    by_role = {str(item.get("role")): item for item in results}
    for role in required_roles:
        if by_role.get(role, {}).get("status") not in OK_STATUSES:
            return False
    for item in results:
        if item.get("required", True) and item.get("status") not in OK_STATUSES:
            return False
    return True


def load_existing_summary(path: Path, skill: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        summary = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"legacy_unparseable_summary": str(path)}
    if "phase_runs" in summary:
        return summary
    return {
        "skill": summary.get("skill") or skill.get("name"),
        "artifact_dir": summary.get("artifact_dir"),
        "legacy_phase_runs": [summary],
        "phase_runs": [],
    }


def update_summary(
    *,
    summary_path: Path,
    skill: dict[str, Any],
    cfg: dict[str, Any],
    base_out: Path,
    run: dict[str, Any],
) -> dict[str, Any]:
    summary = load_existing_summary(summary_path, skill)
    required_phases = skill.get("required_phases") or list(cfg.get("phases", {}).keys())
    phase_runs = list(summary.get("phase_runs", []))
    phase_runs.append(run)
    complete_phases = sorted({item.get("phase") for item in phase_runs if item.get("complete")})
    missing_required_phases = [phase for phase in required_phases if phase not in complete_phases]
    updated = {
        **{k: v for k, v in summary.items() if k not in {"phase_runs", "latest_run"}},
        "skill": skill.get("name"),
        "artifact_dir": str(base_out),
        "updated_at": now_iso(),
        "required_phases": required_phases,
        "complete_phases": complete_phases,
        "missing_required_phases": missing_required_phases,
        "phase_runs": phase_runs,
        "latest_run": run,
        "complete": not missing_required_phases,
    }
    summary_path.write_text(json.dumps(updated, indent=2, ensure_ascii=False), encoding="utf-8")
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one configured model-panel phase.")
    parser.add_argument("--phase", required=True)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--context-file", action="append", default=[])
    parser.add_argument("--out")
    parser.add_argument("--working-dir", default=os.getcwd())
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--roles", help="Comma-separated role override")
    parser.add_argument(
        "--native-response",
        action="append",
        default=[],
        metavar="ROLE=PATH",
        help="Path to an already executed native response for a native role.",
    )
    parser.add_argument(
        "--fail-on-incomplete",
        action="store_true",
        help="Return non-zero when any required role is missing, pending, or failed.",
    )
    args = parser.parse_args()

    skill_root = get_skill_root()
    cfg = load_toml(skill_root / "assets" / "routing.toml")
    skill = cfg.get("skill", {})
    working_dir = Path(args.working_dir).expanduser().resolve()
    phase_cfg = cfg.get("phases", {}).get(args.phase, {})
    configured_roles = list(phase_cfg.get("roles", []))
    if args.roles:
        roles = [role.strip() for role in args.roles.split(",") if role.strip()]
    else:
        roles = list(configured_roles)
    mandatory = list(skill.get("mandatory_presence", []))
    for role in reversed(mandatory):
        if role not in roles:
            roles.insert(0, role)
    required_roles = list(dict.fromkeys(configured_roles + mandatory))
    if not required_roles:
        required_roles = list(dict.fromkeys(roles + mandatory))

    context = read_context(args.context_file)
    native_response_overrides = parse_native_response_args(args.native_response)
    base_out = Path(args.out or skill.get("artifact_dir") or ".codex_workflow/panel")
    prompts_dir = base_out / "prompts"
    transcripts_dir = base_out / "transcripts"
    native_responses_dir = base_out / "native_responses"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    native_responses_dir.mkdir(parents=True, exist_ok=True)

    providers = cfg.get("providers", {})
    role_defs = cfg.get("roles", {})
    results: list[dict[str, Any]] = []
    for role in roles:
        role_cfg = role_defs.get(role, {})
        provider_key = role_cfg.get("provider") or role
        provider_cfg = providers.get(provider_key)
        if not provider_cfg:
            results.append(
                {
                    "role": role,
                    "status": "missing_provider",
                    "provider": provider_key,
                    "required": True,
                }
            )
            continue
        if provider_cfg.get("enabled", True) is False:
            results.append(
                {
                    "role": role,
                    "status": "disabled",
                    "provider": provider_key,
                    "required": True,
                }
            )
            continue

        prompt = build_prompt(skill, role, role_cfg, provider_cfg, args.phase, args.goal, context)
        prompt_path = write_prompt(prompts_dir, args.phase, role, prompt)
        role_stamp = f"{stamp()}_{safe_name(args.phase)}_{safe_name(role)}"
        stdout_path = transcripts_dir / f"{role_stamp}_stdout.txt"
        stderr_path = transcripts_dir / f"{role_stamp}_stderr.txt"
        output_file = transcripts_dir / f"{role_stamp}_output.json"
        kind = provider_cfg.get("kind")
        if kind == "native_codex":
            results.append(
                record_native_role(
                    provider_cfg=provider_cfg,
                    role=role,
                    phase=args.phase,
                    prompt_path=prompt_path,
                    native_responses_dir=native_responses_dir,
                    native_response_overrides=native_response_overrides,
                )
            )
        elif kind == "runner":
            results.append(
                run_runner_role(
                    provider_cfg=provider_cfg,
                    role_cfg=role_cfg,
                    role=role,
                    phase=args.phase,
                    prompt_path=prompt_path,
                    output_file=output_file,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                    working_dir=working_dir,
                    skill_root=skill_root,
                    dry_run=args.dry_run,
                )
            )
        elif kind == "cli":
            results.append(
                run_direct_cli_role(
                    provider_cfg=provider_cfg,
                    role=role,
                    phase=args.phase,
                    prompt=prompt,
                    prompt_path=prompt_path,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                    dry_run=args.dry_run,
                )
            )
        else:
            results.append(
                {
                    "role": role,
                    "status": "unknown_kind",
                    "kind": kind,
                    "provider": provider_key,
                    "required": True,
                }
            )

    run = {
        "phase": args.phase,
        "goal": args.goal,
        "created_at": now_iso(),
        "roles": roles,
        "configured_roles": configured_roles,
        "required_roles": required_roles,
        "role_override": bool(args.roles),
        "mandatory_presence": mandatory,
        "dry_run": bool(args.dry_run),
        "complete": phase_is_complete(results, required_roles),
        "results": results,
    }
    summary = update_summary(
        summary_path=base_out / "panel_summary.json",
        skill=skill,
        cfg=cfg,
        base_out=base_out,
        run=run,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.fail_on_incomplete and not run["complete"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
