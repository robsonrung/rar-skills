import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / 'scripts'))
import measure  # noqa: E402


def write(root, rel, text):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class Imports(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write(self.root, 'app/__init__.py', '')
        write(self.root, 'app/a.py', 'from app import b\n')
        write(self.root, 'app/b.py', 'def f():\n    from app import c\n')
        write(self.root, 'app/c.py', 'import app.a\n')
        write(self.root, 'app/d.py', 'from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from app import a\n')
        write(self.root, 'node_modules/x.py', 'import app.a\n')
        write(self.root, 'tests/test_a.py', 'import app.a\n')

    def tearDown(self):
        self.tmp.cleanup()

    def run_imports(self, **kw):
        args = Namespace(root=self.root, lang='python', prefix='app', include_tests=False, depth=2, top=5)
        vars(args).update(kw)
        return measure.cmd_imports(args)

    def test_deferred_import_hides_a_cycle(self):
        r = self.run_imports()
        self.assertEqual(r['largest_cycle_module_level']['size'], 0)
        self.assertEqual(r['largest_cycle_including_deferred']['members'], ['app.a', 'app.b', 'app.c'])
        self.assertEqual(r['edges_by_kind'], {'function': 1, 'module': 2, 'type_checking': 1})

    def test_excluded_and_test_paths_are_skipped(self):
        self.assertEqual(self.run_imports()['modules'], 5)
        self.assertTrue(measure.excluded(Path('node_modules/x.py')))
        self.assertTrue(measure.excluded(Path('config/.env.local')))
        self.assertFalse(measure.excluded(Path('app/a.py')))


@unittest.skipUnless(shutil.which('git'), 'git not available')
class History(unittest.TestCase):
    def test_churn_co_change_and_fixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            env = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@example.com',
                       GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@example.com')
            def git(*a):
                subprocess.run(['git', '-C', str(repo), *a], check=True, capture_output=True, env=env)
            git('init', '-q')
            for i, (files, msg) in enumerate([(['a.py', 'b.py'], 'add a and b'), (['a.py', 'b.py'], 'fix: shared bug'),
                                              (['a.py'], 'tune a')]):
                for f in files:
                    write(repo, f, f'# {i}\n')
                git('add', '.')
                git('commit', '-q', '-m', msg)
            r = measure.cmd_history(Namespace(root=repo, since='10 years ago', path=None, top=5, max_files_per_commit=30))
            self.assertEqual(r['commits'], 3)
            self.assertEqual(r['churn_top'][0], ('a.py', 3))
            self.assertEqual(r['co_change_top'], [dict(a='a.py', b='b.py', commits=2, support=1.0)])
            self.assertEqual([f for f, _, _ in r['fix_commits_top']], ['a.py', 'b.py'])


class Cli(unittest.TestCase):
    def test_refuses_output_inside_measured_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp), 'm.py', 'import os\n')
            p = subprocess.run([sys.executable, str(SKILL / 'scripts' / 'measure.py'), '--out', f'{tmp}/out.json',
                                'imports', tmp], capture_output=True, text=True)
            self.assertEqual(p.returncode, 1)
            self.assertIn('outside the measured tree', p.stderr)
            p = subprocess.run([sys.executable, str(SKILL / 'scripts' / 'measure.py'), 'occurrences', tmp,
                                '--pattern', 'import'], capture_output=True, text=True)
            self.assertEqual(json.loads(p.stdout)['occurrences'], 1)


if __name__ == '__main__':
    unittest.main()
