"""P002: real Git/file fixtures around the continuity gate, never camera qualification."""
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import zipfile
from unittest.mock import patch

import test_research_contract as research
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import verify_repository_continuity as continuity


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def capsule(xml, *, revision='a' * 40, path='junit.xml', extras=None, manifest_change=None):
    """Synthetic archived verdicts, not execution of an Android test."""
    files = {path: xml.encode(), **(extras or {})}
    provenance = {'source_revision': revision, 'original_artifact_sha256': 'b' * 64,
        'origin': 'Authored synthetic JUnit fixture', 'scope': 'Archive parser test only',
        'members': {k: hashlib.sha256(v).hexdigest() for k, v in files.items()}}
    if manifest_change:
        manifest_change(provenance)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
        z.writestr('provenance.json', json.dumps(provenance))
    return stream.getvalue()


class ContinuityCiTests(unittest.TestCase):
    ONE = '<testsuite tests="1" failures="0" errors="0" skipped="0"><testcase classname="OwnerTest" name="keepsSource"/></testsuite>'

    def test_tc_p002_04_junit_wrapper_and_individual_outcomes(self):
        xml = ('<testsuites tests="3" failures="1" errors="0" skipped="1">' + self.ONE +
            '<testsuite tests="2" failures="1" errors="0" skipped="1">'
            '<testcase classname="OwnerTest" name="fails"><failure message="deliberate"/></testcase>'
            '<testcase classname="OwnerTest" name="missingPhone"><skipped/></testcase>'
            '</testsuite></testsuites>')
        observed = continuity.ci_cases(capsule(xml), 'a' * 40)
        self.assertEqual({'keepsSource': 'passed', 'fails': 'failed', 'missingPhone': 'not_run'},
                         {key[2]: value for key, value in observed.items()})

    def test_tc_p002_04_green_summary_cannot_hide_failed_child(self):
        child = self.ONE.replace('failures="0"', 'failures="1"').replace('/></testsuite>', '><failure/></testcase></testsuite>')
        for xml in [child.replace('failures="1"', 'failures="0"'),
                    '<testsuites tests="1" failures="0" errors="0" skipped="0">' + child + '</testsuites>',
                    self.ONE.replace('tests="1"', 'tests="2"')]:
            with self.subTest(xml=xml), self.assertRaisesRegex(ValueError, 'JUnit summary contradicts'):
                continuity.ci_cases(capsule(xml), 'a' * 40)

    def test_tc_p002_03_ci_hash_and_inventory_are_independently_checked(self):
        for change in [lambda p: p['members'].update({'junit.xml': '0' * 64}),
                       lambda p: p['members'].clear()]:
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'CI member'):
                continuity.ci_cases(capsule(self.ONE, manifest_change=change), 'a' * 40)

    def test_tc_p002_02_wrong_ci_revision_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'source revision'):
            continuity.ci_cases(capsule(self.ONE), 'c' * 40)

    def test_tc_p002_03_archive_paths_and_entities_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            continuity.ci_cases(capsule(self.ONE, path='../junit.xml'), 'a' * 40)
        with self.assertRaisesRegex(ValueError, 'declarations'):
            continuity.ci_cases(capsule('<!DOCTYPE testsuite [<!ENTITY e "fake">]>' + self.ONE), 'a' * 40)

    def test_tc_p002_04_duplicate_case_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate JUnit'):
            continuity.ci_cases(capsule('<testsuites tests="2">' + self.ONE * 2 + '</testsuites>'), 'a' * 40)


