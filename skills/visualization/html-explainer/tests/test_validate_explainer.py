import re
import sys
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
import validate_explainer  # noqa: E402

TEMPLATE = validate_explainer.TEMPLATE


def finished() -> str:
    """The template with its comments removed and its example section turned into four real ones."""
    html = re.sub(r"<!--.*?-->", "", TEMPLATE, flags=re.S)
    section = re.search(r'<section class="card" id="sec-example">.*?</section>', html, re.S).group(0)
    html = html.replace(section, "".join(section.replace("sec-example", f"sec-s{i}") for i in range(1, 5)))
    return html.replace("sec-example", "sec-s1")


def failures(html, **kwargs):
    return [name for name, ok, _ in validate_explainer.validate(html, **kwargs) if not ok]


class Explainer(unittest.TestCase):
    def test_template_passes_in_template_mode(self):
        self.assertEqual(failures(TEMPLATE, template_mode=True), [])

    def test_template_fails_strict_mode(self):
        self.assertIn("no leftover template slots", failures(TEMPLATE))
        self.assertIn("markup safety (html_guard)", failures(TEMPLATE))

    def test_finished_page_passes(self):
        self.assertEqual(failures(finished()), [])

    def test_injection_is_rejected(self):
        html = finished()
        cases = [
            html.replace("<pre>", "<pre><img src=x onerror=alert(1)>", 1),
            html.replace("<pre>", "<pre></pre><svg><title><img src=x onerror=alert(1)></title></svg><pre>", 1),
            html.replace('<p class="lede">', '<p class="lede"><a href="javascript:alert(1)">x</a>', 1),
            html.replace("<button onclick=\"setAll(true)\">", "<button onclick=\"fetch('//x')\">", 1),
            html.replace("function setAll(open) {", "function setAll(open) { fetch('//x');", 1),
            "\n".join(line for line in html.splitlines() if "Content-Security-Policy" not in line),
            html.replace("<footer>", "<!-- note --><footer>", 1),
            html.replace("</head>", '<link rel="stylesheet" href="https://fonts.example/x.css"></head>', 1),
        ]
        for case in cases:
            with self.subTest(case=case[:0]):
                self.assertIn("markup safety (html_guard)", failures(case))

    def test_escaped_generic_passes(self):
        html = finished().replace("Promise&lt;Result&gt;", "Record&lt;string, T&gt;")
        self.assertEqual(failures(html), [])


if __name__ == "__main__":
    unittest.main()
