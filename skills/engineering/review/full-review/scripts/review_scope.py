#!/usr/bin/env python3
"""Compute deterministic scope signals for full-review.

Reports diff size, changed-file classes, and risk signals. The approved review
plan selects the scope; this helper supplies evidence and never selects seats.

Adapted from EveryInc/compound-engineering-plugin (MIT). See NOTICE at repo root.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

CODE_EXTENSIONS = {
    ".rb", ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs",
    ".java", ".swift", ".kt", ".c", ".cc", ".cpp", ".cs", ".php",
    ".ex", ".exs", ".scala",
}

SIGNAL_PATTERNS = {
    "migrations": re.compile(
        r"db/migrate/|schema\.(rb|sql)|/migrations?/|alembic|flyway|liquibase",
        re.IGNORECASE,
    ),
    "frontend": re.compile(
        r"\.(tsx|jsx|vue|svelte|css|scss|html|erb|haml)$|/components?/|stimulus|turbo",
        re.IGNORECASE,
    ),
    "api": re.compile(
        r"/(routes?|controllers?|api|serializers?|graphql)/|\.proto$|openapi|swagger",
        re.IGNORECASE,
    ),
    "swift-ios": re.compile(r"\.(swift|kt|pbxproj|xcconfig|entitlements)$", re.IGNORECASE),
    # Silent-pass surface: CI/gating, coverage, and test-double infrastructure.
    # These changes can go green while the thing they guard is red, so they are
    # never lite-eligible and always draw the adversarial false-pass brief.
    "verification_guard": re.compile(
        r"\.github/workflows/|\.gitlab-ci|\.circleci/|jenkinsfile|azure-pipelines|"
        r"buildkite|(^|/)ci/|codecov|\.coveragerc|(^|/)coverage\.[^/]+$|"
        r"(^|/)__mocks__/|(^|/)mocks?/|conftest\.py|jest\.config|vitest\.config|"
        r"karma\.conf|pytest\.ini|\.pre-commit-config|(^|/)dangerfile",
        re.IGNORECASE,
    ),
}

TEST_PATTERN = re.compile(
    r"(^|/)(tests?|spec|__tests__)/|(^|/)[^/]+[._-](test|spec)\.[^/]+$",
    re.IGNORECASE,
)


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False
    )


def valid_commit(ref: str | None) -> bool:
    if not ref:
        return False
    return git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode == 0


def unique_merge_base(base: str, head: str) -> str | None:
    result = git("merge-base", "--all", base, head)
    candidates = [line for line in result.stdout.splitlines() if line]
    if result.returncode != 0 or len(candidates) != 1:
        return None
    return candidates[0]


def fail_closed(reason: str) -> dict[str, object]:
    return {
        "status": "unknown",
        "reason": reason,
        "changed_code_lines": None,
        "non_code_files": 1,
        "changed_files": [],
        "signals": [],
        "test_files_changed": False,
        "small_local_diff": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head")
    args = parser.parse_args()

    if not valid_commit(args.base):
        print(json.dumps(fail_closed("invalid base endpoint"), sort_keys=True))
        return 0
    if args.head is not None and not valid_commit(args.head):
        print(json.dumps(fail_closed("invalid head endpoint"), sort_keys=True))
        return 0

    diff_args = [args.base]
    if args.head:
        merge_base = unique_merge_base(args.base, args.head)
        if merge_base is None:
            print(json.dumps(fail_closed("merge base unavailable or ambiguous"), sort_keys=True))
            return 0
        diff_args = [merge_base, args.head]

    names = git("diff", "--name-only", *diff_args)
    numstat = git("diff", "--numstat", *diff_args)
    if names.returncode != 0 or numstat.returncode != 0:
        print(json.dumps(fail_closed("git diff failed"), sort_keys=True))
        return 0

    files = sorted(line for line in names.stdout.splitlines() if line)
    executable_lines = 0
    for line in numstat.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3 or Path(parts[2]).suffix.lower() not in CODE_EXTENSIONS:
            continue
        try:
            executable_lines += int(parts[0]) + int(parts[1])
        except ValueError:
            # Binary and unknown counts are excluded from the code-line total.
            pass

    uncounted = sum(
        1 for file in files if Path(file).suffix.lower() not in CODE_EXTENSIONS
    )
    signals = [
        name
        for name, pattern in SIGNAL_PATTERNS.items()
        if any(pattern.search(file) for file in files)
    ]
    small_local_diff = 1 <= executable_lines <= 39 and uncounted == 0 and not signals

    result = {
        "status": "complete",
        "reason": None,
        "changed_code_lines": executable_lines,
        "non_code_files": uncounted,
        "changed_files": files,
        "signals": signals,
        "test_files_changed": any(TEST_PATTERN.search(file) for file in files),
        "small_local_diff": small_local_diff,
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
