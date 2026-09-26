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
import render_report
from validate_report import ROOT, read_json, validate

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
        self.assertGreaterEqual(len(cases),26)
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


if __name__=='__main__': unittest.main(verbosity=2)
