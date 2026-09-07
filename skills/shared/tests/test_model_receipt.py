#!/usr/bin/env python3
"""Contract tests for truthful runner model provenance."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "shared" / "scripts"))

from model_receipt import attach_model_receipt  # noqa: E402


class ModelReceiptTests(unittest.TestCase):
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
