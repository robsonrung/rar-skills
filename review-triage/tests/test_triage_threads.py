#!/usr/bin/env python3
"""Unit tests for review-triage (triage_threads.py).

Run: python3 -m unittest discover -s review-triage/tests -p 'test_*.py'
  or python3 review-triage/tests/test_triage_threads.py
"""

import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import triage_threads  # noqa: E402


def comment(login, body, typename="User", commit="abc1234"):
    author = None if login is None else {"login": login, "__typename": typename}
    return {
        "id": f"c-{login}-{len(body)}",
        "body": body,
        "createdAt": "2026-01-01T00:00:00Z",
        "author": author,
        "originalCommit": {"oid": commit},
    }


def thread(tid, comments, resolved=False, outdated=False, path="src/a.py", line=10, original_line=None):
    return {
        "id": tid,
        "isResolved": resolved,
        "isOutdated": outdated,
        "path": path,
        "line": line,
        "originalLine": original_line,
        "comments": {"nodes": comments},
    }


def payload(*threads_):
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": list(threads_),
                    }
                }
            }
        }
    }


class ClassifyAuthorTests(unittest.TestCase):
    def test_bot_suffix_login(self):
        login, kind = triage_threads.classify_author(
            {"login": "greptile-apps[bot]", "__typename": "Bot"}, "text", triage_threads.KNOWN_BOTS
        )
        self.assertEqual(kind, "bot")

    def test_known_bot_without_suffix(self):
        _, kind = triage_threads.classify_author(
            {"login": "coderabbitai", "__typename": "User"}, "text", triage_threads.KNOWN_BOTS
        )
        self.assertEqual(kind, "bot")

    def test_unknown_login_is_human(self):
        _, kind = triage_threads.classify_author(
            {"login": "some-engineer", "__typename": "User"}, "looks wrong", triage_threads.KNOWN_BOTS
        )
        self.assertEqual(kind, "human")

    def test_automation_header_outranks_human_login(self):
        body = "> [!NOTE]\n> 🤖 Automated comment by **review-swarm** — not written by a human\n\nfinding"
        _, kind = triage_threads.classify_author(
            {"login": "some-engineer", "__typename": "User"}, body, triage_threads.KNOWN_BOTS
        )
        self.assertEqual(kind, "bot")

    def test_ghost_author_is_human(self):
        login, kind = triage_threads.classify_author(None, "orphan comment", triage_threads.KNOWN_BOTS)
        self.assertEqual((login, kind), ("ghost", "human"))


class NormalizeTests(unittest.TestCase):
    def test_human_participation_sets_gate(self):
        docs = [payload(thread("t1", [comment("greptile-apps[bot]", "bot says"), comment("alice", "I agree")]))]
        result = triage_threads.normalize(docs)
        self.assertTrue(result["threads"][0]["has_human"])
        self.assertEqual(result["summary"]["human_gated"], 1)
        self.assertEqual(result["summary"]["bot_only"], 0)

    def test_header_only_thread_is_bot_only(self):
        body = "🤖 Automated comment by **review-swarm** — not written by a human\nHIGH finding"
        docs = [payload(thread("t1", [comment("robson", body)]))]
        result = triage_threads.normalize(docs)
        self.assertFalse(result["threads"][0]["has_human"])
        self.assertEqual(result["threads"][0]["source"], "review-swarm")

    def test_resolved_threads_skipped_by_default(self):
        docs = [payload(thread("t1", [comment("alice", "x")], resolved=True))]
        result = triage_threads.normalize(docs)
        self.assertEqual(result["summary"]["total"], 1)
        self.assertEqual(result["summary"]["returned"], 0)
        self.assertEqual(
            triage_threads.normalize(docs, include_resolved=True)["summary"]["returned"], 1
        )

    def test_stale_is_outdated_bot_only(self):
        bot = comment("dependabot[bot]", "bump", typename="Bot")
        docs = [payload(thread("t1", [bot], outdated=True), thread("t2", [bot, comment("alice", "hold")], outdated=True))]
        result = triage_threads.normalize(docs)
        by_id = {t["id"]: t for t in result["threads"]}
        self.assertTrue(by_id["t1"]["stale"])
        self.assertFalse(by_id["t2"]["stale"], "outdated thread with a human is deferred, not stale")
        self.assertEqual(result["summary"]["stale"], 1)

    def test_trim_and_truncation_flag(self):
        docs = [payload(thread("t1", [comment("alice", "x" * 2000)]))]
        result = triage_threads.normalize(docs, trim=1500)
        c = result["threads"][0]["comments"][0]
        self.assertEqual(len(c["body"]), 1500)
        self.assertTrue(c["body_truncated"])

    def test_line_falls_back_to_original_line(self):
        docs = [payload(thread("t1", [comment("alice", "x")], line=None, original_line=7))]
        self.assertEqual(triage_threads.normalize(docs)["threads"][0]["line"], 7)

    def test_extra_known_bots(self):
        docs = [payload(thread("t1", [comment("acme-review-bot", "finding")]))]
        self.assertTrue(triage_threads.normalize(docs)["threads"][0]["has_human"])
        result = triage_threads.normalize(docs, known_bots={"acme-review-bot"})
        self.assertFalse(result["threads"][0]["has_human"])

    def test_paginated_stream_merges(self):
        docs = [payload(thread("t1", [comment("alice", "x")])), payload(thread("t2", [comment("bob", "y")]))]
        result = triage_threads.normalize(docs)
        self.assertEqual(result["summary"]["total"], 2)

    def test_participants_deduped(self):
        docs = [payload(thread("t1", [comment("alice", "one"), comment("alice", "two")]))]
        self.assertEqual(len(triage_threads.normalize(docs)["threads"][0]["participants"]), 1)


class StreamAndMainTests(unittest.TestCase):
    def run_main(self, stdin_text, argv=None):
        out = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(stdin_text)):
            with mock.patch.object(sys, "stdout", out):
                code = triage_threads.main(argv or [])
        return code, out.getvalue()

    def test_main_ok(self):
        stdin = json.dumps(payload(thread("t1", [comment("alice", "x")])))
        code, out = self.run_main(stdin, ["--head-sha", "deadbeef"])
        self.assertEqual(code, 0)
        parsed = json.loads(out)
        self.assertEqual(parsed["head_sha"], "deadbeef")
        self.assertEqual(parsed["summary"]["returned"], 1)

    def test_concatenated_documents_on_stdin(self):
        stdin = json.dumps(payload(thread("t1", [comment("a", "x")]))) + "\n" + json.dumps(
            payload(thread("t2", [comment("b", "y")]))
        )
        code, out = self.run_main(stdin)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["summary"]["total"], 2)

    def test_malformed_json_exits_2(self):
        code, _ = self.run_main("this is not json")
        self.assertEqual(code, 2)

    def test_graphql_error_exits_2(self):
        code, _ = self.run_main(json.dumps({"errors": [{"message": "boom"}]}))
        self.assertEqual(code, 2)

    def test_missing_pr_exits_2(self):
        code, _ = self.run_main(json.dumps({"data": {"repository": {"pullRequest": None}}}))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
