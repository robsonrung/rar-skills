#!/usr/bin/env python3
"""Validate the bundled report contract without installing dependencies."""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]

class ReportError(ValueError):
    pass

def read_json(path: Path):
    def reject_constant(value):
        raise ValueError(f'Non-finite JSON number: {value}')
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8'), parse_constant=reject_constant,
                      object_pairs_hook=unique_keys)

def schema_errors(value, schema, root, path='$'):
    """Implement only keywords used in the bundled schema, not general JSON Schema."""
    if '$ref' in schema:
        target = root
        for part in schema['$ref'].removeprefix('#/').split('/'):
            target = target[part]
        return schema_errors(value, target, root, path)
    errors = []
    tests = {'object': lambda x: isinstance(x, dict),
             'array': lambda x: isinstance(x, list),
             'string': lambda x: isinstance(x, str),
             'integer': lambda x: isinstance(x, int) and not isinstance(x, bool),
             'number': lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
             'boolean': lambda x: isinstance(x, bool), 'null': lambda x: x is None}
    allowed = schema.get('type', list(tests))
    allowed = [allowed] if isinstance(allowed, str) else allowed
    if not any(tests[t](value) for t in allowed):
        return [f'{path}: expected {allowed}, got {type(value).__name__}']
    if 'enum' in schema and value not in schema['enum']:
        errors.append(f'{path}: not in {schema["enum"]}')
    if isinstance(value, dict):
        props = schema.get('properties', {})
        for key in schema.get('required', []):
            if key not in value:
                errors.append(f'{path}: missing {key}')
        for key, item in value.items():
            if key in props:
                errors += schema_errors(item, props[key], root, f'{path}.{key}')
            elif schema.get('additionalProperties') is False:
                errors.append(f'{path}: unknown field {key}')
    if isinstance(value, list):
        if len(value) < schema.get('minItems', 0):
            errors.append(f'{path}: too few items')
        for index, item in enumerate(value):
            errors += schema_errors(item, schema.get('items', {}), root, f'{path}[{index}]')
    if isinstance(value, str):
        if len(value) < schema.get('minLength', 0) or ('minLength' in schema and not value.strip()):
            errors.append(f'{path}: empty text')
        if 'pattern' in schema and not re.search(schema['pattern'], value):
            errors.append(f'{path}: invalid format')
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if 'minimum' in schema and value < schema['minimum']:
            errors.append(f'{path}: below minimum')
        if 'maximum' in schema and value > schema['maximum']:
            errors.append(f'{path}: above maximum')
    return errors

