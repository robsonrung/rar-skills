#!/usr/bin/env python3
"""Mechanical guards for skill hygiene. CI-safe: no network, no LLM judgment.

Checks, across every top-level skill dir (any dir containing SKILL.md):
  1. SKILL.md opens with YAML frontmatter delimited by --- lines, and that
     frontmatter parses as strict YAML. Harnesses that load skills with a real
     YAML parser (OpenHands and other AgentSkills hosts) silently drop a skill
     whose unquoted description contains ": " — quote it or use a block scalar.
  2. `name:` present, equal to the directory name, and matching the AgentSkills
     pattern (lowercase alphanumerics and hyphens — an underscore makes the
     skill undiscoverable on AgentSkills hosts). Upstream prefixes like `ce-`
     are banned in skill names.
  3. `description:` present and at least 20 characters (enough to route on).
  4. Runner parity: every `*-runner/` dir ships scripts/run_<prefix>.py and is
     either registered in _shared/scripts/discover_runners.py or explicitly
     allowlisted below as a non-seat runner. A new runner dir that is neither
     fails CI — adding a runner skill without registering its seat is the
     drift this guard exists to catch.

Run: python3 _shared/scripts/validate_skill_frontmatter.py
Exit 0 on success, 1 with a FAIL line per violation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # keep the guard runnable without the dep
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[2]

# AgentSkills name rule: lowercase alphanumerics separated by single hyphens.
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Runner dirs that intentionally have no seat in discover_runners.py:
# transport delegates and seats dropped from the council lineup.
NON_SEAT_RUNNERS = {
    "dcode-runner",     # manual-only runner; no council seat (see _shared/references/model-roster.md)
    "gemma-runner",     # dropped from council lineup
    "minimax-runner",   # dropped from council lineup
    "opencode-runner",  # not part of the seat catalog
    "qwen-runner",      # dropped from council lineup
}

BANNED_NAME_PREFIXES = ("ce-",)

# _shared/SKILL.md is a marker, not a skill: it stops AgentSkills hosts from
# pinning every file under _shared/references/ into the system prompt as an
# always-on legacy skill. Its name is intentionally not AgentSkills-valid so
# hosts skip loading it. See _shared/SKILL.md.
NOT_A_SKILL = {"_shared"}

# AgentSkills hosts truncate descriptions at this length, cutting off the
# "Use when ... / Do not use ..." tail that routing depends on.
DESCRIPTION_TRUNCATION_LIMIT = 1024


def check_frontmatter(failures: list[str], warnings: list[str]) -> int:
    count = 0
    for skill_md in sorted(REPO_ROOT.glob("*/SKILL.md")):
        if skill_md.parent.name in NOT_A_SKILL:
            continue
        count += 1
        rel = skill_md.relative_to(REPO_ROOT)
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not m:
            failures.append(f"{rel}: missing YAML frontmatter")
            continue
        fm = m.group(1)
        if yaml is not None:
            try:
                yaml.safe_load(fm)
            except yaml.YAMLError as exc:
                detail = str(exc).splitlines()[0]
                failures.append(
                    f"{rel}: frontmatter is not valid YAML ({detail}) — AgentSkills "
                    "hosts drop this skill; quote the value or use a >- block scalar"
                )
        name = re.search(r"^name:\s*(.+)$", fm, re.M)
        if not name:
            failures.append(f"{rel}: frontmatter has no name:")
        else:
            n = name.group(1).strip().strip("\"'")
            if n != skill_md.parent.name:
                failures.append(f"{rel}: name {n!r} != directory {skill_md.parent.name!r}")
            if not SKILL_NAME_RE.match(n):
                failures.append(
                    f"{rel}: name {n!r} is not AgentSkills-compatible — use lowercase "
                    "alphanumerics separated by single hyphens"
                )
            for prefix in BANNED_NAME_PREFIXES:
                if n.startswith(prefix):
                    failures.append(f"{rel}: name {n!r} carries banned upstream prefix {prefix!r}")
        desc = extract_description(fm)
        if desc is None:
            failures.append(f"{rel}: frontmatter has no description:")
        elif len(desc) < 20:
            failures.append(f"{rel}: description under 20 chars — too thin to route on")
        elif len(desc) > DESCRIPTION_TRUNCATION_LIMIT:
            warnings.append(
                f"{rel}: description is {len(desc)} chars — AgentSkills hosts truncate "
                f"at {DESCRIPTION_TRUNCATION_LIMIT}, dropping the routing tail"
            )
    return count


def extract_description(fm: str) -> str | None:
    """Return the description value, handling inline and YAML block scalars
    (>, |, >-, |-). Returns None when the key is absent."""
    m = re.search(r"^description:[ \t]*(.*)$", fm, re.M)
    if not m:
        return None
    first = m.group(1).strip()
    if first and first[0] not in "|>":
        return first.strip("\"'")
    # Block scalar: collect subsequent more-indented lines.
    lines = fm.splitlines()
    start = next(i for i, ln in enumerate(lines) if re.match(r"^description:", ln))
    body = []
    for ln in lines[start + 1:]:
        if ln.strip() == "":
            body.append("")
            continue
        if re.match(r"^\S", ln):  # next top-level key ends the block
            break
        body.append(ln.strip())
    return " ".join(b for b in body if b).strip()


def check_runner_parity(failures: list[str]) -> None:
    discover_src = (REPO_ROOT / "_shared" / "scripts" / "discover_runners.py").read_text(
        encoding="utf-8", errors="replace"
    )
    for runner_dir in sorted(REPO_ROOT.glob("*-runner")):
        if not runner_dir.is_dir():
            continue
        prefix = runner_dir.name.removesuffix("-runner")
        if runner_dir.name in NON_SEAT_RUNNERS:
            # Non-seat runners may be intentionally scriptless (e.g. opencode-runner
            # routes through the host approval flow with no bundled script).
            continue
        script = runner_dir / "scripts" / f"run_{prefix}.py"
        if not script.exists():
            failures.append(f"{runner_dir.name}: missing scripts/run_{prefix}.py")
        if prefix not in discover_src:
            failures.append(
                f"{runner_dir.name}: not registered in discover_runners.py and not in "
                "NON_SEAT_RUNNERS — register the seat or allowlist it deliberately"
            )


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []
    count = check_frontmatter(failures, warnings)
    check_runner_parity(failures)
    for w in warnings:
        print(f"warning: {w}")
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        print(f"{len(failures)} violation(s) across {count} skills.")
        return 1
    suffix = f" ({len(warnings)} warning(s))" if warnings else ""
    print(f"OK: {count} skills pass frontmatter + runner-parity guards{suffix}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