class RepositoryContinuityTests(unittest.TestCase):
    def setUp(self):
        # Composition reuses the independently authored P001 receipts without
        # inheriting/recounting the P001 test methods as new P002 coverage.
        self.f = research.ResearchContractTests(methodName='runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.root = self.f.root
        self.f.charter['policies'] = [{'id': 'TIME-1', 'version': 1, 'metric': 'latency', 'unit': 'ms',
            'domain': 'sensor_time', 'operator': 'le', 'limit': 4, 'supersedes': None, 'review': None}]
        for name, value in [('RESEARCH_CHARTER.json', self.f.charter), ('REQUIREMENT_EVIDENCE.json', self.f.index)]:
            (self.root / 'docs' / name).write_text(json.dumps(value) + '\n')
        self.f.git('add', '.'); self.f.git('commit', '-m', 'Synthetic P001 contract and original policy')
        contents = {
            'app/build.gradle.kts': 'plugins { id("com.android.application") }\n',
            'app/src/main/java/Owner.kt': '\n'.join(
                'fun ' + name + '() = Unit' for name in continuity.REQUIRED_SEAMS if name != 'build') + '\n',
            'app/src/test/java/OwnerTest.kt': '@Test fun keepsSource() { assertEquals(original, retained) }\n',
        }
        for name, data in contents.items():
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(data)
        self.f.git('add', 'app'); self.f.git('commit', '-m', 'Synthetic reusable production seams')
        self.base = self.f.git('rev-parse', 'HEAD').strip()
        files = [{'path': name, 'blob_sha': self.f.git('rev-parse', self.base + ':' + name).strip(),
                  'sha256': sha(self.root / name), 'role': role,
                  'reviewed_lines': [[1, len((self.root / name).read_text().splitlines())]]}
                 for name, role in zip(contents, ['build', 'production', 'test'])]
        self.f.index['inspections'].append({'id': 'I-P002', 'revision': self.base,
            'scope': 'Authored synthetic source excerpts, not Android execution.',
            'files': [{'path': item['path'], 'sha256': item['sha256']} for item in files]})
        self.f.index['current_inspections'].append('I-P002')
        def ref(path, anchor):
            return {'path': path, 'anchor': anchor, 'purpose': 'Synthetic ownership boundary'}
        owner = 'app/src/main/java/Owner.kt'
        self.plan = {'schema_version': 1, 'phase': 'P002', 'inspection_id': 'I-P002',
            'source_revision': self.base, 'source_tree': self.f.git('rev-parse', 'HEAD^{tree}').strip(),
            'scope': 'Selected production and test excerpts only; all other files uninspected.',
            'files': files, 'seams': [], 'mappings': [], 'decisions': [], 'prior_ci': None}
        for name in continuity.REQUIRED_SEAMS:
            entry = ref('app/build.gradle.kts', 'plugins {') if name == 'build' else ref(owner, 'fun ' + name + '(')
            self.plan['seams'].append({'id': name, 'owner': entry,
                'callers': [] if name == 'build' else [ref(owner, 'fun presentation(')],
                'tests': [] if name == 'build' else [{**ref('app/src/test/java/OwnerTest.kt', 'fun keepsSource('),
                    'evidence_class': 'host_unit_test', 'execution': {'outcome': 'not_run', 'reason': 'Static fixture only'}}],
                'inputs': 'Retained synthetic bytes', 'outputs': 'Declared result',
                'limits': ['No physical device or production algorithm was executed.']})
        for req in self.f.charter['requirements']:
            state = {'required_outcome': 'partial', 'conditional_research': 'conditional',
                     'prohibited_claim': 'prohibited', 'excluded_scope': 'excluded'}[req['category']]
            self.plan['mappings'].append({'requirement_id': req['id'], 'implementation': state,
                'seam_ids': ['raw_source'], 'summary': 'Synthetic static mapping, not feature acceptance.',
                'gaps': [{'phase': req['phase'], 'reason': 'Owning acceptance work remains open.'}]})
        self.plan['decisions'] = [{'component': 'capture', 'seam_id': 'capture', 'action': 'reuse',
                                  'phase': 'P003', 'reason': 'Do not duplicate the camera engine.'}]
        self.write()
        self.baseline = deepcopy(self.plan)

    def write(self):
        for name, value in [('RESEARCH_CHARTER.json', self.f.charter), ('REQUIREMENT_EVIDENCE.json', self.f.index),
                            ('REPOSITORY_CONTINUITY.json', self.plan)]:
            (self.root / 'docs' / name).write_text(json.dumps(value, indent=2) + '\n')

    def check(self, **kwargs):
        self.write()
        return continuity.verify(self.root, self.plan, **kwargs)

    def trace(self, case, label, result):
        target = os.environ.get('S23_P002_EVIDENCE_DIR')
        if not target:
            return
        out = Path(target) / case
        out.mkdir(parents=True, exist_ok=True)
        receipts = {e['id']: self.f.receipt(e['id']) for e in self.f.index['evidence']}
        (out / (label + '.json')).write_text(json.dumps({'case': case, 'scope': 'Synthetic P002 gate test',
            'baseline': self.baseline, 'perturbed_plan': self.plan, 'charter': self.f.charter,
            'index': self.f.index, 'receipts': receipts, 'result': result}, indent=2) + '\n')

    def reject(self, case, label, code, **kwargs):
        before = deepcopy(self.plan)
        result = self.check(**kwargs)
        self.trace(case, label, result)
        self.assertEqual('failed', result['status'], result)
        self.assertIn(code, {x['code'] for x in result['issues']}, result)
        self.assertEqual(before, self.plan)
        return result

    def test_valid_scope_has_no_physical_certification(self):
        result = self.check(expected_head=self.base)
        self.assertEqual('passed', result['status'], result)
        self.assertEqual(self.base, result['inspection_revision'])
        self.assertIn('input.txt', result['uninspected_baseline_files'])
        self.assertFalse(result['physical_certification'])

    def test_tc_p002_01_uncertainty_and_narrower_findings_are_preserved(self):
        for origin, kind, outcome in [('synthetic', 'host', 'passed'), ('emulator', 'emulator', 'passed'),
                                      ('physical_capture', 'physical_phone', 'unavailable')]:
            receipt_id = 'NEW-PHYSICAL-' + origin
            self.f.add_receipt(receipt_id, 'physical_phone_functional',
                origin=origin, environment={'kind': kind, 'detail': 'Authored verdict fixture'},
                requirement_ids=['REQ-RAW-LOG'], outcome=outcome,
                checks=[{'id': 'probe', 'outcome': outcome, 'reason': 'No phone measured'}])
            finding = self.f.finding('REQ-RAW-LOG')
            finding['status'], finding['evidence_ids'] = 'supported', [receipt_id]
            result = self.reject('TC-P002-01', origin, 'research_contract_failed')
            self.assertIn('FINDING-REQ-LOGC3-MATH', result['research_contract']['accepted_findings'])
            self.assertEqual(self.f.charter['research_questions'], result['research_contract']['research_questions'])
            finding['status'], finding['evidence_ids'] = 'open', []
            self.f.index['evidence'] = [e for e in self.f.index['evidence'] if e['id'] != receipt_id]
        self.plan['mappings'][0]['implementation'] = 'physically_qualified'
        self.reject('TC-P002-01', 'static-is-not-qualified', 'mapping_invalid')

    def test_tc_p002_02_unrelated_revision_is_not_a_full_new_audit(self):
        (self.root / 'notes.md').write_text('Independent documentation change')
        self.f.git('add', 'notes.md'); self.f.git('commit', '-m', 'Unrelated note')
        result = self.check()
        self.trace('TC-P002-02', 'unrelated-commit', result)
        self.assertEqual('passed', result['status'], result)
        self.assertEqual(self.base, result['inspection_revision'])
        self.assertNotEqual(self.base, result['current_revision'])
        self.assertIn('notes.md', result['unreviewed_committed_changes'])
        self.reject('TC-P002-02', 'wrong-head', 'head_changed', expected_head=self.base)

    def test_tc_p002_02_changed_code_and_fabricated_blob_require_review(self):
        item = self.plan['files'][1]
        item['blob_sha'] = 'a' * 40
        self.reject('TC-P002-02', 'wrong-blob', 'source_invalid')
        item['blob_sha'] = self.baseline['files'][1]['blob_sha']
        (self.root / item['path']).write_text('fun renamedCapture() = Unit\n')
        self.reject('TC-P002-02', 'changed-interface', 'source_invalid')

    def test_tc_p002_02_new_uninspected_production_file_is_not_silent(self):
        p = self.root / 'app/src/main/java/NewCamera.kt'; p.write_text('class NewCamera\n')
        self.f.git('add', 'app'); self.f.git('commit', '-m', 'New production file')
        self.reject('TC-P002-02', 'new-camera-file', 'production_review_required')

    def test_tc_p002_03_provenance_is_required_across_fixture_kinds(self):
        fixture = self.f.index['fixtures'][0]
        old = fixture['provenance'].pop('owner')
        for kind in ('model', 'stock_profile', 'movie_reference', 'generated_screenshot'):
            fixture['kind'] = kind
            self.reject('TC-P002-03', kind, 'research_contract_failed')
        fixture['provenance']['owner'] = old

    def test_tc_p002_03_missing_test_and_unreviewed_anchor_are_rejected(self):
        test = self.plan['seams'][1]['tests'][0]
        test['anchor'] = 'fun nonexistentTest('
        self.reject('TC-P002-03', 'invented-test', 'seam_invalid')
        test['anchor'] = 'fun keepsSource('
        test['path'] = 'app/src/test/java/Missing.kt'
        self.reject('TC-P002-03', 'missing-test', 'seam_invalid')

    def test_tc_p002_04_individual_outcomes_override_green(self):
        for outcome in ('failed', 'unavailable', 'not_run'):
            receipt_id = 'NEW-OUTCOME-' + outcome
            self.f.add_receipt(receipt_id, 'cpu_reference_comparison',
                run_id='NEW-RUN-' + outcome, checks=[{'id': 'raw-check', 'outcome': outcome,
                    'reason': 'Intentional contradictory synthetic raw verdict'}])
            result = self.reject('TC-P002-04', outcome, 'research_contract_failed')
            self.assertEqual(outcome, result['research_contract']['evidence_outcomes'][receipt_id])
            self.assertIn('contradictory_outcome', {i['code'] for i in result['research_contract']['issues']})
            self.assertIn('FINDING-REQ-LOGC3-MATH', result['research_contract']['accepted_findings'])

    def test_tc_p002_05_units_and_domains_must_match(self):
        policy = self.f.charter['policies'][0]
        raw = self.f.add_receipt('NEW-UNITS', 'cpu_reference_comparison', run_id='NEW-UNITS-RUN')
        measurement = {'policy_id': 'TIME-1', 'policy_sha256': research.digest(policy),
                       'value': 3, 'unit': 'ms', 'domain': 'sensor_time'}
        raw['measurements'] = [measurement]
        self.f.write_receipt('NEW-UNITS', raw)
        self.assertEqual('passed', self.check()['status'])
        for unit, domain in [('', 'sensor_time'), ('us', 'sensor_time'), ('ms', 'display_value')]:
            measurement.update(unit=unit, domain=domain)
            self.f.write_receipt('NEW-UNITS', raw)
            result = self.reject('TC-P002-05', unit + '-' + domain, 'research_contract_failed')
            details = [i['detail'] for i in result['research_contract']['issues'] if i['subject'] == 'NEW-UNITS']
            self.assertTrue(any('unit/domain mismatch' in d for d in details), details)

    def test_tc_p002_04_execution_must_match_the_referenced_test(self):
        path = 'app/build/test-results/testDebugUnitTest/TEST-OwnerTest.xml'
        data = capsule(ContinuityCiTests.ONE, revision=self.base, path=path)
        archive = self.root / 'ci.zip'; archive.write_bytes(data)
        self.plan['prior_ci'] = {'path': 'ci.zip', 'sha256': sha(archive)}
        execution = {'outcome': 'passed', 'ci_entry': path, 'classname': 'OwnerTest',
                     'testcase': 'keepsSource', 'reason': 'Synthetic execution record'}
        test = self.plan['seams'][1]['tests'][0]; test['execution'] = execution
        self.assertEqual('passed', self.check()['status'])
        for field, invalid in [('testcase', 'invented'), ('outcome', 'not_run'), ('classname', 'OtherTest')]:
            old = execution[field]; execution[field] = invalid
            self.reject('TC-P002-04', 'misbound-' + field, 'seam_invalid')
            execution[field] = old
        test['evidence_class'] = 'emulator_instrumentation'
        self.reject('TC-P002-04', 'unit-is-not-emulator', 'seam_invalid')

    def test_tc_p002_06_threshold_history_cannot_be_rewritten(self):
        policy = {'id': 'TIME-1', 'version': 1, 'metric': 'latency', 'unit': 'ms', 'domain': 'sensor_time',
                  'operator': 'le', 'limit': 4, 'supersedes': None, 'review': None}
        self.f.charter['policies'] = [policy]
        self.write(); self.f.git('add', '.'); self.f.git('commit', '-m', 'Retain original policy')
        (self.root / 'next.txt').write_text('Subsequent revision')
        self.f.git('add', '.'); self.f.git('commit', '-m', 'Independent successor')
        before = self.f.git('show', 'HEAD^:docs/RESEARCH_CHARTER.json')
        policy['limit'] = 4000
        self.reject('TC-P002-06', 'unreviewed-threshold', 'research_contract_failed')
        self.assertEqual(before, self.f.git('show', 'HEAD^:docs/RESEARCH_CHARTER.json'))

    def test_tc_p002_07_collaborator_bytes_and_index_are_preserved(self):
        collaborator = self.root / 'untracked-collaborator.txt'; collaborator.write_bytes(b'Keep exactly\x00\xff')
        index_hash = sha(self.root / '.git/index')
        result = self.check()
        self.assertEqual('passed', result['status'], result)
        self.assertEqual(b'Keep exactly\x00\xff', collaborator.read_bytes())
        self.assertEqual(index_hash, sha(self.root / '.git/index'))
        target = self.root / self.plan['files'][1]['path']; target.write_text('Overlapping collaborator change')
        self.reject('TC-P002-07', 'overlapping-change', 'source_invalid')
        self.assertEqual('Overlapping collaborator change', target.read_text())

    def test_tc_p002_07_head_moving_during_validation_is_rejected(self):
        with patch.object(continuity, 'revision', side_effect=[self.base, '0' * 40]):
            self.reject('TC-P002-07', 'moving-head', 'head_changed')

    def test_tc_p002_08_isolated_cli_and_concrete_missing_prerequisite(self):
        self.write()
        home = self.root / 'empty-home'; home.mkdir()
        env = {'PATH': os.path.dirname(shutil.which('git')), 'HOME': str(home)}
        args = [sys.executable, '-I', '-B', str(ROOT / 'scripts/verify_repository_continuity.py'),
                '--root', str(self.root), '--expected-head', self.base]
        good = subprocess.run(args, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(0, good.returncode, good.stdout + good.stderr)
        (self.root / self.plan['files'][1]['path']).unlink()
        bad = subprocess.run(args, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(1, bad.returncode, bad.stdout + bad.stderr)
        self.assertIn('Missing prerequisite file', bad.stdout)
        self.trace('TC-P002-08', 'missing-source', json.loads(bad.stdout))

    def test_readme_only_and_duplicate_camera_plan_fail(self):
        self.plan['files'] = []
        self.reject('TC-P002-02', 'readme-only-audit', 'schema_invalid')
        self.plan = deepcopy(self.baseline)
        self.plan['decisions'][0]['action'] = 'replace_camera_engine'
        self.reject('TC-P002-02', 'duplicate-camera-engine', 'decision_invalid')

    def test_real_repository_map_passes(self):
        plan = json.loads((ROOT / 'docs/REPOSITORY_CONTINUITY.json').read_text())
        result = continuity.verify(ROOT, plan)
        self.assertEqual('passed', result['status'], result)
        self.assertEqual(20, len(result['mapped_requirements']))


if __name__ == '__main__':
    unittest.main()
