#!/usr/bin/env python3
"""Normalize GitHub PR review threads for triage.

Reads the JSON emitted by the GraphQL query documented in
references/github-thread-ops.md (a single document, or the concatenated
stream `gh api graphql --paginate` produces) on stdin and writes one
normalized JSON document to stdout:

  {
    "head_sha": "...",
    "summary": {"total": N, "unresolved": N, "returned": N,
                 "human_gated": N, "bot_only": N, "stale": N},
    "threads": [
      {"id": "...", "path": "...", "line": 42,
       "is_resolved": false, "is_outdated": false, "stale": false,
       "has_human": true, "source": "review-swarm",
       "participants": [{"login": "...", "kind": "bot|human"}],
       "comments": [{"author": "...", "kind": "bot|human",
                      "body": "...", "body_truncated": false,
                      "original_commit": "..."}]}
    ]
  }

Classification rules (the deterministic half of triage — bucketing stays
with the agent):

  - A comment is bot-authored when its login ends in "[bot]", its author
    __typename is "Bot", its login (suffix stripped) is in the known-bot
    list, or its body carries an "Automated comment by" header.
  - A thread has_human when any comment is human-authored. Deleted/ghost
    authors count as human so the human-participation gate errs toward
    deferring.
  - stale = bot-only AND GitHub reports the anchor outdated.

Exit codes: 0 = ok, 2 = malformed input or usage error.
"""
from __future__ import annotations

import argparse
import json
import sys

AUTOMATION_HEADER = "automated comment by"

KNOWN_BOTS = {
    "claude",
    "codecov",
    "codecov-commenter",
    "coderabbit",
    "coderabbitai",
    "codescene",
    "codescene-delta-analysis",
    "copilot",
    "copilot-pull-request-reviewer",
    "cursor",
    "cursor-com",
    "dependabot",
    "devin-ai-integration",
    "gemini-code-assist",
    "github-actions",
    "graphite-app",
    "greptile",
    "greptile-apps",
    "renovate",
    "sonarcloud",
    "sonarqubecloud",
    "sourcery-ai",
    "stamphog",
    "vercel",
}

SOURCE_MARKERS = [
    ("review-swarm", "review-swarm"),
    ("qa swarm", "qa-swarm"),
    ("qa-swarm", "qa-swarm"),
]


def strip_bot_suffix(login: str) -> str:
    return login[: -len("[bot]")] if login.endswith("[bot]") else login


def classify_author(author: dict | None, body: str, known_bots: set[str]) -> tuple[str, str]:
    """Return (login, kind) for one comment."""
    if AUTOMATION_HEADER in (body or "").lower():
        login = (author or {}).get("login") or "ghost"
        return login, "bot"
    if not author or not author.get("login"):
        return "ghost", "human"
    login = author["login"]
    if login.endswith("[bot]") or author.get("__typename") == "Bot":
        return login, "bot"
    if strip_bot_suffix(login).lower() in known_bots:
        return login, "bot"
    return login, "human"


def detect_source(comments: list[dict]) -> str:
    """Name the automation that opened the thread, or 'human'."""
    if not comments:
        return "human"
    first = comments[0]
    body = (first.get("body") or "").lower()
    for marker, name in SOURCE_MARKERS:
        if marker in body:
            return name
    if first["kind"] == "bot":
        return strip_bot_suffix(first["author"]).lower()
    return "human"


def parse_stream(text: str) -> list[dict]:
    """Parse one JSON document or a concatenated stream of them."""
    decoder = json.JSONDecoder()
    docs: list[dict] = []
    idx, length = 0, len(text)
    while idx < length:
        while idx < length and text[idx].isspace():
            idx += 1
        if idx >= length:
            break
        doc, end = decoder.raw_decode(text, idx)
        docs.append(doc)
        idx = end
    if not docs:
        raise ValueError("no JSON documents on stdin")
    return docs


def extract_threads(doc: dict) -> list[dict]:
    if doc.get("errors") and not doc.get("data"):
        raise ValueError(f"GraphQL error: {doc['errors'][0].get('message', 'unknown')}")
    try:
        pr = doc["data"]["repository"]["pullRequest"]
        if pr is None:
            raise ValueError("pull request not found")
        return pr["reviewThreads"]["nodes"] or []
    except (KeyError, TypeError) as exc:
        raise ValueError(f"unexpected payload shape: missing {exc}") from exc


def normalize(
    docs: list[dict],
    head_sha: str | None = None,
    trim: int = 1500,
    include_resolved: bool = False,
    known_bots: set[str] | None = None,
) -> dict:
    bots = set(KNOWN_BOTS)
    if known_bots:
        bots |= {strip_bot_suffix(b).lower() for b in known_bots}

    nodes: list[dict] = []
    for doc in docs:
        nodes.extend(extract_threads(doc))

    threads: list[dict] = []
    total = unresolved = human_gated = bot_only = stale_count = 0
    for node in nodes:
        total += 1
        is_resolved = bool(node.get("isResolved"))
        if not is_resolved:
            unresolved += 1
        if is_resolved and not include_resolved:
            continue

        comments = []
        for c in (node.get("comments") or {}).get("nodes") or []:
            body = c.get("body") or ""
            login, kind = classify_author(c.get("author"), body, bots)
            truncated = len(body) > trim
            comments.append(
                {
                    "author": login,
                    "kind": kind,
                    "body": body[:trim],
                    "body_truncated": truncated,
                    "original_commit": ((c.get("originalCommit") or {}).get("oid")),
                }
            )

        has_human = any(c["kind"] == "human" for c in comments)
        is_outdated = bool(node.get("isOutdated"))
        stale = is_outdated and not has_human
        if not is_resolved:
            if has_human:
                human_gated += 1
            else:
                bot_only += 1
            if stale:
                stale_count += 1

        participants: list[dict] = []
        seen: set[str] = set()
        for c in comments:
            if c["author"] not in seen:
                seen.add(c["author"])
                participants.append({"login": c["author"], "kind": c["kind"]})

        threads.append(
            {
                "id": node.get("id"),
                "path": node.get("path"),
                "line": node.get("line") if node.get("line") is not None else node.get("originalLine"),
                "is_resolved": is_resolved,
                "is_outdated": is_outdated,
                "stale": stale,
                "has_human": has_human,
                "source": detect_source(comments),
                "participants": participants,
                "comments": comments,
            }
        )

    return {
        "head_sha": head_sha,
        "summary": {
            "total": total,
            "unresolved": unresolved,
            "returned": len(threads),
            "human_gated": human_gated,
            "bot_only": bot_only,
            "stale": stale_count,
        },
        "threads": threads,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize PR review threads for triage.")
    parser.add_argument("--head-sha", default=None, help="current PR HEAD sha (recorded in the output)")
    parser.add_argument("--trim", type=int, default=1500, help="max characters kept per comment body")
    parser.add_argument("--include-resolved", action="store_true", help="also emit resolved threads")
    parser.add_argument("--known-bots", default="", help="comma-separated extra bot logins")
    args = parser.parse_args(argv)

    extra = {b.strip() for b in args.known_bots.split(",") if b.strip()}
    try:
        docs = parse_stream(sys.stdin.read())
        result = normalize(
            docs,
            head_sha=args.head_sha,
            trim=args.trim,
            include_resolved=args.include_resolved,
            known_bots=extra,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
