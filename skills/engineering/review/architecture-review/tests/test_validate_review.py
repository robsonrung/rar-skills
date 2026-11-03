import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / 'scripts'))
import render_review  # noqa: E402
import validate_review  # noqa: E402
import html_guard  # noqa: E402  (render_review put shared/scripts on the path)

EXAMPLE = json.loads((SKILL / 'examples' / 'example-review.json').read_text(encoding='utf-8'))


def example():
    return copy.deepcopy(EXAMPLE)


def dim(review, did):
    return next(r for r in review['dimensions']['rows'] if r['id'] == did)


def finding(review):
    return review['findings']['items'][0]


class ShippedExample(unittest.TestCase):
    def test_example_validates(self):
        self.assertEqual(validate_review.validate(example()), [])

    def test_example_renders_and_passes_the_guard(self):
        page, found = render_review.render(example())
        self.assertEqual(found, [])
        for hook in ('id="sec-verdict"', 'id="sec-evidence"', 'class="dim" id="D20"', "onclick=\"jump('F01')\"",
                     '<code class="loc">orders/checkout.py:3-4</code>', 'href="#E001"', 'href="#Q1"', 'data-first-move'):
            self.assertIn(hook, page)
        self.assertEqual(page.count('<script'), 1)


class BrokenReviews(unittest.TestCase):
    def assertFails(self, review, fragment):
        found = validate_review.validate(review)
        self.assertTrue(any(fragment in m for m in found), f'{fragment!r} not in {found}')

    def test_shape(self):
        r = example()
        del finding(r)['rollback']
        r['verdict']['top'] = 'F01'
        r['extra'] = 1
        found = validate_review.validate(r)
        for fragment in ('items[0].rollback: missing', 'verdict.top: expected a list', 'review.extra: unknown key'):
            self.assertTrue(any(fragment in m for m in found), f'{fragment!r} not in {found}')

    def test_missing_dimension(self):
        r = example()
        r['dimensions']['rows'] = [x for x in r['dimensions']['rows'] if x['id'] != 'D07']
        self.assertFails(r, 'D01-D20 once each')

    def test_rated_dimension_without_evidence(self):
        r = example()
        dim(r, 'D03')['evidence'] = []
        self.assertFails(r, 'D03: cite at least one evidence record')

    def test_unknown_dimension_with_high_confidence(self):
        r = example()
        dim(r, 'D10')['confidence'] = 'high'
        self.assertFails(r, 'D10: unknown cannot carry high confidence')

    def test_unknown_dimension_without_reason(self):
        r = example()
        dim(r, 'D10')['note'] = ' '
        self.assertFails(r, 'D10: give the assessment or the reason')

    def test_finding_without_evidence(self):
        r = example()
        finding(r)['evidence'] = []
        self.assertFails(r, 'F01: cite at least one evidence record')

    def test_dangling_evidence(self):
        r = example()
        finding(r)['evidence'] = ['E099']
        self.assertFails(r, "F01: unknown evidence ['E099']")

    def test_finding_with_an_empty_part(self):
        r = example()
        finding(r)['rollback'] = ''
        self.assertFails(r, "F01: empty ['rollback']")

    def test_decision_anchor(self):
        r = example()
        finding(r)['decision'] = 'It breaks across the capture timeout window.'
        self.assertFails(r, 'missing from the decision')
        r = example()
        finding(r)['recommendation'] = 'Write a capture intent row.'
        self.assertFails(r, 'missing from the recommendation and the acceptance')

    def test_low_confidence_p1(self):
        r = example()
        finding(r)['confidence'] = 'low'
        self.assertFails(r, 'P0/P1 needs high or medium')

    def test_critical_dimension_without_p0_p1_finding(self):
        r = example()
        finding(r)['priority'] = 'P2'
        self.assertFails(r, 'D09: a critical dimension needs a P0/P1 finding')

    def test_code_evidence_without_location(self):
        r = example()
        r['evidence']['records'][3]['locations'] = ['tests/test_checkout.py']
        self.assertFails(r, 'E004: cite path:line')

    def test_measurement_without_command(self):
        r = example()
        del r['evidence']['records'][2]['command']
        self.assertFails(r, 'E003: a measurement records its exact command')

    def test_missing_keep_option(self):
        r = example()
        r['options']['items'][0]['kind'] = 'structural'
        self.assertFails(r, 'keeping the current architecture')

    def test_two_recommended_options(self):
        r = example()
        r['options']['items'][0]['position'] = 'recommended'
        self.assertFails(r, 'at most one recommended')

    def test_four_first_moves(self):
        r = example()
        r['roadmap']['steps'] *= 4
        self.assertFails(r, 'at most three first moves')

    def test_missing_challenge_pass(self):
        r = example()
        del r['evidence']['checks'][0]['challenge']
        self.assertFails(r, 'record the challenge pass')

    def test_diagram_links_only_known_findings(self):
        r = example()
        r['architecture']['diagrams'][0]['nodes'][1]['finding'] = "F01');alert(1);('"
        self.assertFails(r, 'unknown findings')
        self.assertEqual(render_review.render(r)[0], '')


class HostileText(unittest.TestCase):
    PAYLOADS = ('</title><script>alert(1)</script>', '<img src=x onerror=alert(1)>', '"><svg onload=alert(1)>',
                "'); alert(1); ('", '<!-- x --!>', '`<b>x</b>`', 'javascript:alert(1)')

    def test_every_value_renders_inert(self):
        for payload in self.PAYLOADS:
            with self.subTest(payload=payload):
                r = example()
                r['system'] = payload
                finding(r)['title'] = payload
                finding(r)['observation'] = payload
                r['architecture']['diagrams'][0]['nodes'][0]['label'] = payload
                r['architecture']['diagrams'][0]['label'] = payload
                r['evidence']['records'][1]['source'] = payload
                r['context']['scenarios'][0]['stimulus'] = payload
                page, found = render_review.render(r)
                self.assertEqual(found, [])
                self.assertEqual(page.count('<script'), 1)
                self.assertNotIn('<img', page)
                self.assertNotIn('<b>', page)

    def test_secret_value_blocks_the_page(self):
        r = example()
        finding(r)['impact'] = 'AKIAABCDEFGHIJKLMNOP'
        self.assertTrue(any('secret-shaped' in m for m in render_review.render(r)[1]))

    def test_shell_carries_the_guarded_policy(self):
        self.assertEqual(html_guard.csp_directives(html_guard.CSP),
                         html_guard.csp_directives(render_review.SHELL.split('content="')[1].split('"')[0]))


class CommandLine(unittest.TestCase):
    def test_repo_check_and_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, out = Path(tmp) / 'repo', Path(tmp) / 'report.html'
            (repo / 'orders').mkdir(parents=True)
            (repo / 'tests').mkdir()
            (repo / 'orders' / 'checkout.py').write_text('def checkout():\n    order = load()\n    capture()\n    commit()\n')
            (repo / 'tests' / 'test_checkout.py').write_text('import mock\nmock.patch("client")\n')
            review = SKILL / 'examples' / 'example-review.json'
            run = lambda: subprocess.run([sys.executable, str(SKILL / 'scripts' / 'render_review.py'), str(review),
                                          '--out', str(out), '--repo', str(repo)], capture_output=True, text=True)
            self.assertEqual(run().returncode, 0)
            self.assertTrue(out.is_file())
            out.unlink()
            (repo / 'orders' / 'checkout.py').write_text('def checkout():\n')
            result = run()
            self.assertEqual(result.returncode, 1)
            self.assertIn('E001: orders/checkout.py:3-4 at --repo', result.stdout)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
