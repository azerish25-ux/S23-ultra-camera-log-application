#!/usr/bin/env python3
"""Independent P003 ordinary-recording/probe consumer. Reads observations, never grants device certification."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_research_contract import decode, fields, identity, require, text

STAGES = ('advertised', 'preparation', 'configured', 'encoded_output', 'audio_samples',
          'output_validation', 'full_decode', 'publication', 'retention', 'physical_qualification')
SEVERITY = ('failed', 'blocked', 'unavailable', 'not_run', 'inconclusive', 'passed')
POLICY = {'id': 'ordinary-recording-existing-0.9-v1', 'durationUnit': 'us',
          'durationDomain': 'muxed_video_presentation_timestamp_span',
          'decodeScope': 'all_packets_and_sample_decode_not_full_decode',
          'cadenceToleranceFraction': .03, 'cadenceMinimumSpanUs': 2_000_000,
          'cadenceWarningPreservesFootage': True}


def integer(obj, key, minimum=None):
    require(isinstance(obj, dict), "Expected an object for " + key)
    v = obj.get(key)
    require(type(v) is int and (minimum is None or v >= minimum), 'Invalid integer ' + key)
    return v


def media(value):
    require(isinstance(value, dict) and value.get('algorithm') == 'SHA-256' and identity(value.get('sha256')), 'Invalid media identity')
    integer(value, 'byteCount', 1)


def strings(values, label):
    require(isinstance(values, list) and all(text(v) for v in values), 'Invalid ' + label)


def probe(value, expected_revision):
    require(isinstance(value, dict) and identity(expected_revision, 40), "Malformed capability report or revision")
    require(type(value.get("schemaVersion")) is int, "Invalid capability schema version")
    require(value.get('schemaVersion') == 2 and value.get('evidence') == 'advertised_only', 'Unknown capability schema/scope')
    require(value.get('sourceRevision') == expected_revision and text(value.get('deviceBuild')) and text(value.get('reportId')), 'Missing capability identity')
    require(isinstance(value.get('sections'), list) and value['sections'], 'Missing capability observations')
    errors = 0
    # This mirrors the *wire states*, not the producer's aggregate count. Nested stream
    # diagnostics explicitly use query_failed/unsupported/not_reported too.
    def count(obj):
        if isinstance(obj, dict):
            return int(obj.get('status') == 'query_failed') + sum(
                int(v is not None) if k in ('minFrameDurationError', 'stallDurationError', 'queryError')
                else count(v) for k, v in obj.items())
        if isinstance(obj, list):
            return sum(map(count, obj))
        return 0
    for section in value['sections']:
        require(isinstance(section, dict) and isinstance(section.get('fields'), dict), 'Missing capability fields')
        for item in section['fields'].values():
            require(isinstance(item, dict), 'Malformed capability field')
            require(item.get('status') in ('reported', 'not_reported', 'unsupported', 'query_failed'), 'Unknown capability field state')
            if item['status'] in ('unsupported', 'query_failed'):
                require(text(item.get('detail')), 'Capability failure needs detail')
        errors += count(section['fields'])
    require(type(value.get('queryErrors')) is int and errors == value['queryErrors'], 'Capability summary hides query failure')
    stage = value.get('stageEvidence', {})
    require(isinstance(stage, dict) and type(stage.get('schemaVersion')) is int, 'Malformed capability stage')
    require(stage.get('schemaVersion') == 1 and stage.get('stage') == 'advertised' and text(stage.get('scope')), 'Missing advertised stage')
    require(stage.get('recordingVerified') is False and stage.get('physicalCameraCertified') is False, 'Advertisement cannot certify a recording')
    require(stage.get('outcome') == ('inconclusive' if errors else 'passed'), 'Capability outcome contradicts queries')
    return {'reportId': value['reportId'], 'queryErrors': errors, 'outcome': stage['outcome'], 'recordingVerified': False}


def facts(stage, value, context):
    mode = context['selectedMode']
    channels = context['audioChannels']
    if stage == 'advertised':
        p = value['plan']
        require(p.get('kind') == 'recording-mode-plan' and p.get('evidence') == 'advertised_only', 'Not capability evidence')
        require(text(p.get('generatedAt')) and text(p.get('reportId')), 'Missing planner provenance')
        require(p['device'] == context['device'] and all(p.get(k) == context['requested'].get(k) for k in ('logicalCamera', 'physicalCamera')), 'Capability route/revision mismatch')
        require(p['plan']['candidates'] == [mode], 'Capability selected mode mismatch')
    elif stage == 'preparation':
        require(value.get('surfaceInputCreated') is True and value.get('encoderStarted') is True, 'Encoder/surface preparation missing')
        require(value.get('encoder') == mode['encoder'] and integer(value, 'audioChannels') == channels, 'Preparation format mismatch')
    elif stage == 'configured':
        require(value.get('cameraSessionCallback') is True and value.get('repeatingRequestSubmitted') is True, 'Session callback not observed')
    elif stage == 'encoded_output':
        require(integer(value, 'receivedSamples', 1) >= integer(value, 'writtenSamples', 1), 'Written count exceeds received count')
        integer(value, 'sampleSpanUs', 0)
        require(all(value.get(k) == POLICY[k] for k in ('durationUnit', 'durationDomain')), 'Sample span units/domain missing')
    elif stage == 'audio_samples':
        require(channels in (1, 2) and integer(value, 'channels') == channels and integer(value, 'sampleRate') == 48000, 'Audio format differs from request')
        integer(value, 'writtenSamples', 1)
    elif stage == 'output_validation':
        v = value['verification']
        require(all(value.get(k) == POLICY[k] for k in ('durationUnit', 'durationDomain', 'decodeScope')), 'Wrong output units/decode scope')
        require(v.get('mime') == mode['mime'] and all(integer(v, k) == integer(mode, k) for k in ('width', 'height')) and integer(v, 'requestedFps') == mode['fps'], 'Output mode differs from request')
        integer(v, 'samples', 2); integer(v, 'encodedBytes', 1); integer(v, 'sampleSpanUs', 1)
        require(v.get('firstSyncFrameDecoded') is True, 'No decoded video sample')
        media(v.get('mediaIdentity'))
        require(v.get('audioRequested') is (channels > 0) and integer(v, 'audioTrackCount') == int(channels > 0), 'Requested audio disappeared')
        require(v.get('nominalFpsIsNotSustainedRateProof') is True and v.get('cadenceWarningPreservesFootage') is True, 'Overstated cadence claim')
        require(type(v.get('cadenceToleranceFraction')) in (int, float) and v['cadenceToleranceFraction'] == .03 and integer(v, 'cadenceMinimumSpanUs') == 2000000, 'Existing cadence policy changed')
        if mode['dynamicRange'] == 'HLG10':
            require(tuple(integer(v, k) for k in ('lumaBitDepth', 'chromaBitDepth', 'colorStandard', 'colorTransfer', 'colorRange')) == (10, 10, 6, 7, 2), 'HLG signal contract mismatch')
        if channels:
            require(v.get('firstAudioPcmDecoded') is True, 'No decoded audio sample')
            a = v['audio']
            require(a.get('mime') == 'audio/mp4a-latm' and a.get('profile') == 'AAC-LC' and integer(a, 'sampleRate') == 48000 and integer(a, 'channels') == channels, 'Decoded audio format mismatch')
            integer(a, 'samples', 2)
    elif stage == 'publication':
        require(text(value.get('uri')) and value['uri'].startswith('content://'), 'Publication URI missing')
        media(value.get('mediaIdentity'))
    elif stage == 'retention':
        require(text(value.get('uri')) and value['uri'].startswith('content://'), 'Recovery URI missing')
        integer(value, 'byteCount', 1)
    else:
        raise ValueError('Ordinary recording cannot provide independent ' + stage)


def validate(value, expected_revision):
    require(isinstance(value, dict) and type(value.get("schemaVersion")) is int, "Malformed recording report")
    require(identity(expected_revision, 40) and value.get('sourceRevision') == expected_revision, 'Missing or mismatched source revision')
    require(value.get('schemaVersion') == 1 and value.get('kind') == 'ordinary-recording-evidence', 'Unknown recording evidence schema')
    attempt = value.get('attemptId')
    require(isinstance(attempt, str) and re.fullmatch(r'[0-9a-f-]{36}', attempt) is not None, 'Invalid attempt identity')
    require(type(value.get('closed')) is bool and text(value.get('startedAt')), 'Missing lifecycle state')
    require((text(value.get('endedAt')) if value['closed'] else value.get('endedAt') is None), 'Inconsistent completion time')
    require(value.get('physicalCameraCertified') is False and value.get('customLog') is False, 'Unsupported physical/custom-Log claim')
    require(value.get('policy') == POLICY and all(type(value['policy'][k]) is type(v) for k, v in POLICY.items()), 'Unreviewed recording policy change')
    context = value['context']
    require(isinstance(context, dict), 'Malformed recording context')
    mode, device = context.get('selectedMode'), context.get('device')
    require(isinstance(mode, dict) and isinstance(device, dict), 'Malformed mode/device context')
    require(isinstance(context.get('requested'), dict) and device.get('appCommit') == expected_revision and text(device.get('fingerprint')), 'Missing device/source context')
    require(integer(context, 'audioChannels') in (0, 1, 2) and context.get('audioMode') == ('OFF', 'MONO', 'STEREO')[context['audioChannels']], 'Audio request mismatch')
    for k in ('width', 'height', 'fps', 'bitrate'):
        integer(mode, k, 1)
    require(all(text(mode.get(k)) for k in ('key', 'encoder', 'mime', 'dynamicRange')), 'Missing selected-mode binding')
    strings(value.get('captureErrors'), 'capture errors'); strings(value.get('reportErrors'), 'report errors')
    require(value.get('persistenceError') is None or text(value.get('persistenceError')), 'Invalid persistence state')
    rows = value['stages']; observations = value['observations']
    require(isinstance(rows, list) and all(isinstance(r, dict) for r in rows) and len(rows) == len(STAGES) and {r.get('stage') for r in rows} == set(STAGES), 'Missing/duplicate stage')
    require(isinstance(observations, dict), 'Missing observations')
    outcomes, used, underlying = {}, set(), {}
    for r in rows:
        stage = r['stage']; outcome = r.get('outcome'); checks = r.get('checks')
        require(outcome in SEVERITY and text(r.get('reason')) and r.get('sourceRevision') == expected_revision, 'Invalid or stale stage')
        require(isinstance(checks, list) and all(isinstance(c, dict) and text(c.get('id')) and text(c.get('reason')) and c.get('outcome') in SEVERITY for c in checks), 'Invalid individual checks')
        require(len({c['id'] for c in checks}) == len(checks), 'Duplicate check')
        observed = next((o for o in SEVERITY if any(c['outcome'] == o for c in checks)), 'not_run')
        require(observed == outcome, 'Aggregate contradicts individual outcome')
        if outcome == 'not_run':
            require(not checks and r.get('evidenceRef') is None and r.get('evidenceSha256') is None, 'Unrun stage has invented evidence')
        else:
            ref = r.get('evidenceRef'); payload = observations.get(ref)
            require(text(ref) and ref not in used and isinstance(payload, str) and hashlib.sha256(payload.encode()).hexdigest() == r.get('evidenceSha256'), 'Missing/tampered observation')
            raw = decode(payload.encode()); used.add(ref)
            require(isinstance(raw, dict), 'Malformed observation object')
            require(raw.get('attemptId') == attempt and raw.get('sourceRevision') == expected_revision and raw.get('stage') == stage, 'Observation belongs to another attempt/revision/stage')
            require(isinstance(raw.get('facts'), dict), 'Malformed raw facts')
            underlying[stage] = raw['facts']
            if outcome == 'passed':
                facts(stage, raw['facts'], context)
        require(stage not in ('full_decode', 'physical_qualification') or outcome == 'not_run', 'Unavailable independent protocol was promoted')
        outcomes[stage] = outcome
    require(used == set(observations), 'Hidden/unreferenced observations')
    if outcomes['publication'] == 'passed':
        require(outcomes['output_validation'] == 'passed' and underlying['publication']['mediaIdentity'] == underlying['output_validation']['verification']['mediaIdentity'], 'Published identity differs from checked output')
    if outcomes['output_validation'] == 'passed' and outcomes['encoded_output'] == 'passed':
        require(underlying['output_validation']['verification']['samples'] == underlying['encoded_output']['writtenSamples'], 'Decoded report differs from written sample count')
    closed = value['closed']
    checked = closed and outcomes['output_validation'] == 'passed'
    published = checked and outcomes['publication'] == 'passed'
    succeeded = published and not value['captureErrors'] and all(outcomes[s] == 'passed' for s in ('preparation', 'configured', 'encoded_output')) and (not context['audioChannels'] or outcomes['audio_samples'] == 'passed')
    classification = {'outputChecked': checked, 'publishedOutput': published, 'recordingSucceeded': succeeded,
                      'retainedForRecovery': closed and outcomes['retention'] == 'passed', 'fullDecodeVerified': False,
                      'physicalCameraCertified': False, 'issues': []}
    require(isinstance(value.get('classification'), dict) and all(type(value['classification'].get(k)) is bool for k in classification if k != 'issues'), 'Classification flags must be booleans')
    require(value.get('classification') == classification, 'Producer aggregate contradicts independent classification')
    return {'attemptId': attempt, 'sourceRevision': expected_revision, 'closed': closed, 'outcomes': outcomes, **classification}


def archive_reports(path: Path, expected_revision: str, require_integration=False):
    reports, probes, legacy, controls = [], [], [], []
    with tarfile.open(path) as archive:
        members = archive.getmembers()
        require(len({m.name for m in members}) == len(members), 'Duplicate archive member')
        for member in members:
            p = PurePosixPath(member.name)
            require(not p.is_absolute() and '..' not in p.parts, 'Unsafe archive path')
            if not member.name.endswith('.json') or not member.name.startswith('files/exports/'):
                continue
            require(member.isfile() and 0 < member.size <= 4*1024*1024, 'Invalid JSON archive member')
            value = decode(archive.extractfile(member).read())
            require(isinstance(value, dict), 'Malformed exported JSON report')
            if value.get('kind') == 'ordinary-recording-evidence':
                require(len(reports) < 1024, 'Too many recording reports')
                reports.append(validate(value, expected_revision))
            elif value.get('kind') == 'recording-validation':
                legacy.append(value)
                if member.name.startswith('files/exports/recording-controls/'):
                    controls.append(value)
            elif value.get('schemaVersion') == 2 and value.get('evidence') == 'advertised_only':
                probes.append(probe(value, expected_revision))
    require(reports, 'No ordinary recording attempts were exported')
    by_id = {r['attemptId']: r for r in reports}
    require(len(by_id) == len(reports), 'Repeated attempt identity')
    if require_integration:
        require(probes and legacy and any(r['recordingSucceeded'] for r in reports), 'Missing real probe/recording integration evidence')
        require(any(r['outcomes']['preparation'] == 'failed' for r in reports), 'Missing early-setup failure experiment')
        require(any(r['outcomes']['encoded_output'] == 'blocked' for r in reports), 'Missing no-frame cancellation experiment')
        require(len(controls) == 1, 'Missing retained no-frame control sidecar')
        control = controls[0]
        require(control.get('status') == 'rejected' and type(control.get('encodedSamples')) is int and control['encodedSamples'] == 0,
                'Deliberate no-frame control was relabelled successful')
        require(control.get('requested', {}).get('testKind') == 'P003-no-camera-no-frames-control', 'Unknown recording control')
        controlled = by_id.get(control.get('attemptId'), {})
        require(controlled.get('outcomes', {}).get('encoded_output') == 'blocked' and controlled.get('recordingSucceeded') is False,
                'Control sidecar does not match its failed production attempt')
        for old in legacy:
            require(old.get('attemptId') in by_id and old.get('attemptReport') == 'recording-attempt-' + old['attemptId'] + '.json', 'Recording sidecar is not bound to an attempt')
            r = by_id[old['attemptId']]
            if old.get('status') == 'checked':
                require(r['recordingSucceeded'], 'Checked legacy recording lacks matching successful attempt')
    return {'status': 'passed', 'reports': reports, 'capabilityReports': probes, 'physicalCameraCertified': False,
            'scope': 'Ordinary report consistency; full-file decode remains the separate check_video.py gate'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('path', type=Path); p.add_argument('--expected-revision', required=True)
    p.add_argument('--require-integration', action='store_true')
    args = p.parse_args()
    try:
        if args.path.suffix == '.json':
            require(args.path.stat().st_size <= 4*1024*1024 and args.path.is_file() and not args.path.is_symlink(), 'Invalid report file')
            value = decode(args.path.read_bytes())
            require(isinstance(value, dict), 'Malformed report object')
            result = probe(value, args.expected_revision) if value.get('evidence') == 'advertised_only' else validate(value, args.expected_revision)
        else:
            result = archive_reports(args.path, args.expected_revision, args.require_integration)
        print(json.dumps(result, indent=2, allow_nan=False)); return 0
    except (ValueError, KeyError, TypeError, OSError, tarfile.TarError) as error:
        print(json.dumps({'status': 'failed', 'reason': str(error)})); return 1

if __name__ == '__main__':
    raise SystemExit(main())
