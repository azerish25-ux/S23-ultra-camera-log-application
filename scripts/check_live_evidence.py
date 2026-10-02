#!/usr/bin/env python3
"""P003 independent live-attempt consumer. Full decode is not original-RAW or sensor proof."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_research_contract import decode, identity, require, text

STAGES = ('profile_validation', 'gpu_reference', 'codec_qualification', 'configured', 'matched_raw_frames',
          'encoded_output', 'full_decode', 'publication', 'resource_cleanup', 'source_pixel_comparison', 'physical_qualification')
OUTCOMES = ('failed', 'blocked', 'unavailable', 'not_run', 'inconclusive', 'passed')
POLICY = {'id': 'live-existing-0.9-v1', 'gpuLogErrorLimit': .001, 'gpuP010ErrorLimit': 2, 'gpuLogDomain': 'LogC3_RGB',
          'meanCodeErrorLimit': .75, 'peakCodeErrorLimit': 2, 'minimumRampLevels': 600, 'colourPatchErrorLimit': 12,
          'codeUnit': 'code_value', 'codeDomain': 'decoded_P010', 'durationUnit': 'us',
          'durationDomain': 'relative_sensor_presentation_timestamps', 'timestampToleranceUs': 2,
          'maximumFrames': 18000, 'cadenceToleranceFraction': .03, 'cadenceMinimumSpanNs': 2_000_000_000}


def integer(obj, key, minimum=0):
    require(isinstance(obj, dict) and type(obj.get(key)) is int and obj[key] >= minimum, 'Invalid integer ' + key)
    return obj[key]


def real(obj, key):
    require(isinstance(obj, dict), 'Expected object for ' + key)
    n = obj.get(key)
    require(type(n) in (int, float) and math.isfinite(n) and n >= 0, 'Invalid measurement ' + key)
    return n


def media(value):
    require(isinstance(value, dict) and value.get('algorithm') == 'SHA-256' and identity(value.get('sha256')), 'Invalid media identity')
    integer(value, 'byteCount', 1)


def signal(value, width, height, count, relative=False):
    require(isinstance(value, dict) and value.get('fullDecodeVerified') is True, 'Full decode not observed')
    require(text(value.get('decoder')) and value.get('mime') == 'video/hevc', 'Missing decoder/signal provenance')
    for key, expected in [('width', width), ('height', height), ('decodedFrames', count), ('lumaBitDepth', 10),
                          ('chromaBitDepth', 10), ('colorPrimariesCode', 2), ('transferCharacteristicsCode', 2),
                          ('matrixCoefficientsCode', 1), ('colorRange', 2), ('colorTransfer', 0)]:
        require(integer(value, key) == expected, 'Wrong decoded ' + key)
    require(count >= 2 and value.get('timestampContract') == ('relative_sensor_timestamps' if relative else 'CFR'), 'Wrong timestamp contract')


def ramp(value, width, height, count, degraded):
    signal(value, width, height, count)
    require(value.get('deliberatelyDegraded') is degraded, 'Missing precision-fixture lineage')
    mean, peak = real(value, 'meanCodeError'), real(value, 'maximumCodeError')
    levels, colour = integer(value, 'distinctRampLevels', 1), integer(value, 'colourPatchPeakCodeError')
    require(levels <= 877, 'Impossible ramp level count')
    passed = mean <= .75 and peak <= 2 and levels >= 600 and colour <= 12
    require(value.get('passed') is passed, 'Ramp aggregate contradicts measurements')
    return passed


def backend(value, context, outcome):
    require(isinstance(value, dict) and value.get('kind') == 'live-log-backend-probe', 'Missing raw backend probe')
    request = context['requested']
    for key in ('width', 'height', 'fps'):
        require(integer(value, key, 1) == request[key], 'Backend configuration mismatch: ' + key)
    require(value.get('syntheticInputs') is True and value.get('sensorPrecisionMeasured') is False and
            value.get('hlgTransferRequested') is False, 'Backend fixture misrepresented as sensor/HLG proof')
    routes = value.get('routes')
    require(isinstance(routes, list) and all(isinstance(r, dict) for r in routes), 'Missing route observations')
    accepted = [r for r in routes if r.get('status') == 'qualified']
    if outcome == 'passed':
        require(value.get('status') == 'qualified' and len(accepted) == 1, 'No unique qualified backend')
        r = accepted[0]
        require(text(r.get('codec')) and r['codec'] == value.get('selectedCodec') and r.get('input') in ('P010_IMAGE', 'RGB10_SURFACE') and
                r['input'] == value.get('selectedInput'), 'Selected backend differs from qualified route')
        require(ramp(r.get('positive'), 1024, 128, 4, False), 'Positive precision failed')
        require(not ramp(r.get('eightBitNegative'), 1024, 128, 4, True), 'Eight-bit negative incorrectly passed')
        require(ramp(r.get('selectedSize'), request['width'], request['height'], 2, False), 'Selected-size precision failed')
        require(all(real(r[name],'measuredFps') == request['fps'] for name in ('positive','eightBitNegative','selectedSize')), 'Qualification cadence differs from selected request')
        require(context.get('selectedBackend') == {'codec': r['codec'], 'input': r['input']}, 'Selected route context mismatch')
    else:
        require(value.get('status') == ('unavailable' if outcome == 'unavailable' else 'query_failed'), 'Backend outcome contradiction')
        require(not accepted and value.get('selectedCodec') is None and value.get('selectedInput') is None and
                context.get('selectedBackend') is None, 'Unavailable backend contains a qualified route')


def facts(stage, outcome, f, context, kind, attempt):
    require(isinstance(f, dict), 'Malformed raw observation')
    if stage == 'codec_qualification' and 'report' in f and outcome in ('passed', 'unavailable', 'inconclusive'):
        backend(f['report'], context, outcome)
    if outcome != 'passed':
        return
    request = context['requested']
    if kind == 'backend_test':
        require(stage in ('gpu_reference', 'codec_qualification'), 'Backend-only result cannot supply camera evidence')
    if stage == 'profile_validation':
        require(kind == 'camera_session', 'No profile in backend-only test')
        profile = decode(context['profilePayload'].encode())
        binding = f.get('sourceBinding')
        require(isinstance(binding, dict) and binding == profile.get('source') == context.get('sourceBinding'), 'Profile/source binding mismatch')
        require(set(binding) == {'fingerprint', 'logicalCamera', 'physicalCamera', 'width', 'height', 'cfa'}, 'Incomplete source layout')
        require(binding['fingerprint'] == context['device']['fingerprint'] and text(binding['logicalCamera']) and
                (binding['physicalCamera'] is None or text(binding['physicalCamera'])), 'Wrong device or camera route')
        require(integer(binding, 'cfa') <= 3 and integer(binding, 'width', 1) * integer(binding, 'height', 1) <= 16_000_000, 'Invalid RAW layout')
        calibration = profile.get('calibration', {})
        require(calibration.get('status') in ('measured', 'provisional') and text(calibration.get('evidence')) and text(calibration.get('illuminant')),
                'Missing profile provenance or synthetic profile presented as camera data')
        require(calibration['status'] != 'provisional' or request['allowProvisional'] is True, 'Missing provisional consent')
        require(f.get('routeAndLayoutMatched') is True and f.get('requestedControlsApplicable') is True and
                f.get('calibrationIndependentlyVerified') is False, 'Profile checks/calibration boundary missing')
        crop = request['sourceCrop']
        require(crop[0] + crop[2] <= binding['width'] and crop[1] + crop[3] <= binding['height'], 'Crop exceeds source')
    elif stage == 'gpu_reference':
        r = f.get('report', {})
        require(r.get('status') == 'passed' and r.get('synthetic') is True and r.get('sensorPrecisionMeasured') is False, 'GPU evidence boundary missing')
        require(integer(r, 'bayerReductionCases') == 12 and real(r, 'maximumLogRgbError') <= .001 and
                integer(r, 'maximumP010CodeError') <= 2, 'GPU reference comparison failed')
    elif stage == 'codec_qualification':
        require('report' in f, 'Missing backend facts')
    elif stage == 'configured':
        require(f.get('cameraSessionCallback') is True and f.get('repeatingRequestSubmitted') is True and
                isinstance(context.get('sourceBinding'), dict) and f.get('sourceBinding') == context['sourceBinding'], 'No matched camera callback')
    elif stage == 'matched_raw_frames':
        require(integer(f, 'imagesReceived') >= integer(f, 'matchedFrames') >= integer(f, 'processedFrames', 1), 'Invalid RAW frame accounting')
        require(f.get('exactSensorTimestampPairing') is True and f.get('profileExposureAndFocusChecked') is True and
                f.get('sourcePixelsStored') is False, 'RAW-source checks or retention boundary missing')
    elif stage == 'encoded_output':
        r = f.get('encoding', {})
        require(integer(r, 'encodedFrames', 2) == integer(f, 'framesSubmitted', 2) <= 18000, 'Encoded/submitted frame mismatch')
        selected = context.get('selectedBackend', {})
        require(text(r.get('codec')) and r['codec'] == selected.get('codec') and r.get('input') == selected.get('input'), 'Encoded route mismatch')
        require(r.get('hlgTransferUsed') is False and r.get('pictureNalsUnchangedByMetadataRewrite') is True and
                r.get('timestampMapping') == 'sensor_delta_ns_divided_by_1000' and r.get('audio') == 'none', 'Encoded signal/source contract changed')
    elif stage == 'full_decode':
        pts = f.get('sensorPresentationTimesUs')
        require(isinstance(pts, list) and 2 <= len(pts) <= 18000 and all(type(n) is int for n in pts) and pts[0] == 0 and
                all(a < b for a, b in zip(pts, pts[1:])), 'Invalid relative sensor timestamp index')
        require(f.get('durationUnit') == 'us' and f.get('durationDomain') == 'relative_sensor_presentation_timestamps' and
                integer(f, 'timestampSpanUs', 1) == pts[-1], 'Timestamp units/domain/span mismatch')
        r = f.get('verification', {})
        signal(r, request['width'], request['height'], len(pts), relative=True)
        require(r.get('pixelSourceComparison') is False and r.get('physicalCameraCertified') is False, 'Full decode is not source/physical proof')
        require(math.isclose(real(r, 'measuredFps'), (len(pts)-1)*1e6/pts[-1], rel_tol=1e-9), 'Decoded cadence contradicts timestamps')
        require(f.get('partialName') == f'live-{attempt}.partial.mp4', 'Output belongs to another attempt')
        media(f.get('mediaIdentity'))
    elif stage == 'publication':
        require(f.get('renameSucceeded') is True and f.get('publishedName') == f'live-{attempt}.mp4', 'Publication failed or belongs to another attempt')
        media(f.get('mediaIdentity'))
    elif stage == 'resource_cleanup':
        require(f.get('scope') == 'application_owner_close_acknowledgments' and all(f.get(k) is True for k in
                ('cameraCloseAcknowledged', 'previewCleanupConfirmed', 'gpuCloseReturned', 'eglCloseReturned', 'encoderCloseReturned')),
                'Cleanup acknowledgments incomplete')
    else:
        raise ValueError('No independent source/physical protocol for ' + stage)


def validate(value, expected_revision):
    require(isinstance(value, dict) and type(value.get('schemaVersion')) is int and value['schemaVersion'] == 1 and
            value.get('kind') == 'live-attempt-evidence', 'Unknown live-attempt schema')
    require(identity(expected_revision, 40) and value.get('sourceRevision') == expected_revision, 'Wrong source revision')
    kind, attempt = value.get('attemptKind'), value.get('attemptId')
    require(kind in ('backend_test', 'camera_session') and isinstance(attempt, str) and re.fullmatch('[0-9a-f-]{36}', attempt), 'Missing attempt kind/identity')
    closed, recording = value.get('closed'), value.get('recordingRequested')
    require(type(closed) is bool and type(recording) is bool and not (kind == 'backend_test' and recording), 'Invalid attempt lifecycle')
    require(text(value.get('startedAt')) and (text(value.get('endedAt')) if closed else value.get('endedAt') is None), 'Completion timestamp mismatch')
    require(value.get('activeStage') in ((None,) if closed else (*STAGES, None)), 'Invalid active-stage checkpoint')
    require(all(value.get(k) is False for k in ('sourcePixelsStored', 'pixelSourceComparison', 'physicalCameraCertified')), 'Unsupported source/physical claim')
    require(value.get('policy') == POLICY and all(type(value['policy'][k]) is type(v) for k, v in POLICY.items()), 'Changed numerical policy/units')
    context = value.get('context'); require(isinstance(context, dict), 'Missing context')
    device, request = context.get('device'), context.get('requested')
    require(isinstance(device, dict) and device.get('appCommit') == expected_revision and text(device.get('fingerprint')), 'Missing device/revision provenance')
    require(isinstance(request, dict) and integer(request, 'width', 1) % 2 == 0 and integer(request, 'height', 1) % 2 == 0 and
            integer(request, 'fps', 1) in (24,30), 'Invalid requested geometry/cadence')
    if kind == 'backend_test':
        require(context.get('profilePayload') is None and context.get('profileSha256') is None and context.get('sourceBinding') is None, 'Backend test invented camera provenance')
    else:
        payload = context.get('profilePayload')
        require(isinstance(payload, str) and len(payload.encode()) <= 1_048_576 and
                hashlib.sha256(payload.encode()).hexdigest() == context.get('profileSha256'), 'Missing/tampered profile identity')
        require(isinstance(decode(payload.encode()), dict), 'Malformed profile payload')
        require(all(type(request.get(k)) is bool for k in ('allowProvisional','allowClipping')), 'Missing consent choice')
        crop = request.get('sourceCrop'); divisor = request.get('divisor')
        require(isinstance(crop, list) and len(crop) == 4 and all(type(v) is int and v >= 0 and v % 2 == 0 for v in crop) and
                type(divisor) is int and divisor in (1,2,4) and crop[2] == request['width']*divisor and crop[3] == request['height']*divisor,
                'Changed crop/reduction contract')
        real(request, 'focusDiopters')
    for k in ('errors','reportErrors'):
        require(isinstance(value.get(k), list) and all(text(v) for v in value[k]), 'Malformed error record')
    require(value.get('persistenceError') is None or text(value['persistenceError']), 'Malformed persistence error')
    rows, observations = value.get('stages'), value.get('observations')
    require(isinstance(rows, list) and len(rows) == len(STAGES) and all(isinstance(r, dict) for r in rows) and
            {r.get('stage') for r in rows} == set(STAGES) and isinstance(observations, dict), 'Missing/duplicate stages or observations')
    outcomes, underlying, used = {}, {}, set()
    for r in rows:
        stage, outcome, checks = r['stage'], r.get('outcome'), r.get('checks')
        require(r.get('sourceRevision') == expected_revision and outcome in OUTCOMES and text(r.get('reason')), 'Stale or invalid stage')
        require(isinstance(checks,list) and all(isinstance(c,dict) and text(c.get('id')) and text(c.get('reason')) and
                c.get('outcome') in OUTCOMES for c in checks) and len({c['id'] for c in checks}) == len(checks), 'Invalid individual checks')
        actual = next((o for o in OUTCOMES if any(c['outcome'] == o for c in checks)), 'not_run')
        require(actual == outcome, 'Green aggregate contradicts individual outcomes')
        if outcome == 'not_run':
            require(not checks and r.get('evidenceRef') is None and r.get('evidenceSha256') is None, 'Unrun stage has invented evidence')
        else:
            ref = r.get('evidenceRef'); payload = observations.get(ref)
            require(ref == stage+'-observation' and isinstance(payload, str) and hashlib.sha256(payload.encode()).hexdigest() ==
                    r.get('evidenceSha256'), 'Missing or tampered observation identity')
            raw = decode(payload.encode()); used.add(ref)
            require(isinstance(raw,dict) and raw.get('sourceRevision') == expected_revision and raw.get('attemptId') == attempt and
                    raw.get('stage') == stage, 'Observation belongs to another revision/attempt/stage')
            underlying[stage] = raw.get('facts')
            facts(stage,outcome,underlying[stage],context,kind,attempt)
        require(stage not in ('physical_qualification','source_pixel_comparison') or outcome == 'not_run', 'Independent physical/source gate was fabricated')
        require(kind != 'backend_test' or stage in ('gpu_reference','codec_qualification') or outcome == 'not_run', 'Backend-only test inherited camera stage')
        outcomes[stage] = outcome
    require(used == set(observations), 'Hidden/unreferenced observations')
    if outcomes['full_decode'] == outcomes['encoded_output'] == 'passed':
        require(len(underlying['full_decode']['sensorPresentationTimesUs']) == underlying['encoded_output']['framesSubmitted'], 'Encoded/decoded frame count mismatch')
    if outcomes['publication'] == 'passed':
        require(outcomes['full_decode'] == 'passed' and underlying['publication']['mediaIdentity'] == underlying['full_decode']['mediaIdentity'], 'Published identity differs from decoded movie')
    is_backend = closed and all(outcomes[k] == 'passed' for k in ('gpu_reference','codec_qualification'))
    camera = closed and kind == 'camera_session' and all(outcomes[k] == 'passed' for k in ('profile_validation','configured','matched_raw_frames'))
    decoded = closed and kind == 'camera_session' and recording and outcomes['full_decode'] == 'passed'
    published = decoded and outcomes['publication'] == 'passed'
    succeeded = published and is_backend and camera and all(outcomes[k] == 'passed' for k in ('encoded_output','resource_cleanup')) and not value['errors']
    verdict = {'backendQualified':is_backend,'cameraFramesObserved':camera,'outputDecoded':decoded,'publishedOutput':published,
               'recordingSucceeded':succeeded,'previewOnly':camera and not recording,'pixelSourceComparison':False,'physicalCameraCertified':False,'issues':[]}
    require(isinstance(value.get('classification'),dict) and all(type(value['classification'].get(k)) is bool for k in verdict if k!='issues') and
            value['classification'] == verdict, 'Producer classification differs from independent result')
    return {'attemptId':attempt,'attemptKind':kind,'sourceRevision':expected_revision,'closed':closed,'outcomes':outcomes, **verdict}


def archive_reports(path, expected_revision, require_integration=False):
    reports, legacy, receipts, publication_controls, size = [], [], [], [], 0
    with tarfile.open(path) as archive:
        members=archive.getmembers()
        require(len(members)<=10000 and len({m.name for m in members})==len(members), 'Duplicate/excessive archive members')
        for m in members:
            p=PurePosixPath(m.name)
            require(not p.is_absolute() and '..' not in p.parts and not m.issym() and not m.islnk(), 'Unsafe archive path')
            if not m.name.endswith('.json') or not m.name.startswith(('files/exports/live-evidence/','files/exports/live-log/')):
                continue
            require(m.isfile() and 0<m.size<=4*1024*1024, 'Invalid live report file')
            size+=m.size; require(size<=256*1024*1024, 'Live report batch exceeds 256 MiB')
            raw=decode(archive.extractfile(m).read());require(isinstance(raw,dict), 'Malformed live JSON')
            if raw.get('kind')=='live-attempt-evidence':
                require(len(reports)<1024, 'Too many live reports')
                reports.append(validate(raw,expected_revision))
            elif raw.get('kind') == 'live-attempt-integration-test':
                receipts.append(raw)
            elif raw.get('kind') == 'live-publication-file-test':
                publication_controls.append(raw)
            elif raw.get('attemptId') is not None:
                legacy.append(raw)
    require(reports, 'No production live attempts were exported')
    by_id={r['attemptId']:r for r in reports};require(len(by_id)==len(reports), 'Repeated live attempt identity')
    for old in legacy:
        attempt=old['attemptId'];require(attempt in by_id and old.get('attemptReport')==f'live-attempt-{attempt}.json', 'Unpaired legacy live report')
        if old.get('kind')=='live-raw-logc3' and old.get('status')=='container_checked':
            require(by_id[attempt]['publishedOutput'], 'Legacy saved flag contradicts publication evidence')
    if require_integration:
        require(legacy, 'Missing original live sidecar exports')
        cases={r.get('case'):r for r in receipts}
        require(len(cases)==len(receipts) and set(cases)=={'default-backend','cancelled','io-failure','synthetic-profile','stale-profile'},
                'Missing or repeated actual-worker integration cases')
        for case, receipt in cases.items():
            require(receipt.get('appCommit')==expected_revision and receipt.get('status')=='passed' and
                    receipt.get('physicalCameraTested') is False, 'Invalid integration identity/scope')
            require(receipt.get('attemptId') in by_id, 'Integration case has no matching exported attempt')
            result=by_id[receipt['attemptId']]
            require(result['closed'], 'Unfinished worker integration')
            if case=='default-backend':
                require(receipt.get('defaultBackendInvoked') is True and receipt.get('faultInjected') is False and
                        result['attemptKind']=='backend_test' and result['outcomes']['gpu_reference']=='passed' and
                        result['outcomes']['codec_qualification'] in ('passed','unavailable','inconclusive'), 'Missing actual default backend attempt')
            else:
                require(receipt.get('faultInjected') is True and receipt.get('defaultBackendInvoked') is False,
                        'Injected negative control misrepresented as actual backend')
                if case in ('cancelled','io-failure'):
                    require(result['attemptKind']=='backend_test' and result['outcomes']['gpu_reference']==('blocked' if case=='cancelled' else 'failed') and
                            result['outcomes']['codec_qualification']=='not_run', 'Fault outcome or unrun backend was relabelled')
                else:
                    require(result['attemptKind']=='camera_session' and result['outcomes']['profile_validation']=='failed' and
                            result['outcomes']['configured']=='not_run' and result['outcomes']['gpu_reference']=='not_run', 'Invalid profile control opened a camera or fabricated a pass')
        require(len(publication_controls)==1, 'Missing publication failure/collision exercise')
        control=publication_controls[0]
        require(control.get('appCommit')==expected_revision and control.get('status')=='passed' and
                all(control.get(k) is True for k in ('sourceBytesPreserved','existingDestinationPreserved','failedRenameNotPublished')) and
                control.get('validVideoTested') is False and control.get('physicalCameraTested') is False, 'Publication file control was weakened or overclaimed')
    return {'status':'passed','reports':reports,'scope':'Live report consistency; camera/physical/RAW comparisons remain separate', 'physicalCameraCertified':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('path',type=Path);p.add_argument('--expected-revision',required=True)
    p.add_argument('--require-integration',action='store_true');a=p.parse_args()
    try:
        if a.path.suffix=='.json':
            require(a.path.is_file() and not a.path.is_symlink() and a.path.stat().st_size<=4*1024*1024,'Invalid report file')
            result=validate(decode(a.path.read_bytes()),a.expected_revision)
        else: result=archive_reports(a.path,a.expected_revision,a.require_integration)
        print(json.dumps(result,indent=2,allow_nan=False));return 0
    except (ValueError,KeyError,TypeError,OSError,tarfile.TarError) as e:
        print(json.dumps({'status':'failed','reason':str(e)}));return 1

if __name__=='__main__':
    raise SystemExit(main())
