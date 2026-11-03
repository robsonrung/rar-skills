import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "validate_consensus_summary.py"
FIXTURE = HERE / "fixtures" / "valid-summary.html"

spec = importlib.util.spec_from_file_location("validate_consensus_summary", SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ValidateConsensusSummaryTest(unittest.TestCase):
    def check(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.html"
            path.write_text(text, encoding="utf-8")
            errors, _ = validator.validate(path)
        return errors

    def test_fixture_passes(self):
        self.assertEqual(self.check(FIXTURE.read_text(encoding="utf-8")), [])

    def test_bundled_template_still_has_slots(self):
        template = HERE.parent / "assets" / "template.html"
        errors = self.check(template.read_text(encoding="utf-8"))
        self.assertTrue(any("placeholder" in error for error in errors))

    def test_missing_section_fails(self):
        text = FIXTURE.read_text(encoding="utf-8").replace('id="limits"', 'id="other"')
        self.assertIn("missing required section ids: limits", self.check(text))

    def test_second_next_step_fails(self):
        text = FIXTURE.read_text(encoding="utf-8").replace(
            "</body>", '<p data-role="next-step">Also this.</p></body>'
        )
        self.assertIn("data-role='next-step' must appear exactly once", self.check(text))

    def test_empty_seat_table_fails(self):
        text = FIXTURE.read_text(encoding="utf-8")
        start = text.index("<tbody>") + len("<tbody>")
        end = text.index("</tbody>")
        errors = self.check(text[:start] + text[end:])
        self.assertIn("seat table must contain at least one body row", errors)

    def test_external_script_fails(self):
        text = FIXTURE.read_text(encoding="utf-8").replace(
            "</head>", '<script src="https://example.com/x.js"></script></head>'
        )
        self.assertTrue(any(error.startswith("markup safety") for error in self.check(text)))

    def test_bundled_template_passes_the_guard(self):
        self.assertEqual(validator.guard_problems(validator.TEMPLATE, allow_comments=True), [])

    def test_injected_council_text_fails(self):
        fixture = FIXTURE.read_text(encoding="utf-8")
        cases = [
            fixture.replace("<p>Agreement point</p>", "<p>Agreement <img src=x onerror=alert(1)></p>"),
            fixture.replace("<p>Agreement point</p>", "<svg><title><img src=x onerror=alert(1)></title></svg>"),
            fixture.replace("<p>Agreement point</p>", '<p><a href="javascript:alert(1)">report</a></p>'),
            fixture.replace("--value: 70%", "--value: 70%; background: url(https://x/y)"),
            fixture.replace("function setAll(open) {", "function setAll(open) { fetch('//x');"),
            fixture.replace("<p>Agreement point</p>", "<!-- seat said --><p>Agreement point</p>"),
            "\n".join(line for line in fixture.splitlines() if "Content-Security-Policy" not in line),
        ]
        for text in cases:
            with self.subTest(text=text[:0]):
                self.assertTrue(any(error.startswith("markup safety") for error in self.check(text)), self.check(text))

    def test_escaped_council_text_passes(self):
        text = FIXTURE.read_text(encoding="utf-8").replace(
            "<p>Agreement point</p>", "<p>Seat A wrote &lt;script&gt;alert(1)&lt;/script&gt; verbatim.</p>")
        self.assertEqual(self.check(text), [])


if __name__ == "__main__":
    unittest.main()
