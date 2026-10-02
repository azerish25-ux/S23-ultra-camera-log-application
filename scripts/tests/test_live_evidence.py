"""Authored report fixtures and adversarial controls, never camera or codec measurements."""
import copy
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

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import check_live_evidence as c

REV='a'*40
ID='12345678-1234-1234-1234-123456789abc'
MEDIA={'algorithm':'SHA-256','sha256':'b'*64,'byteCount':1234}


def decoded(w=1920,h=1080,n=2,relative=False):
    return {'fullDecodeVerified':True,'decoder':'authored-decoder','mime':'video/hevc','width':w,'height':h,'decodedFrames':n,
        'lumaBitDepth':10,'chromaBitDepth':10,'colorPrimariesCode':2,'transferCharacteristicsCode':2,'matrixCoefficientsCode':1,
        'colorRange':2,'colorTransfer':0,'timestampContract':'relative_sensor_timestamps' if relative else 'CFR','measuredFps':30.0}


def ramp(w,h,n,degraded=False):
    return {**decoded(w,h,n),'meanCodeError':1.0 if degraded else .1,'maximumCodeError':2.0 if degraded else 1.0,
        'distinctRampLevels':220 if degraded else 800,'colourPatchPeakCodeError':1,'passed':not degraded,'deliberatelyDegraded':degraded}


def backend(width=1920,height=1080):
    return {'kind':'live-log-backend-probe','width':width,'height':height,'fps':30,'syntheticInputs':True,'sensorPrecisionMeasured':False,
        'hlgTransferRequested':False,'status':'qualified','selectedCodec':'authored-codec','selectedInput':'P010_IMAGE','routes':[
        {'status':'qualified','codec':'authored-codec','input':'P010_IMAGE','positive':ramp(1024,128,4),
         'eightBitNegative':ramp(1024,128,4,True),'selectedSize':ramp(width,height,2)}]}


def set_stage(value,stage,facts=None,outcome='passed'):
    rows=value['stages'];row=next((r for r in rows if r['stage']==stage),None)
    if row is None:row={'stage':stage};rows.append(row)
    ref=stage+'-observation'
    row.update(outcome=outcome,reason='Authored fixture for contract tests',sourceRevision=value['sourceRevision'])
    if outcome=='not_run':
        row.update(evidenceRef=None,evidenceSha256=None,checks=[]);value['observations'].pop(ref,None)
    else:
        payload=json.dumps({'attemptId':value['attemptId'],'sourceRevision':value['sourceRevision'],'stage':stage,'facts':facts or {}})
        value['observations'][ref]=payload
        row.update(evidenceRef=ref,evidenceSha256=hashlib.sha256(payload.encode()).hexdigest(),checks=[{'id':'observation','outcome':outcome,'reason':'Authored fixture'}])


def alter(value,stage,operation):
    row=next(r for r in value['stages'] if r['stage']==stage);raw=json.loads(value['observations'][row['evidenceRef']])
    operation(raw['facts']);set_stage(value,stage,raw['facts'],row['outcome'])


