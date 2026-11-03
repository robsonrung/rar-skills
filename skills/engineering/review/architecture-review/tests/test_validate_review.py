import re
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / 'scripts'))
import validate_review  # noqa: E402

TEMPLATE = (SKILL / 'assets' / 'report.html').read_text(encoding='utf-8')
EXAMPLE = (SKILL / 'examples' / 'example-report.html').read_text(encoding='utf-8')


def failures(html, **kwargs):
    return [name for name, ok, _ in validate_review.validate(html, **kwargs) if not ok]


class ShippedFiles(unittest.TestCase):
    def test_example_passes(self):
        self.assertEqual(failures(EXAMPLE), [])

    def test_template_passes_in_template_mode(self):
        self.assertEqual(failures(TEMPLATE, template=True), [])

    def test_template_fails_only_on_placeholders_in_strict_mode(self):
        self.assertEqual(failures(TEMPLATE), ['no unresolved template placeholders'])


class BrokenReports(unittest.TestCase):
    def assertFails(self, html, check):
        found = failures(html)
        self.assertTrue(any(check in name for name in found), f'{check!r} not in {found}')

    def test_missing_dimension(self):
        self.assertFails(re.sub(r'<tr class="dim" id="D07".*?</tr>', '', EXAMPLE), 'D01-D20 each present once')

    def test_rated_dimension_without_evidence(self):
        html = re.sub(r'(<tr class="dim" id="D03".*?<td class="d-evidence">).*?(</td>)', r'\1\2', EXAMPLE)
        self.assertFails(html, 'D03 rated status cites evidence')

    def test_unknown_dimension_with_high_confidence(self):
        html = EXAMPLE.replace('id="D10" data-status="unknown" data-confidence="unknown"',
                               'id="D10" data-status="unknown" data-confidence="high"')
        self.assertFails(html, 'D10 unknown is not high confidence')

    def test_finding_without_evidence(self):
        html = re.sub(r'<dd class="f-evidence">.*?</dd>', '<dd class="f-evidence">see code</dd>', EXAMPLE)
        self.assertFails(html, 'F01 cites evidence')

    def test_finding_missing_a_part(self):
        self.assertFails(re.sub(r'<dt>Rollback</dt><dd class="f-rollback">.*?</dd>', '', EXAMPLE), 'F01 complete')

    def test_decision_anchor_must_recur(self):
        html = EXAMPLE.replace('this restores end-to-end correctness', 'this fixes it')
        self.assertFails(html, 'F01 anchor recurs in the action or check')

    def test_low_confidence_p1(self):
        self.assertFails(EXAMPLE.replace('data-priority="P1" data-confidence="high"',
                                         'data-priority="P1" data-confidence="low"'), 'P0/P1 needs high or medium')

    def test_critical_dimension_without_p0_p1_finding(self):
        self.assertFails(EXAMPLE.replace('data-priority="P1"', 'data-priority="P2"'), 'D09 critical has a P0/P1 finding')

    def test_unresolved_placeholder(self):
        self.assertFails(EXAMPLE.replace('<p class="lede">', '<!-- SLOT: lede --><p class="lede">', 1),
                         'no unresolved template placeholders')

    def test_external_script(self):
        self.assertFails(EXAMPLE.replace('<script>', '<script src="https://cdn.example.com/x.js"></script><script>'),
                         'self-contained')

    def test_missing_content_security_policy(self):
        html = '\n'.join(l for l in EXAMPLE.splitlines() if 'Content-Security-Policy' not in l)
        self.assertFails(html, 'content security policy')

    def test_unknown_event_handler(self):
        self.assertFails(EXAMPLE.replace('<p class="lede">', '<p class="lede" onmouseover="alert(1)">', 1),
                         'only known event handlers')

    def test_injected_onclick(self):
        self.assertFails(EXAMPLE.replace("onclick=\"setAll(true)\"", "onclick=\"fetch('//x')\"", 1),
                         'only known event handlers')

    def test_unsafe_urls(self):
        for url in ('javascript:alert(1)', 'java&#9;script:alert(1)', '&#1;javascript:alert(1)', 'JaVaScRiPt:x',
                    'vbscript:x', 'data:text/html,x', 'http://example.com'):
            with self.subTest(url=url):
                self.assertFails(EXAMPLE.replace('<p class="lede">', f'<p class="lede"><a href="{url}">x</a>', 1),
                                 'only safe URLs')
        for tag in ('<object data="javascript:x"></object>', '<form action="java\nscript:x"></form>'):
            with self.subTest(tag=tag):
                self.assertFails(EXAMPLE.replace('<p class="lede">', tag + '<p class="lede">', 1), 'only safe URLs')

    def test_second_inline_script(self):
        self.assertFails(EXAMPLE.replace('<p class="lede">', '<script>alert(1)</script><p class="lede">', 1),
                         'one inline script')

    def test_dangling_evidence_link(self):
        self.assertFails(EXAMPLE.replace('<a href="#E004">', '<a href="#E099">', 1), 'every #anchor')

    def test_code_evidence_without_location(self):
        self.assertFails(EXAMPLE.replace('<code class="loc">tests/test_checkout.py:2</code>', 'tests/test_checkout.py'),
                         'E004 cites path:line')

    def test_missing_keep_option(self):
        self.assertFails(EXAMPLE.replace('data-kind="keep"', 'data-kind="structural"'), 'keeping the current architecture')

    def test_missing_challenge_pass(self):
        self.assertFails(EXAMPLE.replace('data-check="challenge"', ''), 'challenge pass recorded')

    def test_secret_value(self):
        self.assertFails(EXAMPLE.replace('No lost payments', 'AKIAABCDEFGHIJKLMNOP'), 'no secret-shaped strings')


class CitedLines(unittest.TestCase):
    def test_repo_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / 'orders').mkdir()
            (repo / 'tests').mkdir()
            (repo / 'orders' / 'checkout.py').write_text('def checkout():\n    order = load()\n    capture()\n    commit()\n')
            (repo / 'tests' / 'test_checkout.py').write_text('import mock\nmock.patch("client")\n')
            self.assertEqual(failures(EXAMPLE, repo=repo), [])
            (repo / 'orders' / 'checkout.py').write_text('def checkout():\n')
            self.assertIn('E001 orders/checkout.py:3-4 exists at --repo', failures(EXAMPLE, repo=repo))


if __name__ == '__main__':
    unittest.main()
