#!/usr/bin/env python3
"""Shared background-job tracking for runner skills.

Runner wrappers call launch_background() to detach a run into a tracked job
under <working-dir>/.ai-workflow/runner-jobs/<job-id>/ (manifest, log, and the
final wrapper envelope as result.json). This module is also the management CLI:

    python3 runner_jobs.py list [--runner NAME]
    python3 runner_jobs.py status [job-id]
    python3 runner_jobs.py result [job-id]
    python3 runner_jobs.py cancel [job-id]
"""

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

JOBS_DIR_PARTS = (".ai-workflow", "runner-jobs")
LOG_TAIL_LINES = 5


def jobs_root(working_dir: Optional[str]) -> Path:
    return Path(working_dir or os.getcwd()).joinpath(*JOBS_DIR_PARTS)


def write_manifest(job_dir: Path, manifest: dict[str, Any]) -> None:
    (job_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_manifest(job_dir: Path) -> Optional[dict[str, Any]]:
    try:
        return json.loads((job_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def launch_background(
    runner_name: str,
    script_path: Path,
    cli_args: list[str],
    working_dir: Optional[str] = None,
    prompt_excerpt: str = "",
    manifest_extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Detach a runner invocation into a tracked job and return a launch summary.

    cli_args is the wrapper's original argv (without the program name); the
    --background flag is stripped here so the child runs in the foreground.
    """
    if "--output-file" in cli_args:
        raise ValueError("--background manages its own result file; remove --output-file")

    child_args = [arg for arg in cli_args if arg not in ("--background", "--json", "-j")]

    job_id = f"{runner_name}-{uuid.uuid4().hex[:8]}"
    job_dir = jobs_root(working_dir) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    result_file = job_dir / "result.json"
    log_file = job_dir / "run.log"
    child_argv = [
        sys.executable,
        str(Path(script_path).resolve()),
        *child_args,
        "--json",
        "--output-file",
        str(result_file),
    ]

    with open(log_file, "ab") as log_handle:
        process = subprocess.Popen(
            child_argv,
            stdout=log_handle,
            stderr=log_handle,
            stdin=subprocess.DEVNULL,
            cwd=working_dir or None,
            start_new_session=True,
        )

    manifest = {
        "job_id": job_id,
        "runner": runner_name,
        "pid": process.pid,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "prompt_excerpt": " ".join(prompt_excerpt.split())[:120],
        "working_dir": working_dir or os.getcwd(),
        "command": " ".join(shlex.quote(part) for part in child_argv),
        "result_file": str(result_file),
        "log_file": str(log_file),
    }
    manifest.update(manifest_extra or {})
    write_manifest(job_dir, manifest)

    return {
        "success": True,
        "background": True,
        "job_id": job_id,
        "runner": runner_name,
        "pid": process.pid,
        "job_dir": str(job_dir),
        "result_file": str(result_file),
        "log_file": str(log_file),
        "hint": f"Check with: python3 {Path(__file__).resolve()} status {job_id}",
    }


def list_jobs(root: Path, runner: Optional[str] = None) -> list[tuple[Path, dict[str, Any]]]:
    if not root.is_dir():
        return []
    jobs = []
    for job_dir in root.iterdir():
        if not job_dir.is_dir():
            continue
        manifest = load_manifest(job_dir)
        if manifest and (runner is None or manifest.get("runner") == runner):
            jobs.append((job_dir, manifest))
    jobs.sort(key=lambda item: item[1].get("started_at") or "", reverse=True)
    return jobs


def resolve_job(root: Path, job_id: Optional[str]) -> tuple[Path, dict[str, Any]]:
    if job_id:
        job_dir = root / job_id
        manifest = load_manifest(job_dir)
        if not manifest:
            raise SystemExit(f"No job named {job_id} under {root}")
        return job_dir, manifest
    jobs = list_jobs(root)
    if not jobs:
        raise SystemExit(f"No runner jobs found under {root}")
    return jobs[0]


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def job_status(job_dir: Path, manifest: dict[str, Any]) -> str:
    if manifest.get("status") == "cancelled":
        return "cancelled"
    result_file = Path(manifest.get("result_file") or job_dir / "result.json")
    if result_file.is_file():
        try:
            result = json.loads(result_file.read_text(encoding="utf-8"))
            return "completed" if result.get("success") else "failed"
        except (OSError, json.JSONDecodeError):
            return "completed"
    if pid_alive(int(manifest.get("pid", -1))):
        return "running"
    return "died"


def log_tail(manifest: dict[str, Any], lines: int = LOG_TAIL_LINES) -> list[str]:
    log_file = manifest.get("log_file")
    if not log_file:
        return []
    try:
        content = Path(log_file).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [line for line in content.splitlines() if line.strip()][-lines:]


def load_result(job_dir: Path, manifest: dict[str, Any]) -> Optional[dict[str, Any]]:
    result_file = Path(manifest.get("result_file") or job_dir / "result.json")
    try:
        return json.loads(result_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def status_payload(job_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": manifest.get("job_id", job_dir.name),
        "runner": manifest.get("runner"),
        "status": job_status(job_dir, manifest),
        "pid": manifest.get("pid"),
        "started_at": manifest.get("started_at"),
        "prompt_excerpt": manifest.get("prompt_excerpt"),
        "role": manifest.get("role"),
        "model": manifest.get("model"),
        "result_file": manifest.get("result_file"),
        "log_file": manifest.get("log_file"),
        "log_tail": log_tail(manifest),
    }


def cmd_list(root: Path, as_json: bool, runner: Optional[str]) -> int:
    jobs = [status_payload(job_dir, manifest) for job_dir, manifest in list_jobs(root, runner)]
    if as_json:
        print(json.dumps(jobs, indent=2, ensure_ascii=False))
    elif not jobs:
        print(f"No runner jobs found under {root}")
    else:
        for job in jobs:
            print(
                f"{job['job_id']}  {job['runner'] or '?':<8}  {job['status']:<9}  "
                f"{job['started_at']}  {job['prompt_excerpt']}"
            )
    return 0


def cmd_status(root: Path, job_id: Optional[str], as_json: bool) -> int:
    job_dir, manifest = resolve_job(root, job_id)
    payload = status_payload(job_dir, manifest)
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"Job:     {payload['job_id']}")
        print(f"Runner:  {payload['runner']}")
        print(f"Status:  {payload['status']}")
        print(f"Started: {payload['started_at']}")
        print(f"Prompt:  {payload['prompt_excerpt']}")
        if payload["log_tail"]:
            print("Log tail:")
            for line in payload["log_tail"]:
                print(f"  {line}")
    return 0


def cmd_result(root: Path, job_id: Optional[str], as_json: bool) -> int:
    job_dir, manifest = resolve_job(root, job_id)
    status = job_status(job_dir, manifest)
    result = load_result(job_dir, manifest)
    if result is None:
        message = f"Job {manifest.get('job_id', job_dir.name)} has no stored result yet (status: {status})"
        if as_json:
            print(json.dumps({"success": False, "status": status, "error": message}, ensure_ascii=False))
        else:
            print(message)
        return 1
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(result.get("agent_message") or result.get("stdout") or "(empty output)")
        if result.get("session_id"):
            print(f"\nSession id: {result['session_id']}")
    return 0 if result.get("success") else 1


def cmd_cancel(root: Path, job_id: Optional[str], as_json: bool) -> int:
    job_dir, manifest = resolve_job(root, job_id)
    status = job_status(job_dir, manifest)
    name = manifest.get("job_id", job_dir.name)
    if status != "running":
        message = f"Job {name} is not running (status: {status})"
        if as_json:
            print(json.dumps({"success": False, "status": status, "error": message}, ensure_ascii=False))
        else:
            print(message)
        return 1

    pid = int(manifest["pid"])
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass

    for _ in range(10):
        if not pid_alive(pid):
            break
        time.sleep(0.2)
    if pid_alive(pid):
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except OSError:
            pass

    manifest["status"] = "cancelled"
    manifest["cancelled_at"] = datetime.now(timezone.utc).isoformat()
    write_manifest(job_dir, manifest)

    if as_json:
        print(json.dumps({"success": True, "job_id": name, "status": "cancelled"}, ensure_ascii=False))
    else:
        print(f"Cancelled job {name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage background runner jobs")
    parser.add_argument(
        "command",
        choices=("list", "status", "result", "cancel"),
        help="Job operation to perform",
    )
    parser.add_argument(
        "job_id",
        nargs="?",
        default=None,
        help="Job id (defaults to the most recent job)",
    )
    parser.add_argument(
        "--working-dir",
        "-w",
        type=str,
        default=None,
        help="Directory whose .ai-workflow/runner-jobs is inspected (default: current dir)",
    )
    parser.add_argument(
        "--runner",
        type=str,
        default=None,
        help="Filter the list command by runner name (codex, claude, gemini, qwen, kimi, ...)",
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Return output in JSON format"
    )
    args = parser.parse_args()

    root = jobs_root(args.working_dir)
    if args.command == "list":
        return cmd_list(root, args.json, args.runner)
    if args.command == "status":
        return cmd_status(root, args.job_id, args.json)
    if args.command == "result":
        return cmd_result(root, args.job_id, args.json)
    return cmd_cancel(root, args.job_id, args.json)


if __name__ == "__main__":
    sys.exit(main())
