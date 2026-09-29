"""Check portable package structure and local references."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_skill_frontmatter_and_size(self):
        text = (ROOT / "SKILL.md").read_text()
        self.assertTrue(text.startswith("---\nname: code-deslop\n"))
        self.assertIn("\ndescription: ", text)
        self.assertLess(len(text.splitlines()), 500)

    def test_local_markdown_links_exist(self):
        for path in ROOT.rglob("*.md"):
            for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                if "://" in target or target.startswith("#"):
                    continue
                self.assertTrue((path.parent / target.split("#", 1)[0]).exists(), f"{path}: {target}")

    def test_case_ids_and_kinds(self):
        data = json.loads((ROOT / "evals/cases.json").read_text())
        cases = data["cases"]
        self.assertEqual(len(cases), 32)
        self.assertEqual(len({case["id"] for case in cases}), 32)
        self.assertEqual(sum(c["kind"] == "positive" for c in cases), 8)
        self.assertEqual(sum(c["kind"] == "hard-negative" for c in cases), 14)
        self.assertEqual(sum(c["kind"] == "workflow" for c in cases), 10)
        for case in cases:
            for key in ("id", "kind", "stack", "task", "context", "expected", "forbidden"):
                self.assertIsInstance(case[key], str)
                self.assertTrue(case[key].strip())

    def test_no_provider_specific_runtime_assignment(self):
        text = (ROOT / "SKILL.md").read_text().split("---", 2)[1]
        self.assertNotIn("\nmodel:", text)
        self.assertNotIn("\nallowed-tools:", text)

    def test_scripts_parse_as_python310(self):
        import ast
        for path in (ROOT / "scripts").glob("*.py"):
            ast.parse(path.read_text(), feature_version=(3, 10))


if __name__ == "__main__":
    unittest.main()
