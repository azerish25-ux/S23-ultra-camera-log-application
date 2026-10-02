"""P004 acceptance controls. Authored fixtures are not physical measurements."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import baseline

class BaselineTests(unittest.TestCase):
    def test_tc_p004_01_unsupported_physical_claim_preserves_software(self):
        observed = {'tests': [{'id': 'host:valid', 'outcome': 'passed'}],
                    'physical': {'outcome': 'unavailable', 'certified': False}}
        claimed = deepcopy(observed)
        claimed['physical'] = {'outcome': 'passed', 'certified': True}
        result = baseline.verify_report(claimed, observed)
        self.assertEqual('failed', result['status'])
        self.assertEqual(observed, result['observed'])

    def test_tc_p004_04_omitted_failure_is_rejected(self):
        observed = {'tests': [{'id': 'host:valid', 'outcome': 'passed'},
                              {'id': 'emulator:decode', 'outcome': 'failed'}],
                    'physical': {'outcome': 'unavailable', 'certified': False}}
        claimed = deepcopy(observed)
        claimed['tests'].pop()
        result = baseline.verify_report(claimed, observed)
        self.assertEqual('failed', result['status'])
        self.assertEqual('failed', result['observed']['tests'][1]['outcome'])

import hashlib
import io
import json
import os
import subprocess
import tempfile
import urllib.request
import warnings
import zipfile
from unittest.mock import patch


def zipped(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return stream.getvalue()


def junit(fail=False, skipped=False):
    tag = '<failure message="deliberate">original failure</failure>' if fail else '<skipped message="no hardware"/>' if skipped else ''
    return (f'<testsuite tests="1" failures="{int(fail)}" errors="0" skipped="{int(skipped)}">'
            f'<testcase classname="Fixture" name="case" time="0.1">{tag}</testcase></testsuite>').encode()


class BaselineFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.source = {'app/build.gradle.kts': b'// authored unit fixture\n', 'scripts/check_fixture.py': b'# fixture, never executed\n'}
        manifest = {n: ('100644', baseline.object_id('blob', d)) for n, d in self.source.items()}
        self.rev = 'a' * 40
        self.tree = baseline.tree_id(manifest)
        self.observations = {'recordings': {'recordings': 1}, 'p003': {'status': 'passed', 'scope': 'Authored fixture'},
                             'liveBackend': {'backend': 'unavailable'}, 'savedRawBackend': {'codecRoute': 'unavailable'},
                             'externalFullDecode': True, 'physicalCameraCertified': False}
        self.members = {'evidence/commit.txt': (self.rev + '\n').encode(),
                        'evidence/S23Log-source.zip': zipped(self.source),
                        'evidence/git-tree.txt': ''.join(f'{m} blob {s}\t{n}\n' for n, (m, s) in manifest.items()).encode(),
                        'app/build/test-results/unit.xml': junit(),
                        'app/build/outputs/androidTest-results/device.xml': junit(fail=True),
                        'evidence/emulator/permission-instrumentation.txt': b'OK (1 test)\n'}
        for name, key in [('p003-cross-adapter-summary.json', 'p003'), ('live-log-summary.json', 'liveBackend'),
                          ('raw-development-summary.json', 'savedRawBackend'), ('summary.json', 'recordings')]:
            self.members['evidence/emulator/' + name] = json.dumps(self.observations[key]).encode()
        self.job = {'id': 2, 'run_id': 1, 'run_attempt': 1, 'head_sha': self.rev,
                    'status': 'completed', 'conclusion': 'failure',
                    'started_at': '2026-10-02T00:00:00Z', 'completed_at': '2026-10-02T00:00:01Z',
                    'steps': [{'number': 1, 'name': 'Authored fixture', 'status': 'completed', 'conclusion': 'failure'}]}
        self.lock = {'schemaVersion': 1, 'baselineId': 'synthetic-P004', 'repository': baseline.REPOSITORY,
                     'source': {'revision': self.rev, 'tree': self.tree},
                     'run': {'id': 1, 'jobId': 2, 'attempt': 1, 'workflowRevision': self.rev},
                     'inputs': {}, 'expectedCounts': {'host': 1, 'jvm': 1, 'emulator': 1, 'permission': 1},
                     'scope': 'Authored synthetic acceptance fixture; no Android or physical execution.'}
        self.raw = {'verification.zip': b'', 'apk.zip': zipped({'fixture.apk': zipped({'AndroidManifest.xml': b'fixture', 'classes.dex': b'fixture'})}),
                    'job.json': b'', 'job.log': b'test_pass (fixture.Host.test_pass) ... ok\n\nRan 1 test in 0.01s\n\nOK\n'}
        self.refresh()
        self.original = deepcopy(self.lock)
        self.mock = patch.object(baseline, 'replay', return_value=self.observations)
        self.mock.start()
        self.addCleanup(self.mock.stop)

    def refresh(self):
        self.raw['verification.zip'] = zipped(self.members)
        self.raw['job.json'] = json.dumps(self.job).encode()
        for name, data in self.raw.items():
            (self.folder / name).write_bytes(data)
            self.lock['inputs'][name] = {'sha256': baseline.digest(data), 'bytes': len(data),
                                        'apiPath': '/actions/artifacts/3/zip' if name.endswith('.zip') else '/actions/jobs/2' + ('/logs' if name.endswith('.log') else ''),
                                        'owner': 'Authored test fixture', 'purpose': 'Deterministic negative control; never production evidence'}

    def collect(self):
        return baseline.collect(self.lock, self.folder)

    def save_case(self, case, claimed, observed, result):
        location = os.environ.get('S23_P004_EVIDENCE_DIR')
        if location:
            path = Path(location) / case
            path.mkdir(parents=True, exist_ok=True)
            (path / (self.id().split('.')[-1] + '.json')).write_text(json.dumps(
                {'fixture': 'Authored synthetic baseline, not phone evidence', 'claimed': claimed,
                 'observed': observed, 'result': result, 'lock': self.lock}, indent=2))

    def test_mixed_baseline_is_valid_record_not_all_pass(self):
        report = self.collect()
        self.assertEqual('passed', report['status'])
        self.assertEqual('failed', report['softwareResult'])
        self.assertEqual({'failed': 1}, report['counts']['emulator'])
        self.assertEqual('unavailable', report['physical']['outcome'])

    def test_tc_p004_01_hardware_cannot_inherit_host_or_emulator(self):
        observed = self.collect()
        for label in ('host', 'emulator', 'unavailable_backend'):
            claimed = deepcopy(observed)
            claimed['physical'] = {'outcome': 'passed', 'certified': True, 'reason': label}
            result = baseline.verify_report(claimed, observed)
            self.assertEqual('failed', result['status'])
            self.assertEqual({'passed': 1}, result['observed']['counts']['host'])
            self.save_case('TC-P004-01', claimed, observed, result)

    def test_tc_p004_02_wrong_revision_blocks_affected_evidence(self):
        self.lock['source']['revision'] = 'b' * 40
        with self.assertRaisesRegex(ValueError, 'Source revision mismatch'):
            self.collect()
        self.lock['source']['revision'] = self.rev
        self.job['head_sha'] = 'b' * 40
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'provenance mismatch'):
            self.collect()

    def test_tc_p004_02_source_content_cannot_keep_old_tree(self):
        self.source['app/build.gradle.kts'] = b'// changed interface'
        self.members['evidence/S23Log-source.zip'] = zipped(self.source)
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'Source blob mismatch'):
            self.collect()

    def test_tc_p004_03_missing_provenance_and_corrupted_input(self):
        for field in ('owner', 'purpose', 'sha256'):
            original = self.lock['inputs']['apk.zip'][field]
            self.lock['inputs']['apk.zip'][field] = ''
            with self.assertRaisesRegex(ValueError, 'identity/ownership'):
                self.collect()
            self.lock['inputs']['apk.zip'][field] = original
        (self.folder / 'apk.zip').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            self.collect()

    def test_tc_p004_04_removed_failure_or_skipped_case_rejected(self):
        for skipped in (False, True):
            self.members['app/build/outputs/androidTest-results/device.xml'] = junit(fail=not skipped, skipped=skipped)
            self.refresh()
            observed = self.collect()
            claimed = deepcopy(observed)
            claimed['tests'] = [r for r in claimed['tests'] if r['family'] != 'emulator']
            result = baseline.verify_report(claimed, observed)
            self.assertEqual('failed', result['status'])
            self.assertEqual(4, len(result['observed']['tests']))
            self.save_case('TC-P004-04', claimed, observed, result)

    def test_tc_p004_04_raw_junit_failure_beats_green_aggregate(self):
        self.members['app/build/outputs/androidTest-results/device.xml'] = junit(fail=True).replace(b'failures="1"', b'failures="0"')
        self.job['conclusion'] = 'success'
        self.refresh()
        report = self.collect()
        self.assertEqual('failed', report['status'])
        self.assertEqual({'failed': 1}, report['counts']['emulator'])
        self.assertTrue(any('aggregate failures' in s for s in report['issues']))
        self.assertTrue(any('Workflow success contradicts' in s for s in report['issues']))
        self.save_case('TC-P004-04', {}, report, {'status': report['status']})

    def test_tc_p004_04_missing_entire_test_file_is_incomplete(self):
        del self.members['app/build/outputs/androidTest-results/device.xml']
        self.refresh()
        report = self.collect()
        self.assertEqual('failed', report['status'])
        self.assertIn('Incomplete emulator execution inventory', report['issues'])

    def test_tc_p004_04_isolated_instrumentation_failure_is_not_missing(self):
        self.members['evidence/emulator/permission-instrumentation.txt'] = b'FAILURES!!!\nTests run: 1, Failures: 1\n'
        self.refresh()
        observed = self.collect()
        self.assertEqual({'failed': 1}, observed['counts']['permission'])
        self.assertEqual('failed', observed['softwareResult'])
        self.members['evidence/emulator/permission-instrumentation.txt'] += b'OK (1 test)\n'
        self.refresh()
        self.assertEqual('failed', self.collect()['status'])

    def test_tc_p004_04_duplicate_case_cannot_replace_omitted_case(self):
        self.members['app/build/test-results/duplicate.xml'] = self.members['app/build/test-results/unit.xml']
        self.lock['expectedCounts']['jvm'] = 2
        self.refresh()
        observed = self.collect()
        self.assertEqual('failed', observed['status'])
        self.assertIn('Duplicate case identity across test files', observed['issues'])

    def test_tc_p004_05_units_domains_and_values_not_interchangeable(self):
        observed = self.collect()
        for field, value in [('unit', 'ms'), ('domain', 'sensor_time'), ('value', 1000)]:
            claimed = deepcopy(observed)
            claimed['job']['duration'][field] = value
            result = baseline.verify_report(claimed, observed)
            self.assertEqual('failed', result['status'])
            self.save_case('TC-P004-05', claimed, observed, result)
        del claimed['job']['duration']['unit']
        self.assertEqual('failed', baseline.verify_report(claimed, observed)['status'])

    def test_tc_p004_06_policy_hash_cannot_be_relabelled(self):
        observed = self.collect()
        claimed = deepcopy(observed)
        claimed['policySourceHashes']['app/build.gradle.kts'] = 'f' * 64
        result = baseline.verify_report(claimed, observed)
        self.assertEqual('failed', result['status'])
        with self.assertRaisesRegex(ValueError, 'Changed acceptance policy'):
            baseline.compare_runs(observed, claimed)
        self.save_case('TC-P004-06', claimed, observed, result)

    def test_tc_p004_07_input_change_during_collection_is_not_overwritten(self):
        def concurrent(*args):
            (self.folder / 'job.log').write_bytes(b'collaborator change')
            return self.observations
        with patch.object(baseline, 'replay', side_effect=concurrent):
            with self.assertRaisesRegex(ValueError, 'changed during collection'):
                self.collect()
        self.assertEqual(b'collaborator change', (self.folder / 'job.log').read_bytes())

    def test_tc_p004_08_missing_input_is_concrete_failure(self):
        (self.folder / 'apk.zip').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing or oversized prerequisite: .*apk.zip'):
            self.collect()

    def test_replayed_aggregate_not_copied_green_summary(self):
        self.members['evidence/emulator/live-log-summary.json'] = b'{"backend":"qualified"}'
        self.refresh()
        report = self.collect()
        self.assertEqual('failed', report['status'])
        self.assertEqual('unavailable', report['replayed']['liveBackend']['backend'])

    def test_current_tree_is_independently_checked_by_git(self):
        repo = self.folder / 'git-oracle'; repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        for path, data in self.source.items():
            target = repo / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
        tree = subprocess.check_output(['git', '-C', str(repo), 'write-tree'], text=True).strip()
        self.assertEqual(tree, self.tree)


class BaselineParserTests(unittest.TestCase):
    def test_host_diagnostics_between_name_and_verdict(self):
        log = b'test_retry (tests.Transfer.test_retry) ... ADB failed as intended\nretry diagnostic\nok\nRan 1 test in 0.1s\nOK\n'
        rows, issues = baseline.host_cases(log)
        self.assertEqual([], issues)
        self.assertEqual(1, len(rows))
        self.assertIn('retry diagnostic', rows[0]['detail'])
        self.assertEqual('passed', rows[0]['outcome'])

    def test_host_missing_terminal_verdict_is_not_pass(self):
        rows, issues = baseline.host_cases(b'test_retry (test.Transfer.test_retry) ... missing\nRan 1 test in 0.1s\n')
        self.assertTrue(issues)
        self.assertEqual([], rows)

    def test_host_green_footer_does_not_override_failure(self):
        rows, issues = baseline.host_cases(b'test_fail (tests.Host.test_fail) ... FAIL\nRan 1 test in 0.1s\nOK\n')
        self.assertEqual('failed', rows[0]['outcome'])
        self.assertTrue(any('contradicts' in i for i in issues))

    def test_nested_junit_wrappers_are_checked(self):
        payload = b'<testsuites tests="1" failures="0">' + junit(fail=True) + b'</testsuites>'
        rows, issues = baseline.junit_cases(payload, 'emulator', 'fixture.xml')
        self.assertEqual('failed', rows[0]['outcome'])
        self.assertTrue(issues)

    def test_junit_duplicate_entities_and_nonfinite_duration_rejected(self):
        for payload in [b'<!DOCTYPE testsuite>' + junit(), junit().replace(b'time="0.1"', b'time="NaN"'),
                        b'<testsuites tests="2">' + junit() + junit() + b'</testsuites>']:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                baseline.junit_cases(payload, 'emulator', 'fixture.xml')

    def test_archive_traversal_duplicate_and_symlink_rejected(self):
        with self.assertRaises(ValueError):
            baseline.zip_files(zipped({'../escape': b'x'}))
        for mode in (0o120777, 0o020666):
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w') as z:
                info = zipfile.ZipInfo('link'); info.external_attr = mode << 16; z.writestr(info, b'target')
            with self.assertRaises(ValueError):
                baseline.zip_files(stream.getvalue())
        stream = io.BytesIO()
        with warnings.catch_warnings(), zipfile.ZipFile(stream, 'w') as z:
            warnings.simplefilter('ignore'); z.writestr('file', b'first'); z.writestr('file', b'second')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            baseline.zip_files(stream.getvalue())

    def test_archive_budget_precedes_decompression(self):
        with patch.object(baseline, 'MAX_EXPANDED', 2), self.assertRaisesRegex(ValueError, 'budget'):
            baseline.zip_files(zipped({'file': b'large'}))

    def test_redirect_drops_token_at_storage_boundary(self):
        req = urllib.request.Request('https://api.github.com/a', headers={'Authorization': 'Bearer synthetic'})
        redirected = baseline.SafeRedirect().redirect_request(req, None, 302, 'Found', {}, 'https://storage.example/a')
        self.assertIsNone(redirected.get_header('Authorization'))
        with self.assertRaisesRegex(ValueError, 'Non-HTTPS'):
            baseline.SafeRedirect().redirect_request(req, None, 302, 'Found', {}, 'http://storage.example/a')

    def test_tc_p004_08_isolated_cli_missing_prerequisite(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, '-I', '-B', str(baseline.ROOT / 'scripts/baseline.py'),
                                     'collect', '--lock', str(Path(folder)/'missing-lock.json'), '--inputs', folder],
                                    env={'PATH': os.environ['PATH'], 'HOME': folder}, capture_output=True, timeout=20)
        self.assertEqual(1, result.returncode)
        self.assertIn('Missing or oversized prerequisite', json.loads(result.stdout)['reason'])

    def test_tc_p004_07_and_06_workspace_is_readonly_and_history_frozen(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            def git(*args):
                return subprocess.check_output(['git', '-C', folder, *args], stderr=subprocess.DEVNULL).decode().strip()
            git('init', '-b', 'main'); git('config', 'user.name', 'Test'); git('config', 'user.email', 'test@example.invalid')
            lock = root/'lock.json'; lock.write_text('{"revision":1}')
            git('add','.'); git('commit','-m','Original')
            (root/'notes.txt').write_text('unrelated'); git('add','.'); git('commit','-m','Successor')
            (root/'collaborator.txt').write_bytes(b'keep\x00exact')
            before = baseline.digest((root/'.git/index').read_bytes())
            head = baseline.workspace(root, git('rev-parse','HEAD'), lock)
            self.assertEqual(before, baseline.digest((root/'.git/index').read_bytes()))
            with self.assertRaisesRegex(ValueError, 'HEAD changed'):
                baseline.workspace(root, '0'*40, lock)
            lock.write_text('{"revision":2}')
            with self.assertRaisesRegex(ValueError, 'Historical baseline lock'):
                baseline.workspace(root, head, lock)
            self.assertEqual(b'keep\x00exact', (root/'collaborator.txt').read_bytes())


class BaselineAdditionalTests(unittest.TestCase):
    def test_tree_order_matches_git_for_directory_prefixes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(['git', 'init', '-q', folder], check=True)
            files = {'a.c': b'x', 'a/d': b'y', 'a0': b'z', 'b/empty': b''}
            for n,d in files.items():
                p=root/n; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(d)
            subprocess.run(['git','-C',folder,'add','.'],check=True)
            expected=subprocess.check_output(['git','-C',folder,'write-tree'],text=True).strip()
            self.assertEqual(expected,baseline.tree_id({n:('100644',baseline.object_id('blob',d)) for n,d in files.items()}))

    def test_unsafe_fetch_origin_rejected_without_network(self):
        f=BaselineFixtureTests(methodName='runTest'); f.setUp()
        try:
            f.lock['inputs']['job.log']['apiPath']='https://attacker.invalid/secrets'
            with patch.object(baseline.urllib.request,'build_opener') as opener:
                with self.assertRaisesRegex(ValueError,'Unapproved'):
                    baseline.fetch(f.lock,f.folder)
                opener.assert_not_called()
        finally: f.doCleanups()

    def test_fetch_reuses_matching_inputs_and_never_overwrites(self):
        f=BaselineFixtureTests(methodName='runTest'); f.setUp()
        try:
            with patch.object(baseline.urllib.request,'build_opener') as opener:
                baseline.fetch(f.lock,f.folder)
                opener.return_value.open.assert_not_called()
                (f.folder/'job.log').write_bytes(b'keep collaborator evidence')
                with self.assertRaisesRegex(ValueError,'Refusing to overwrite'):
                    baseline.fetch(f.lock,f.folder)
                self.assertEqual(b'keep collaborator evidence',(f.folder/'job.log').read_bytes())
        finally:f.doCleanups()

    def test_comparison_keeps_real_failure_and_apk_variation_separate(self):
        f=BaselineFixtureTests(methodName='runTest'); f.setUp()
        try:
            a=f.collect(); b=deepcopy(a); b['apk']['sha256']='c'*64
            result=baseline.compare_runs(a,b)
            self.assertEqual('passed',result['status'])
            self.assertEqual('failed',result['originalSoftwareResult'])
            self.assertFalse(result['sameApkBytes'])
            b['softwareResult']='passed'
            self.assertEqual('failed',baseline.compare_runs(a,b)['status'])
            b['source']['revision']='d'*40
            with self.assertRaisesRegex(ValueError,'different source'):
                baseline.compare_runs(a,b)
        finally:f.doCleanups()


class FrozenReferenceTests(unittest.TestCase):
    def test_reference_rejects_changed_counts_or_digest(self):
        report = {'baselineId': 'unit', 'source': {'revision': 'a'}, 'counts': {'host': {'passed': 1}},
                  'apk': {'sha256': 'b'}, 'physical': baseline.PHYSICAL, 'sourceFiles': {'one': 'file'}}
        ref = {k: deepcopy(report[k]) for k in ('baselineId', 'source', 'counts', 'apk', 'physical')}
        ref.update(sourceFileCount=1, canonicalReportSha256=baseline.canonical_hash(report))
        baseline.verify_reference(ref, report)
        ref['counts']['host']['passed'] = 2
        with self.assertRaisesRegex(ValueError, 'contradicts'):
            baseline.verify_reference(ref, report)
        ref['counts'] = deepcopy(report['counts']); ref['canonicalReportSha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'digest differs'):
            baseline.verify_reference(ref, report)
