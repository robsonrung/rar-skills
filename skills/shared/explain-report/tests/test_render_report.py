"""The rendered report must pass the shared page guard and keep report text as data."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "render_report.py"
sys.path.insert(0, str(SCRIPT.parent))
import render_report as rr  # noqa: E402

FIXTURES = {name: json.loads((HERE / "fixtures" / f"{name}.json").read_text(encoding="utf-8"))
            for name in ("plan", "work")}


class RenderedPageTest(unittest.TestCase):
    def test_fixtures_are_valid_reports(self):
        for name, data in FIXTURES.items():
            with self.subTest(name):
                self.assertEqual(rr.validate_report(data), [])

    def test_rendered_pages_pass_html_guard(self):
        for name, data in FIXTURES.items():
            with self.subTest(name):
                self.assertEqual(rr.page_problems(rr.render_html(data)), [])

    def test_hostile_text_is_escaped(self):
        page = rr.render_html(FIXTURES["plan"])
        self.assertNotIn("<script>alert(1)", page)
        self.assertIn("&lt;script&gt;alert(1)", page)
        self.assertIn("Promise&lt;Delivery&gt;", page)
        self.assertNotIn("&amp;lt;", page)

    def test_hostile_text_in_metadata_stays_inside_the_attribute(self):
        data = copy.deepcopy(FIXTURES["plan"])
        data["decisions"][0]["title"] = '"><img src=x onerror=alert(1)>'
        self.assertEqual(rr.page_problems(rr.render_html(data)), [])

    def test_css_url_shaped_text_does_not_trip_the_guard(self):
        data = copy.deepcopy(FIXTURES["plan"])
        data["decisions"][0]["title"] = "see url(x) here"
        data["architecture"]["after"]["nodes"][0]["label"] = "url(evil)"
        data["architecture"]["after"]["title"] = "url(title)"
        self.assertEqual(rr.page_problems(rr.render_html(data)), [])

    def test_cli_writes_nothing_when_the_guard_fails(self):
        data = copy.deepcopy(FIXTURES["plan"])
        data["evidence"][0]["excerpt"] = "key = AKIA" + "ABCDEFGHIJKLMNOP"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "in.json").write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run([sys.executable, str(SCRIPT), str(out / "in.json"),
                                     "--html", str(out / "r.html"), "--markdown", str(out / "r.md")],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("secret-shaped", result.stderr)
            self.assertFalse((out / "r.html").exists() or (out / "r.md").exists())

    def test_no_template_token_survives(self):
        for name, data in FIXTURES.items():
            with self.subTest(name):
                self.assertNotIn("@@", rr.render_html(data))

    def test_plain_http_urls_are_rejected(self):
        data = copy.deepcopy(FIXTURES["plan"])
        data["sources"][0]["url"] = "http://example.com/backoff"
        self.assertTrue(any("HTTPS" in e for e in rr.validate_report(data)))

    def test_guard_blocks_unsafe_markup(self):
        page = rr.render_html(FIXTURES["plan"]).replace("</main>", "<textarea></textarea></main>")
        self.assertTrue(rr.page_problems(page))

    def test_cli_writes_html_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            result = subprocess.run([sys.executable, str(SCRIPT), str(HERE / "fixtures" / "work.json"),
                                     "--html", str(out / "r.html"), "--markdown", str(out / "r.md")],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((out / "r.html").is_file() and (out / "r.md").is_file())


if __name__ == "__main__":
    unittest.main()
