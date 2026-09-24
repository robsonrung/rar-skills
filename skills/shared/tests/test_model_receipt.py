#!/usr/bin/env python3
"""Contract tests for truthful runner model provenance."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "shared" / "scripts"))

from model_receipt import attach_model_receipt, attach_claude_model_receipt  # noqa: E402


class ModelReceiptTests(unittest.TestCase):
    def test_normalization_preserves_matching_verified_receipt(self):
        result = attach_model_receipt({"native_model_id": "served"}, "requested", observed_source="native_event")
        self.assertEqual(attach_model_receipt(result, "requested")["effective_model"], "served")
        result["native_model_id"] = "different"
        self.assertIsNone(attach_model_receipt(result, "requested")["effective_model"])

    def test_primary_serving_evidence_ignores_init_synthetic_and_usage_labels(self):
        requested = "claude-fable-5-1"
        events = [
            {"type": "system", "model": requested},
            {"type": "assistant", "message": {"model": "<synthetic>"}},
            {"type": "result", "modelUsage": {requested: {"costUSD": 1}}},
        ]
        result = attach_claude_model_receipt({"model": requested}, events, requested)
        self.assertIsNone(result["effective_model"])
        self.assertEqual(result["primary_model_ids"], [])
        self.assertEqual(result["model_receipt"]["status"], "unverified")
        events.append({"type": "assistant", "message": {"model": requested}})
        result = attach_claude_model_receipt(result, events, requested)
        self.assertEqual(result["effective_model"], requested)
        self.assertTrue(result["model_matches_requested"])

    def test_mismatch_and_multiple_primary_ids_are_explicit(self):
        events = [{"type": "assistant", "message": {"model": "claude-opus-5-5"}}]
        result = attach_claude_model_receipt({}, events, "claude-fable-5-1")
        self.assertFalse(result["model_matches_requested"])
        self.assertEqual(result["effective_model"], "claude-opus-5-5")
        self.assertIn("differs", result["model_identity_error"])
        events.append({"type": "assistant", "message": {"model": "claude-fable-5-1"}})
        result = attach_claude_model_receipt(result, events, "claude-fable-5-1")
        self.assertIsNone(result["effective_model"])
        self.assertEqual(result["model_receipt"]["status"], "unverified")
        self.assertEqual(len(result["primary_model_ids"]), 2)

    def test_auxiliary_events_and_cost_breakdown_do_not_change_primary_or_total(self):
        events = [
            {"type": "assistant", "message": {"model": "claude-fable-5-1"}},
            {"type": "assistant", "parent_tool_use_id": "task-1", "message": {"model": "claude-opus-5-5"}},
            {"type": "result", "modelUsage": {"claude-fable-5-1": {"costUSD": 1}, "claude-opus-5-5": {"costUSD": 2}}},
        ]
        result = attach_claude_model_receipt({"metrics": {"reported_cost_usd": 3}}, events, "claude-fable-5-1")
        self.assertEqual(result["effective_model"], "claude-fable-5-1")
        self.assertEqual(result["auxiliary_model_ids"], ["claude-opus-5-5"])
        self.assertEqual(result["auxiliary_model_usage"], {"claude-opus-5-5": {"costUSD": 2}})
        self.assertEqual(result["metrics"]["reported_cost_usd"], 3)

    def test_alias_match_is_unknown_and_synthetic_native_id_is_not_proof(self):
        result = attach_claude_model_receipt({}, [{"type": "assistant", "message": {"model": "claude-opus-5-5"}}], "opus")
        self.assertIsNone(result["model_matches_requested"])
        self.assertIsNone(result["model_identity_error"])
        self.assertIsNone(attach_model_receipt({"native_model_id": "<synthetic>"}, "opus", observed_source="native_event")["effective_model"])

    def test_configured_model_is_not_a_serving_receipt(self) -> None:
        envelope = attach_model_receipt(
            {"model": "gpt-6-astra", "effective_model": "gpt-6-astra"},
            "gpt-6-astra",
        )

        self.assertEqual(envelope["requested_model"], "gpt-6-astra")
        self.assertEqual(envelope["configured_model"], "gpt-6-astra")
        self.assertIsNone(envelope["effective_model"])
        self.assertEqual(
            envelope["model_receipt"],
            {
                "status": "unverified",
                "source": "configured_model",
                "observed_model": None,
            },
        )

    def test_native_event_verifies_the_observed_model(self) -> None:
        envelope = attach_model_receipt(
            {"model": "requested", "native_model_id": "served"},
            "requested",
            observed_source="native_event",
        )

        self.assertEqual(envelope["configured_model"], "requested")
        self.assertEqual(envelope["effective_model"], "served")
        self.assertEqual(
            envelope["model_receipt"],
            {
                "status": "verified",
                "source": "native_event",
                "observed_model": "served",
            },
        )

    def test_non_forwarded_label_stays_unverified(self) -> None:
        envelope = attach_model_receipt(
            {"model": "gemini-3.8-flash", "model_forwarded": False},
            "gemini-3.8-flash",
        )

        self.assertEqual(envelope["requested_model"], "gemini-3.8-flash")
        self.assertIsNone(envelope["configured_model"])
        self.assertIsNone(envelope["effective_model"])
        self.assertEqual(envelope["model_receipt"]["status"], "unverified")
        self.assertEqual(envelope["model_receipt"]["source"], "not_observed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
