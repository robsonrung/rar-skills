#!/usr/bin/env python3
"""Resolve installed and source skill layouts without searching unrelated files."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import skill_paths


class SkillPathTests(unittest.TestCase):
    def test_both_layouts_resolve_and_hash_current_instructions(self):
        for layout in ("example", "engineering/practice/example"):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                marker = root / "shared/scripts/runner_jobs.py"
                marker.parent.mkdir(parents=True)
                marker.touch()
                entry = root / layout / "SKILL.md"
                entry.parent.mkdir(parents=True)
                entry.write_text("First instructions")
                first = skill_paths.resolve_skills(entry, ["example"])
                self.assertEqual(first["skills"]["example"]["path"], str(entry.resolve()))
                entry.write_text("Changed instructions")
                self.assertNotEqual(first, skill_paths.resolve_skills(entry, ["example"]))
                for names in (["missing"], ["../outside"], ["*"], ["example", "example"]):
                    with self.assertRaises(ValueError):
                        skill_paths.resolve_skills(entry, names)


if __name__ == "__main__":
    unittest.main()
