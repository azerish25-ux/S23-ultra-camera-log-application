"""P003 independent consumer fixtures: these are report mutations, not simulated phone certification."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_recording_evidence as c

REV = 'a'*40
ATTEMPT = '12345678-1234-1234-1234-123456789abc'
MEDIA = {'algorithm': 'SHA-256', 'sha256': 'b'*64, 'byteCount': 3000}

def sample(channels=0, width=1920, height=1080):
    context = {'device': {'appCommit': REV, 'fingerprint': 'authored-host-fixture'},
        'selectedMode': {'key': 'fixture', 'width': width, 'height': height, 'fps': 30, 'bitrate': 8000000,
                         'encoder': 'authored-codec', 'mime': 'video/avc', 'dynamicRange': 'SDR'},
        'requested': {'logicalCamera': '0', 'physicalCamera': None}, 'audioMode': ('OFF','MONO','STEREO')[channels], 'audioChannels': channels}
    verification = {'mime': 'video/avc', 'width': width, 'height': height, 'requestedFps': 30, 'samples': 31,
        'encodedBytes': 3000, 'sampleSpanUs': 1000000, 'firstSyncFrameDecoded': True,
        'mediaIdentity': MEDIA, 'audioRequested': channels>0, 'audioTrackCount': int(channels>0),
        'nominalFpsIsNotSustainedRateProof': True, 'cadenceWarningPreservesFootage': True,
        'cadenceToleranceFraction': .03, 'cadenceMinimumSpanUs': 2000000}
    if channels:
        verification.update(firstAudioPcmDecoded=True, audio={'mime': 'audio/mp4a-latm', 'profile': 'AAC-LC',
            'channels': channels, 'sampleRate': 48000, 'samples': 47})
    payloads = {
        'advertised': {'plan': {'kind':'recording-mode-plan','evidence':'advertised_only','reportId':'authored','generatedAt':'2026-10-02',
            'device':context['device'],'logicalCamera':'0','physicalCamera':None,'plan':{'candidates':[context['selectedMode']]}}},
        'preparation': {'surfaceInputCreated':True,'encoderStarted':True,'encoder':'authored-codec','audioChannels':channels},
        'configured': {'cameraSessionCallback':True,'repeatingRequestSubmitted':True},
        'encoded_output': {'receivedSamples':31,'writtenSamples':31,'sampleSpanUs':1000000,
                           'durationUnit':'us','durationDomain':c.POLICY['durationDomain']},
        'output_validation': {'verification':verification,'durationUnit':'us','durationDomain':c.POLICY['durationDomain'],'decodeScope':c.POLICY['decodeScope']},
        'publication': {'uri':'content://fixture/output','mediaIdentity':MEDIA}}
    if channels: payloads['audio_samples']={'writtenSamples':47,'channels':channels,'sampleRate':48000}
    result={'schemaVersion':1,'kind':'ordinary-recording-evidence','attemptId':ATTEMPT,'sourceRevision':REV,
        'startedAt':'2026-10-02T12:00:00Z','endedAt':'2026-10-02T12:01:00Z','closed':True,'context':context,
        'policy':copy.deepcopy(c.POLICY),'captureErrors':[],'reportErrors':[],'persistenceError':None,
        'physicalCameraCertified':False,'customLog':False,'stages':[], 'observations':{},
        'classification':{'outputChecked':True,'publishedOutput':True,'recordingSucceeded':True,'retainedForRecovery':False,
                          'fullDecodeVerified':False,'physicalCameraCertified':False,'issues':[]}}
    for s in c.STAGES:
        run=s in payloads;ref=s+'-observation';payload=json.dumps({'attemptId':ATTEMPT,'sourceRevision':REV,'stage':s,'facts':payloads.get(s,{})})
        result['stages'].append({'stage':s,'outcome':'passed' if run else 'not_run','reason':'Authored fixture',
            'sourceRevision':REV,'evidenceRef':ref if run else None,
            'evidenceSha256':hashlib.sha256(payload.encode()).hexdigest() if run else None,
            'checks':[{'id':'observed-operation','outcome':'passed','reason':'Authored fixture'}] if run else []})
        if run:result['observations'][ref]=payload
    return copy.deepcopy(result)


def alter(value,stage,operation):
    row=next(r for r in value['stages'] if r['stage']==stage)
    raw=json.loads(value['observations'][row['evidenceRef']]);operation(raw)
    payload=json.dumps(raw);value['observations'][row['evidenceRef']]=payload;row['evidenceSha256']=hashlib.sha256(payload.encode()).hexdigest()


def unrun(value,stage):
    row=next(r for r in value['stages'] if r['stage']==stage)
    value['observations'].pop(row['evidenceRef'],None)
    row.update(outcome='not_run',evidenceRef=None,evidenceSha256=None,checks=[])


class RecordingEvidenceTests(unittest.TestCase):
    def setUp(self):self.value=sample()
    def rejected(self,case):
        with self.assertRaises((ValueError,KeyError,TypeError)) as raised:c.validate(self.value,REV)
        target=os.environ.get('S23_RECORDING_EVIDENCE_DIR')
        if target:
            p=Path(target)/case;p.mkdir(parents=True,exist_ok=True)
            (p/(self._testMethodName+'.json')).write_text(json.dumps({'input':self.value,'rejection':str(raised.exception)},indent=2))
    def test_positive_video_and_audio_are_not_full_decode_or_physical(self):
        for n in range(3):
            result=c.validate(sample(n),REV);self.assertTrue(result['recordingSucceeded']);self.assertFalse(result['fullDecodeVerified']);self.assertFalse(result['physicalCameraCertified'])
    def test_tc_p003_01_8k_configured_without_footage(self):
        self.value=sample(width=7680,height=4320)
        for s in ('encoded_output','output_validation','publication'):unrun(self.value,s)
        self.value['classification'].update(outputChecked=False,publishedOutput=False,recordingSucceeded=False)
        result=c.validate(self.value,REV);self.assertEqual('passed',result['outcomes']['advertised']);self.assertFalse(result['recordingSucceeded'])
        self.value['classification']['physicalCameraCertified']=True;self.rejected('TC-P003-01')
    def test_tc_p003_01_sample_decode_cannot_be_full_decode(self):
        self.value['classification']['fullDecodeVerified']=True;self.rejected('TC-P003-01')
    def test_tc_p003_02_mixed_revision(self):
        self.value['stages'][2]['sourceRevision']='f'*40;self.rejected('TC-P003-02')
    def test_tc_p003_02_other_attempt_receipt(self):
        alter(self.value,'configured',lambda r:r.update(attemptId='b'*36));self.rejected('TC-P003-02')
    def test_tc_p003_02_selected_mode_changed(self):
        self.value['context']['selectedMode']['width']=7680;self.rejected('TC-P003-02')
    def test_tc_p003_03_missing_or_tampered_observation(self):
        self.value['observations']['configured-observation']+=' ';self.rejected('TC-P003-03')
    def test_tc_p003_03_missing_device_context(self):
        self.value['context']['device'].pop('fingerprint');self.rejected('TC-P003-03')
    def test_tc_p003_04_green_summary_cannot_override_failure(self):
        self.value['stages'][2]['checks'][0]['outcome']='failed';self.rejected('TC-P003-04')
    def test_tc_p003_04_requested_audio_cannot_disappear(self):
        self.value=sample(2);alter(self.value,'output_validation',lambda r:r['facts']['verification'].update(audioTrackCount=0));self.rejected('TC-P003-04')
    def test_tc_p003_04_boolean_counts_are_not_samples(self):
        alter(self.value,'encoded_output',lambda r:r['facts'].update(writtenSamples=True));self.rejected('TC-P003-04')
    def test_tc_p003_04_source_report_and_written_count_must_agree(self):
        alter(self.value,'encoded_output',lambda r:r['facts'].update(writtenSamples=2));self.rejected('TC-P003-04')
    def test_tc_p003_04_hidden_evidence_and_duplicate_stages(self):
        self.value['observations']['hidden']='{}';self.rejected('TC-P003-04')
        self.value=sample();self.value['stages'].append(self.value['stages'][0]);self.rejected('TC-P003-04')
    def test_tc_p003_05_wrong_duration_domain(self):
        alter(self.value,'encoded_output',lambda r:r['facts'].update(durationUnit='ms'));self.rejected('TC-P003-05')
    def test_tc_p003_06_threshold_change(self):
        alter(self.value,'output_validation',lambda r:r['facts']['verification'].update(cadenceToleranceFraction=.5));self.rejected('TC-P003-06')
    def test_tc_p003_06_policy_revision_is_explicit(self):
        self.value['policy']['id']='relaxed';self.rejected('TC-P003-06')
    def test_tc_p003_07_report_is_read_only(self):
        before=copy.deepcopy(self.value);c.validate(self.value,REV);self.assertEqual(before,self.value)
    def test_tc_p003_07_publication_identity_must_match_verified_file(self):
        alter(self.value,'publication',lambda r:r['facts']['mediaIdentity'].update(sha256='f'*64));self.rejected('TC-P003-07')
    def test_report_failure_does_not_revoke_observed_output(self):
        self.value['reportErrors']=['sidecar directory unavailable'];self.value['persistenceError']='previous checkpoint failed'
        self.assertTrue(c.validate(self.value,REV)['recordingSucceeded'])
    def test_capture_failure_retains_narrower_output_check(self):
        self.value['captureErrors']=['Requested audio interrupted'];self.value['classification']['recordingSucceeded']=False
        self.assertTrue(c.validate(self.value,REV)['outputChecked'])
    def test_incomplete_checkpoint_is_not_completed_recording(self):
        self.value['closed']=False;self.value['endedAt']=None
        self.value['classification'].update(outputChecked=False,publishedOutput=False,recordingSucceeded=False)
        self.assertFalse(c.validate(self.value,REV)['recordingSucceeded'])
    def test_tc_p003_08_fresh_cli_and_missing_prerequisite(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'attempt.json';p.write_text(json.dumps(self.value));script=Path(c.__file__)
            command=[sys.executable,'-I',str(script),str(p),'--expected-revision',REV]
            result=subprocess.run(command,capture_output=True,text=True,env={'HOME':t},timeout=10)
            self.assertEqual(0,result.returncode,result.stdout+result.stderr)
            p.unlink();result=subprocess.run(command,capture_output=True,text=True,env={'HOME':t},timeout=10)
            self.assertEqual(1,result.returncode);self.assertIn('No such file',result.stdout)
    def test_capability_keeps_failed_and_unsupported_fields(self):
        p={'schemaVersion':2,'evidence':'advertised_only','sourceRevision':REV,'deviceBuild':'fixture','reportId':'fixture',
           'queryErrors':1,'sections':[{'fields':{'raw':{'status':'unsupported','value':None,'detail':'not supported'},
                                               'lens':{'status':'query_failed','value':None,'detail':'failed'}}}],
           'stageEvidence':{'schemaVersion':1,'stage':'advertised','outcome':'inconclusive','scope':'fixture','recordingVerified':False,'physicalCameraCertified':False}}
        self.assertEqual(1,c.probe(p,REV)['queryErrors'])
        p['queryErrors']=0
        with self.assertRaises(ValueError):c.probe(p,REV)
        # Existing StreamDiagnostics also retains individual timing-query errors.
        for key in ('minFrameDurationError', 'stallDurationError', 'queryError'):
            q = copy.deepcopy(p)
            q['queryErrors'] = 2
            q['sections'][0]['fields']['stream'] = {'status': 'reported', 'detail': None,
                'value': [{'status': 'reported', key: 'retained framework exception'}]}
            self.assertEqual(2, c.probe(q, REV)['queryErrors'])
            q['sections'][0]['fields']['stream']['value'][0][key] = None
            q['queryErrors'] = 1
            self.assertEqual(1, c.probe(q, REV)['queryErrors'])

class StrictReportTypes(unittest.TestCase):
    def test_malformed_roots_and_contexts_fail_closed(self):
        for value in (None, [], "not an object", {"schemaVersion": True}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                c.validate(value, REV)
        for key in ('context',):
            for bad in (None, [], 'missing'):
                value = sample(); value[key] = bad
                with self.subTest(key=key, bad=bad), self.assertRaises(ValueError): c.validate(value, REV)
    def test_numeric_booleans_cannot_replace_classification_or_policy(self):
        for key in ('outputChecked', 'recordingSucceeded', 'physicalCameraCertified'):
            value = sample(); value['classification'][key] = int(value['classification'][key])
            with self.subTest(key=key), self.assertRaises(ValueError): c.validate(value, REV)
        value = sample(); value['policy']['cadenceWarningPreservesFootage'] = 1
        with self.assertRaises(ValueError): c.validate(value, REV)

if __name__=='__main__':unittest.main()
