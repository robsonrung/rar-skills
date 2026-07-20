#!/usr/bin/env python3
"""Deterministic approval gates for a PR diff.

Classifies a change into an approval tier from `git diff --numstat` output,
with zero model judgment involved:

  T0  only excluded file kinds changed (docs, tests, snapshots, assets,
      lockfiles, generated) — deterministically approvable
  T1  substantive change, no deny-list hits — eligible for the
      showstopper-only agent pass (size ceiling permitting)
  T2  one or more deny-list hits — never auto-approved

The deny-list is evaluated against every changed path, including paths the
size count excludes: a test file touching auth is still an auth change.
False positives are intentional — the safe failure mode is escalating to a
human.

Input modes (exactly one):
  --numstat-file PATH   output of `git diff --numstat -M <base>...<head>`
                        (PATH of '-' reads stdin)
  --git BASE HEAD       run git itself

Output: one JSON document on stdout (tier, blockers, counts, hits).
Exit codes: 0 = evaluated (any tier), 2 = usage or input error.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys


def _words(*words: str) -> str:
    """Regex matching any word delimited by path separators, dots, dashes, or underscores."""
    return r"(?:^|[/_.\-])(?:" + "|".join(words) + r")(?=$|[/_.\-])"


LOCKFILES = (
    r"(?:^|/)(?:package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|uv\.lock|"
    r"cargo\.lock|gemfile\.lock|composer\.lock|go\.sum|flake\.lock|bun\.lockb?)$"
)

DENY_RULES: list[tuple[str, re.Pattern]] = [
    (
        "auth",
        re.compile(
            _words(
                "auth", "authn", "authz", "authentication", "authorization", "authorize",
                "oauth", "oauth2", "saml", "sso", "login", "logout", "session", "sessions",
                "permission", "permissions", "rbac", "acl", "mfa",
            )
        ),
    ),
    (
        "crypto-secrets",
        re.compile(
            _words(
                "crypto", "cryptography", "secret", "secrets", "vault", "credential",
                "credentials", "keychain", "cert", "certs", "certificate", "certificates",
                "token", "tokens", "password", "passwords", "signing", "jwt",
            )
            + r"|(?:^|/)\.env(?:\.[^/]*)?$|\.(?:pem|p12|pfx|crt|cer|jks)$|(?<![a-z0-9])id_rsa"
        ),
    ),
    (
        "migrations",
        re.compile(
            r"(?:^|/)(?:migrations?|alembic)(?:/|$)"
            r"|(?:^|/)(?:schema\.(?:rb|prisma|sql)|structure\.sql)$|\.ddl$"
            + "|" + _words("migration", "migrations", "backfill", "backfills")
        ),
    ),
    (
        "infra-ci",
        re.compile(
            r"(?:^|/)\.github/workflows/|\.(?:tf|tfvars)$"
            r"|(?:^|/)(?:terraform|infra|infrastructure|k8s|kubernetes|helm|charts|ansible|iam)(?:/|$)"
            r"|(?:^|/)dockerfile(?:[._\-][^/]*)?$|(?:^|/)docker-compose[^/]*\.ya?ml$"
            r"|(?:^|/)(?:\.circleci|\.buildkite)(?:/|$)|(?:^|/)jenkinsfile$"
            r"|(?:^|/)\.gitlab-ci\.ya?ml$|(?:^|/)codeowners$"
        ),
    ),
    (
        "billing",
        re.compile(
            _words(
                "billing", "payment", "payments", "stripe", "invoice", "invoices",
                "subscription", "subscriptions", "checkout", "pricing", "refund",
                "refunds", "payout", "payouts",
            )
        ),
    ),
    (
        "public-api",
        re.compile(
            r"(?:openapi|swagger)(?:[/_.\-]|$)|\.proto$"
            r"|(?:^|/)public[_\-]?api(?:[/.]|$)|(?:^|/)api[_\-]?(?:spec|public)"
        ),
    ),
    (
        "dependencies",
        re.compile(
            r"(?:^|/)(?:package\.json|pyproject\.toml|requirements[^/]*\.txt|setup\.(?:py|cfg)|"
            r"go\.mod|cargo\.toml|gemfile|composer\.json|build\.gradle(?:\.kts)?|pom\.xml)$"
            + "|" + LOCKFILES
        ),
    ),
]

EXCLUDE_RULES: list[tuple[str, re.Pattern]] = [
    (
        "docs",
        re.compile(
            r"\.(?:md|mdx|rst|txt|adoc)$|(?:^|/)(?:docs?|documentation)(?:/|$)"
            r"|(?:^|/)(?:license|licence|notice|changelog)[^/]*$"
        ),
    ),
    (
        "tests",
        re.compile(
            r"(?:^|/)(?:tests?|specs?|__tests__|__mocks__|fixtures|testdata)(?:/|$)"
            r"|(?:^|/)test_[^/]+$|_test\.[a-z0-9]+$|\.(?:test|spec)\.[a-z0-9]+$"
            r"|(?:^|/)conftest\.py$"
        ),
    ),
    ("snapshots", re.compile(r"(?:^|/)__snapshots__(?:/|$)|\.(?:snap|ambr)$")),
    (
        "assets",
        re.compile(r"\.(?:png|jpe?g|gif|svg|ico|webp|avif|woff2?|ttf|otf|eot|mp[34]|webm|pdf)$"),
    ),
    ("lockfiles", re.compile(LOCKFILES)),
    (
        "generated",
        re.compile(
            r"(?:^|/)(?:dist|build|out|vendor|node_modules|__pycache__)(?:/|$)"
            r"|\.min\.(?:js|css)$|\.generated\.|_pb2(?:_grpc)?\.py$|\.pb\.go$|\.map$"
        ),
    ),
]

RENAME_BRACES = re.compile(r"\{[^{}]*? => ([^{}]*?)\}")


def resolve_rename(path: str) -> str:
    """Reduce git numstat rename syntax to the post-rename path."""
    path = RENAME_BRACES.sub(r"\1", path)
    if " => " in path:
        path = path.split(" => ")[-1]
    while "//" in path:
        path = path.replace("//", "/")
    return path.lstrip("/")


def parse_numstat(text: str) -> list[dict]:
    entries = []
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            raise ValueError(f"not a numstat line: {line!r}")
        added_s, deleted_s = parts[0].strip(), parts[1].strip()
        path = resolve_rename("\t".join(parts[2:]).strip())
        added = None if added_s == "-" else int(added_s)
        deleted = None if deleted_s == "-" else int(deleted_s)
        entries.append({"path": path, "added": added, "deleted": deleted})
    return entries


def exclusion_reason(path: str) -> str | None:
    low = path.lower()
    for reason, rx in EXCLUDE_RULES:
        if rx.search(low):
            return reason
    return None


def deny_categories(path: str, extra_rules: list[tuple[str, re.Pattern]] | None = None) -> list[str]:
    low = path.lower()
    cats = [cat for cat, rx in DENY_RULES if rx.search(low)]
    for cat, rx in extra_rules or []:
        if rx.search(low) and cat not in cats:
            cats.append(cat)
    return cats


def evaluate(
    entries: list[dict],
    max_lines: int = 800,
    max_files: int = 30,
    extra_rules: list[tuple[str, re.Pattern]] | None = None,
) -> dict:
    files, hits, excluded = [], [], []
    substantive_lines = substantive_files = 0
    for e in entries:
        path = e["path"]
        reason = exclusion_reason(path)
        cats = deny_categories(path, extra_rules)
        files.append(
            {
                "path": path,
                "added": e["added"],
                "deleted": e["deleted"],
                "excluded_reason": reason,
                "deny_categories": cats,
            }
        )
        for cat in cats:
            hits.append({"path": path, "category": cat})
        if reason is None:
            substantive_files += 1
            substantive_lines += (e["added"] or 0) + (e["deleted"] or 0)
        else:
            excluded.append({"path": path, "reason": reason})

    if hits:
        tier = "T2"
    elif substantive_files == 0:
        tier = "T0"
    else:
        tier = "T1"

    blockers = [f"deny-list:{c}" for c in sorted({h["category"] for h in hits})]
    if substantive_lines > max_lines:
        blockers.append(f"size:lines {substantive_lines}>{max_lines}")
    if substantive_files > max_files:
        blockers.append(f"size:files {substantive_files}>{max_files}")

    return {
        "tier": tier,
        "blockers": blockers,
        "substantive_lines": substantive_lines,
        "substantive_files": substantive_files,
        "files_total": len(entries),
        "size_gate": {
            "max_lines": max_lines,
            "max_files": max_files,
            "within": substantive_lines <= max_lines and substantive_files <= max_files,
        },
        "denylist_hits": hits,
        "excluded": excluded,
        "files": files,
    }


def parse_extra_deny(specs: list[str]) -> list[tuple[str, re.Pattern]]:
    rules = []
    for spec in specs:
        category, sep, pattern = spec.partition("=")
        if not sep or not category or not pattern:
            raise ValueError(f"--extra-deny expects CATEGORY=REGEX, got: {spec!r}")
        try:
            rules.append((category, re.compile(pattern, re.IGNORECASE)))
        except re.error as exc:
            raise ValueError(f"--extra-deny {category}: bad regex: {exc}") from exc
    return rules


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic approval gates for a PR diff.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--numstat-file", help="numstat output to read ('-' for stdin)")
    source.add_argument("--git", nargs=2, metavar=("BASE", "HEAD"), help="run git diff --numstat -M BASE...HEAD")
    parser.add_argument("--max-lines", type=int, default=800, help="substantive line ceiling (default 800)")
    parser.add_argument("--max-files", type=int, default=30, help="substantive file ceiling (default 30)")
    parser.add_argument(
        "--extra-deny", action="append", default=[], metavar="CATEGORY=REGEX",
        help="additional deny-list rule (repeatable); regex is matched case-insensitively against each path",
    )
    args = parser.parse_args(argv)

    try:
        extra_rules = parse_extra_deny(args.extra_deny)
        if args.git:
            base, head = args.git
            proc = subprocess.run(
                ["git", "diff", "--numstat", "-M", f"{base}...{head}"],
                capture_output=True, text=True,
            )
            if proc.returncode != 0:
                print(f"error: git diff failed: {proc.stderr.strip()}", file=sys.stderr)
                return 2
            text = proc.stdout
        elif args.numstat_file == "-":
            text = sys.stdin.read()
        else:
            with open(args.numstat_file, encoding="utf-8") as fh:
                text = fh.read()
        report = evaluate(parse_numstat(text), args.max_lines, args.max_files, extra_rules)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    json.dump(report, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
