"""Keep resumed session summaries behind the request policy boundary."""

import json
import shutil
import unittest

import test_local_provider as fixture


@unittest.skipUnless(shutil.which("pi"), "Installed Pi is required for the local adapter experiment")
class CompactionGuardTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.LocalProviderTests("test_max_effort_reaches_payload_without_cli_alias")
        self.addCleanup(self.case.doCleanups)
        self.case.setUp()

    def test_resume_stops_before_unprotected_compaction(self):
        case = self.case
        session = case.root / "session.jsonl"
        first = fixture.run_pi.run_pi("synthetic " * 6000, model=fixture.MODEL,
            provider_routing=fixture.POLICY, thinking="high", no_tools=True,
            session_id=str(session), working_dir=str(case.root), timeout=20)
        self.assertTrue(first["success"])
        second = fixture.run_pi.run_pi("recent synthetic " * 1000, model=fixture.MODEL,
            provider_routing=fixture.POLICY, thinking="high", no_tools=True,
            session_id=str(session), working_dir=str(case.root), timeout=20)
        self.assertTrue(second["success"])
        # Two turns make the older turn eligible for compaction. High fixture
        # usage forces the next prompt's preflight to cross the threshold.
        rows = [json.loads(line) for line in session.read_text().splitlines()]
        for row in rows:
            if row.get("message", {}).get("role") == "assistant":
                row["message"]["usage"].update(input=32000, totalTokens=32003)
        session.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
        settings = case.root / "agent" / "settings.json"
        settings.write_text(json.dumps({"retry": {"enabled": False},
            "compaction": {"enabled": True, "reserveTokens": 4096, "keepRecentTokens": 256}}))
        case.requests.clear()
        result = case.execute(thinking="high", no_tools=True, session_id=str(session))
        self.assertFalse(result["success"])
        self.assertEqual(case.requests, [], "Compaction must stop before source enters an unprotected request")
        self.assertNotIn("provider_policy_receipt", result)


if __name__ == "__main__":
    unittest.main()