def sample(kind='camera_session'):
    binding={'fingerprint':'authored-host-fixture','logicalCamera':'0','physicalCamera':None,'width':1920,'height':1080,'cfa':0}
    payload=json.dumps({'kind':'raw-colour-profile','schemaVersion':1,'source':binding,'calibration':{
        'status':'provisional','evidence':'Authored declared profile provenance; no chart measured','illuminant':'Authored D65 fixture'}})
    context={'device':{'appCommit':REV,'fingerprint':'authored-host-fixture'},'requested':{'width':1920,'height':1080,'fps':30},
        'profilePayload':payload if kind=='camera_session' else None,
        'profileSha256':hashlib.sha256(payload.encode()).hexdigest() if kind=='camera_session' else None,
        'selectedBackend':{'codec':'authored-codec','input':'P010_IMAGE'}}
    if kind=='camera_session':
        context['sourceBinding']=binding
        context['requested'].update(sourceCrop=[0,0,1920,1080],divisor=1,focusDiopters=0.0,allowProvisional=True,allowClipping=False,displayRotationDegrees=0)
    value={'schemaVersion':1,'kind':'live-attempt-evidence','attemptKind':kind,'attemptId':ID,'sourceRevision':REV,
        'startedAt':'2026-10-02T00:00:00Z','endedAt':'2026-10-02T00:00:01Z','closed':True,'activeStage':None,'recordingRequested':kind=='camera_session',
        'context':context,'policy':copy.deepcopy(c.POLICY),'errors':[],'reportErrors':[],'persistenceError':None,
        'sourcePixelsStored':False,'pixelSourceComparison':False,'physicalCameraCertified':False,'stages':[],'observations':{}}
    for s in c.STAGES:set_stage(value,s,outcome='not_run')
    set_stage(value,'gpu_reference',{'report':{'status':'passed','synthetic':True,'sensorPrecisionMeasured':False,
        'bayerReductionCases':12,'maximumLogRgbError':.0001,'maximumP010CodeError':1}})
    set_stage(value,'codec_qualification',{'report':backend()})
    if kind=='camera_session':
        set_stage(value,'profile_validation',{'sourceBinding':binding,'routeAndLayoutMatched':True,'requestedControlsApplicable':True,'calibrationIndependentlyVerified':False})
        set_stage(value,'configured',{'cameraSessionCallback':True,'repeatingRequestSubmitted':True,'sourceBinding':binding})
        set_stage(value,'matched_raw_frames',{'processedFrames':31,'matchedFrames':31,'imagesReceived':31,'exactSensorTimestampPairing':True,
            'profileExposureAndFocusChecked':True,'sourcePixelsStored':False})
        set_stage(value,'encoded_output',{'encoding':{'codec':'authored-codec','input':'P010_IMAGE','encodedFrames':31,'hlgTransferUsed':False,
            'pictureNalsUnchangedByMetadataRewrite':True,'timestampMapping':'sensor_delta_ns_divided_by_1000','audio':'none'},'framesSubmitted':31})
        set_stage(value,'full_decode',{'verification':{**decoded(n=31,relative=True),'pixelSourceComparison':False,'physicalCameraCertified':False},
            'sensorPresentationTimesUs':[i*1000000//30 for i in range(31)],'timestampSpanUs':1000000,'durationUnit':'us',
            'durationDomain':'relative_sensor_presentation_timestamps','partialName':f'live-{ID}.partial.mp4','mediaIdentity':MEDIA})
        set_stage(value,'publication',{'renameSucceeded':True,'publishedName':f'live-{ID}.mp4','mediaIdentity':MEDIA})
        set_stage(value,'resource_cleanup',{'scope':'application_owner_close_acknowledgments',**{k:True for k in
            ['cameraCloseAcknowledged','previewCleanupConfirmed','gpuCloseReturned','eglCloseReturned','encoderCloseReturned']}})
    value['classification']={'backendQualified':True,'cameraFramesObserved':kind=='camera_session','outputDecoded':kind=='camera_session',
        'publishedOutput':kind=='camera_session','recordingSucceeded':kind=='camera_session','previewOnly':False,
        'pixelSourceComparison':False,'physicalCameraCertified':False,'issues':[]}
    return copy.deepcopy(value)


class LiveEvidenceTests(unittest.TestCase):
    def setUp(self):self.value=sample();self.baseline=copy.deepcopy(self.value)
    def reject(self,case,phrase=None):
        with self.assertRaises(ValueError) as caught:c.validate(self.value,REV)
        if phrase:self.assertIn(phrase,str(caught.exception))
        target=os.environ.get('S23_LIVE_EVIDENCE_DIR')
        if target:
            p=Path(target)/case;p.mkdir(parents=True,exist_ok=True)
            (p/(self._testMethodName+'.json')).write_text(json.dumps({'scope':'Authored report mutation, not phone evidence',
                'baseline':self.baseline,'perturbed':self.value,'rejection':str(caught.exception)},indent=2)+'\n')
    def test_complete_software_fixture_does_not_certify_phone(self):
        result=c.validate(self.value,REV);self.assertTrue(result['recordingSucceeded']);self.assertFalse(result['physicalCameraCertified'])
    def test_tc_p003_01_backend_only_cannot_inherit_camera(self):
        self.value=sample('backend_test');self.assertTrue(c.validate(self.value,REV)['backendQualified'])
        self.value['classification']['cameraFramesObserved']=True;self.reject('TC-P003-01')
    def test_tc_p003_01_physical_claim_is_not_decoded_ramp(self):
        self.value['physicalCameraCertified']=True;self.reject('TC-P003-01')
    def test_tc_p003_01_live_does_not_retain_raw_comparison(self):
        self.value['pixelSourceComparison']=True;self.reject('TC-P003-01')
    def test_tc_p003_01_backend_stage_cannot_describe_camera(self):
        self.value=sample('backend_test');set_stage(self.value,'configured',{'cameraSessionCallback':True});self.reject('TC-P003-01')
    def test_tc_p003_02_changed_revision(self):
        self.value['sourceRevision']='c'*40;self.reject('TC-P003-02')
    def test_tc_p003_02_changed_stage_revision(self):
        self.value['stages'][0]['sourceRevision']='c'*40;self.reject('TC-P003-02')
    def test_tc_p003_02_wrong_attempt_file(self):
        alter(self.value,'publication',lambda f:f.update(publishedName='live-other.mp4'));self.reject('TC-P003-02')
    def test_tc_p003_02_changed_backend_geometry(self):
        alter(self.value,'codec_qualification',lambda f:f['report'].update(width=7680));self.reject('TC-P003-02')
    def test_tc_p003_02_backend_observed_cadence_is_bound(self):
        alter(self.value,'codec_qualification',lambda f:f['report']['routes'][0]['positive'].update(measuredFps=24.0));self.reject('TC-P003-02')
    def test_tc_p003_03_missing_profile_provenance(self):
        p=json.loads(self.value['context']['profilePayload']);p['calibration'].pop('evidence');payload=json.dumps(p)
        self.value['context'].update(profilePayload=payload,profileSha256=hashlib.sha256(payload.encode()).hexdigest());self.reject('TC-P003-03')
    def test_tc_p003_03_profile_hash_tampered(self):
        self.value['context']['profileSha256']='0'*64;self.reject('TC-P003-03')
    def test_tc_p003_03_missing_device(self):
        self.value['context']['device'].pop('fingerprint');self.reject('TC-P003-03')
    def test_tc_p003_03_missing_or_tampered_observation(self):
        self.value['observations']['gpu_reference-observation']='{}';self.reject('TC-P003-03')
    def test_tc_p003_03_consent_is_not_implicit(self):
        self.value['context']['requested']['allowProvisional']=False;self.reject('TC-P003-03')
    def test_tc_p003_04_green_summary_does_not_override_failure(self):
        self.value['stages'][0]['checks'][0]['outcome']='failed';self.reject('TC-P003-04')
    def test_tc_p003_04_actual_negative_measurements_required(self):
        alter(self.value,'codec_qualification',lambda f:f['report']['routes'][0]['eightBitNegative'].update(meanCodeError=.1,maximumCodeError=1,distinctRampLevels=800))
        self.reject('TC-P003-04','Ramp aggregate')
    def test_tc_p003_04_colour_patch_failure_cannot_pass(self):
        alter(self.value,'codec_qualification',lambda f:f['report']['routes'][0]['selectedSize'].update(colourPatchPeakCodeError=100))
        self.reject('TC-P003-04')
    def test_tc_p003_04_partial_decode_is_not_complete(self):
        alter(self.value,'full_decode',lambda f:f['verification'].update(decodedFrames=2));self.reject('TC-P003-04')
    def test_tc_p003_04_timestamps_must_be_original_not_duplicate(self):
        alter(self.value,'full_decode',lambda f:f['sensorPresentationTimesUs'].__setitem__(3,0));self.reject('TC-P003-04')
    def test_tc_p003_04_wrong_signal_tags(self):
        alter(self.value,'full_decode',lambda f:f['verification'].update(transferCharacteristicsCode=18));self.reject('TC-P003-04')
    def test_tc_p003_04_requested_mode_cannot_change(self):
        self.value['context']['requested']['width']=1280;self.reject('TC-P003-04')
    def test_tc_p003_04_no_boolean_measurement(self):
        alter(self.value,'matched_raw_frames',lambda f:f.update(processedFrames=True));self.reject('TC-P003-04')
    def test_tc_p003_04_unavailable_keeps_gpu_result(self):
        self.value=sample('backend_test');self.value['context'].pop('selectedBackend')
        r=backend();r.update(status='unavailable',selectedCodec=None,selectedInput=None,routes=[])
        set_stage(self.value,'codec_qualification',{'report':r},'unavailable');self.value['classification']['backendQualified']=False
        result=c.validate(self.value,REV);self.assertEqual('passed',result['outcomes']['gpu_reference']);self.assertFalse(result['recordingSucceeded'])
        r['routes']=[{'status':'qualified'}];set_stage(self.value,'codec_qualification',{'report':r},'unavailable');self.reject('TC-P003-04')
    def test_tc_p003_04_preview_stop_is_not_recorded_take(self):
        self.value['recordingRequested']=False
        for stage in ('encoded_output','full_decode','publication'):set_stage(self.value,stage,outcome='not_run')
        self.value['classification'].update(outputDecoded=False,publishedOutput=False,recordingSucceeded=False,previewOnly=True)
        self.assertTrue(c.validate(self.value,REV)['previewOnly'])
    def test_tc_p003_04_incomplete_checkpoint_never_claims_published(self):
        self.value.update(closed=False,endedAt=None,activeStage='full_decode');self.reject('TC-P003-04')
    def test_tc_p003_05_unit_domain_rejected(self):
        alter(self.value,'full_decode',lambda f:f.update(durationUnit='ms'));self.reject('TC-P003-05')
    def test_tc_p003_05_span_is_not_nominal_duration(self):
        alter(self.value,'full_decode',lambda f:f.update(timestampSpanUs=999999));self.reject('TC-P003-05')
    def test_tc_p003_05_decoded_rate_matches_pts(self):
        alter(self.value,'full_decode',lambda f:f['verification'].update(measuredFps=24));self.reject('TC-P003-05')
    def test_tc_p003_06_threshold_revision(self):
        self.value['policy']['peakCodeErrorLimit']=64;self.reject('TC-P003-06')
    def test_tc_p003_07_failed_rename_preserves_decoded_result(self):
        set_stage(self.value,'publication',{'renameSucceeded':False,'retainedName':f'live-{ID}.partial.mp4','mediaIdentity':MEDIA},'failed')
        self.value['errors']=['Final naming failed'];self.value['classification'].update(publishedOutput=False,recordingSucceeded=False)
        result=c.validate(self.value,REV);self.assertTrue(result['outputDecoded']);self.assertFalse(result['publishedOutput'])
        self.value['classification']['publishedOutput']=True;self.reject('TC-P003-07')
    def test_tc_p003_07_auxiliary_write_failure_does_not_delete_movie(self):
        self.value['reportErrors']=['Library publication failed; verified movie retained']
        self.assertTrue(c.validate(self.value,REV)['publishedOutput'])
    def test_tc_p003_07_publication_identity_must_match(self):
        alter(self.value,'publication',lambda f:f['mediaIdentity'].update(sha256='d'*64));self.reject('TC-P003-07')
    def test_tc_p003_07_hidden_or_duplicate_evidence(self):
        self.value['observations']['hidden']='{}';self.reject('TC-P003-07')
        self.value=copy.deepcopy(self.baseline);self.value['stages'].append(self.value['stages'][0]);self.reject('TC-P003-07')
    def test_tc_p003_08_isolated_consumer_reproduces_and_preserves_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'attempt.json';p.write_text(json.dumps(self.value));before=p.read_bytes()
            result=subprocess.run([sys.executable,'-I',str(Path(c.__file__)),str(p),'--expected-revision',REV],capture_output=True,text=True,timeout=10)
            self.assertEqual(0,result.returncode,result.stdout+result.stderr);self.assertTrue(json.loads(result.stdout)['recordingSucceeded'])
            self.assertEqual(before,p.read_bytes())
    def test_tc_p003_08_empty_archive_cannot_count_unrun_adapter(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'empty.tar'
            with tarfile.open(p,'w'):pass
            with self.assertRaisesRegex(ValueError,'No production'):c.archive_reports(p,REV,True)


class LiveArchiveIntegrationTests(unittest.TestCase):
    def archive(self,path,omit=None,edit=None):
        records={}; ids={}
        for index,name in enumerate(['default-backend','cancelled','io-failure','synthetic-profile','stale-profile']):
            value=sample('camera_session' if 'profile' in name else 'backend_test')
            unique=f'12345678-1234-1234-1234-{index:012d}'
            value=json.loads(json.dumps(value).replace(ID,unique));ids[name]=unique
            for row in value['stages']:
                if row['evidenceRef'] is not None:row['evidenceSha256']=hashlib.sha256(value['observations'][row['evidenceRef']].encode()).hexdigest()
            if name!='default-backend':
                for stage in c.STAGES:set_stage(value,stage,outcome='not_run')
                value['context'].pop('selectedBackend',None);value['recordingRequested']=False
                for key in value['classification']:
                    if key!='issues':value['classification'][key]=False
                target='profile_validation' if 'profile' in name else 'gpu_reference'
                set_stage(value,target,{'exception':'Authored negative control'},'blocked' if name=='cancelled' else 'failed')
            records[f'files/exports/live-evidence/live-attempt-{unique}.json']=value
            if name!=omit:
                receipt={'kind':'live-attempt-integration-test','appCommit':REV,'case':name,'attemptId':unique,
                    'defaultBackendInvoked':name=='default-backend','faultInjected':name!='default-backend','physicalCameraTested':False,'status':'passed'}
                if edit:edit(receipt)
                records[f'files/exports/live-evidence/integration-{name}.json']=receipt
        records['files/exports/live-log/backend.json']={'kind':'live-log-backend-probe','attemptId':ids['default-backend'],
            'attemptReport':f"live-attempt-{ids['default-backend']}.json"}
        records['files/exports/live-evidence/publication-file-test.json']={'kind':'live-publication-file-test','appCommit':REV,
            'status':'passed','sourceBytesPreserved':True,'existingDestinationPreserved':True,'failedRenameNotPublished':True,
            'validVideoTested':False,'physicalCameraTested':False}
        with tarfile.open(path,'w') as tar:
            for name,value in records.items():
                data=json.dumps(value).encode();m=tarfile.TarInfo(name);m.size=len(data);tar.addfile(m,io.BytesIO(data))
    def test_complete_authored_integration_fixture_keeps_faults_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'fixture.tar';self.archive(path)
            result=c.archive_reports(path,REV,True)
            self.assertEqual(5,len(result['reports']));self.assertFalse(result['physicalCameraCertified'])
    def test_missing_actual_backend_receipt_cannot_inherit_synthetic_pass(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'fixture.tar';self.archive(path,omit='default-backend')
            with self.assertRaisesRegex(ValueError,'integration cases'):c.archive_reports(path,REV,True)
    def test_injected_fault_cannot_be_relabelled_default_backend(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'fixture.tar';self.archive(path,edit=lambda r:r.update(faultInjected=False))
            with self.assertRaisesRegex(ValueError,'Injected'):c.archive_reports(path,REV,True)


class CrossAdapterTests(unittest.TestCase):
    def test_ordinary_sample_decode_cannot_be_live_full_decode(self):
        from test_recording_evidence import sample as ordinary
        value=ordinary()
        with self.assertRaisesRegex(ValueError,'schema'):c.validate(value,REV)
    def test_saved_raw_proof_is_not_live_capture(self):
        import test_development_evidence as saved
        value=saved.fixture()
        with self.assertRaisesRegex(ValueError,'schema'):c.validate(value,REV)
    def test_live_cannot_satisfy_saved_raw_pixel_comparison(self):
        import check_development_evidence as saved
        with self.assertRaisesRegex(ValueError,'schema'):saved.validate(sample(),REV)
    def test_8k_advertised_configured_without_frames_is_not_recording(self):
        import check_recording_evidence as ordinary
        from test_recording_evidence import sample as source, unrun
        value=source(width=7680,height=4320)
        for stage in ('encoded_output','output_validation','publication'):unrun(value,stage)
        value['classification'].update(outputChecked=False,publishedOutput=False,recordingSucceeded=False)
        result=ordinary.validate(value,REV)
        self.assertEqual('passed',result['outcomes']['advertised']);self.assertEqual('passed',result['outcomes']['configured'])
        self.assertFalse(result['recordingSucceeded']);self.assertFalse(result['physicalCameraCertified'])

class CrossAdapterAggregateTests(unittest.TestCase):
    def reports(self):
        import check_development_evidence as saved
        import check_recording_evidence as ordinary
        from test_development_evidence import fixture
        from test_recording_evidence import sample as recording_sample
        a=saved.validate(fixture(),REV);b=ordinary.validate(recording_sample(),REV);d=c.validate(sample(),REV)
        # Independent attempt identities from three separately authored fixtures.
        b['attemptId']='bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
        return [a],[b],[d]
    def test_observed_families_stay_distinct(self):
        from check_p003_evidence import compare
        result=compare(*self.reports(),REV)
        self.assertFalse(result['physicalCameraCertified']);self.assertTrue(result['live'][0]['outputDecoded'])
        self.assertFalse(result['ordinary'][0]['fullDecodeVerified']);self.assertFalse(result['live'][0]['pixelSourceComparison'])
    def test_duplicate_attempt_or_mixed_revision_cannot_join(self):
        from check_p003_evidence import compare
        a,b,d=self.reports();b[0]['attemptId']=a[0]['attemptId']
        with self.assertRaisesRegex(ValueError,'identity'):compare(a,b,d,REV)
        a,b,d=self.reports();d[0]['sourceRevision']='f'*40
        with self.assertRaisesRegex(ValueError,'revision'):compare(a,b,d,REV)
    def test_missing_adapter_cannot_count_as_acceptance(self):
        from check_p003_evidence import compare
        a,b,d=self.reports()
        with self.assertRaisesRegex(ValueError,'unrun'):compare(a,b,[],REV)
    def test_full_decode_and_source_claims_cannot_cross_boundaries(self):
        from check_p003_evidence import compare
        for family,key in [(1,'fullDecodeVerified'),(2,'pixelSourceComparison')]:
            rows=self.reports();rows[family][0][key]=True
            with self.assertRaises(ValueError):compare(*rows,REV)

if __name__=='__main__':unittest.main()
