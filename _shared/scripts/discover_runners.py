#!/usr/bin/env python3
"""Preflight probe for runner-skill availability.

Standardized seat discovery shared by skills that fan work out across multiple
model runners (full-review, models-roundtable, council, dynamic-harness, …).
Probes the CLIs each runner depends on and emits a stable JSON envelope that
callers can parse to build their seat table.

Usage:
    python3 discover_runners.py probe [--native-agent {yes,no,unknown}]
                                       [--seat NAME ...]
                                       [--preset {off,light,quality}]
                                       [--format {json,text,md}]
                                       [--version-timeout SECONDS]

Default: probes every known seat, with `--native-agent unknown`, JSON output.

Notes:
  * The native `Agent` tool (used to spawn Opus/Sonnet inside Claude Code) is
    only visible to the agent invoking this script, not to the script itself.
    Pass `--native-agent yes` when you are running inside a Claude Code host
    that exposes it; the probe will then mark `opus`/`sonnet` as available via
    `agent_native` regardless of whether the `claude` CLI is on PATH. With
    `unknown` (default) or `no`, the probe falls back to checking the `claude`
    CLI for the claude-runner execution path.
  * Quorum signals (`light_quorum_met`, `quality_quorum_met`) are advisory —
    callers can choose to proceed under degraded posture.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

SCHEMA_VERSION = 1

LIGHT_QUORUM = 2
QUALITY_QUORUM = 3


@dataclass(frozen=True)
class SeatSpec:
    seat: str
    execution_path: str
    probe_cli: str
    depends_on: tuple[str, ...] = ()
    version_args: tuple[str, ...] = ("--version",)
    fallback_version_args: tuple[tuple[str, ...], ...] = (("-V",), ("version",))
    notes: str = ""


# Seat → probe table. Keep in sync with full-review SKILL.md Phase 3 and
# models-roundtable SKILL.md Preflight step 1.
SEAT_SPECS: tuple[SeatSpec, ...] = (
    SeatSpec(
        seat="opus",
        execution_path="claude_runner",
        probe_cli="claude",
        notes="Prefer the native Agent tool when --native-agent yes is set; otherwise falls back to claude-runner CLI.",
    ),
    SeatSpec(
        seat="sonnet",
        execution_path="claude_runner",
        probe_cli="claude",
        notes="Prefer the native Agent tool when --native-agent yes is set; otherwise falls back to claude-runner CLI.",
    ),
    SeatSpec(
        seat="codex",
        execution_path="codex_runner",
        probe_cli="codex",
    ),
    SeatSpec(
        seat="gemini",
        execution_path="gemini_runner",
        probe_cli="agy",
        notes="Antigravity CLI (`agy`).",
    ),
    SeatSpec(
        seat="kimi",
        execution_path="kimi_runner",
        probe_cli="kimi-cli",
    ),
    SeatSpec(
        seat="glm",
        execution_path="glm_runner_via_dcode",
        probe_cli="dcode",
        depends_on=("dcode",),
        notes="dcode-backed shim; requires the dcode CLI configured with a GLM provider in ~/.deepagents/.",
    ),
)

CLAUDE_SEATS = frozenset({"opus", "sonnet"})


@dataclass
class SeatProbe:
    seat: str
    execution_path: str
    probe_cli: str
    available: bool
    version: Optional[str] = None
    cli_path: Optional[str] = None
    blocked_reason: Optional[str] = None
    depends_on: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "seat": self.seat,
            "execution_path": self.execution_path,
            "probe_cli": self.probe_cli,
            "available": self.available,
            "version": self.version,
            "cli_path": self.cli_path,
            "blocked_reason": self.blocked_reason,
            "depends_on": list(self.depends_on),
            "notes": self.notes,
        }


def _probe_version(cli_path: str, spec: SeatSpec, timeout: float) -> Optional[str]:
    candidate_arg_lists: tuple[tuple[str, ...], ...] = (spec.version_args, *spec.fallback_version_args)
    for args in candidate_arg_lists:
        try:
            result = subprocess.run(
                [cli_path, *args],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            stdout = (result.stdout or "").strip()
            if stdout:
                return stdout.splitlines()[0].strip()
            stderr = (result.stderr or "").strip()
            if stderr:
                return stderr.splitlines()[0].strip()
    return None


def probe_seat(spec: SeatSpec, native_agent: str, version_timeout: float) -> SeatProbe:
    if spec.seat in CLAUDE_SEATS and native_agent == "yes":
        return SeatProbe(
            seat=spec.seat,
            execution_path="agent_native",
            probe_cli=spec.probe_cli,
            available=True,
            cli_path=None,
            depends_on=spec.depends_on,
            notes="Native Agent tool reported by host (--native-agent yes).",
        )

    cli_path = shutil.which(spec.probe_cli)
    if cli_path is None:
        blocked = f"{spec.probe_cli!r} not found on PATH"
        if spec.depends_on:
            blocked += f" (depends on {', '.join(spec.depends_on)})"
        return SeatProbe(
            seat=spec.seat,
            execution_path=spec.execution_path,
            probe_cli=spec.probe_cli,
            available=False,
            cli_path=None,
            blocked_reason=blocked,
            depends_on=spec.depends_on,
            notes=spec.notes,
        )

    version = _probe_version(cli_path, spec, version_timeout)
    return SeatProbe(
        seat=spec.seat,
        execution_path=spec.execution_path,
        probe_cli=spec.probe_cli,
        available=True,
        cli_path=cli_path,
        version=version,
        depends_on=spec.depends_on,
        notes=spec.notes,
    )


def filter_specs(seat_filter: Optional[set[str]]) -> tuple[SeatSpec, ...]:
    if not seat_filter:
        return SEAT_SPECS
    unknown = seat_filter - {s.seat for s in SEAT_SPECS}
    if unknown:
        print(
            f"discover_runners: unknown seat(s): {sorted(unknown)}",
            file=sys.stderr,
        )
        sys.exit(2)
    return tuple(s for s in SEAT_SPECS if s.seat in seat_filter)


def count_distinct_models(probes: list[SeatProbe]) -> int:
    """Count distinct model identities (opus + sonnet collapse into one model family for quorum)."""
    seen: set[str] = set()
    for p in probes:
        if not p.available:
            continue
        # opus and sonnet ship via the same CLI but are distinct models in the
        # roster sense. Count each seat once, but treat duplicate Claude seats
        # honestly — quorum logic in the calling skill decides what to do.
        seen.add(p.seat)
    return len(seen)


def summarize(probes: list[SeatProbe]) -> dict:
    distinct = count_distinct_models(probes)
    return {
        "available": sum(1 for p in probes if p.available),
        "unavailable": sum(1 for p in probes if not p.available),
        "distinct_seats_available": distinct,
        "light_quorum_met": distinct >= LIGHT_QUORUM,
        "quality_quorum_met": distinct >= QUALITY_QUORUM,
        "light_quorum_required": LIGHT_QUORUM,
        "quality_quorum_required": QUALITY_QUORUM,
    }


def apply_preset_filter(probes: list[SeatProbe], preset: Optional[str]) -> list[SeatProbe]:
    if preset is None or preset == "off":
        return probes
    if preset == "light":
        # `light` = two cheap broad-sweep seats. Surface the cheap pool only.
        cheap = {"kimi", "glm"}
        return [p for p in probes if p.seat in cheap]
    if preset == "quality":
        return probes
    raise ValueError(f"unknown preset: {preset}")


def render_text(probes: list[SeatProbe], summary: dict, host: dict) -> str:
    lines: list[str] = []
    lines.append(f"Runner discovery @ {host['checked_at']} ({host['platform']})")
    lines.append("")
    header = f"{'seat':<10} {'status':<11} {'path':<30} {'version':<30} reason/notes"
    lines.append(header)
    lines.append("-" * len(header))
    for p in probes:
        status = "available" if p.available else "missing"
        path = p.cli_path or ("native" if p.execution_path == "agent_native" else "-")
        version = p.version or "-"
        reason = p.blocked_reason or p.notes or ""
        lines.append(f"{p.seat:<10} {status:<11} {path:<30} {version:<30} {reason}")
    lines.append("")
    lines.append(
        f"available={summary['available']} unavailable={summary['unavailable']} "
        f"distinct_seats={summary['distinct_seats_available']} "
        f"light_quorum_met={summary['light_quorum_met']} "
        f"quality_quorum_met={summary['quality_quorum_met']}"
    )
    return "\n".join(lines)


def render_md(probes: list[SeatProbe], summary: dict, host: dict) -> str:
    lines: list[str] = []
    lines.append(f"## Runner Discovery — {host['checked_at']}")
    lines.append("")
    lines.append("| Seat | Status | Path | Version | Reason / notes |")
    lines.append("|---|---|---|---|---|")
    for p in probes:
        status = "available" if p.available else "**missing**"
        path = p.cli_path or ("native" if p.execution_path == "agent_native" else "—")
        version = p.version or "—"
        reason = (p.blocked_reason or p.notes or "").replace("|", "\\|")
        lines.append(f"| `{p.seat}` | {status} | `{path}` | {version} | {reason} |")
    lines.append("")
    lines.append(
        f"_available {summary['available']} · unavailable {summary['unavailable']} · "
        f"distinct seats {summary['distinct_seats_available']} · "
        f"light quorum {'met' if summary['light_quorum_met'] else 'missed'} · "
        f"quality quorum {'met' if summary['quality_quorum_met'] else 'missed'}_"
    )
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="discover_runners",
        description="Probe the runner CLIs each seat depends on and emit a stable seat-availability envelope.",
    )
    sub = parser.add_subparsers(dest="command")

    probe = sub.add_parser("probe", help="Probe seats and emit availability (default).")
    probe.add_argument(
        "--native-agent",
        choices=("yes", "no", "unknown"),
        default="unknown",
        help="Whether the calling host exposes the native Agent tool (Claude Code). Default: unknown.",
    )
    probe.add_argument(
        "--seat",
        action="append",
        default=None,
        help="Restrict to specific seat(s); pass multiple times.",
    )
    probe.add_argument(
        "--preset",
        choices=("off", "light", "quality"),
        default=None,
        help="Filter to the seats a preset would engage (light = cheap broad-sweep pool only; quality = all).",
    )
    probe.add_argument(
        "--format",
        choices=("json", "text", "md"),
        default="json",
    )
    probe.add_argument(
        "--version-timeout",
        type=float,
        default=2.0,
        help="Seconds to wait for `<cli> --version` before giving up. Default: 2.0.",
    )

    args = parser.parse_args(argv)

    # `probe` is the default and only subcommand today.
    if args.command not in (None, "probe"):
        parser.error(f"unknown command: {args.command}")
        return 2

    seat_filter = set(args.seat) if getattr(args, "seat", None) else None
    specs = filter_specs(seat_filter)

    native_agent = getattr(args, "native_agent", "unknown")
    version_timeout = getattr(args, "version_timeout", 2.0)

    probes = [probe_seat(spec, native_agent, version_timeout) for spec in specs]
    probes = apply_preset_filter(probes, getattr(args, "preset", None))

    summary = summarize(probes)
    host = {
        "platform": sys.platform,
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "native_agent": native_agent,
    }

    fmt = getattr(args, "format", "json")
    if fmt == "json":
        envelope = {
            "schema_version": SCHEMA_VERSION,
            "host": host,
            "seats": [p.to_dict() for p in probes],
            "summary": summary,
        }
        json.dump(envelope, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    elif fmt == "text":
        print(render_text(probes, summary, host))
    elif fmt == "md":
        print(render_md(probes, summary, host))
    else:  # pragma: no cover
        raise AssertionError(f"unreachable format: {fmt}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
