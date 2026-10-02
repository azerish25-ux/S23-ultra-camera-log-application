#!/usr/bin/env python3
"""Validate P001 research records, not camera capability or free-form prose.

Read-only, offline and standard-library-only. Receipts are independently read from
hashed files; a green aggregate never overrides their individual outcomes. Hashes
bind bytes, not the truth of a measurement. P002/P003 own broader source mapping
and production-report adapters; P005 owns calibrated measurement policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

MASTER = 'docs/master-directive/S23_Cinema_Master_Directive_200000_Words.md'
MANIFEST = 'docs/master-directive/directive_manifest.json'
CHARTER = 'docs/RESEARCH_CHARTER.json'
INDEX = 'docs/REQUIREMENT_EVIDENCE.json'
MASTER_SHA256 = '6c8b91612767e7f9c733ff4bc908eed2d385cc0250f3239d7cc0b8a4346dfefc'
OUTCOMES = ('failed', 'blocked', 'unavailable', 'not_run', 'inconclusive', 'passed')
CLASSES = frozenset({'static_inspection', 'host_unit_test', 'property_fuzz_test',
    'cpu_reference_comparison', 'gpu_differential_test', 'codec_encode_decode',
    'emulator_instrumentation', 'physical_phone_functional', 'sustained_physical_recording',
    'controlled_color_optics', 'reviewed_perceptual_study', 'external_consumer_interoperability'})
PHYSICAL = frozenset({'physical_phone_functional', 'sustained_physical_recording', 'controlled_color_optics'})
FORMATS = frozenset({'super_8', 'super_16', 'standard_35mm', 'super_35', '65mm_5perf', '65mm_15perf_horizontal'})
CONSTRAINTS = frozenset({'continue_existing_app', 'retain_source', 'separate_controls',
                       'offline_core', 'no_scene_replacement', 'firmware_fresh_authorization'})
REQUIRED = frozenset({'REQ-RAW-LOG', 'REQ-LOGC3-MATH', 'REQ-SOURCE-RETENTION', 'REQ-SIX-FORMATS',
    'REQ-FILM-LAB', 'REQ-VIRTUAL-OPTICS', 'REQ-OFFLINE', 'REQ-CONTROL-SEPARATION',
    'REQ-MOVIE-CATALOGUE', 'REQ-DEFERRED-JOBS', 'REQ-RECOVERY', 'REQ-EVIDENCE'})
CATEGORIES = {**dict.fromkeys(REQUIRED, 'required_outcome'),
    **dict.fromkeys(('REQ-NATIVE-HIRES', 'REQ-FIRMWARE'), 'conditional_research'),
    **dict.fromkeys(('CLAIM-SDR-ADDS-DR', 'CLAIM-LOG-IS-ARRI', 'CLAIM-VIRTUAL-SENSOR',
                     'CLAIM-UPSCALED-NATIVE'), 'prohibited_claim'),
    **dict.fromkeys(('EXCLUDED-CLOUD-GENERATION', 'EXCLUDED-PLATFORM'), 'excluded_scope')}
SCOPE_KEYS = frozenset({'device_build', 'camera_route', 'codec', 'profile', 'geometry',
                       'frame_rate', 'duration_seconds', 'environment'})


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(detail)


def text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def finite(value) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def identity(value, length=64) -> bool:
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{' + str(length) + '}', value) is not None


def fields(value, names: str) -> None:
    require(isinstance(value, dict) and set(value) == set(names.split()),
            'Expected exact fields: ' + names)


def keyed(rows) -> dict:
    require(isinstance(rows, list), 'Expected a list of records')
    result = {}
    for row in rows:
        require(isinstance(row, dict) and text(row.get('id')), 'Record needs a stable id')
        require(row['id'] not in result, 'Duplicate id: ' + row['id'])
        result[row['id']] = row
    return result


def names(value, *, nonempty=True) -> list:
    require(isinstance(value, list) and (bool(value) or not nonempty), 'Expected a string list')
    require(all(text(v) for v in value) and len(value) == len(set(value)), 'Invalid or duplicate references')
    return value


def canonical_hash(value) -> str:
    data = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def decode(data: bytes):
    def pairs(items):
        obj = {}
        for key, value in items:
            require(key not in obj, 'Duplicate JSON key: ' + key)
            obj[key] = value
        return obj
    def invalid(value):
        raise ValueError('Nonfinite JSON number: ' + value)
    def real(value):
        parsed = float(value)
        require(math.isfinite(parsed), 'Nonfinite JSON number: ' + value)
        return parsed
    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid, parse_float=real)


def relative_name(relative: str) -> str:
    require(text(relative) and '\\' not in relative, 'Invalid relative path')
    path = PurePosixPath(relative)
    require(not path.is_absolute() and '..' not in path.parts and str(path) == relative,
            'Unsafe or noncanonical path: ' + relative)
    return relative


def safe_path(root: Path, relative: str) -> Path:
    result = root / relative_name(relative)
    for p in (result, *result.parents):
        require(not p.is_symlink(), 'Symlink is not evidence: ' + relative)
        if p == root:
            break
    require(result.is_file(), 'Missing prerequisite file: ' + relative)
    require(result.stat().st_size <= 4 * 1024 * 1024, 'Evidence file exceeds 4 MiB: ' + relative)
    return result


def git(root: Path, *args: str) -> bytes:
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=15)
    require(result.returncode == 0, 'Missing Git prerequisite or invalid revision: ' + ' '.join(args))
    return result.stdout


def git_file(root: Path, sha: str, path: str) -> bytes:
    require(identity(sha, 40), 'Invalid source revision')
    data = git(root, 'show', sha + ':' + relative_name(path))
    require(len(data) <= 4 * 1024 * 1024, 'Historical source exceeds 4 MiB')
    return data


def revision(root: Path) -> str:
    return git(root, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip()


def validate_contract(charter: dict, index: dict, root: Path, *,
                      expected_head: str | None = None, previous: tuple | None = None) -> dict:
    root = Path(root).absolute()
    report = {'status': 'failed', 'scope': 'P001 record consistency; not physical certification',
              'issues': [], 'accepted_findings': [], 'rejected_findings': [],
              'evidence_outcomes': {}, 'evidence_applicability': {}, 'inspection_revisions': [], 'research_questions': [],
              'history_check': 'compared' if previous is not None else 'initial_contract'}
    def issue(code, subject, detail):
        report['issues'].append({'code': code, 'subject': subject, 'detail': str(detail)})
    reads = {}
    def read(path, expected=None):
        data = safe_path(root, path).read_bytes()
        observed = hashlib.sha256(data).hexdigest()
        require(path not in reads or reads[path] == observed, 'File changed during validation: ' + path)
        reads[path] = observed
        if expected is not None:
            require(identity(expected) and observed == expected, 'Content hash mismatch: ' + path)
        return data
    try:
        start = revision(root)
        report['current_revision'] = start
        if expected_head is not None and expected_head != start:
            issue('head_changed', 'repository', 'Expected ' + expected_head + '; observed ' + start)
        fields(charter, 'schema_version charter_version active_phase adoption_revision directive_sha256 constraints virtual_formats requirements research_questions policies amendments')
        fields(index, 'schema_version charter_version inspections current_inspections fixtures evidence findings')
        require(type(charter['schema_version']) is int and charter['schema_version'] == 1 and
                type(index['schema_version']) is int and index['schema_version'] == 1, 'Unknown schema version')
        require(type(charter['charter_version']) is int and charter['charter_version'] > 0 and
                type(index['charter_version']) is int and index['charter_version'] == charter['charter_version'], 'Charter version mismatch')
        require(charter['active_phase'] == 'P001' and identity(charter['adoption_revision'], 40), 'Invalid P001 identity')
        require(charter['directive_sha256'] == MASTER_SHA256, 'Governing directive identity changed')
        read(MASTER, MASTER_SHA256)
        phases = keyed(decode(read(MANIFEST))['phases'])
        require(isinstance(charter['constraints'], dict) and set(charter['constraints']) == CONSTRAINTS and all(v is True for v in charter['constraints'].values()), 'A governing constraint was weakened')
        require(set(names(charter['virtual_formats'])) == FORMATS, 'All six declared virtual formats are required')
        requirements, inspections = keyed(charter['requirements']), keyed(index['inspections'])
        current_inspections = set(names(index['current_inspections']))
        require(current_inspections <= set(inspections), 'Unknown current inspection')
        fixtures, entries, findings = keyed(index['fixtures']), keyed(index['evidence']), keyed(index['findings'])
        policies = keyed(charter['policies'])
        keyed(charter['amendments'])
        if previous is None:
            require(charter['charter_version'] == 1 and not charter['amendments'], 'Initial contract must start at version 1 without historical amendments')
        require(set(requirements) >= set(CATEGORIES), 'A required charter obligation is missing')
        for req in requirements.values():
            fields(req, 'id category phase dependencies owner measurement_class statement required_evidence')
            require(req['category'] in set(CATEGORIES.values()) and
                    (req['id'] not in CATEGORIES or req['category'] == CATEGORIES[req['id']]), 'Requirement category changed: ' + req['id'])
            require(req['phase'] in phases and req['dependencies'] == phases[req['phase']]['dependencies'], 'Phase dependency mismatch: ' + req['id'])
            require(text(req['owner']) and text(req['statement']), 'Missing owner or observable statement')
            require(req['measurement_class'] in {'physical_capture', 'numerical', 'functional', 'perceptual', 'inspection'}, 'Unknown measurement class')
            classes = names(req['required_evidence'], nonempty=req['category'] in {'required_outcome', 'conditional_research'})
            require(set(classes) <= CLASSES, 'Unknown evidence class')
            if req['id'] in {'REQ-RAW-LOG', 'REQ-NATIVE-HIRES'}:
                require(req['measurement_class'] == 'physical_capture' and bool(set(classes) & PHYSICAL), 'Physical target cannot be satisfied by software alone')
        questions = keyed(charter['research_questions'])
        for question in questions.values():
            fields(question, 'id requirement_id question')
            require(question['requirement_id'] in requirements and text(question['question']), 'Invalid research question')
        require(any(q['requirement_id'] == 'CLAIM-SDR-ADDS-DR' for q in questions.values()), 'Retain the unsupported SDR sensor claim as an explicit research question')
        report['research_questions'] = charter['research_questions']
        report['charter_sha256'] = canonical_hash(charter)
        report['index_sha256'] = canonical_hash(index)
        stale = set()
        for inspected in inspections.values():
            fields(inspected, 'id revision scope files')
            require(identity(inspected['revision'], 40) and text(inspected['scope']), 'Invalid inspection identity/scope')
            require(isinstance(inspected['files'], list) and inspected['files'], 'Inspection has no source files')
            paths = set()
            for source in inspected['files']:
                fields(source, 'path sha256')
                path = source['path']
                require(path not in paths, 'Duplicate inspected path'); paths.add(path)
                original = git_file(root, inspected['revision'], path)
                require(identity(source['sha256']) and hashlib.sha256(original).hexdigest() == source['sha256'], 'Inspection does not match its Git revision: ' + path)
                if inspected['id'] in current_inspections and hashlib.sha256(read(path)).hexdigest() != source['sha256']:
                    stale.add((inspected['id'], path))
                    issue('stale_source', inspected['id'], 'Incremental inspection required: ' + path)
        report['inspection_revisions'] = sorted({i['revision'] for i in inspections.values()})
    except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError) as error:
        issue('schema_invalid', 'contract', error)
        return report

    valid_fixtures = set()
    for fixture in fixtures.values():
        try:
            fields(fixture, 'id path sha256 kind provenance' + (' git_revision' if 'git_revision' in fixture else ''))
            require(fixture['kind'] in {'source_text', 'synthetic', 'model', 'stock_profile', 'movie_reference', 'generated_screenshot', 'owned_media'}, 'Unknown fixture kind')
            fields(fixture['provenance'], 'origin owner acquired_at permitted_use')
            require(all(text(v) for v in fixture['provenance'].values()), 'Missing provenance context, owner, date or permitted use')
            if fixture.get('git_revision') is not None:
                original = git_file(root, fixture['git_revision'], fixture['path'])
                require(identity(fixture['sha256']) and hashlib.sha256(original).hexdigest() == fixture['sha256'], 'Historical fixture hash mismatch')
            else:
                read(fixture['path'], fixture['sha256'])
            valid_fixtures.add(fixture['id'])
        except (ValueError, TypeError, KeyError, OSError) as error:
            issue('fixture_invalid', fixture['id'], error)

    valid_policies = set()
    for policy in policies.values():
        try:
            fields(policy, 'id version metric unit domain operator limit supersedes review')
            require(type(policy['version']) is int and policy['version'] > 0, 'Invalid policy version')
            require(all(text(policy[k]) for k in ('metric', 'unit', 'domain')) and finite(policy['limit']) and policy['operator'] in {'le', 'ge', 'eq'}, 'Policy requires finite threshold, units and domain')
            if policy['supersedes'] is not None:
                old = policies[policy['supersedes']]
                require(old['version'] + 1 == policy['version'] and old['metric'] == policy['metric'], 'Policy lineage mismatch')
                fields(policy['review'], 'reviewer reason validation_evidence')
                require(text(policy['review']['reviewer']) and text(policy['review']['reason']), 'Policy revision needs an explicit review')
                names(policy['review']['validation_evidence'])
            else:
                require(policy['version'] == 1 and policy['review'] is None, 'Initial policy must have version 1')
            valid_policies.add(policy['id'])
        except (ValueError, TypeError, KeyError) as error:
            issue('policy_invalid', policy['id'], error)

    rewritten = {k: set() for k in ('policies', 'amendments', 'inspections', 'fixtures', 'evidence')}
    if previous is not None:
        old_charter = None
        try:
            old_charter, old_index = previous
            # Compare immutable records against the independently read Git predecessor.
            groups = [(k, old_charter[k], charter[k]) for k in ('policies', 'amendments')]
            groups += [(k, old_index[k], index[k]) for k in ('inspections', 'fixtures', 'evidence')]
            for kind, old_rows, new_rows in groups:
                old_map, new_map = keyed(old_rows), keyed(new_rows)
                rewritten[kind] = {k for k, v in old_map.items() if new_map.get(k) != v}
                if rewritten[kind]:
                    issue('history_rewritten', kind, 'Changed/removed immutable records: ' + ', '.join(sorted(rewritten[kind])))
        except (ValueError, TypeError, KeyError) as error:
            issue('history_rewritten', 'history', error)
        if old_charter is not None and old_charter != charter:
            try:
                require(charter['charter_version'] == old_charter['charter_version'] + 1, 'Changed charter needs the next version')
                amendments = keyed(charter['amendments'])
                latest = list(amendments.values())[-1]
                fields(latest, 'id from_version to_version reviewer reason affected_requirements validation_evidence')
                require(latest['from_version'] == old_charter['charter_version'] and latest['to_version'] == charter['charter_version'], 'Amendment version mismatch')
                require(text(latest['reviewer']) and text(latest['reason']), 'Missing charter review')
                affected = set(names(latest['affected_requirements']))
                old_reqs = keyed(old_charter['requirements'])
                changed = {k for k in set(old_reqs) | set(requirements) if old_reqs.get(k) != requirements.get(k)}
                require(changed <= affected <= set(requirements) and set(old_reqs) <= set(requirements), 'Amendment omits changed obligations')
                names(latest['validation_evidence'])
            except (ValueError, TypeError, KeyError, IndexError) as error:
                issue('amendment_missing', 'charter', error)

    valid_fixtures -= rewritten['fixtures']
    valid_policies -= rewritten['policies']
    receipts, usable = {}, set()
    for entry in entries.values():
        try:
            fields(entry, 'id artifact reported_outcome')
            fields(entry['artifact'], 'path sha256')
            raw = decode(read(entry['artifact']['path'], entry['artifact']['sha256']))
            fields(raw, 'schema_version id run_id inspection_id source_revision requirement_ids evidence_class origin environment fixture_ids source_paths scope command outcome checks measurements')
            require(type(raw['schema_version']) is int and raw['schema_version'] == 1 and raw['id'] == entry['id'] and text(raw['run_id']), 'Receipt identity mismatch')
            require(raw['inspection_id'] in inspections, 'Unknown inspection')
            inspected = inspections[raw['inspection_id']]
            require(raw['source_revision'] == inspected['revision'], 'Receipt and inspection revisions disagree')
            sources = names(raw['source_paths'])
            require(set(sources) <= {f['path'] for f in inspected['files']}, 'Receipt cites uninspected source')
            require(not any((inspected['id'], p) in stale for p in sources), 'Receipt source needs incremental inspection')
            require(set(names(raw['requirement_ids'])) <= set(requirements), 'Unknown receipt requirement')
            require(set(names(raw['fixture_ids'])) <= valid_fixtures, 'Fixture provenance or bytes are invalid')
            require(raw['evidence_class'] in CLASSES and text(raw['command']), 'Missing evidence class or reproducible command/protocol')
            fields(raw['environment'], 'kind detail')
            require(raw['environment']['kind'] in {'host', 'emulator', 'physical_phone'} and text(raw['environment']['detail']), 'Unknown test environment')
            require(raw['origin'] in {'static_source', 'synthetic', 'emulator', 'physical_capture', 'imported_owned'}, 'Unknown source origin')
            require(isinstance(raw['scope'], dict), 'Scope must be explicit')
            # Retain the attributable run even when a later measurement fails validation.
            # Otherwise a malformed critical receipt could disappear from cherry-pick checks.
            receipts[entry['id']] = raw
            report['evidence_applicability'][entry['id']] = 'current' if raw['inspection_id'] in current_inspections else 'historical_only'
            require(entry['id'] not in rewritten['evidence'] and raw['inspection_id'] not in rewritten['inspections'], 'Receipt or inspection rewrites immutable history')
            if raw['evidence_class'] in PHYSICAL and raw['outcome'] == 'passed':
                require(raw['origin'] == 'physical_capture' and raw['environment']['kind'] == 'physical_phone' and
                        all(fixtures[f]['kind'] == 'owned_media' for f in raw['fixture_ids']), 'Synthetic/emulator/source-text fixture cannot be relabelled as physical evidence')
                require(set(raw['scope']) == SCOPE_KEYS and all(text(raw['scope'][k]) for k in SCOPE_KEYS - {'duration_seconds'}) and
                        finite(raw['scope']['duration_seconds']) and raw['scope']['duration_seconds'] > 0, 'Incomplete exact physical configuration/duration')
            if raw['evidence_class'] == 'emulator_instrumentation':
                require(raw['environment']['kind'] == 'emulator', 'Instrumentation environment mismatch')
            checks = keyed(raw['checks'])
            require(bool(checks), 'No individual checks; aggregate alone is insufficient')
            outcomes = []
            for check in checks.values():
                fields(check, 'id outcome reason')
                require(check['outcome'] in OUTCOMES and text(check['reason']), 'Missing raw outcome or reason')
                outcomes.append(check['outcome'])
            require(isinstance(raw['measurements'], list), 'Measurements must be explicit')
            for measured in raw['measurements']:
                fields(measured, 'policy_id policy_sha256 value unit domain')
                require(measured['policy_id'] in valid_policies, 'Missing/invalid measurement policy')
                policy = policies[measured['policy_id']]
                require(measured['policy_sha256'] == canonical_hash(policy), 'Measurement policy identity changed')
                require(text(measured['unit']) and measured['unit'] == policy['unit'] and
                        text(measured['domain']) and measured['domain'] == policy['domain'], 'Measurement unit/domain mismatch')
                require(finite(measured['value']), 'Measurement must be a finite number, not a Boolean')
                value, limit = measured['value'], policy['limit']
                passed = {'le': value <= limit, 'ge': value >= limit, 'eq': value == limit}[policy['operator']]
                outcomes.append('passed' if passed else 'failed')
            outcome = min(outcomes, key=OUTCOMES.index)
            report['evidence_outcomes'][entry['id']] = outcome
            if outcome != raw['outcome'] or outcome != entry['reported_outcome']:
                issue('contradictory_outcome', entry['id'], 'Underlying checks/measurements: ' + outcome + '; declared summaries disagree')
            else:
                usable.add(entry['id'])
        except (ValueError, TypeError, KeyError, OSError) as error:
            issue('evidence_invalid', entry['id'], error)

    # Human review declarations are not cryptographic approvals. They must at least
    # link valid, passing, independently retained comparison evidence.
    reviews = [(p['id'], p['review']) for p in policies.values() if p.get('supersedes')]
    reviews += [(a['id'], a) for a in charter['amendments']]
    for review_id, review in reviews:
        try:
            refs = names(review['validation_evidence'])
            require(all(r in usable and report['evidence_outcomes'][r] == 'passed' for r in refs), 'Review lacks retained passing validation evidence')
        except (ValueError, TypeError, KeyError) as error:
            valid_policies.discard(review_id)
            issue('policy_invalid', review_id, error)
    # No descendant may inherit a pass from an invalid policy revision.
    while True:
        invalid = {p for p in valid_policies if policies[p]['supersedes'] is not None and policies[p]['supersedes'] not in valid_policies}
        if not invalid:
            break
        valid_policies -= invalid
    usable = {e for e in usable if all(m['policy_id'] in valid_policies for m in receipts[e]['measurements'])}

    represented = []
    for finding in findings.values():
        try:
            fields(finding, 'id requirement_id status evidence_ids scope limits')
            req = requirements[finding['requirement_id']]
            represented.append(req['id'])
            refs = names(finding['evidence_ids'], nonempty=False)
            require(set(refs) <= set(entries), 'Finding cites unknown evidence')
            require(isinstance(finding['scope'], dict), 'Finding scope must be explicit')
            names(finding['limits'])
            if finding['status'] != 'supported':
                expected = {'required_outcome': 'open', 'conditional_research': 'conditional',
                            'prohibited_claim': 'prohibited', 'excluded_scope': 'excluded'}[req['category']]
                require(finding['status'] == expected, 'Invalid finding disposition')
                continue
            require(req['category'] in {'required_outcome', 'conditional_research'}, 'Prohibited/excluded claim cannot be accepted')
            require(refs and all(r in usable and report['evidence_outcomes'][r] == 'passed' for r in refs), 'Missing, invalid or non-passing evidence')
            selected = [receipts[r] for r in refs]
            require(all(r['inspection_id'] in current_inspections for r in selected), 'Historical-only evidence cannot certify the current inspection scope')
            require(all(req['id'] in r['requirement_ids'] for r in selected), 'Evidence does not test this obligation')
            require(set(req['required_evidence']) <= {r['evidence_class'] for r in selected}, 'Required independent evidence classes are missing')
            require(all(r['scope'] == finding['scope'] for r in selected) and len({r['source_revision'] for r in selected}) == 1, 'Evidence configurations or source revisions do not match the claim')
            if req['measurement_class'] == 'physical_capture':
                require(set(finding['scope']) == SCOPE_KEYS and all(r['origin'] == 'physical_capture' for r in selected), 'No exact physical source/configuration proof')
            runs = {r['run_id'] for r in selected}
            require(not any(r['run_id'] in runs and req['id'] in r['requirement_ids'] and r['scope'] == finding['scope'] and
                            (identity not in usable or report['evidence_outcomes'][identity] != 'passed')
                            for identity, r in receipts.items()), 'Critical contradictory result in the same run was omitted')
            report['accepted_findings'].append(finding['id'])
        except (ValueError, TypeError, KeyError) as error:
            report['rejected_findings'].append(finding['id'])
            issue('unsupported_claim', finding['id'], error)
    if set(represented) != set(requirements) or len(represented) != len(set(represented)):
        issue('schema_invalid', 'findings', 'Every obligation needs exactly one explicit disposition')
    try:
        require(revision(root) == start, 'Git HEAD moved during validation')
        for path, sha in reads.items():
            require(hashlib.sha256(safe_path(root, path).read_bytes()).hexdigest() == sha, 'Evidence changed during validation: ' + path)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        issue('head_changed', 'validation_snapshot', error)
    report['status'] = 'passed' if not report['issues'] else 'failed'
    return report


def previous_records(root: Path, base: str, adoption: str) -> tuple | None:
    require(identity(base, 40), 'Baseline must be an exact commit SHA')
    current = revision(root)
    current_files = git(root, 'ls-tree', '--name-only', current, '--', CHARTER, INDEX).decode().splitlines()
    parents = git(root, 'rev-list', '--parents', '-n', '1', current).decode().split()
    bootstrap = current == base == adoption and not current_files
    require(bootstrap or (len(parents) >= 2 and base == parents[1]), 'Baseline must be the immediate predecessor, not an older convenient revision')
    files = git(root, 'ls-tree', '--name-only', base, '--', CHARTER, INDEX).decode().splitlines()
    if not files:
        require(base == adoption, 'Missing earlier contract outside the declared adoption revision')
        return None
    require(set(files) == {CHARTER, INDEX}, 'Incomplete previous contract')
    return decode(git(root, 'show', base + ':' + CHARTER)), decode(git(root, 'show', base + ':' + INDEX))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--expected-head', help='Exact planned checkout SHA; never fetches, resets or writes Git')
    parser.add_argument('--baseline-ref', help='Exact independent prior commit (default: first parent)')
    args = parser.parse_args()
    try:
        root = args.root.absolute()
        inputs = {p: safe_path(root, p).read_bytes() for p in (CHARTER, INDEX)}
        charter, index = decode(inputs[CHARTER]), decode(inputs[INDEX])
        base = args.baseline_ref or git(root, 'rev-parse', '--verify', 'HEAD^').decode().strip()
        old = previous_records(root, base, charter['adoption_revision'])
        report = validate_contract(charter, index, root, expected_head=args.expected_head, previous=old)
        report['baseline_revision'] = base
        require(all(safe_path(root, p).read_bytes() == data for p, data in inputs.items()), 'Charter/index changed during validation')
    except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError) as error:
        report = {'status': 'failed', 'scope': 'P001 record consistency; not physical certification',
                  'issues': [{'code': 'missing_prerequisite', 'subject': 'CLI', 'detail': str(error)}]}
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
