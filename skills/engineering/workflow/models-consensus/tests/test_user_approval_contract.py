#!/usr/bin/env python3
"""Regression checks for the council's user-controlled dispatch boundary."""

from __future__ import annotations

import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]


class UserApprovalContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_DIR / relative_path).read_text(encoding="utf-8")

    def test_skill_cannot_be_implicitly_invoked(self):
        skill = self.read("SKILL.md")
        metadata = self.read("agents/openai.yaml")
        self.assertIn("disable-model-invocation: true", skill)
        self.assertIn("allow_implicit_invocation: false", metadata)
        self.assertIn("Wait for a clear approval", skill)
        self.assertIn("not approval", skill)

    def test_preview_must_precede_dispatch_and_capture_the_full_budget(self):
        skill = self.read("SKILL.md")
        operations = self.read("references/operations.md")
        self.assertIn("Before dispatching any model", skill)
        self.assertIn("Approve this council plan, or specify changes", skill)
        self.assertIn("maximum_calls", operations)
        self.assertIn("one possible retry for every planned or conditional call", operations)

    def test_no_automatic_dispatch_or_substitution_path_remains(self):
        documents = "\n".join(
            path.read_text(encoding="utf-8")
            for path in SKILL_DIR.rglob("*.md")
        )
        self.assertNotIn("--auto", documents)
        self.assertNotIn("auto: true", documents)
        self.assertIn("Do not substitute", documents)
        self.assertIn("Do not switch", documents)

    def test_routing_uses_current_frontier_seats_and_supported_effort(self):
        routing = self.read("references/role-routing.md")
        self.assertIn("`astra`", routing)
        self.assertIn("`fable`", routing)
        self.assertIn("`gemini`, `effort: null`, `effort_control: runtime`", routing)
        self.assertIn("`grok`, all `high`", routing)
        self.assertIn("`qwen`, all `high`", routing)
        self.assertIn("`model_receipt: {status: unverified, source: configured_model, observed_model: null}`", routing)
        self.assertNotIn("gpt-", routing.lower())
        self.assertNotIn("claude-fable-", routing.lower())

    def test_runner_policy_is_read_only(self):
        runners = self.read("references/runner-invocations.md")
        self.assertIn("--disable-fallback", runners)
        self.assertIn("Do not pass a write permission", runners)
        self.assertIn("or `implementer` role", runners)

    def test_cmux_relay_requires_an_approved_state_and_recorded_surface(self):
        relay = self.read("scripts/cmux_council.py")
        self.assertIn('add_argument("--approval-state", required=True)', relay)
        self.assertIn('add_argument("--adopted-state", required=True)', relay)
        self.assertIn("def approved_surface", relay)
        self.assertIn("approval_scope_fingerprint", relay)
        self.assertNotIn('send.add_argument("--surface"', relay)


if __name__ == "__main__":
    unittest.main(verbosity=2)
