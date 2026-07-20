#!/usr/bin/env python3
"""Unit tests for approval-gate (gate_check.py).

Run: python3 -m unittest discover -s approval-gate/tests -p 'test_*.py'
  or python3 approval-gate/tests/test_gate_check.py
"""

import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import gate_check  # noqa: E402


def entries(*rows):
    return [{"path": p, "added": a, "deleted": d} for a, d, p in rows]


class RenameAndParseTests(unittest.TestCase):
    def test_plain_line(self):
        got = gate_check.parse_numstat("10\t2\tsrc/app.py\n")
        self.assertEqual(got, [{"path": "src/app.py", "added": 10, "deleted": 2}])

    def test_binary_line(self):
        got = gate_check.parse_numstat("-\t-\tassets/logo.png\n")
        self.assertEqual(got[0]["added"], None)

    def test_brace_rename_resolves_to_new_path(self):
        self.assertEqual(gate_check.resolve_rename("src/{old => new}/mod.py"), "src/new/mod.py")

    def test_brace_rename_with_empty_side(self):
        self.assertEqual(gate_check.resolve_rename("src/{ => sub}/mod.py"), "src/sub/mod.py")
        self.assertEqual(gate_check.resolve_rename("src/{sub => }/mod.py"), "src/mod.py")

    def test_whole_path_rename(self):
        self.assertEqual(gate_check.resolve_rename("old.py => new.py"), "new.py")

    def test_malformed_line_raises(self):
        with self.assertRaises(ValueError):
            gate_check.parse_numstat("not numstat\n")


class TierTests(unittest.TestCase):
    def test_docs_only_is_t0(self):
        report = gate_check.evaluate(entries((5, 1, "README.md"), (3, 0, "docs/guide.rst")))
        self.assertEqual(report["tier"], "T0")
        self.assertEqual(report["substantive_files"], 0)
        self.assertEqual(report["blockers"], [])

    def test_plain_source_is_t1(self):
        report = gate_check.evaluate(entries((40, 10, "src/widgets/render.py")))
        self.assertEqual(report["tier"], "T1")
        self.assertTrue(report["size_gate"]["within"])
        self.assertEqual(report["blockers"], [])

    def test_auth_path_is_t2(self):
        report = gate_check.evaluate(entries((3, 1, "src/auth/middleware.py")))
        self.assertEqual(report["tier"], "T2")
        self.assertIn("deny-list:auth", report["blockers"])

    def test_deny_outranks_test_exclusion(self):
        report = gate_check.evaluate(entries((3, 1, "tests/test_login.py")))
        self.assertEqual(report["tier"], "T2", "an auth test is still an auth change")
        self.assertEqual(report["substantive_files"], 0, "still excluded from the size count")

    def test_lockfile_is_dependencies_deny_and_size_excluded(self):
        report = gate_check.evaluate(entries((5000, 4000, "package-lock.json")))
        self.assertEqual(report["tier"], "T2")
        self.assertIn("deny-list:dependencies", report["blockers"])
        self.assertEqual(report["substantive_lines"], 0)

    def test_billing_in_filename(self):
        report = gate_check.evaluate(entries((2, 2, "src/user_billing.py")))
        self.assertIn("deny-list:billing", report["blockers"])

    def test_workflow_file_is_infra(self):
        report = gate_check.evaluate(entries((1, 1, ".github/workflows/ci.yml")))
        self.assertIn("deny-list:infra-ci", report["blockers"])

    def test_migrations_dir(self):
        report = gate_check.evaluate(entries((9, 0, "app/migrations/0042_add_flag.py")))
        self.assertIn("deny-list:migrations", report["blockers"])

    def test_authors_is_not_auth(self):
        report = gate_check.evaluate(entries((1, 1, "src/authors.py")))
        self.assertEqual(report["tier"], "T1")

    def test_certifi_is_not_cert(self):
        report = gate_check.evaluate(entries((1, 1, "lib/certifi/core.py")))
        self.assertEqual(report["tier"], "T1")

    def test_env_file_is_crypto_secrets(self):
        report = gate_check.evaluate(entries((1, 0, ".env.production")))
        self.assertIn("deny-list:crypto-secrets", report["blockers"])


class SizeTests(unittest.TestCase):
    def test_line_ceiling(self):
        report = gate_check.evaluate(entries((900, 0, "src/big.py")))
        self.assertEqual(report["tier"], "T1")
        self.assertFalse(report["size_gate"]["within"])
        self.assertTrue(any(b.startswith("size:lines") for b in report["blockers"]))

    def test_file_ceiling(self):
        rows = [(1, 0, f"src/f{i}.py") for i in range(31)]
        report = gate_check.evaluate(entries(*rows))
        self.assertTrue(any(b.startswith("size:files") for b in report["blockers"]))

    def test_binary_counts_as_file_not_lines(self):
        report = gate_check.evaluate(entries((None, None, "src/blob.bin")))
        self.assertEqual(report["substantive_files"], 1)
        self.assertEqual(report["substantive_lines"], 0)

    def test_custom_ceilings(self):
        report = gate_check.evaluate(entries((90, 0, "src/a.py")), max_lines=50)
        self.assertFalse(report["size_gate"]["within"])


class ExtraDenyTests(unittest.TestCase):
    def test_extra_rule_applies(self):
        rules = gate_check.parse_extra_deny(["design-tokens=tokens\\.ts$"])
        report = gate_check.evaluate(entries((1, 1, "src/theme/tokens.ts")), extra_rules=rules)
        self.assertIn("deny-list:design-tokens", report["blockers"])

    def test_bad_spec_raises(self):
        with self.assertRaises(ValueError):
            gate_check.parse_extra_deny(["no-equals-sign"])
        with self.assertRaises(ValueError):
            gate_check.parse_extra_deny(["cat=[unclosed"])


class MainTests(unittest.TestCase):
    def run_main(self, argv, stdin_text=""):
        out = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(stdin_text)):
            with mock.patch.object(sys, "stdout", out):
                code = gate_check.main(argv)
        return code, out.getvalue()

    def test_stdin_mode(self):
        code, out = self.run_main(["--numstat-file", "-"], "4\t1\tsrc/app.py\n")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["tier"], "T1")

    def test_bad_extra_deny_exits_2(self):
        code, _ = self.run_main(["--numstat-file", "-", "--extra-deny", "broken"], "1\t1\ta.py\n")
        self.assertEqual(code, 2)

    def test_malformed_numstat_exits_2(self):
        code, _ = self.run_main(["--numstat-file", "-"], "garbage\n")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
