#!/usr/bin/env python3
"""Exercise the package contract, safe metadata inventory and offline renderer."""
from __future__ import annotations
import copy
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import inventory
import measure
import render_report
import revision_check
import evidence_tool
import compare_audits
from validate_report import ROOT, read_json, validate, repo_errors

class Elements(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids=[]; self.links=[]; self.external=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if 'id' in a: self.ids.append(a['id'])
        if a.get('href','').startswith('#'): self.links.append(a['href'][1:])
        if tag in ('script','img','iframe','link') and (a.get('src') or a.get('href')):
            self.external.append(a.get('src') or a.get('href'))

class ContractTests(unittest.TestCase):
    def setUp(self): self.data=read_json(ROOT/'examples/demo-audit.json')
    def assertInvalid(self, data=None, fragment=None):
        errors=validate(self.data if data is None else data)
        self.assertTrue(errors)
        if fragment: self.assertTrue(any(fragment in e for e in errors),errors)
    def test_demo_valid(self): self.assertEqual(validate(self.data),[])
    def test_missing_dimension(self):
        self.data['dimensions'].pop(); self.assertInvalid()
    def test_duplicate_dimension(self):
        self.data['dimensions'][-1]=copy.deepcopy(self.data['dimensions'][0]); self.assertInvalid()
    def test_ghost_evidence(self):
        self.data['findings'][0]['evidence']=['GHOST']; self.assertInvalid(fragment='unknown reference')
    def test_unknown_field(self):
        self.data['invented_score']=99; self.assertInvalid(fragment='unknown field')
    def test_navigation_id_collision(self):
        self.data['metrics'][0]['id']='main'; self.assertInvalid(fragment='collide')
    def test_source_script_url(self):
        self.data['sources'][0]['url']='javascript:alert(1)'; self.assertInvalid()
    def test_source_credentials(self):
        self.data['sources'][0]['url']='https://secret:password@example.org'; self.assertInvalid()
    def test_real_report_disallows_demo_evidence(self):
        self.data['meta']['is_demo']=False; self.assertInvalid(fragment='demo evidence')
    def test_real_report_disallows_demo_diagram(self):
        self.data['meta']['is_demo']=False; self.assertInvalid(fragment='demo diagram')
    def test_evidence_self_support(self):
        e=self.data['evidence'][0]; e['supports']=[e['id']]; self.assertInvalid(fragment='support itself')
    def test_evidence_cycle(self):
        a,b=self.data['evidence'][:2]; a['supports']=[b['id']]; b['supports']=[a['id']]
        self.assertInvalid(fragment='support cycle')
    def test_inference_requires_support(self):
        self.data['evidence'][0]['kind']='inference'; self.assertInvalid(fragment='supporting evidence')
    def test_code_requires_lines(self):
        e=self.data['evidence'][0]; e['kind']='code'; e['line_start']=e['line_end']=None
        self.assertInvalid(fragment='line numbers')
    def test_invalid_line_range(self):
        e=self.data['evidence'][0]; e['line_start']=9; e['line_end']=2
        self.assertInvalid(fragment='line range')
    def test_unknown_is_not_numeric(self):
        m=self.data['metrics'][0]; m['current_kind']='unknown'; m['current']=500
        self.assertInvalid(fragment='must be null')
    def test_unknown_confidence(self):
        d=self.data['dimensions'][0]; d['status']='unknown'; d['confidence']='high'
        self.assertInvalid(fragment='high confidence')
    def test_no_status_quo(self):
        self.data['options']=[o for o in self.data['options'] if o['position']!='keep']
        self.assertInvalid(fragment='maintaining')
    def test_multiple_recommendations(self):
        self.data['options'][-1]['position']='recommended'; self.assertInvalid(fragment='at most one')
    def test_roadmap_cycle(self):
        a,b=self.data['roadmap'][:2]; a['depends_on']=[b['id']]; b['depends_on']=[a['id']]
        self.assertInvalid(fragment='dependency cycle')
    def test_unexecuted_has_no_exit(self):
        self.data['verification'][0]['exit_code']=0; self.assertInvalid(fragment='null exit code')
    def test_pass_requires_zero_exit(self):
        v=self.data['verification'][0]; v['status']='pass'; v['exit_code']=1
        self.assertInvalid(fragment='exit code 0')
    def test_agent_pass_needs_evidence(self):
        a=self.data['agent_checks'][0]; a['status']='pass'; a['evidence']=[]
        self.assertInvalid(fragment='result needs evidence')
    def test_diagram_unknown_node(self):
        self.data['diagrams'][0]['edges'][0]['to']='UNKNOWN'; self.assertInvalid(fragment='unknown reference')
    def test_diagram_overlapping_cells(self):
        a,b=self.data['diagrams'][0]['nodes'][:2]; b['col']=a['col']; b['row']=a['row']
        self.assertInvalid(fragment='same cell')
    def test_no_diagram_requires_explanation(self):
        self.data['diagrams']=[]; self.data['diagram_gaps']=[]; self.assertInvalid(fragment='reconstructed')
    def test_current_diagram_cannot_mix_proposals(self):
        d=self.data['diagrams'][0]; d['state']='observed'; d['edges'][0]['basis']='proposed'
        self.assertInvalid(fragment='current architecture')
    def test_json_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'data.json'; p.write_text('{"a":1,"a":2}')
            with self.assertRaises(ValueError): read_json(p)
    def test_json_nonfinite_number(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'data.json'; p.write_text('{"a":NaN}')
            with self.assertRaises(ValueError): read_json(p)

class RenderTests(unittest.TestCase):
    def setUp(self): self.data=read_json(ROOT/'examples/demo-audit.json')
    def test_deterministic(self): self.assertEqual(render_report.render(self.data),render_report.render(self.data))
    def test_escapes_untrusted_markup(self):
        self.data['verdict']['headline']='UNTRUSTED<script>window.pwned=true</script>'
        html=render_report.render(self.data)
        self.assertIn('UNTRUSTED&lt;script&gt;',html)
        self.assertNotIn('UNTRUSTED<script>',html)
    def test_internal_links_and_ids(self):
        parser=Elements(); parser.feed(render_report.render(self.data))
        self.assertEqual(len(parser.ids),len(set(parser.ids)))
        self.assertEqual(set(parser.links)-set(parser.ids),set())
    def test_no_external_assets(self):
        parser=Elements(); parser.feed(render_report.render(self.data)); self.assertEqual(parser.external,[])
    def test_english_interface(self):
        self.data['language']='en'; self.assertIn('FICTIONAL DEMONSTRATION.',render_report.render(self.data))
    def test_diagrams_and_no_placeholders(self):
        html=render_report.render(self.data)
        self.assertEqual(html.count('<svg '),4); self.assertNotIn('@@CONTENT@@',html)
    def test_exports_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'report.html'; paths=render_report.export(self.data,p)
            before={str(x):x.read_bytes() for x in paths}
            with self.assertRaises(ValueError): render_report.export(self.data,p)
            self.assertEqual(before,{str(x):x.read_bytes() for x in paths})
            self.assertEqual(len((Path(td)/'evidence.jsonl').read_text().splitlines()),len(self.data['evidence']))
    def test_export_preflight_no_partial_files(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/'evidence.jsonl').write_text('existing')
            with self.assertRaises(ValueError): render_report.export(self.data,p/'report.html')
            self.assertFalse((p/'report.html').exists())

class InventoryTests(unittest.TestCase):
    def fixture(self,root):
        (root/'src').mkdir(); (root/'src/main.py').write_text('raise RuntimeError("MUST NOT EXECUTE")')
        (root/'.env').write_text('PASSWORD=do-not-read')
        (root/'node_modules').mkdir(); (root/'node_modules/vendor.js').write_text('skip')
        (root/'README.md').write_text('fixture')
        (root/'linked.py').symlink_to(root/'src/main.py')
    def test_metadata_only_exclusions_and_no_modification(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.fixture(root)
            before={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file() and not p.is_symlink()}
            with patch.object(inventory,'git',side_effect=OSError('unavailable')):
                data=inventory.collect(root)
            names={f['path'] for f in data['files']}
            self.assertEqual(names,{'src/main.py','README.md'})
            self.assertFalse(data['truncated'])
            after={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file() and not p.is_symlink()}
            self.assertEqual(before,after)
            self.assertNotIn('do-not-read',json.dumps(data))
    def test_content_is_not_read(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.fixture(root)
            with patch.object(inventory,'git',side_effect=OSError('unavailable')), patch.object(Path,'read_text',side_effect=AssertionError('content read')), patch.object(Path,'read_bytes',side_effect=AssertionError('content read')):
                self.assertEqual(inventory.collect(root)['included_files'],2)
    def test_file_limit_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.fixture(root)
            with patch.object(inventory,'git',side_effect=OSError('unavailable')): data=inventory.collect(root,1)
            self.assertTrue(data['truncated']); self.assertEqual(data['included_files'],1)
    def test_refuses_output_inside_repo(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.fixture(root)
            result=subprocess.run([sys.executable,str(ROOT/'scripts/inventory.py'),str(root),'--out',str(root/'inventory.json')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0); self.assertFalse((root/'inventory.json').exists())
    def test_sensitive_paths(self):
        for name in ('.env','.env.example','.npmrc','private-key.txt','secrets/config.yaml','auth-token.json','cert.pem'):
            self.assertTrue(inventory.excluded(Path(name)),name)

class CanonicalContractTests(unittest.TestCase):
    def setUp(self): self.data=read_json(ROOT/'examples/demo-audit.json')
    def rejected(self,fragment):
        errors=validate(self.data)
        self.assertTrue(any(fragment in e for e in errors),errors)
    def test_schema_version_two(self):
        self.data['schema_version']='1.0'; self.rejected('not in')
    def test_english_only_contract(self):
        self.data['language']='pt-BR'; self.rejected('not in')
    def test_concept_register_required(self):
        del self.data['concept_applications']; self.rejected('missing concept_applications')
    def test_finding_anchor_required(self):
        del self.data['findings'][0]['leitwort']; self.rejected('missing leitwort')
    def test_unknown_term_rejected(self):
        self.data['concept_applications'][0]['term_id']='T99'; self.rejected('unknown canonical term')
    def test_unknown_finding_term_rejected(self):
        self.data['findings'][0]['leitwort']='T99'; self.rejected('unknown canonical term')
    def test_decision_names_canonical_term(self):
        self.data['concept_applications'][0]['decision']='Investigate everything carefully.'
        self.rejected('decision must name the canonical term')
    def test_concept_requires_active_recurrence(self):
        self.data['concept_applications'][0]['action']='Collect a baseline.'
        self.data['concept_applications'][0]['verification']='Inspect the results.'
        self.rejected('active term must recur')
    def test_applied_decision_needs_evidence(self):
        self.data['concept_applications'][0]['evidence']=[]; self.rejected('applied decision needs evidence')
    def test_applied_decision_needs_attribution(self):
        self.data['concept_applications'][0]['sources']=[]; self.rejected('applied decision needs source attribution')
    def test_concept_reference_exists(self):
        self.data['concept_applications'][0]['related_findings']=['GHOST']; self.rejected('unknown reference')
    def test_finding_must_link_applied_decision(self):
        self.data['concept_applications'][0]['status']='unknown'; self.rejected('linked applied concept decision')
    def test_finding_must_name_anchor(self):
        self.data['findings'][0]['decision_statement']='Improve the structure.'
        self.rejected('decision_statement must name the canonical term')
    def test_finding_requires_active_recurrence(self):
        f=self.data['findings'][0]
        f['recommendation']='Improve recovery.'; f['validation']='Inspect recovery.'; f['acceptance']='Recovery works.'
        self.rejected('main Leitwort must recur')
    def test_navigation_reserves_concepts(self):
        self.data['concept_applications'][0]['id']='concepts'; self.rejected('collide')
    def test_term_catalog_ids_and_sources(self):
        terms=read_json(ROOT/'assets/terms.json'); sources={s['id'] for s in read_json(ROOT/'assets/sources.json')}
        self.assertEqual(len(terms),len({t['id'] for t in terms}))
        self.assertEqual(len(terms),len({t['term'] for t in terms}))
        for t in terms:
            self.assertTrue(t['definition'] and t['decision_question'] and t['guardrail'])
            self.assertFalse(set(t['sources'])-sources,t['id'])
    def test_requested_terminology_present(self):
        names={t['term'] for t in read_json(ROOT/'assets/terms.json')}
        required={'Ubiquitous Language','Bounded Context','Context Map','Anticorruption Layer',
                  'Tactical Building Blocks','Entity','Entities','Value Object','Aggregate',
                  'Aggregate Root','Domain Service','Repository','Factory','Specification',
                  'Side-Effect-Free Function','Intention-Revealing Interface','The Dependency Rule',
                  'Use Cases (Interactors)','Interface Adapters','Frameworks and Drivers',
                  'Component Cohesion','Component Coupling','Main Sequence and Distance',
                  'Humble Object Pattern','Policy vs. Detail','Screaming Architecture',
                  'ACID','SSTables and LSM-Trees','B-Trees','Column-Oriented Storage','Quorums',
                  'Replication Lag Anomalies','Read-After-Write','Monotonic Reads','Consistent Prefix Reads',
                  'Linearizability','Multi-Version Concurrency Control (MVCC)',
                  'Serializable Snapshot Isolation (SSI)','Total Order Broadcast','Consensus','Paxos','Raft',
                  'Change Data Capture (CDC)','Event Sourcing','Effectively-Once Processing','seam'}
        self.assertFalse(required-names)
        for acronym in ('REP','CCP','CRP','ADP','SDP','SAP'):
            self.assertTrue(any('('+acronym+')' in n for n in names),acronym)
    def test_concepts_render_with_decisions(self):
        document=render_report.render(self.data)
        self.assertIn('Concepts in action',document)
        for c in self.data['concept_applications']:
            self.assertIn('id="'+c['id']+'"',document)
            self.assertIn(render_report.esc(c['decision']),document)
    def test_decision_markup_is_escaped(self):
        self.data['concept_applications'][0]['action']='<script>attack()</script>'
        document=render_report.render(self.data)
        self.assertNotIn('<script>attack()',document)
        self.assertIn('&lt;script&gt;attack()',document)
    def test_behavioral_cases_are_not_executed(self):
        cases=read_json(ROOT/'evals/cases.json')
        self.assertGreaterEqual(len(cases),33)
        self.assertTrue(all(c['status']=='not_run' for c in cases))
    def test_english_artifacts_no_portuguese_markers(self):
        import re
        pattern=re.compile(r'\b(não|usuários|avaliação|evidências|relatório|repositório|faturamento|desconhecido|implantação|verificação|Somente leitura|premissa fictícia|melhoria|conceitos|nenhum|português)\b',re.I)
        for folder in ('references','assets','examples','evals'):
            for path in (ROOT/folder).rglob('*'):
                if path.suffix in ('.md','.json','.jsonl','.html'):
                    self.assertIsNone(pattern.search(path.read_text()),str(path))
    def test_nonapplied_concept_keeps_explicit_status(self):
        statuses={c['status'] for c in self.data['concept_applications']}
        self.assertTrue({'applied','unknown','not_applicable'}<=statuses)
        self.assertEqual(validate(self.data),[])


class SchemaV21Tests(unittest.TestCase):
    def setUp(self): self.data=read_json(ROOT/'examples/demo-audit.json')
    def rejected(self,fragment):
        errors=validate(self.data)
        self.assertTrue(any(fragment in e for e in errors),errors)
    def test_demo_uses_v21(self):
        self.assertEqual(self.data['schema_version'],'2.1'); self.assertEqual(validate(self.data),[])
    def test_v20_report_still_valid(self):
        for k in ('revision_check','respected_decisions','guardrails','target','external_reviews'): self.data.pop(k)
        for f in self.data['findings']:
            for k in ('summary','dependency_category','newer_ref_status','adr_conflict','incident','guardrails'): f.pop(k,None)
        for r in self.data['roadmap']:
            for k in ('must_preserve','first_move','guardrails'): r.pop(k,None)
        self.data['schema_version']='2.0'; self.assertEqual(validate(self.data),[])
    def test_v21_fields_require_version(self):
        self.data['schema_version']='2.0'; self.rejected('require schema_version 2.1')
    def test_first_move_limit(self):
        for r in self.data['roadmap']: r['first_move']=True
        self.data['roadmap'].append(dict(copy.deepcopy(self.data['roadmap'][0]),id='R099',depends_on=[]))
        self.rejected('at most three')
    def test_newer_ref_requires_recheck(self):
        self.data['revision_check']['newer_ref']='origin/main'; self.rejected('record newer_ref_status')
    def test_fixed_upstream_cannot_stay_p1(self):
        self.data['revision_check']['newer_ref']='origin/main'
        for f in self.data['findings']: f['newer_ref_status']='unchanged'
        f=self.data['findings'][0]; f['priority']='P1'; f['newer_ref_status']='fixed'
        self.rejected('cannot stay P0/P1')
    def test_unknown_guardrail_reference(self):
        self.data['findings'][1]['guardrails']=['GR99']; self.rejected('unknown reference GR99')
    def test_proposed_guardrail_needs_sketch(self):
        self.data['guardrails'][0]['sketch']=None; self.rejected('needs a sketch')
    def test_target_diagram_must_be_proposed(self):
        self.data['target']['diagram']='G001'; self.rejected('must be a proposed view')
    def test_summary_wins_are_short(self):
        self.data['findings'][1]['summary']['wins']=['x'*71]; self.rejected('short phrases')
    def test_external_review_references_findings(self):
        self.data['external_reviews'][0]['adopted_findings']=['F999']; self.rejected('unknown reference F999')
    def test_new_ids_are_unique(self):
        self.data['guardrails'][0]['id']='F001'; self.rejected('unique')
    def test_repo_check_lines_and_excerpt(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td); (repo/'src').mkdir(); (repo/'src/a.py').write_text('def f():\n    return 42\n')
            e=self.data['evidence'][0]
            e.update(kind='code',location='src/a.py',line_start=1,line_end=2,excerpt='return 42')
            self.assertEqual(repo_errors(self.data,repo),[])
            e['excerpt']='return 43'; self.assertTrue(any('excerpt' in x for x in repo_errors(self.data,repo)))
            e['line_end']=9; self.assertTrue(any('exceeds' in x for x in repo_errors(self.data,repo)))
            e['location']='src/missing.py'; self.assertTrue(any('not found' in x for x in repo_errors(self.data,repo)))

class RenderV21Tests(unittest.TestCase):
    def setUp(self): self.data=read_json(ROOT/'examples/demo-audit.json')
    def test_new_sections_render(self):
        html=render_report.render(self.data)
        for anchor in ('revision','decisions','target','guardrails','reviews','GR01','TR01','RD01','XR01'):
            self.assertIn(f'id="{anchor}"',html)
        self.assertIn('First move',html); self.assertIn('Must preserve',html)
        self.assertIn('summary-block',html)
    def test_both_themes_defined(self):
        html=render_report.render(self.data)
        self.assertIn('@media (prefers-color-scheme: dark){:root:not([data-theme="light"])',html)
        self.assertIn(':root[data-theme="dark"]',html)
        self.assertIn('var(--svg-node)',html)
        self.assertNotIn('fill="#fff"',html)
    def test_artifact_mode(self):
        html=render_report.render(self.data,artifact=True)
        self.assertTrue(html.startswith('<title>Atlas Architecture Review</title>'))
        for banned in ('<!doctype','<html','<head>','<body>','print-button','window.print','Content-Security-Policy'):
            self.assertNotIn(banned,html)
        self.assertIn('<style>',html); self.assertIn('id="report-search"',html)
    def test_artifact_links_resolve(self):
        parser=Elements(); parser.feed(render_report.render(self.data,artifact=True))
        self.assertEqual(set(parser.links)-set(parser.ids),set()); self.assertEqual(parser.external,[])
    def test_custom_title(self):
        self.assertIn('<title>Atlas Review</title>',render_report.render(self.data,artifact=True,title='Atlas Review'))

class MeasureTests(unittest.TestCase):
    def pkg(self,root):
        app=root/'app'; (app/'core').mkdir(parents=True); (root/'tests').mkdir()
        (app/'__init__.py').write_text(''); (app/'core/__init__.py').write_text('')
        (app/'a.py').write_text('from app import b\nfrom typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from app import c\n')
        (app/'b.py').write_text('def g():\n    from app.a import x\n    return x\nclass Order:\n    __tablename__ = "orders"\n')
        (app/'c.py').write_text('from app.b import Order\nfrom sqlalchemy import update\ndef h(db):\n    db.add(Order())\n    db.execute(update(Order))\n    gate(1, relax=True)\n')
        (app/'core/d.py').write_text('from .. import a\nSTATUS = "done"\n')
        (root/'tests/test_x.py').write_text('from unittest.mock import patch\n@patch("app.b.g")\n@patch("app.c._private")\ndef test_x(): pass\n')
        (root/'.env').write_text('SECRET=do-not-read')
    def test_import_graph_cycle_and_contexts(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.pkg(root)
            mods,edges,_=measure.python_imports(root,'app',False)
            self.assertEqual(edges[('app.a','app.b')],'module')
            self.assertEqual(edges[('app.b','app.a')],'function')
            self.assertEqual(edges[('app.a','app.c')],'type_checking')
            self.assertEqual(edges[('app.core.d','app.a')],'module')
            summary=measure.graph_summary(mods,edges,2,5)
            self.assertEqual(summary['largest_cycle_including_deferred']['size'],2)
            self.assertEqual(summary['largest_cycle_module_level']['size'],0)
    def test_writers_callers_pins_occurrences(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.pkg(root)
            ns=lambda **k: type('A',(),dict(dict(include_tests=False,top=5),**k))()
            w=measure.cmd_writers(ns(root=root/'app'))
            self.assertEqual(sorted(w['tables']['orders']['writers']),['c.py'])
            c=measure.cmd_callers(ns(root=root/'app',function='gate',keyword='relax=True'))
            self.assertEqual(c['sites'],1)
            t=measure.cmd_test_pins(ns(root=root,prefix='app.'))
            self.assertEqual((t['pins'],t['private_name_pins']),(2,1))
            o=measure.cmd_occurrences(ns(root=root/'app',pattern='"done"',suffix=None))
            self.assertEqual(o['files'],1)
            self.assertNotIn('do-not-read',json.dumps([w,c,t,o]))
    def test_js_imports(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/'src').mkdir()
            (root/'src/a.ts').write_text("import { b } from './b'\nconst c = () => import('./c')\n")
            (root/'src/b.ts').write_text("export const b = 1\nimport a from './a'\n"); (root/'src/c.ts').write_text('export {}')
            mods,edges,_=measure.js_imports(root,False)
            self.assertEqual(edges[('src/a','src/b')],'module'); self.assertEqual(edges[('src/a','src/c')],'function')
            self.assertEqual(measure.graph_summary(mods,edges,1,5)['largest_cycle_module_level']['size'],2)
    def test_refuses_output_inside_tree(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); self.pkg(root)
            r=subprocess.run([sys.executable,str(ROOT/'scripts/measure.py'),'--out',str(root/'m.json'),'imports',str(root)],capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0); self.assertFalse((root/'m.json').exists())

def make_git_repo(root):
    run=lambda *a: subprocess.run(['git','-C',str(root),*a],check=True,capture_output=True)
    run('init','-q'); run('config','user.email','t@example.org'); run('config','user.name','T')
    (root/'a.py').write_text('x = 1\n'); run('add','.'); run('commit','-qm','feat: start')
    (root/'a.py').write_text('x = 2\n'); run('commit','-qam','fix: correct x')
    return run

@unittest.skipUnless(__import__('shutil').which('git'),'git not available')
class GitToolTests(unittest.TestCase):
    def test_revision_check_reports_dirty_state(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'repo'; root.mkdir(); make_git_repo(root); (root/'b.py').write_text('y')
            before=subprocess.run(['git','-C',str(root),'status','--porcelain'],capture_output=True,text=True).stdout
            r=revision_check.check(root)
            self.assertEqual(r['dirty_files'],1); self.assertIsNone(r['behind']); self.assertTrue(r['advice'])
            self.assertEqual(before,subprocess.run(['git','-C',str(root),'status','--porcelain'],capture_output=True,text=True).stdout)
    def test_export_outside_repo_only(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'repo'; root.mkdir(); make_git_repo(root)
            with self.assertRaises(ValueError): revision_check.export(root,'HEAD',root/'export')
            info=revision_check.export(root,'HEAD~1',Path(td)/'export')
            self.assertEqual((Path(td)/'export/a.py').read_text(),'x = 1\n'); self.assertEqual(info['files'],1)
    def test_history_counts_fix_commits(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'repo'; root.mkdir(); make_git_repo(root)
            ns=type('A',(),dict(root=root,since='10 years ago',path=None,top=5,max_files_per_commit=30))()
            h=measure.cmd_history(ns)
            self.assertEqual(h['commits'],2); self.assertEqual(h['fix_commits_top'][0][:2],('a.py',1))

class EvidenceToolTests(unittest.TestCase):
    def test_assemble_ids_supports_dedupe_and_checks(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)/'repo'; repo.mkdir(); (repo/'a.py').write_text('one\ntwo\n')
            recs=[dict(local_id='w1',kind='code',location='a.py',line_start=1,line_end=2,observation='Two lines.',excerpt='one two'),
                  dict(local_id='w2',kind='code',location='a.py',line_start=1,line_end=2,observation='Two  lines.'),
                  dict(local_id='w3',kind='inference',location='a.py',observation='Derived.',supports=['w1']),
                  dict(local_id='w4',kind='code',location='a.py',line_start=1,line_end=9,observation='Too long.'),
                  dict(local_id='w5',kind='measurement',location='a.py',observation='No command.')]
            for r in recs: r['_origin']='x'
            ev,idmap,errors=evidence_tool.assemble(recs,repo.resolve(),'rev','env','2026-09-27','E',1)
            self.assertEqual(idmap['w1'],'E001'); self.assertEqual(idmap['w2'],'E001')
            self.assertEqual([e for e in ev if e['id']==idmap['w3']][0]['supports'],['E001'])
            self.assertTrue(any('exceed' in e for e in errors)); self.assertTrue(any('command' in e for e in errors))

class CompareTests(unittest.TestCase):
    def test_added_resolved_and_changed(self):
        old=read_json(ROOT/'examples/demo-audit.json'); new=copy.deepcopy(old)
        new['findings'][0]['priority']='P0'
        gone=new['findings'].pop()
        new['findings'].append(dict(copy.deepcopy(new['findings'][1]),id='F099',title='A brand new unrelated problem'))
        r=compare_audits.compare(old,new)
        self.assertIn(gone['id'],[x['id'] for x in r['findings']['resolved_or_dropped']])
        self.assertIn('F099',[x['id'] for x in r['findings']['added']])
        self.assertEqual(r['findings']['priority_changed'][0]['priority'][1],'P0')
        self.assertIn('## New findings',compare_audits.markdown(r))


if __name__=='__main__': unittest.main(verbosity=2)
