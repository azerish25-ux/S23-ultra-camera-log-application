"""TC-P001-01..08: synthetic acceptance inputs, never phone/codec certification.

The oracle is independently constructed file bytes, Git identities and expected
verdicts. S23_P001_EVIDENCE_DIR retains each perturbed input and observed output.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_research_contract import validate_contract, decode, previous_records


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ResearchContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='p001-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.charter = json.loads((ROOT / 'docs/RESEARCH_CHARTER.json').read_text())
        self.index = json.loads((ROOT / 'docs/REQUIREMENT_EVIDENCE.json').read_text())
        (self.root / 'docs/master-directive').mkdir(parents=True)
        for name in ('directive_manifest.json', 'S23_Cinema_Master_Directive_200000_Words.md'):
            shutil.copyfile(ROOT / 'docs/master-directive' / name,
                            self.root / 'docs/master-directive' / name)
        (self.root / 'input.txt').write_text('Owned synthetic contract stimulus, not a captured image.\n')
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'P001 synthetic test')
        self.git('config', 'user.email', 'p001@example.invalid')
        self.git('add', '.')
        self.git('commit', '-m', 'Synthetic baseline')
        self.revision = self.git('rev-parse', 'HEAD').strip()
        self.charter['adoption_revision'] = self.revision
        self.index['inspections'] = [{'id': 'I-1', 'revision': self.revision,
            'scope': 'Synthetic input only; no claim that other code was inspected.',
            'files': [{'path': 'input.txt', 'sha256': file_hash(self.root / 'input.txt')}]}]
        self.index['current_inspections'] = ['I-1']
        self.index['fixtures'] = [{'id': 'FIX-1', 'path': 'input.txt',
            'sha256': file_hash(self.root / 'input.txt'), 'kind': 'synthetic',
            'provenance': {'origin': 'Owned deterministic synthetic test fixture',
                'owner': 'P001 test suite', 'acquired_at': '2026-10-01',
                'permitted_use': 'Test and redistribute this authored fixture'}}]
        self.index['evidence'] = []
        for f in self.index['findings']:
            f['evidence_ids'] = []
        self.add_receipt('MATH-A', 'host_unit_test')
        self.add_receipt('MATH-B', 'cpu_reference_comparison')
        f = self.finding('REQ-LOGC3-MATH')
        f['status'], f['evidence_ids'] = 'supported', ['MATH-A', 'MATH-B']
        baseline_result = self.check()
        self.assertEqual(baseline_result['status'], 'passed')
        self.baseline = {'charter': deepcopy(self.charter), 'index': deepcopy(self.index),
                         'receipts': {e['id']: self.receipt(e['id']) for e in self.index['evidence']},
                         'result': baseline_result}

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args],
                                       stderr=subprocess.DEVNULL, text=True)

    def finding(self, requirement):
        return next(f for f in self.index['findings'] if f['requirement_id'] == requirement)

    def add_receipt(self, identity, evidence_class, **overrides):
        receipt = {'schema_version': 1, 'id': identity, 'run_id': 'SYNTHETIC-RUN-1',
            'inspection_id': 'I-1', 'source_revision': self.revision,
            'requirement_ids': ['REQ-LOGC3-MATH'], 'evidence_class': evidence_class,
            'origin': 'synthetic', 'environment': {'kind': 'host', 'detail': 'Synthetic contract fixture'},
            'fixture_ids': ['FIX-1'], 'source_paths': ['input.txt'], 'scope': {},
            'command': 'Authored verdict fixture; not execution of an imaging algorithm',
            'outcome': 'passed', 'checks': [{'id': 'oracle', 'outcome': 'passed',
                'reason': 'Synthetic unit-test verdict for P001 validator only'}], 'measurements': []}
        receipt.update(overrides)
        self.index['evidence'].append({'id': identity, 'artifact': {}, 'reported_outcome': receipt['outcome']})
        self.write_receipt(identity, receipt)
        return receipt

    def receipt(self, identity):
        return json.loads((self.root / f'{identity}.json').read_text())

    def write_receipt(self, identity, receipt):
        path = self.root / f'{identity}.json'
        path.write_text(json.dumps(receipt, allow_nan=False) + '\n')
        entry = next(e for e in self.index['evidence'] if e['id'] == identity)
        entry['artifact'] = {'path': path.name, 'sha256': file_hash(path)}

    def check(self, **kwargs):
        return validate_contract(self.charter, self.index, self.root, **kwargs)

    def trace(self, case, label, result):
        directory = os.environ.get('S23_P001_EVIDENCE_DIR')
        if directory:
            out = Path(directory) / case
            out.mkdir(parents=True, exist_ok=True)
            data = {'case': case, 'variant': label, 'scope': 'Synthetic P001 validator test only',
                    'baseline': self.baseline, 'charter': self.charter, 'index': self.index,
                    'receipts': {e['id']: self.receipt(e['id']) if (self.root / f"{e['id']}.json").is_file()
                                 else {'unavailable': 'Receipt removed by the test adversary'}
                                 for e in self.index['evidence']},
                    'fixture_bytes_hex': {f['id']: (subprocess.check_output(['git', '-C', str(self.root), 'show', f["git_revision"] + ':' + f['path']])
                                                               if f.get('git_revision') else (self.root / f['path']).read_bytes()).hex()
                                          for f in self.index['fixtures']
                                          if (self.root / f['path']).is_file()},
                    'result': result}
            (out / f'{label}.json').write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')

    def rejected(self, case, label, code, **kwargs):
        before = deepcopy((self.charter, self.index))
        result = self.check(**kwargs)
        self.trace(case, label, result)
        self.assertEqual(result['status'], 'failed', label)
        self.assertIn(code, {i['code'] for i in result['issues']}, result)
        self.assertEqual(before, (self.charter, self.index), 'Validator modified its inputs')
        return result

    def test_tc_p001_01_unsupported_certainty(self):
        for req in ('REQ-NATIVE-HIRES', 'REQ-RAW-LOG', 'CLAIM-SDR-ADDS-DR', 'EXCLUDED-CLOUD-GENERATION'):
            with self.subTest(requirement=req):
                f = self.finding(req)
                old = f['status']
                f['status'] = 'supported'
                result = self.rejected('TC-P001-01', req, 'unsupported_claim')
                self.assertIn('FINDING-REQ-LOGC3-MATH', result['accepted_findings'])
                self.assertEqual(result['research_questions'], self.charter['research_questions'])
                f['status'] = old
        for origin, environment, outcome in [('synthetic', 'host', 'passed'),
                                             ('emulator', 'emulator', 'passed'),
                                             ('physical_capture', 'physical_phone', 'unavailable')]:
            with self.subTest(origin=origin):
                identity = f'PHYSICAL-{origin}'
                self.add_receipt(identity, 'physical_phone_functional',
                    origin=origin, environment={'kind': environment, 'detail': 'Synthetic declared environment'},
                    requirement_ids=['REQ-RAW-LOG'], outcome=outcome,
                    checks=[{'id': 'capture', 'outcome': outcome, 'reason': 'Synthetic declaration, no phone'}])
                f = self.finding('REQ-RAW-LOG')
                f['status'], f['evidence_ids'] = 'supported', [identity]
                self.rejected('TC-P001-01', origin, 'unsupported_claim')
                f['status'], f['evidence_ids'] = 'open', []
                self.index['evidence'] = [e for e in self.index['evidence'] if e['id'] != identity]

    def test_tc_p001_02_revision_scope_is_not_silently_promoted(self):
        self.rejected('TC-P001-02', 'wrong-expected-head', 'head_changed', expected_head='0' * 40)
        (self.root / 'notes.md').write_text('Unrelated collaborator documentation')
        self.git('add', 'notes.md'); self.git('commit', '-m', 'Unrelated change')
        result = self.check()
        self.trace('TC-P001-02', 'unrelated-change', result)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['inspection_revisions'], [self.revision])
        self.assertNotEqual(result['current_revision'], self.revision)
        (self.root / 'input.txt').write_text('Changed capture-interface fixture')
        self.rejected('TC-P001-02', 'overlapping-source-change', 'stale_source')

    def test_tc_p001_03_missing_provenance_cannot_support_a_claim(self):
        for kind in ('model', 'stock_profile', 'movie_reference', 'generated_screenshot'):
            for field in ('origin', 'owner', 'acquired_at', 'permitted_use'):
                with self.subTest(kind=kind, field=field):
                    fixture = self.index['fixtures'][0]
                    fixture['kind'] = kind
                    old = fixture['provenance'].pop(field)
                    result = self.rejected('TC-P001-03', f'{kind}-{field}', 'fixture_invalid')
                    self.assertNotIn('FINDING-REQ-LOGC3-MATH', result['accepted_findings'])
                    fixture['provenance'][field] = old

    def test_tc_p001_04_raw_outcomes_override_green_summaries(self):
        original = self.receipt('MATH-A')
        for outcome in ('failed', 'blocked', 'unavailable', 'not_run', 'inconclusive'):
            with self.subTest(outcome=outcome):
                receipt = deepcopy(original)
                receipt['checks'][0]['outcome'] = outcome
                self.write_receipt('MATH-A', receipt)
                result = self.rejected('TC-P001-04', outcome, 'contradictory_outcome')
                self.assertEqual(result['evidence_outcomes']['MATH-A'], outcome)
        stale = deepcopy(original); stale['source_revision'] = '1' * 40
        self.write_receipt('MATH-A', stale)
        self.rejected('TC-P001-04', 'stale-report', 'evidence_invalid')
        self.write_receipt('MATH-A', original)
        self.add_receipt('OMITTED-FAILURE', 'host_unit_test', outcome='failed',
            checks=[{'id': 'critical', 'outcome': 'failed', 'reason': 'Known failure in same run'}])
        self.rejected('TC-P001-04', 'cherry-picked-green', 'unsupported_claim')

    def with_policy(self):
        policy = {'id': 'POLICY-LATENCY-1', 'version': 1, 'metric': 'latency', 'unit': 'ms',
                  'domain': 'synthetic_test_time', 'operator': 'le', 'limit': 10,
                  'supersedes': None, 'review': None}
        self.charter['policies'] = [policy]
        receipt = self.receipt('MATH-A')
        receipt['measurements'] = [{'policy_id': policy['id'], 'policy_sha256': digest(policy),
                                    'value': 5, 'unit': 'ms', 'domain': policy['domain']}]
        self.write_receipt('MATH-A', receipt)
        self.assertEqual(self.check()['status'], 'passed')
        return policy, receipt

    def test_tc_p001_05_units_domains_and_numerical_outcomes(self):
        _, original = self.with_policy()
        for label, patch in [('missing-unit', {'unit': ''}), ('microseconds-as-ms', {'unit': 'us'}),
                             ('display-as-scene', {'domain': 'display_encoded'}),
                             ('missing-domain', {'domain': ''}), ('boolean-value', {'value': True})]:
            with self.subTest(label=label):
                receipt = deepcopy(original); receipt['measurements'][0].update(patch)
                self.write_receipt('MATH-A', receipt)
                self.rejected('TC-P001-05', label, 'evidence_invalid')
        receipt = deepcopy(original); receipt['measurements'][0]['value'] = 11
        self.write_receipt('MATH-A', receipt)
        self.rejected('TC-P001-05', 'measured-failure-hidden-by-pass', 'contradictory_outcome')

    def test_tc_p001_06_threshold_and_history_are_not_rewritten(self):
        policy, receipt = self.with_policy()
        previous = deepcopy((self.charter, self.index))
        policy['limit'] = 20
        # Even re-hashing both new inputs does not erase the independently supplied old policy.
        receipt['measurements'][0]['policy_sha256'] = digest(policy)
        self.write_receipt('MATH-A', receipt)
        self.rejected('TC-P001-06', 'threshold-rewrite', 'history_rewritten', previous=previous)
        self.charter, self.index = deepcopy(previous)
        self.index['evidence'].pop()
        self.rejected('TC-P001-06', 'deleted-old-evidence', 'history_rewritten', previous=previous)
        self.charter, self.index = deepcopy(previous)
        new_policy = deepcopy(policy)
        new_policy.update(id='POLICY-LATENCY-2', version=2, supersedes='POLICY-LATENCY-1')
        self.charter['policies'].append(new_policy)
        self.rejected('TC-P001-06', 'unreviewed-new-version', 'policy_invalid', previous=previous)

    def test_tc_p001_07_collaborator_changes_survive_validation(self):
        sentinel = self.root / 'untracked-collaborator.txt'
        sentinel.write_bytes(b'Irreplaceable collaborator change\x00\xff')
        before = sentinel.read_bytes()
        result = self.check(expected_head=self.revision)
        self.trace('TC-P001-07', 'untracked-change-preserved', result)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(sentinel.read_bytes(), before)
        self.git('add', sentinel.name); self.git('commit', '-m', 'Concurrent commit')
        self.rejected('TC-P001-07', 'head-moved', 'head_changed', expected_head=self.revision)
        self.assertEqual(sentinel.read_bytes(), before)
        (self.root / 'input.txt').write_bytes(b'Overlapping collaborator change')
        self.rejected('TC-P001-07', 'overlap-preserved', 'stale_source')
        self.assertEqual((self.root / 'input.txt').read_bytes(), b'Overlapping collaborator change')

    def test_tc_p001_08_fresh_offline_cli_and_missing_prerequisite(self):
        (self.root / 'docs/RESEARCH_CHARTER.json').write_text(json.dumps(self.charter))
        (self.root / 'docs/REQUIREMENT_EVIDENCE.json').write_text(json.dumps(self.index))
        (self.root / 'scripts').mkdir()
        shutil.copyfile(ROOT / 'scripts/verify_research_contract.py', self.root / 'scripts/verify_research_contract.py')
        def run():
            return subprocess.run([sys.executable, '-I', str(self.root / 'scripts/verify_research_contract.py'),
                '--root', str(self.root), '--expected-head', self.revision, '--baseline-ref', self.revision],
                cwd='/', env={'PATH': os.environ['PATH'], 'HOME': str(self.root / 'empty-home')},
                capture_output=True, text=True)
        result = run()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'passed')
        self.trace('TC-P001-08', 'fresh-isolated-offline-cli', json.loads(result.stdout))
        (self.root / 'MATH-A.json').unlink()
        result = run()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.trace('TC-P001-08', 'missing-file-in-fresh-environment', report)
        self.assertEqual(report['status'], 'failed')
        self.assertIn('evidence_invalid', {i['code'] for i in report['issues']})


    def physical_receipts(self, fixture_kind='owned_media'):
        self.index['fixtures'][0]['kind'] = fixture_kind
        scope = {'device_build': 'synthetic-device-build', 'camera_route': 'rear:0',
                 'codec': 'declared-codec', 'profile': 'test-profile', 'geometry': '1920x1080',
                 'frame_rate': '24/1 fps', 'duration_seconds': 60, 'environment': 'synthetic-room'}
        ids = []
        for i, cls in enumerate(('codec_encode_decode', 'physical_phone_functional', 'controlled_color_optics')):
            identity = f'PHYSICAL-{i}'
            ids.append(identity)
            self.add_receipt(identity, cls, origin='physical_capture',
                environment={'kind': 'physical_phone', 'detail': 'Synthetic positive schema fixture, not phone footage'},
                requirement_ids=['REQ-RAW-LOG'], scope=scope)
        finding = self.finding('REQ-RAW-LOG')
        finding.update(status='supported', evidence_ids=ids, scope=scope)
        return scope

    def test_tc_p001_01_physical_positive_control_is_only_schema_evidence(self):
        self.physical_receipts()
        result = self.check()
        self.trace('TC-P001-01', 'declared-physical-positive-control', result)
        self.assertEqual(result['status'], 'passed', result)
        self.assertIn('FINDING-REQ-RAW-LOG', result['accepted_findings'])
        receipt = self.receipt('PHYSICAL-1')
        receipt['scope']['geometry'] = '3840x2160'
        self.write_receipt('PHYSICAL-1', receipt)
        self.rejected('TC-P001-01', 'mismatched-physical-configuration', 'unsupported_claim')

    def test_tc_p001_01_synthetic_fixture_cannot_be_relabelled_as_phone_capture(self):
        self.physical_receipts(fixture_kind='synthetic')
        result = self.rejected('TC-P001-01', 'relabelled-synthetic-fixture', 'evidence_invalid')
        self.assertNotIn('FINDING-REQ-RAW-LOG', result['accepted_findings'])

    def test_tc_p001_03_missing_bytes_and_symlinks_fail_without_mutation(self):
        fixture = deepcopy(self.index['fixtures'][0])
        fixture.update(id='FIX-MISSING', path='absent.dat')
        self.index['fixtures'].append(fixture)
        self.rejected('TC-P001-03', 'missing-artifact-bytes', 'fixture_invalid')
        self.index['fixtures'].pop()
        target = self.root / 'symlink.dat'
        target.symlink_to(self.root / 'input.txt')
        fixture.update(path='symlink.dat')
        self.index['fixtures'].append(fixture)
        self.rejected('TC-P001-03', 'symlink-artifact', 'fixture_invalid')
        self.assertTrue(target.is_symlink())

    def test_tc_p001_04_invalid_receipt_cannot_hide_same_run_contradiction(self):
        bad = self.add_receipt('BAD-MEASUREMENT', 'host_unit_test')
        bad['measurements'] = [{'policy_id': 'ABSENT', 'policy_sha256': '0' * 64,
                               'value': 99, 'unit': 'ms', 'domain': 'time'}]
        self.write_receipt('BAD-MEASUREMENT', bad)
        result = self.rejected('TC-P001-04', 'invalid-known-run-measurement', 'evidence_invalid')
        self.assertNotIn('FINDING-REQ-LOGC3-MATH', result['accepted_findings'])

    def test_tc_p001_05_nonfinite_and_duplicate_json_are_rejected(self):
        for data in (b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}'):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    decode(data)

    def test_tc_p001_05_measurement_domains_are_not_interchangeable(self):
        policy, original = self.with_policy()
        for unit, domain in [('ms', 'time'), ('deltaE', 'colorimetric'), ('bytes', 'memory'),
                             ('pixels', 'geometric_blur_diameter'), ('codes', 'source_precision')]:
            with self.subTest(domain=domain):
                policy.update(unit=unit, domain=domain)
                receipt = deepcopy(original)
                receipt['measurements'][0].update(unit=unit, domain=domain, policy_sha256=digest(policy))
                self.write_receipt('MATH-A', receipt)
                self.assertEqual(self.check()['status'], 'passed')
                receipt['measurements'][0]['domain'] = 'different_domain'
                self.write_receipt('MATH-A', receipt)
                self.rejected('TC-P001-05', domain, 'evidence_invalid')

    def test_tc_p001_06_rewritten_policy_cannot_leave_an_accepted_finding(self):
        policy, receipt = self.with_policy()
        previous = deepcopy((self.charter, self.index))
        policy['limit'] = 20
        receipt['measurements'][0]['policy_sha256'] = digest(policy)
        self.write_receipt('MATH-A', receipt)
        result = self.rejected('TC-P001-06', 'rewritten-policy-not-accepted', 'history_rewritten', previous=previous)
        self.assertNotIn('FINDING-REQ-LOGC3-MATH', result['accepted_findings'])

    def test_tc_p001_06_reviewed_new_policy_preserves_original_failure(self):
        policy, receipt = self.with_policy()
        receipt['measurements'][0]['value'] = 15
        receipt['outcome'] = 'failed'
        self.write_receipt('MATH-A', receipt)
        self.index['evidence'][0]['reported_outcome'] = 'failed'
        self.finding('REQ-LOGC3-MATH')['status'] = 'open'
        self.assertEqual(self.check()['status'], 'passed')
        previous = deepcopy((self.charter, self.index))
        replacement = deepcopy(policy)
        replacement.update(id='POLICY-LATENCY-2', version=2, limit=20, supersedes=policy['id'],
            review={'reviewer': 'Synthetic reviewer', 'reason': 'Explicit test-only protocol revision',
                    'validation_evidence': ['MATH-B']})
        self.charter['policies'].append(replacement)
        self.charter['charter_version'] = self.index['charter_version'] = 2
        self.charter['amendments'].append({'id': 'AMENDMENT-1', 'from_version': 1, 'to_version': 2,
            'reviewer': 'Synthetic owner review', 'reason': 'Positive control for versioned policy updates',
            'affected_requirements': ['REQ-LOGC3-MATH'], 'validation_evidence': ['MATH-B']})
        fresh = self.add_receipt('MATH-A2', 'host_unit_test', run_id='SYNTHETIC-RUN-2')
        fresh['measurements'] = deepcopy(receipt['measurements'])
        fresh['measurements'][0].update(policy_id=replacement['id'], policy_sha256=digest(replacement))
        self.write_receipt('MATH-A2', fresh)
        self.add_receipt('MATH-B2', 'cpu_reference_comparison', run_id='SYNTHETIC-RUN-2')
        self.finding('REQ-LOGC3-MATH').update(status='supported', evidence_ids=['MATH-A2', 'MATH-B2'])
        result = self.check(previous=previous)
        self.trace('TC-P001-06', 'reviewed-version-with-original-failure-retained', result)
        self.assertEqual(result['status'], 'passed', result)
        self.assertEqual(result['evidence_outcomes']['MATH-A'], 'failed')
        self.assertEqual(result['evidence_outcomes']['MATH-A2'], 'passed')
        self.assertEqual(previous[1]['evidence'], self.index['evidence'][:2])

    def test_tc_p001_06_old_baseline_cannot_bypass_later_history(self):
        (self.root / 'docs/RESEARCH_CHARTER.json').write_text(json.dumps(self.charter))
        (self.root / 'docs/REQUIREMENT_EVIDENCE.json').write_text(json.dumps(self.index))
        self.git('add', '.'); self.git('commit', '-m', 'First contract')
        first_contract = self.git('rev-parse', 'HEAD').strip()
        (self.root / 'notes.md').write_text('Later unrelated revision')
        self.git('add', '.'); self.git('commit', '-m', 'Later revision')
        with self.assertRaisesRegex(ValueError, 'immediate'):
            previous_records(self.root, self.revision, self.revision)
        old = previous_records(self.root, first_contract, self.revision)
        self.assertEqual(old[0], self.charter)

    def test_tc_p001_07_head_moving_during_read_is_detected(self):
        from unittest.mock import patch
        with patch('verify_research_contract.revision', side_effect=[self.revision, '1' * 40]):
            self.rejected('TC-P001-07', 'head-changed-during-check', 'head_changed')

    def test_charter_cannot_drop_scope_or_weaken_constraints(self):
        original = deepcopy(self.charter)
        for mutate in (lambda c: c['virtual_formats'].pop(),
                       lambda c: c['requirements'].pop(),
                       lambda c: c['constraints'].update(retain_source=False),
                       lambda c: c['constraints'].update(offline_core=1),
                       lambda c: c.update(schema_version=True),
                       lambda c: c['requirements'].append(deepcopy(c['requirements'][0]))):
            self.charter = deepcopy(original)
            mutate(self.charter)
            self.assertEqual(self.check()['status'], 'failed')

    def test_checkout_contract_has_no_accepted_product_claims(self):
        charter = json.loads((ROOT / 'docs/RESEARCH_CHARTER.json').read_text())
        index = json.loads((ROOT / 'docs/REQUIREMENT_EVIDENCE.json').read_text())
        result = validate_contract(charter, index, ROOT)
        self.assertEqual(result['status'], 'passed', result)
        self.assertEqual(result['accepted_findings'], [])
        self.assertEqual(len(charter['virtual_formats']), 6)


    def test_tc_p001_02_fresh_inspection_preserves_superseded_evidence(self):
        # An audit must be able to advance without rewriting an older report.
        self.index['fixtures'][0]['git_revision'] = self.revision
        old_receipts = deepcopy(self.index['evidence'])
        (self.root / 'input.txt').write_text('A newly inspected production interface')
        self.git('add', 'input.txt'); self.git('commit', '-m', 'Source evolution')
        current = self.git('rev-parse', 'HEAD').strip()
        self.index['inspections'].append({'id': 'I-2', 'revision': current,
            'scope': 'Explicit incremental inspection of the changed source only',
            'files': [{'path': 'input.txt', 'sha256': file_hash(self.root / 'input.txt')}]})
        self.index['current_inspections'] = ['I-2']
        self.finding('REQ-LOGC3-MATH')['status'] = 'open'
        result = self.check()
        self.trace('TC-P001-02', 'superseded-source-preserves-history', result)
        self.assertEqual(result['status'], 'passed', result)
        self.assertEqual(result['evidence_outcomes']['MATH-A'], 'passed')
        self.assertEqual(result['evidence_applicability']['MATH-A'], 'historical_only')
        self.assertEqual(result['accepted_findings'], [])
        self.assertEqual(self.index['evidence'], old_receipts)
        self.finding('REQ-LOGC3-MATH')['status'] = 'supported'
        self.rejected('TC-P001-02', 'old-result-cannot-certify-new-source', 'unsupported_claim')


if __name__ == '__main__':
    unittest.main()
