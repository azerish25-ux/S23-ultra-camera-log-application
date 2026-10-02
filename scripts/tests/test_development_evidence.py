"""P003 negative controls for the independent consumer of actual saved-RAW report schema."""
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_development_evidence import POLICY, STAGES, validate, decode
REV = 'a' * 40
ID = '01234567-1234-5678-1234-0123456789ab'


def artifact(name):
    return {'name': name, 'sha256': 'b' * 64, 'byteCount': 4096}


def signal():
    return {'fullDecodeVerified': True, 'lumaBitDepth': 10, 'chromaBitDepth': 10,
            'colorPrimariesCode': 2, 'transferCharacteristicsCode': 2, 'matrixCoefficientsCode': 1, 'decodedFrames': 4, 'measuredFps': 24.0}


def ramp(negative=False):
    return {**signal(), 'meanCodeError': 1.0 if negative else .1, 'maximumCodeError': 3 if negative else 1,
            'distinctRampLevels': 220 if negative else 800, 'passed': not negative}


def set_facts(report, stage, data):
    payload = json.dumps(data)
    row = next(r for r in report['stages'] if r['stage'] == stage)
    row['evidenceRef'] = stage + '-observation'
    row['evidenceSha256'] = hashlib.sha256(payload.encode()).hexdigest()
    report['observations'][row['evidenceRef']] = payload


def get_facts(report, stage):
    return json.loads(report['observations'][stage + '-observation'])


def fixture():
    facts = {
        'source_validation': {'source': artifact('fixture.s23raw'), 'frames': 4, 'allFrameChecksumsChecked': True,
                              'sourceBinding': {'fingerprint': 'SYNTHETIC'}, 'timestampSpanNs': 125000000,
                              'durationUnit': 'ns', 'durationDomain': 'source_sensor_timestamp_span'},
        'profile_validation': {'profile': artifact('profile.json'), 'sourceBindingChecked': True,
                               'calibrationStatus': 'synthetic', 'width': 128, 'height': 128},
        'codec_qualification': {'codec': 'synthetic-codec', 'qualification': {'status': 'qualified', 'positive': ramp(), 'eightBitNegative': ramp(True)}},
        'encoded_output': {'encoder': {'frames': 4, 'name': 'synthetic-codec'}, 'name': f'logc3-{ID}.partial.mp4', 'byteCount': 4096},
        'decoded_verification': {'verification': {**signal(), 'width': 128, 'height': 128, 'maximumFrameMeanLumaCodeError': .2,
                                  'maximumFrameMeanChromaCodeError': .3, 'maximumCodeError': 2, 'meanErrorLimitCodes': 4.,
                                  'peakErrorLimitCodes': 64, 'mediaIdentity': artifact(f'logc3-{ID}.partial.mp4')}},
        'source_preservation': {'sourceBefore': 'b' * 64, 'sourceAfter': 'b' * 64, 'profileBefore': 'b' * 64, 'profileAfter': 'b' * 64},
        'publication': {'renamedWithoutOverwrite': True, 'name': f'logc3-{ID}.mp4', 'byteCount': 4096},
    }
    report = {'schemaVersion': 1, 'kind': 'saved-raw-development-evidence', 'attemptId': ID, 'sourceRevision': REV,
              'closed': True, 'activeStage': None, 'endedAt': '2026-10-02T12:00:00Z', 'policy': deepcopy(POLICY),
              'physicalCameraCertified': False, 'sourceOwnershipIndependentlyVerified': False,
              'classification': {'verifiedOutput': True, 'publishedOutput': True, 'physicalCameraCertified': False, 'issues': []},
              'context': {'sourceSha256': 'b' * 64, 'profileSha256': 'b' * 64, 'sourceBinding': {'fingerprint': 'SYNTHETIC'},
                          'expectedFrames': 4, 'fps': 24, 'width': 128, 'height': 128, 'codec': 'synthetic-codec'},
              'stages': [], 'observations': {}}
    for stage in STAGES:
        exists = stage in facts
        report['stages'].append({'stage': stage, 'outcome': 'passed' if exists else 'not_run', 'reason': 'Synthetic consumer fixture only',
                                 'sourceRevision': REV, 'evidenceRef': None, 'evidenceSha256': None,
                                 'checks': [{'id': 'producer-contract', 'outcome': 'passed', 'reason': 'Synthetic'}] if exists else []})
        if exists:
            set_facts(report, stage, facts[stage])
    return report


