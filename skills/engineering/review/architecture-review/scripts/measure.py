#!/usr/bin/env python3
"""Deterministic, read-only structural measurements for an architecture review.

Every subcommand parses source text or git history; none imports or executes project code.
Each result carries its counting conventions, so numbers from different runs are comparable
and disagreements can be traced to a convention rather than argued about.

Subcommands
  imports      Import graph: module-level, in-function and TYPE_CHECKING edges, the largest
               dependency cycle (strongly connected component), fan-in/fan-out, instability,
               and a package-to-package edge matrix. Python via AST; JS/TS via import regexes.
  writers      Which modules write each table (Python ORM heuristics: constructors, bulk
               insert/update/delete, Django managers). Attribute changes on loaded rows are
               not detected.
  history      Churn, co-change pairs and fix/revert commits per file from git log.
  test-pins    String literals in tests that name module paths (patch targets); the count
               predicts how many tests a file move breaks.
  endpoints    HTTP route declarations per file (FastAPI, Flask, Express-style routers).
  callers      Python call sites of a function, optionally only those passing a keyword with
               a literal value (for example allow_inactive_connection=True).
  occurrences  Files and lines matching a pattern, to count how many places declare or write
               one concept (for example a task name or a status literal).
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from inventory import excluded, git, EXCLUDED_DIRS

JS_EXT = ('.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs')
TEST_PARTS = {'test', 'tests', '__tests__', 'e2e', 'spec'}


# ---------------------------------------------------------------- file walking
def walk(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    """Files under root with the given suffixes; skips excluded, hidden and symlinked paths."""
    out = []
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d.lower() not in EXCLUDED_DIRS and not d.startswith('.')
                         and not (Path(base) / d).is_symlink())
        for name in sorted(files):
            path = Path(base) / name
            if path.suffix in suffixes and not path.is_symlink() and not excluded(path.relative_to(root)):
                out.append(path)
    return out


def is_test(rel: Path) -> bool:
    name = rel.name
    return (any(p.lower() in TEST_PARTS for p in rel.parts[:-1]) or name.startswith('test_')
            or name.endswith('_test.py') or '.test.' in name or '.spec.' in name)


def parse(path: Path):
    try:
        return ast.parse(path.read_text(encoding='utf-8', errors='replace'))
    except (SyntaxError, ValueError):
        return None


def parents_map(tree) -> dict:
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def context(node, parents) -> str:
    """'type_checking', 'function' or 'module' for an import node."""
    in_function = False
    cur = parents.get(node)
    while cur is not None:
        if isinstance(cur, ast.If) and 'TYPE_CHECKING' in ast.unparse(cur.test):
            return 'type_checking'
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            in_function = True
        cur = parents.get(cur)
    return 'function' if in_function else 'module'


# ---------------------------------------------------------------- graph helpers
def sccs(nodes, edges) -> list[list[str]]:
    """Iterative Tarjan strongly connected components."""
    graph = defaultdict(set)
    for a, b in edges:
        graph[a].add(b)
    index, low, on, stack, result, counter = {}, {}, set(), [], [], [0]
    for start in sorted(nodes):
        if start in index:
            continue
        work = [(start, iter(sorted(graph[start])))]
        index[start] = low[start] = counter[0]; counter[0] += 1
        stack.append(start); on.add(start)
        while work:
            v, it = work[-1]
            advanced = False
            for w in it:
                if w not in index:
                    index[w] = low[w] = counter[0]; counter[0] += 1
                    stack.append(w); on.add(w)
                    work.append((w, iter(sorted(graph[w]))))
                    advanced = True
                    break
                if w in on:
                    low[v] = min(low[v], index[w])
            if advanced:
                continue
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[v])
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop(); on.discard(w); comp.append(w)
                    if w == v:
                        break
                result.append(sorted(comp))
    return result


def graph_summary(modules: set, edges: dict, depth: int, top: int) -> dict:
    """edges: {(a, b): kind}; kinds module|function|type_checking."""
    runtime = {e for e, k in edges.items() if k != 'type_checking'}
    module_level = {e for e, k in edges.items() if k == 'module'}
    all_scc = max(sccs(modules, runtime), key=len, default=[])
    mod_scc = max(sccs(modules, module_level), key=len, default=[])
    fan_in, fan_out = Counter(), Counter()
    for a, b in runtime:
        fan_out[a] += 1; fan_in[b] += 1
    def pkg(m):
        return '.'.join(m.split('.')[:depth]) if '.' in m else m
    matrix = Counter()
    for a, b in runtime:
        if pkg(a) != pkg(b):
            matrix[f'{pkg(a)} -> {pkg(b)}'] += 1
    instability = {}
    for m in modules:
        ca, ce = fan_in[m], fan_out[m]
        if ca + ce:
            instability[m] = round(ce / (ca + ce), 2)
    kinds = Counter(edges.values())
    return dict(
        modules=len(modules), edges=len(edges), edges_by_kind=dict(sorted(kinds.items())),
        largest_cycle_including_deferred=dict(size=len(all_scc) if len(all_scc) > 1 else 0,
                                              members=all_scc if len(all_scc) > 1 else []),
        largest_cycle_module_level=dict(size=len(mod_scc) if len(mod_scc) > 1 else 0,
                                        members=mod_scc if len(mod_scc) > 1 else []),
        fan_in_top=fan_in.most_common(top), fan_out_top=fan_out.most_common(top),
        instability=dict(sorted(instability.items())),
        package_edges=dict(matrix.most_common()))


# ---------------------------------------------------------------- imports
def python_modules(root: Path) -> dict[str, Path]:
    mods = {}
    for path in walk(root, ('.py',)):
        rel = path.relative_to(root).with_suffix('')
        parts = list(rel.parts)
        if parts[-1] == '__init__':
            parts = parts[:-1]
        if parts:
            mods['.'.join(parts)] = path
    return mods


def python_imports(root: Path, prefix: str | None, include_tests: bool) -> tuple[set, dict, list]:
    mods = {m: p for m, p in python_modules(root).items()
            if (include_tests or not is_test(p.relative_to(root))) and (not prefix or m == prefix or m.startswith(prefix + '.'))}
    def resolve(name):
        while name and name not in mods:
            name = name.rpartition('.')[0]
        return name or None
    edges, unparsed = {}, []
    rank = {'module': 2, 'function': 1, 'type_checking': 0}
    for mod, path in mods.items():
        tree = parse(path)
        if tree is None:
            unparsed.append(str(path.relative_to(root))); continue
        parents = parents_map(tree)
        package = mod if path.name == '__init__.py' else mod.rpartition('.')[0]
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Import):
                targets = [resolve(a.name) for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ''
                if node.level:
                    anchor = package.split('.')
                    anchor = anchor[:len(anchor) - (node.level - 1)] if node.level > 1 else anchor
                    base = '.'.join([p for p in anchor if p] + ([base] if base else []))
                targets = [resolve(f'{base}.{a.name}') or resolve(base) for a in node.names]
            else:
                continue
            kind = context(node, parents)
            for t in {t for t in targets if t and t != mod}:
                old = edges.get((mod, t))
                if old is None or rank[kind] > rank[old]:
                    edges[(mod, t)] = kind
    return set(mods), edges, unparsed


JS_IMPORT = re.compile(r'''(?:import\s[^'"]*?from\s*|import\s*|export\s[^'"]*?from\s*)['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\)''')
JS_DYNAMIC = re.compile(r'''import\(\s*['"]([^'"]+)['"]\s*\)''')


def js_imports(root: Path, include_tests: bool) -> tuple[set, dict, list]:
    files = [p for p in walk(root, JS_EXT) if include_tests or not is_test(p.relative_to(root))]
    mods = {p.relative_to(root).with_suffix('').as_posix(): p for p in files}
    def resolve(src: Path, spec: str):
        if not spec.startswith('.'):
            return None  # packages and path aliases are not resolved; see limitations
        base = (src.parent / spec).resolve()
        for cand in [base] + [base.with_suffix(e) for e in JS_EXT] + [base / ('index' + e) for e in JS_EXT]:
            try:
                key = cand.relative_to(root.resolve()).with_suffix('').as_posix()
            except ValueError:
                return None
            if key in mods:
                return key
        return None
    edges = {}
    for key, path in mods.items():
        text = path.read_text(encoding='utf-8', errors='replace')
        for m in JS_IMPORT.finditer(text):
            t = resolve(path, m.group(1) or m.group(2))
            if t and t != key:
                edges[(key, t)] = 'module'
        for m in JS_DYNAMIC.finditer(text):
            t = resolve(path, m.group(1))
            if t and t != key and (key, t) not in edges:
                edges[(key, t)] = 'function'
    return set(mods), edges, []


def cmd_imports(args) -> dict:
    root = args.root.resolve(strict=True)
    if args.lang == 'python':
        modules, edges, unparsed = python_imports(root, args.prefix, args.include_tests)
        conv = ['A module is a .py file (package __init__ counts as the package).',
                'One edge per importing module and imported module pair, however many names are imported.',
                "'from a import b' resolves to module a.b when it exists, else to a.",
                "Edge kind is the strongest context of any import of that pair: module > function > type_checking.",
                'Cycles use module and function edges; TYPE_CHECKING-only imports are excluded.',
                'Instability I = Ce / (Ca + Ce) over runtime edges.']
    else:
        modules, edges, unparsed = js_imports(root, args.include_tests)
        conv = ['A module is a source file; relative specifiers only (package imports and path aliases are not resolved).',
                'Static import/export/require edges are module-level; import() edges count as deferred (function).',
                'Instability I = Ce / (Ca + Ce).']
    result = graph_summary(modules, edges, args.depth, args.top)
    result.update(root=str(root), language=args.lang, conventions=conv, unparsed_files=unparsed,
                  limitations=['Static text analysis: dynamic imports by computed name are invisible.',
                               'Tests are excluded unless --include-tests is given.'])
    return result


# ---------------------------------------------------------------- writers
WRITE_FUNCS = {'insert', 'update', 'delete'}


def cmd_writers(args) -> dict:
    root = args.root.resolve(strict=True)
    files = [p for p in walk(root, ('.py',)) if args.include_tests or not is_test(p.relative_to(root))]
    trees = {p: parse(p) for p in files}
    models = {}
    for path, tree in trees.items():
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            table = None
            for stmt in node.body:
                if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '__tablename__' for t in stmt.targets):
                    if isinstance(stmt.value, ast.Constant):
                        table = str(stmt.value.value)
            if table is None and any(ast.unparse(b).endswith('models.Model') for b in node.bases):
                table = node.name.lower()
            if table:
                models[node.name] = table
    writers = defaultdict(lambda: defaultdict(list))
    for path, tree in trees.items():
        if tree is None:
            continue
        rel = path.relative_to(root).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            how = model = None
            if isinstance(f, ast.Name) and f.id in models:
                how, model = 'construct', f.id
            elif isinstance(f, ast.Name) and f.id in WRITE_FUNCS and node.args and isinstance(node.args[0], ast.Name) and node.args[0].id in models:
                how, model = f.id, node.args[0].id
            elif isinstance(f, ast.Attribute) and f.attr in ('update', 'delete', 'create', 'bulk_create', 'get_or_create', 'update_or_create'):
                text = ast.unparse(f.value)
                m = re.search(r'query\(\s*([A-Z]\w*)', text) or re.match(r'([A-Z]\w*)\.objects', text)
                if m and m.group(1) in models:
                    how, model = f.attr, m.group(1)
            if model:
                writers[models[model]][rel].append(f'{how}:{node.lineno}')
    tables = {t: dict(writer_modules=len(mods), writers={m: v for m, v in sorted(mods.items())})
              for t, mods in sorted(writers.items())}
    return dict(root=str(root), models=len(models), tables_with_writers=len(tables), tables=tables,
                conventions=['A writer is a module containing a constructor call of the model class, insert/update/delete(Model), '
                             'query(Model)...update/delete, or Model.objects create/update/delete.',
                             'Counts are per module; line numbers identify each site.'],
                limitations=['Attribute assignment on loaded rows and raw SQL writes are not detected.',
                             'A constructor call can build an unsaved object; confirm persistence before calling it a write.'])


# ---------------------------------------------------------------- history
FIX = re.compile(r'^(fix|hotfix|revert|bugfix)\b|^Revert\b', re.I)


def cmd_history(args) -> dict:
    repo = args.root.resolve(strict=True)
    fmt = '--format=@@%H%x09%s'
    log = git(repo, 'log', '--no-merges', f'--since={args.since}', '--name-only', fmt)
    commits, cur = [], None
    for line in log.splitlines():
        if line.startswith('@@'):
            sha, _, subject = line[2:].partition('\t')
            cur = dict(sha=sha[:9], subject=subject, files=[]); commits.append(cur)
        elif line.strip() and cur is not None and not excluded(Path(line.strip())):
            cur['files'].append(line.strip())
    churn, fixes, pairs = Counter(), defaultdict(list), Counter()
    for c in commits:
        files = [f for f in c['files'] if not args.path or f.startswith(args.path)]
        churn.update(files)
        if FIX.search(c['subject']):
            for f in files:
                fixes[f].append(f"{c['sha']} {c['subject'][:80]}")
        if 1 < len(files) <= args.max_files_per_commit:
            for i, a in enumerate(sorted(files)):
                for b in sorted(files)[i + 1:]:
                    pairs[(a, b)] += 1
    top_pairs = [dict(a=a, b=b, commits=n, support=round(n / min(churn[a], churn[b]), 2))
                 for (a, b), n in pairs.most_common(args.top) if n >= 2]
    return dict(root=str(repo), since=args.since, commits=len(commits),
                churn_top=churn.most_common(args.top),
                fix_commits_top=sorted(((f, len(v), v[:5]) for f, v in fixes.items()), key=lambda x: -x[1])[:args.top],
                co_change_top=top_pairs,
                conventions=['Merge commits excluded.',
                             f'Co-change ignores commits touching more than {args.max_files_per_commit} files.',
                             'support = shared commits / commits of the less-changed file.',
                             'A fix commit has a subject starting with fix, hotfix, bugfix or revert.'],
                limitations=['Co-change is correlation, not causation.',
                             'Renames are not followed; squash merges hide intermediate history.'])


# ---------------------------------------------------------------- test pins
def cmd_test_pins(args) -> dict:
    root = args.root.resolve(strict=True)
    pattern = re.compile(r'^' + re.escape(args.prefix) + r'[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)+$')
    total, by_module, private = 0, Counter(), 0
    files = [p for p in walk(root, ('.py',)) if is_test(p.relative_to(root))]
    for path in files:
        tree = parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and pattern.match(node.value):
                total += 1
                parts = node.value.split('.')
                by_module['.'.join(parts[:-1])] += 1
                private += parts[-1].startswith('_')
    return dict(root=str(root), prefix=args.prefix, test_files=len(files), pins=total, private_name_pins=private,
                pins_by_module_top=by_module.most_common(args.top),
                conventions=['A pin is a string literal in a test file that names a dotted path under the prefix, '
                             'such as a mock.patch target.'],
                limitations=['Python tests only; JS module mocks are not counted.'])


# ---------------------------------------------------------------- endpoints
PY_ROUTE = re.compile(r'^\s*@(\w+)\.(get|post|put|patch|delete|route|api_route|websocket)\(', re.M)
JS_ROUTE = re.compile(r'\b(router|app|server)\.(get|post|put|patch|delete|all)\(\s*[\'"`]')


def cmd_endpoints(args) -> dict:
    root = args.root.resolve(strict=True)
    per_file = {}
    for path in walk(root, ('.py',) + JS_EXT):
        rel = path.relative_to(root)
        if is_test(rel):
            continue
        text = path.read_text(encoding='utf-8', errors='replace')
        n = len((PY_ROUTE if path.suffix == '.py' else JS_ROUTE).findall(text))
        if n:
            per_file[rel.as_posix()] = n
    return dict(root=str(root), endpoints=sum(per_file.values()), files=len(per_file),
                per_file=dict(sorted(per_file.items(), key=lambda x: -x[1])),
                conventions=['Python: decorators like @router.get/@app.route; JS: router/app.<verb>("path").'],
                limitations=['Routes registered programmatically or by framework conventions are not counted.'])


# ---------------------------------------------------------------- callers
def cmd_callers(args) -> dict:
    root = args.root.resolve(strict=True)
    keyword = None
    if args.keyword:
        k, _, v = args.keyword.partition('=')
        keyword = (k, v)
    sites = []
    for path in walk(root, ('.py',)):
        rel = path.relative_to(root)
        if is_test(rel) and not args.include_tests:
            continue
        tree = parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', None)
            if args.function and name != args.function:
                continue
            if keyword:
                if not any(kw.arg == keyword[0] and ast.unparse(kw.value) == keyword[1] for kw in node.keywords):
                    continue
            sites.append(dict(file=rel.as_posix(), line=node.lineno, call=ast.unparse(node)[:160]))
    return dict(root=str(root), function=args.function, keyword=args.keyword, sites=len(sites),
                modules=sorted({s['file'] for s in sites}), calls=sites,
                conventions=['Matches the called name (bare or attribute); aliases and indirect references are not followed.'],
                limitations=['Python only. Compare the module list with an allowlist to design a caller-pinning test.'])


# ---------------------------------------------------------------- occurrences
def cmd_occurrences(args) -> dict:
    root = args.root.resolve(strict=True)
    pattern = re.compile(args.pattern)
    suffixes = tuple(args.suffix) if args.suffix else ('.py',) + JS_EXT
    hits = {}
    for path in walk(root, suffixes):
        rel = path.relative_to(root)
        if is_test(rel) and not args.include_tests:
            continue
        lines = [i + 1 for i, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines())
                 if pattern.search(line)]
        if lines:
            hits[rel.as_posix()] = lines
    return dict(root=str(root), pattern=args.pattern, files=len(hits), occurrences=sum(len(v) for v in hits.values()),
                per_file=hits,
                conventions=['One occurrence per matching line; tests excluded unless --include-tests.'],
                limitations=['Textual: a match can be a read, a write or a comment. Classify sites before counting '
                             'declarations or writers.'])


# ---------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, help='write JSON here (must be outside the measured tree)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('imports'); p.add_argument('root', type=Path)
    p.add_argument('--lang', choices=('python', 'js'), default='python')
    p.add_argument('--prefix', help='only modules under this dotted prefix, e.g. app')
    p.add_argument('--depth', type=int, default=2, help='dotted depth used to group packages in the matrix')
    p.add_argument('--top', type=int, default=15); p.add_argument('--include-tests', action='store_true')
    p.set_defaults(fn=cmd_imports)
    p = sub.add_parser('writers'); p.add_argument('root', type=Path); p.add_argument('--include-tests', action='store_true')
    p.set_defaults(fn=cmd_writers)
    p = sub.add_parser('history'); p.add_argument('root', type=Path)
    p.add_argument('--since', default='6 months ago'); p.add_argument('--path', help='only files under this path prefix')
    p.add_argument('--top', type=int, default=20); p.add_argument('--max-files-per-commit', type=int, default=30)
    p.set_defaults(fn=cmd_history)
    p = sub.add_parser('test-pins'); p.add_argument('root', type=Path); p.add_argument('--prefix', default='app.')
    p.add_argument('--top', type=int, default=15); p.set_defaults(fn=cmd_test_pins)
    p = sub.add_parser('endpoints'); p.add_argument('root', type=Path); p.set_defaults(fn=cmd_endpoints)
    p = sub.add_parser('callers'); p.add_argument('root', type=Path); p.add_argument('--function')
    p.add_argument('--keyword', help='KEY=VALUE, the literal source text of the value, e.g. host_approved=True')
    p.add_argument('--include-tests', action='store_true'); p.set_defaults(fn=cmd_callers)
    p = sub.add_parser('occurrences'); p.add_argument('root', type=Path); p.add_argument('--pattern', required=True)
    p.add_argument('--suffix', action='append'); p.add_argument('--include-tests', action='store_true')
    p.set_defaults(fn=cmd_occurrences)
    args = ap.parse_args()
    try:
        if args.cmd == 'callers' and not (args.function or args.keyword):
            raise ValueError('callers needs --function, --keyword, or both')
        result = args.fn(args)
        result['measure_version'] = '1.0'
        text = json.dumps(result, indent=2, ensure_ascii=False) + '\n'
        if args.out:
            out = args.out.resolve()
            root = args.root.resolve()
            if out == root or root in out.parents:
                raise ValueError('Output must be outside the measured tree')
            with out.open('x', encoding='utf-8') as fh:
                fh.write(text)
            print(out)
        else:
            sys.stdout.write(text)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
