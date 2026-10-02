#!/usr/bin/env python3
"""P002 source continuity: a bounded static map, not feature/device certification.

Uses the P001 contract for provenance, raw outcomes, units and immutable history.
Only reads local files/Git. Anchors are reviewed text, not a Kotlin call-graph parser.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

# Also works with python -I, without relying on PYTHONPATH or the current directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_research_contract import (CHARTER, INDEX, MANIFEST, decode, fields, git,
    identity, keyed, names, previous_records, relative_name, require, revision,
    safe_path, text, validate_contract)

MAP = 'docs/REPOSITORY_CONTINUITY.json'
REQUIRED_SEAMS = ('build', 'capture', 'raw_source', 'development', 'verification',
                  'recovery', 'presentation', 'evidence')


def inventory(root: Path, ref: str) -> dict:
    """Read mode and blob identity independently of the map; do not change the index."""
    result = {}
    for row in git(root, 'ls-tree', '-rz', ref).split(b'\0'):
        if row:
            header, path = row.split(b'\t', 1)
            mode, kind, sha = header.decode().split()
            result[path.decode()] = (mode, kind, sha)
    return result


def production_path(path: str) -> bool:
    return path.startswith('app/') or path in {
        'build.gradle.kts', 'settings.gradle.kts', 'gradle.properties',
        'gradle/wrapper/gradle-wrapper.properties'}


def ci_cases(data: bytes, expected_revision: str) -> dict:
    """Inspect retained JUnit cases, never infer a codec pass from an emulator test."""
    import io
    cases = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        require(len(members) <= 128 and len({m.filename for m in members}) == len(members),
                'Duplicate or excessive CI archive members')
        require(sum(m.file_size for m in members) <= 4 * 1024 * 1024, 'CI expansion exceeds 4 MiB')
        for member in members:
            relative_name(member.filename)
            require(not member.is_dir() and (member.external_attr >> 16) & 0o170000 != 0o120000,
                    'CI evidence must be regular bytes, not links/directories')
        provenance = decode(archive.read('provenance.json'))
        require(provenance['source_revision'] == expected_revision, 'CI source revision differs from inspection')
        require(identity(provenance['original_artifact_sha256']) and text(provenance['origin']) and
                text(provenance['scope']), 'Missing CI provenance')
        require(isinstance(provenance.get('members'), dict) and
                set(provenance['members']) == {m.filename for m in members} - {'provenance.json'},
                'CI member inventory differs from provenance')
        for member in members:
            if member.filename == 'provenance.json':
                continue
            payload = archive.read(member)
            require(hashlib.sha256(payload).hexdigest() == provenance['members'][member.filename],
                    'CI member hash differs from provenance: ' + member.filename)
            if not member.filename.endswith('.xml'):
                continue
            xml = payload.decode('utf-8-sig')
            require('<!DOCTYPE' not in xml and '<!ENTITY' not in xml, 'XML declarations are not test evidence')
            suite = ET.fromstring(xml)

            def inspect(node, depth=0):
                # Gradle unit reports use testsuite; connected instrumentation uses
                # testsuites containing one testsuite per class. Check BOTH levels.
                require(depth <= 16 and node.tag in {'testsuite', 'testsuites'},
                        'Unsupported or excessively nested JUnit suite')
                counts = {'tests': 0, 'failures': 0, 'errors': 0, 'skipped': 0}
                for child in node:
                    if child.tag in {'testsuite', 'testsuites'}:
                        nested = inspect(child, depth + 1)
                        for key in counts:
                            counts[key] += nested[key]
                    elif child.tag == 'testcase':
                        key = (member.filename, child.get('classname'), child.get('name'))
                        require(all(text(v) for v in key) and key not in cases,
                                'Missing/duplicate JUnit case identity')
                        counts['tests'] += 1
                        for tag, count in [('failure', 'failures'), ('error', 'errors'), ('skipped', 'skipped')]:
                            counts[count] += child.find(tag) is not None
                        cases[key] = ('failed' if child.find('failure') is not None or child.find('error') is not None
                                      else 'not_run' if child.find('skipped') is not None else 'passed')
                    else:
                        require(child.tag in {'properties', 'system-out', 'system-err'},
                                'Unsupported JUnit element: ' + child.tag)
                for key, observed in counts.items():
                    require(int(node.get(key, '-1' if key == 'tests' else '0')) == observed,
                            'JUnit summary contradicts individual ' + key)
                return counts

            inspect(suite)
    return cases


def verify(root: Path, plan: dict, *, expected_head: str | None = None) -> dict:
    root = Path(root).absolute()
    report = {'status': 'failed', 'scope': 'P002 bounded source continuity; not feature or physical acceptance',
              'issues': [], 'physical_certification': False, 'mapped_requirements': [],
              'uninspected_baseline_files': [], 'unreviewed_committed_changes': []}
    reads = {}

    def issue(code, subject, detail):
        report['issues'].append({'code': code, 'subject': subject, 'detail': str(detail)})

    def read(path, expected=None):
        data = safe_path(root, path).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        require(path not in reads or reads[path] == digest, 'File changed during validation: ' + path)
        reads[path] = digest
        require(expected is None or (identity(expected) and expected == digest), 'Content hash mismatch: ' + path)
        return data

    try:
        start = revision(root)
        report['current_revision'] = start
        if expected_head is not None and start != expected_head:
            issue('head_changed', 'repository', 'Planned ' + expected_head + '; observed ' + start)
        charter, index = decode(read(CHARTER)), decode(read(INDEX))
        base = git(root, 'rev-parse', '--verify', 'HEAD^').decode().strip()
        prior = previous_records(root, base, charter['adoption_revision'])
        contract = validate_contract(charter, index, root, expected_head=start, previous=prior)
        report['research_contract'] = contract
        if contract['status'] != 'passed':
            issue('research_contract_failed', 'P001', 'Underlying provenance/outcome/history gate rejected the records')
        fields(plan, 'schema_version phase inspection_id source_revision source_tree scope files seams mappings decisions prior_ci')
        require(type(plan['schema_version']) is int and plan['schema_version'] == 1 and plan['phase'] == 'P002', 'Unknown P002 schema')
        require(text(plan['scope']) and identity(plan['source_revision'], 40) and identity(plan['source_tree'], 40), 'Missing inspection identity/scope')
        inspections = keyed(index['inspections'])
        inspected = inspections[plan['inspection_id']]
        require(plan['inspection_id'] in index['current_inspections'] and inspected['revision'] == plan['source_revision'],
                'Map is not bound to its current P001 inspection')
        actual_tree = git(root, 'rev-parse', plan['source_revision'] + '^{tree}').decode().strip()
        require(actual_tree == plan['source_tree'], 'Inspection tree mismatch')
        baseline = inventory(root, plan['source_revision'])
        current = inventory(root, start)
        report['inspection_revision'] = plan['source_revision']
        require(isinstance(plan['files'], list) and plan['files'], 'No reviewed production files; README is not a source audit')
        source_map = {s['path']: s for s in plan['files']}
        require(len(source_map) == len(plan['files']), 'Duplicate source path')
        registered = {s['path']: s['sha256'] for s in inspected['files']}
        require(registered == {p: s['sha256'] for p, s in source_map.items()}, 'Map and inspection source sets differ')
        phases = keyed(decode(read(MANIFEST))['phases'])
        require(phases['P002']['dependencies'] == ['P001'], 'Unexpected P002 dependency')
        report['uninspected_baseline_files'] = sorted(set(baseline) - set(source_map))
        changed = sorted(p for p in set(baseline) | set(current) if baseline.get(p) != current.get(p))
        report['unreviewed_committed_changes'] = [p for p in changed if p not in source_map]
        pending = git(root, '--no-optional-locks', 'status', '--porcelain=v1', '-z').decode().split('\0')
        report['working_changes'] = [p for p in pending if p]
        unknown = {p for p in report['unreviewed_committed_changes'] if production_path(p)}
        unknown |= {p[3:] for p in pending if len(p) > 3 and production_path(p[3:]) and p[3:] not in source_map}
        if unknown:
            issue('production_review_required', 'uninspected_changes', ', '.join(sorted(unknown)))
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
        issue('schema_invalid', 'map', error)
        return report

    reviewed = {}
    for path, source in source_map.items():
        try:
            fields(source, 'path blob_sha sha256 role reviewed_lines')
            require(source['role'] in {'build', 'production', 'test', 'evidence'}, 'Unknown source role')
            require(path in baseline and baseline[path][0] in {'100644', '100755'} and
                    baseline[path][1:] == ('blob', source['blob_sha']), 'Historical blob/mode mismatch: ' + path)
            lines = read(path, source['sha256']).decode('utf-8').splitlines()
            ranges = source['reviewed_lines']
            require(isinstance(ranges, list) and ranges, 'No reviewed line ranges')
            last = 0
            selected = []
            for span in ranges:
                require(isinstance(span, list) and len(span) == 2 and all(type(n) is int for n in span) and
                        last < span[0] <= span[1] <= len(lines), 'Invalid/overlapping reviewed ranges: ' + path)
                selected.extend(lines[span[0]-1:span[1]])
                last = span[1]
            reviewed[path] = selected
        except (ValueError, KeyError, TypeError, OSError) as error:
            issue('source_invalid', path, error)

    cases = {}
    if plan['prior_ci'] is not None:
        try:
            fields(plan['prior_ci'], 'path sha256')
            cases = ci_cases(read(plan['prior_ci']['path'], plan['prior_ci']['sha256']), plan['source_revision'])
        except (ValueError, KeyError, TypeError, OSError, RuntimeError, ET.ParseError, zipfile.BadZipFile) as error:
            issue('ci_evidence_invalid', 'prior_ci', error)
    report['prior_ci_cases'] = len(cases)

    def reference(ref, role=None):
        fields(ref, 'path anchor purpose')
        require(text(ref['anchor']) and text(ref['purpose']), 'Reference needs a concrete anchor and purpose')
        require(ref['path'] in reviewed and any(ref['anchor'] in line for line in reviewed[ref['path']]),
                'Missing/unreviewed source or anchor: ' + str(ref['path']))
        require(role is None or source_map[ref['path']]['role'] == role, 'Reference has wrong source role')

    valid_seams = set()
    try:
        seams = keyed(plan['seams'])
        require(set(REQUIRED_SEAMS) <= set(seams), 'Missing mandatory ownership seams; no README-only audit')
    except (ValueError, TypeError, KeyError) as error:
        issue('schema_invalid', 'seams', error)
        seams = {}
    for seam in seams.values():
        try:
            fields(seam, 'id owner callers tests inputs outputs limits')
            reference(seam['owner'], 'build' if seam['id'] == 'build' else 'production')
            require(text(seam['inputs']) and text(seam['outputs']), 'Missing input/output contract')
            names(seam['limits'])
            require(isinstance(seam['callers'], list) and isinstance(seam['tests'], list), 'Caller/test references must be lists')
            for caller in seam['callers']:
                reference(caller)
            for test in seam['tests']:
                fields(test, 'path anchor purpose evidence_class execution')
                reference({k: test[k] for k in ('path', 'anchor', 'purpose')}, 'test')
                require(test['evidence_class'] in {'host_unit_test', 'emulator_instrumentation'}, 'Static map cannot certify physical tests')
                execution = test['execution']
                if 'ci_entry' in execution:
                    fields(execution, 'outcome ci_entry classname testcase reason')
                    key = (execution['ci_entry'], execution['classname'], execution['testcase'])
                    require(key in cases and cases[key] == execution['outcome'], 'Declared execution differs from retained JUnit case')
                    method = re.split(r'[\[(]', execution['testcase'])[0]
                    require(method in test['anchor'] and execution['classname'].split('.')[-1] == Path(test['path']).stem,
                            'JUnit evidence belongs to another test')
                    emulator = '/androidTest-results/' in execution['ci_entry']
                    require(emulator == (test['evidence_class'] == 'emulator_instrumentation'), 'JUnit evidence class mismatch')
                else:
                    fields(execution, 'outcome reason')
                    require(execution['outcome'] == 'not_run', 'Execution claim lacks independent JUnit evidence')
                require(text(execution['reason']), 'Execution status requires a reason')
            valid_seams.add(seam['id'])
        except (ValueError, KeyError, TypeError) as error:
            issue('seam_invalid', seam.get('id', 'unknown'), error)

    try:
        mappings = plan['mappings']
        require(isinstance(mappings, list), 'Mappings must be a list')
        requirements = keyed(charter['requirements'])
        seen = set()
        for item in mappings:
            fields(item, 'requirement_id implementation seam_ids summary gaps')
            req = requirements[item['requirement_id']]
            require(req['id'] not in seen, 'Duplicate mapped requirement')
            seen.add(req['id'])
            allowed = {'required_outcome': {'partial', 'planned'}, 'conditional_research': {'conditional'},
                       'prohibited_claim': {'prohibited'}, 'excluded_scope': {'excluded'}}[req['category']]
            require(item['implementation'] in allowed, 'Static inspection cannot declare implemented/qualified acceptance')
            refs = names(item['seam_ids'], nonempty=item['implementation'] == 'partial')
            require(set(refs) <= valid_seams and text(item['summary']), 'Invalid seam mapping or explanation')
            require(isinstance(item['gaps'], list) and item['gaps'], 'Unresolved acceptance must remain explicit')
            for gap in item['gaps']:
                fields(gap, 'phase reason')
                require(gap['phase'] in phases and text(gap['reason']), 'Gap needs owning phase and reason')
        require(seen == set(requirements), 'Every charter obligation must remain mapped')
        report['mapped_requirements'] = sorted(seen)
    except (ValueError, KeyError, TypeError) as error:
        issue('mapping_invalid', 'requirements', error)

    try:
        require(isinstance(plan['decisions'], list) and plan['decisions'], 'No minimal-change architecture decision')
        for decision in plan['decisions']:
            fields(decision, 'component seam_id action phase reason')
            require(text(decision['component']) and text(decision['reason']) and decision['phase'] in phases, 'Incomplete decision')
            require(decision['action'] in {'reuse', 'extend_existing', 'defer'} and decision['seam_id'] in valid_seams,
                    'Replace/duplicate engines are not authorized by this continuity map')
    except (ValueError, KeyError, TypeError) as error:
        issue('decision_invalid', 'architecture', error)
    try:
        require(revision(root) == start, 'HEAD moved during validation')
        for path, digest in reads.items():
            require(hashlib.sha256(safe_path(root, path).read_bytes()).hexdigest() == digest,
                    'File changed during validation: ' + path)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        issue('head_changed', 'validation_snapshot', error)
    report['status'] = 'passed' if not report['issues'] else 'failed'
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--expected-head', help='Exact checkout SHA; no fetch/reset is performed')
    args = parser.parse_args()
    try:
        source = safe_path(args.root.absolute(), MAP)
        data = source.read_bytes()
        report = verify(args.root, decode(data), expected_head=args.expected_head)
        require(source.read_bytes() == data, 'Continuity map changed during validation')
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
        report = {'status': 'failed', 'issues': [{'code': 'missing_prerequisite', 'subject': MAP, 'detail': str(error)}]}
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
