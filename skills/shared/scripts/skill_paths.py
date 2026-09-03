#!/usr/bin/env python3
"""Locate the skills root and sibling skills in either layout.

Two layouts exist:

* **installed** — every skill is a flat sibling under `.agents/skills/` (or
  `.claude/skills/`), and `shared/` sits next to them;
* **source checkout** — everything sits under `skills/`: skills are grouped as
  `skills/engineering/<group>/<skill>`, `skills/visualization/<skill>`, and
  `skills/extras/<skill>`, with `skills/shared/` next to them. `skills/` is the
  skills root in this layout.

Scripts must never assume a fixed number of `parents[]` between themselves and
`shared/`. Walk up until the directory that owns `shared/scripts/` is found,
then resolve sibling skills by *name* with `skill_dir`.

Bootstrap note: a runner script cannot import this module before it has found
`shared/scripts/`, so each runner carries the same three-line walk-up inline
(see `find_skills_root`) and imports this module afterwards for `skill_dir`.
"""

from __future__ import annotations

from pathlib import Path

_MARKER = ("shared", "scripts", "runner_jobs.py")

# Where a skill may live relative to the skills root, in lookup order.
_SEARCH_GLOBS = ("{name}", "engineering/*/{name}", "visualization/{name}", "extras/{name}", "*/{name}", "*/*/{name}")


def find_skills_root(start: Path) -> Path:
    """Walk up from `start` (a file or directory) to the directory owning `shared/scripts/`."""
    start = Path(start).resolve()
    candidates = [start, *start.parents] if start.is_dir() else list(start.parents)
    for parent in candidates:
        if parent.joinpath(*_MARKER).is_file():
            return parent
    # Flat installed layout without the marker file (partial install): assume
    # <skills>/<skill>/scripts/<file>.
    return start.parents[2] if len(start.parents) > 2 else start.parent


def skill_dir(name: str, root: Path | None = None, start: Path | None = None) -> Path:
    """Return the directory of skill `name` under `root` (found from `start` when omitted).

    Falls back to `<root>/<name>` when the skill is not installed, so callers can
    still report a meaningful missing path.
    """
    if root is None:
        root = find_skills_root(start or Path(__file__))
    for pattern in _SEARCH_GLOBS:
        for candidate in sorted(root.glob(pattern.format(name=name))):
            if candidate.is_dir() and (candidate / "SKILL.md").is_file():
                return candidate
    return root / name


def runner_script(name: str, root: Path | None = None, start: Path | None = None) -> Path:
    """Path of `<name>-runner/scripts/run_<name>.py`, resolved by skill name."""
    return skill_dir(f"{name}-runner", root=root, start=start) / "scripts" / f"run_{name}.py"


def iter_skill_dirs(root: Path):
    """Every directory holding a SKILL.md under `root`, excluding `shared/` and vendored trees."""
    skip = {"node_modules", ".git", "__pycache__", ".worktrees"}
    for skill_md in sorted(root.rglob("SKILL.md")):
        parts = set(skill_md.relative_to(root).parts)
        if parts & skip or skill_md.parent.name == "shared":
            continue
        yield skill_md.parent