class DevelopmentEvidenceTests(unittest.TestCase):
    def reject(self, case, report):
        with self.assertRaises((ValueError, KeyError, TypeError)) as error:
            validate(report, REV)
        target = os.environ.get('S23_P003_EVIDENCE_DIR')
        if target:
            directory = Path(target) / case
            directory.mkdir(parents=True, exist_ok=True)
            (directory / (self._testMethodName + '.json')).write_text(json.dumps({
                'baseline': fixture(), 'perturbed': report, 'rejection': str(error.exception),
                'scope': 'Synthetic host consumer fixture; not physical or codec execution'}, indent=2))

    def test_valid_software_report_never_certifies_physical_camera(self):
        result = validate(fixture(), REV)
        self.assertTrue(result['verifiedOutput']); self.assertTrue(result['publishedOutput']); self.assertFalse(result['physicalCameraCertified'])

    def test_tc_p003_01_physical_or_ownership_certainty_rejected(self):
        for key in ('physicalCameraCertified', 'sourceOwnershipIndependentlyVerified'):
            report = fixture(); report[key] = True
            self.reject('TC-P003-01', report)

    def test_tc_p003_01_unavailable_keeps_narrower_results(self):
        report = fixture()
        start = False
        for row in report['stages']:
            if row['stage'] == 'codec_qualification':
                start = True; row['outcome'] = 'unavailable'; row['checks'][0]['outcome'] = 'unavailable'
                set_facts(report, row['stage'], {'reason': 'No P010 backend', 'exception': 'DevelopmentUnavailable'})
            elif start and row['stage'] != 'physical_qualification':
                report['observations'].pop(row['evidenceRef']); row.update(outcome='not_run', checks=[], evidenceRef=None, evidenceSha256=None)
        report['classification'].update(verifiedOutput=False, publishedOutput=False)
        result = validate(report)
        self.assertEqual('passed', result['outcomes']['source_validation']); self.assertEqual('unavailable', result['outcomes']['codec_qualification'])
        report['classification']['verifiedOutput'] = True
        self.reject('TC-P003-01', report)

    def test_tc_p003_02_mixed_revision_rejected(self):
        report = fixture(); report['stages'][2]['sourceRevision'] = 'c' * 40
        self.reject('TC-P003-02', report)

    def test_tc_p003_02_other_attempt_output_cannot_be_reused(self):
        report = fixture(); report['attemptId'] = '11234567-1234-5678-1234-0123456789ab'
        self.reject('TC-P003-02', report)

    def test_tc_p003_03_tampered_or_missing_observations_rejected(self):
        report = fixture(); report['observations']['source_validation-observation'] += ' '
        self.reject('TC-P003-03', report)
        report = fixture(); report['stages'][2]['evidenceRef'] = None
        self.reject('TC-P003-03', report)

    def test_tc_p003_03_source_provenance_must_match(self):
        report = fixture(); report['context']['sourceSha256'] = 'c' * 64
        self.reject('TC-P003-03', report)

    def test_tc_p003_04_green_cannot_hide_failed_checks(self):
        report = fixture(); report['stages'][2]['checks'][0]['outcome'] = 'failed'
        self.reject('TC-P003-04', report)

    def test_tc_p003_04_actual_positive_and_negative_results_required(self):
        for key, change in [('positive', {'distinctRampLevels': 220}), ('eightBitNegative', {'fullDecodeVerified': False}),
                            ('eightBitNegative', {'meanCodeError': .1, 'maximumCodeError': 1, 'distinctRampLevels': 800})]:
            report = fixture(); facts = get_facts(report, 'codec_qualification'); facts['qualification'][key].update(change)
            set_facts(report, 'codec_qualification', facts); self.reject('TC-P003-04', report)

    def test_tc_p003_04_partial_decode_rejected(self):
        report = fixture(); facts = get_facts(report, 'decoded_verification'); facts['verification']['decodedFrames'] = 3
        set_facts(report, 'decoded_verification', facts); self.reject('TC-P003-04', report)

    def test_tc_p003_05_units_and_domains_not_interchangeable(self):
        for key, value in [('durationUnit', 'ms'), ('durationDomain', 'display_time')]:
            report = fixture(); facts = get_facts(report, 'source_validation'); facts[key] = value
            set_facts(report, 'source_validation', facts); self.reject('TC-P003-05', report)

    def test_tc_p003_05_nonfinite_and_duplicate_json_rejected(self):
        for payload in ('{"x":1,"x":2}', '{"x":1e999}', '{"x":NaN}'):
            with self.assertRaises(ValueError): decode(payload)

    def test_tc_p003_06_threshold_rewrite_is_rejected(self):
        report = fixture(); report['policy']['frameMeanLimit'] = 40
        self.reject('TC-P003-06', report)
        report = fixture(); facts = get_facts(report, 'decoded_verification'); facts['verification']['meanErrorLimitCodes'] = 40
        set_facts(report, 'decoded_verification', facts); self.reject('TC-P003-06', report)

    def test_tc_p003_07_source_change_is_not_success(self):
        report = fixture(); facts = get_facts(report, 'source_preservation'); facts['sourceAfter'] = 'c' * 64
        set_facts(report, 'source_preservation', facts); self.reject('TC-P003-07', report)

    def test_tc_p003_08_fresh_cli_is_read_only_and_missing_reports_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.json'; original = json.dumps(fixture()).encode(); path.write_bytes(original)
            cmd = [sys.executable, '-I', '-B', str(ROOT / 'scripts/check_development_evidence.py'), str(path), '--expected-revision', REV]
            result = subprocess.run(cmd, capture_output=True, timeout=15, env={'HOME': tmp})
            self.assertEqual(0, result.returncode, result.stdout); self.assertEqual(original, path.read_bytes())
            path.unlink(); result = subprocess.run(cmd, capture_output=True, timeout=15, env={'HOME': tmp})
            self.assertEqual(1, result.returncode); self.assertIn(b'failed', result.stdout)

    def test_tc_p003_03_malformed_check_objects_fail_cleanly(self):
        for checks in ([None], ['passed'], [{'id': [], 'reason': 'bad', 'outcome': 'passed'}]):
            report = fixture(); report['stages'][2]['checks'] = checks
            self.reject('TC-P003-03', report)

    def test_incomplete_checkpoint_is_not_verified_output(self):
        report = fixture(); report['closed'] = False
        report['classification'].update(verifiedOutput=False, publishedOutput=False)
        self.assertFalse(validate(report)['verifiedOutput'])
        report['classification']['verifiedOutput'] = True; self.reject('TC-P003-04', report)

    def test_duplicate_stages_and_hidden_observations_are_rejected(self):
        report = fixture(); report['stages'].append(deepcopy(report['stages'][0])); self.reject('TC-P003-04', report)
        report = fixture(); report['observations']['unused'] = '{}'; self.reject('TC-P003-04', report)


if __name__ == '__main__':
    unittest.main()
