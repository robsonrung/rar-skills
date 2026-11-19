#!/usr/bin/env python3
"""Tests for the title check in validate_skill_frontmatter.py.

Run: python3 shared/tests/test_validate_skill_frontmatter.py
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "shared" / "scripts"))
import validate_skill_frontmatter as vsf  # noqa: E402


class TitleMatchesName(unittest.TestCase):
    def test_title_case_form_matches(self):
        self.assertTrue(vsf.h1_matches_name("simplify-changes", "Simplify Changes"))
        self.assertTrue(vsf.h1_matches_name("pr-readiness", "PR Readiness"))

    def test_extra_words_after_the_name_match(self):
        self.assertTrue(vsf.h1_matches_name("worktree", "Worktree Isolation"))
        self.assertTrue(vsf.h1_matches_name("tdd", "TDD — Test-First Execution"))
        self.assertTrue(vsf.h1_matches_name("test-lens", "Test Lens: Valuable Unit Testing"))

    def test_pull_request_stands_for_pr(self):
        self.assertTrue(vsf.h1_matches_name("open-pr", "Open Pull Request"))

    def test_stale_title_fails(self):
        self.assertFalse(vsf.h1_matches_name("simplify-changes", "Coding Review Simplify"))
        self.assertFalse(vsf.h1_matches_name("validate-feature", "Validate E2E"))
        self.assertFalse(vsf.h1_matches_name("to-prototype", "Prototype"))

    def test_partial_word_does_not_match(self):
        self.assertFalse(vsf.h1_matches_name("tdd", "TDDs"))


class AllSkillsPass(unittest.TestCase):
    def test_every_skill_title_names_its_skill(self):
        failures: list[str] = []
        vsf.check_h1(failures)
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