def validate(data: dict) -> list[str]:
    schema = read_json(ROOT / 'assets/report.schema.json')
    errors = schema_errors(data, schema, schema)
    if errors:
        return errors  # Cross-reference checks require structural validity.
    expected = {x['id'] for x in read_json(ROOT / 'assets/dimensions.json')}
    actual = [x['id'] for x in data['dimensions']]
    if set(actual) != expected or len(actual) != len(expected):
        errors.append('dimensions: include D01 through D20 exactly once')
    groups = ['dimensions','strengths','findings','scenarios','diagrams','options','roadmap',
              'agent_checks','metrics','evidence','sources','verification','concept_applications']
    ids = []
    for group in groups:
        ids.extend(x['id'] for x in data[group])
    if len(ids) != len(set(ids)):
        errors.append('IDs must be unique across all report sections')
    reserved = {'concepts','main','context','architecture','assessment','strengths','findings',
                'requirements','alternatives','roadmap','agents','cost','evidence','verification',
                'sources','report-search','priority-filter','filter-count','print-button'}
    reserved.update('title-'+d['id'] for d in data['diagrams'])
    reserved.update('desc-'+d['id'] for d in data['diagrams'])
    reserved.update('arrow-'+d['id']+'-'+kind for d in data['diagrams']
                    for kind in ('sync','async','dependency'))
    if set(ids) & reserved:
        errors.append('IDs collide with report navigation or diagram anchors')
    evidence = {x['id']: x for x in data['evidence']}
    sources = {x['id']: x for x in data['sources']}
    findings = {x['id'] for x in data['findings']}
    roadmap = {x['id']: x for x in data['roadmap']}
    def check_refs(values, pool, where):
        for value in values:
            if value not in pool:
                errors.append(f'{where}: unknown reference {value}')
    def walk(item, path='$'):
        if isinstance(item, dict):
            for key, val in item.items():
                if key in ('evidence','supports') and isinstance(val, list) and all(isinstance(x,str) for x in val):
                    check_refs(val, evidence, path+'.'+key)
                elif key == 'sources' and isinstance(val, list) and all(isinstance(x,str) for x in val):
                    check_refs(val, sources, path+'.'+key)
                walk(val, path+'.'+key)
        elif isinstance(item,list):
            for i,val in enumerate(item): walk(val,f'{path}[{i}]')
    walk(data)
    terms = {x['id']: x for x in read_json(ROOT / 'assets/terms.json')}
    def names_term(text, name):
        # Require the canonical phrase, not a substring inside another word.
        normalized = ' '.join(text.casefold().split())
        phrase = ' '.join(name.casefold().split())
        return re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', normalized) is not None
    for c in data['concept_applications']:
        check_refs(c['related_findings'], findings, c['id'] + '.related_findings')
        term = terms.get(c['term_id'])
        if term is None:
            errors.append(c['id'] + ': unknown canonical term ' + c['term_id'])
            continue
        if not names_term(c['decision'], term['term']):
            errors.append(c['id'] + ': decision must name the canonical term ' + term['term'])
        if c['status'] == 'applied':
            if not c['evidence']:
                errors.append(c['id'] + ': applied decision needs evidence')
            if not c['sources']:
                errors.append(c['id'] + ': applied decision needs source attribution')
            if not any(names_term(c[key], term['term']) for key in ('action', 'verification')):
                errors.append(c['id'] + ': active term must recur in action or verification')
    for f in data['findings']:
        term = terms.get(f['leitwort'])
        if term is None:
            errors.append(f['id'] + ': unknown canonical term ' + f['leitwort'])
            continue
        if not names_term(f['decision_statement'], term['term']):
            errors.append(f['id'] + ': decision_statement must name the canonical term ' + term['term'])
        if not any(names_term(f[key], term['term']) for key in ('recommendation', 'validation', 'acceptance')):
            errors.append(f['id'] + ': main Leitwort must recur in recommendation, validation, or acceptance')
        linked = any(c['status'] == 'applied' and c['term_id'] == f['leitwort']
                     and f['id'] in c['related_findings'] for c in data['concept_applications'])
        if not linked:
            errors.append(f['id'] + ': needs a linked applied concept decision for its main Leitwort')

    demo = data['meta']['is_demo']
    def has_direct(refs):
        return any(evidence.get(x,{}).get('kind') not in (None,'hypothesis','inference','demo') for x in refs)
    if not demo and any(e['kind']=='demo' for e in data['evidence']):
        errors.append('Real reports cannot use demo evidence')
    for e in data['evidence']:
        start,end=e['line_start'],e['line_end']
        if (start is None) != (end is None) or (start is not None and end < start):
            errors.append(f'{e["id"]}: invalid line range')
        if e['kind'] in ('code','config') and start is None:
            errors.append(f'{e["id"]}: code/config evidence requires line numbers')
        if e['kind']=='measurement' and not e['command']:
            errors.append(f'{e["id"]}: measurement requires command or exact collection/query procedure')
        if e['kind']=='inference' and not e['supports']:
            errors.append(f'{e["id"]}: inference requires supporting evidence')
        if e['id'] in e['supports']:
            errors.append(f'{e["id"]}: evidence cannot support itself')
    def has_cycle(graph):
        active, done = set(), set()
        def inspect(node):
            if node in active: return True
            if node in done or node not in graph: return False
            active.add(node)
            if any(inspect(dep) for dep in graph[node]): return True
            active.remove(node); done.add(node)
            return False
        return any(inspect(node) for node in graph)
    if has_cycle({key: value['supports'] for key,value in evidence.items()}):
        errors.append('evidence: support cycle')
    for d in data['dimensions']:
        if d['status'] in ('adequate','attention','critical') and not d['evidence']:
            errors.append(f'{d["id"]}: assessed status requires evidence')
        if d['status']=='unknown' and d['confidence']=='high':
            errors.append(f'{d["id"]}: unknown quality cannot have high confidence')
        if d['status']=='critical' and not demo and not has_direct(d['evidence']):
            errors.append(f'{d["id"]}: critical status requires direct evidence')
    for f in data['findings']:
        if f['dimension'] not in expected:
            errors.append(f'{f["id"]}: invalid dimension')
        if f['priority'] in ('P0','P1') and not demo:
            if f['confidence'] in ('low','unknown') or not has_direct(f['evidence']):
                errors.append(f'{f["id"]}: P0/P1 requires sufficient confidence and direct evidence')
    if not any(x['position']=='keep' for x in data['options']):
        errors.append('options: include maintaining the current architecture')
    if sum(x['position']=='recommended' for x in data['options'])>1:
        errors.append('options: at most one recommendation')
    for s in data['sources']:
        url=urlsplit(s['url'])
        if url.scheme not in ('http','https') or not url.netloc or url.username or url.password:
            errors.append(f'{s["id"]}: source must have a safe public HTTP(S) URL without credentials')
    for d in data['diagrams']:
        node_ids=[n['id'] for n in d['nodes']]
        if len(node_ids)!=len(set(node_ids)):
            errors.append(f'{d["id"]}: duplicate diagram node')
        positions=[(n['col'],n['row']) for n in d['nodes']]
        if len(positions)!=len(set(positions)):
            errors.append(f'{d["id"]}: nodes occupy the same cell')
        if not demo and d['state']=='demo':
            errors.append(f'{d["id"]}: demo diagram in real report')
        for n in d['nodes']:
            if d['state']=='observed' and not n['evidence']:
                errors.append(f'{d["id"]}/{n["id"]}: observed node needs evidence')
        for e in d['edges']:
            check_refs([e['from'],e['to']],node_ids,d['id'])
            if e['from']==e['to']:
                errors.append(f'{d["id"]}: expand self-calls as sequence steps')
            if e['basis'] in ('observed','inferred') and not e['evidence']:
                errors.append(f'{d["id"]}: observed/inferred edge needs evidence')
            if d['state']=='observed' and e['basis'] in ('proposed','demo'):
                errors.append(f'{d["id"]}: proposed edge cannot be marked as current architecture')
    if not data['diagrams'] and not data['diagram_gaps']:
        errors.append('diagrams: include a view or explain why it cannot be reconstructed')
    for m in data['metrics']:
        if m['current_kind']=='unknown' and m['current'] is not None:
            errors.append(f'{m["id"]}: unknown current metric must be null')
        if m['current_kind']!='unknown' and m['current'] is None:
            errors.append(f'{m["id"]}: known current metric needs a value')
        if m['target_kind']=='unknown' and m['target'] is not None:
            errors.append(f'{m["id"]}: unknown target must be null')
        if m['target_kind']!='unknown' and m['target'] is None:
            errors.append(f'{m["id"]}: target needs a value')
        if m['current_kind']=='measured' and not demo:
            if not any(evidence.get(x,{}).get('kind')=='measurement' for x in m['evidence']):
                errors.append(f'{m["id"]}: measured value requires measurement evidence')
    for v in data['verification']:
        if v['status']=='pass' and v['exit_code']!=0:
            errors.append(f'{v["id"]}: passed verification must have exit code 0')
        if v['status'] in ('not_run','blocked','not_applicable') and v['exit_code'] is not None:
            errors.append(f'{v["id"]}: non-executed verification must have null exit code')
    for a in data['agent_checks']:
        if a['status'] in ('pass','fail') and not a['evidence']:
            errors.append(f'{a["id"]}: result needs evidence')
    for s in data['scenarios']:
        if s['status'] in ('verified','failed') and not s['evidence']:
            errors.append(f'{s["id"]}: outcome needs evidence')
    for r in data['roadmap']:
        check_refs(r['depends_on'],roadmap,r['id'])
        check_refs(r['related_findings'],findings,r['id'])
    def visit(node,active,finished):
        if node in active: return True
        if node in finished or node not in roadmap: return False
        active.add(node)
        for dep in roadmap[node]['depends_on']:
            if visit(dep,active,finished): return True
        active.remove(node);finished.add(node)
        return False
    finished=set()
    if any(visit(node,set(),finished) for node in roadmap):
        errors.append('roadmap: dependency cycle')
    return errors

def load_validated(path: Path):
    data = read_json(path)
    errors = validate(data)
    if errors:
        raise ReportError('\n'.join(errors))
    return data

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('report',type=Path)
    args=ap.parse_args()
    try:
        data=load_validated(args.report)
    except (OSError,ValueError,RecursionError) as exc:
        print(f'INVALID\n{exc}',file=sys.stderr)
        return 1
    print(f'VALID: {len(data["dimensions"])} dimensions, {len(data["findings"])} findings, '
          f'{len(data["evidence"])} evidence records. Structural checks only.')
    return 0
if __name__=='__main__':
    raise SystemExit(main())
