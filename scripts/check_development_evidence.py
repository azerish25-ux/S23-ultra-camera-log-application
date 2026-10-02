#!/usr/bin/env python3
"""Independently check P003 saved-RAW attempt reports; never certify physical capture."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import tarfile

STAGES = ('advertised', 'configured', 'source_validation', 'profile_validation', 'codec_qualification',
          'encoded_output', 'decoded_verification', 'source_preservation', 'publication', 'physical_qualification')
OUTPUT = STAGES[2:8]
OUTCOMES = ('failed', 'blocked', 'unavailable', 'not_run', 'inconclusive', 'passed')
POLICY = {'id': 'saved-raw-existing-0.9-v1', 'codeUnit': 'code_value', 'codeDomain': 'decoded_P010',
          'durationUnit': 'ns', 'durationDomain': 'source_sensor_timestamp_span', 'positiveMeanLimit': .75,
          'positivePeakLimit': 2.0, 'positiveMinimumLevels': 600, 'frameMeanLimit': 4.0, 'framePeakLimit': 64}


def require(value, message):
    if not value:
        raise ValueError(message)


def decode(data):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, 'Duplicate JSON key: ' + key)
            out[key] = value
        return out
    def invalid(value):
        raise ValueError('Nonfinite number: ' + value)
    def real(value):
        number = float(value)
        require(math.isfinite(number), 'Nonfinite number: ' + value)
        return number
    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid, parse_float=real)


def integer(value):
    return type(value) is int


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def artifact(value):
    require(isinstance(value, dict) and digest(value.get('sha256')) and
            integer(value.get('byteCount')) and value['byteCount'] > 0 and
            isinstance(value.get('name'), str) and value['name'], 'Invalid artifact identity')


def signal(value):
    require(isinstance(value, dict), 'Signal evidence must be an object')
    require(value.get('fullDecodeVerified') is True, 'Full decode missing')
    for key, expected in [('lumaBitDepth', 10), ('chromaBitDepth', 10), ('colorPrimariesCode', 2),
                          ('transferCharacteristicsCode', 2), ('matrixCoefficientsCode', 1)]:
        require(integer(value.get(key)) and value[key] == expected, 'Invalid signal ' + key)


def ramp(value):
    signal(value)
    require(integer(value.get('decodedFrames')) and value['decodedFrames'] == 4, 'Incomplete precision ramp')
    mean, peak, levels = (value.get(k) for k in ('meanCodeError', 'maximumCodeError', 'distinctRampLevels'))
    require(number(mean) and number(peak) and mean >= 0 and peak >= 0 and integer(levels) and 1 <= levels <= 877,
            'Invalid ramp measurement')
    return mean <= .75 and peak <= 2 and levels >= 600


def validate(report: dict, expected_revision: str | None = None) -> dict:
    require(isinstance(report, dict), 'Report must be an object')
    require(report.get('schemaVersion') == 1 and type(report['schemaVersion']) is int and
            report.get('kind') == 'saved-raw-development-evidence', 'Unknown attempt schema')
    revision = report.get('sourceRevision')
    require(isinstance(revision, str) and re.fullmatch('[0-9a-f]{40}', revision), 'Missing exact source revision')
    require(expected_revision is None or expected_revision == revision, 'Wrong source revision')
    attempt = report.get('attemptId')
    require(isinstance(attempt, str) and re.fullmatch('[0-9a-f-]{36}', attempt), 'Missing attempt identity')
    require(report.get('physicalCameraCertified') is False and report.get('sourceOwnershipIndependentlyVerified') is False,
            'Unsupported physical/provenance certainty')
    require(report.get('policy') == POLICY, 'Changed policy or measurement units/domain')
    require(type(report.get('closed')) is bool, 'Missing completion state')
    require(not report['closed'] or (report.get('activeStage') is None and isinstance(report.get('endedAt'), str)),
            'Completed attempt has an active stage or no end time')
    records = report.get('stages'); observations = report.get('observations'); context = report.get('context')
    require(isinstance(records, list) and isinstance(observations, dict) and isinstance(context, dict), 'Missing evidence records')
    require(all(isinstance(r, dict) for r in records), 'Invalid stage record')
    require(len(records) == len(STAGES) and {r.get('stage') for r in records} == set(STAGES), 'Missing/duplicate stages')
    outcomes, facts_by_stage = {}, {}
    for row in records:
        stage, claimed, checks = row['stage'], row.get('outcome'), row.get('checks')
        require(row.get('sourceRevision') == revision, 'Mixed stage revisions')
        require(claimed in OUTCOMES and isinstance(row.get('reason'), str) and row['reason'], 'Invalid outcome/reason')
        require(isinstance(checks, list) and all(isinstance(c, dict) for c in checks), 'Invalid individual checks')
        require(all(isinstance(c.get('id'), str) and c['id'] and isinstance(c.get('reason'), str) and c['reason'] for c in checks), 'Incomplete check identity/reason')
        require(len({c['id'] for c in checks}) == len(checks), 'Duplicate individual checks')
        for c in checks:
            require(isinstance(c, dict), 'Invalid check object')
            require(c.get('outcome') in OUTCOMES and c.get('id') and c.get('reason'), 'Incomplete check')
        actual = next((v for v in OUTCOMES if any(c['outcome'] == v for c in checks)), 'not_run')
        require(actual == claimed, 'Aggregate contradicts individual checks')
        outcomes[stage] = actual
        ref = row.get('evidenceRef')
        if actual == 'not_run' and ref is None:
            require(not checks and row.get('evidenceSha256') is None, 'Unobserved stage has hidden checks')
            continue
        require(ref == stage + '-observation' and isinstance(observations.get(ref), str), 'Missing observation reference')
        payload = observations[ref]
        require(digest(row.get('evidenceSha256')) and hashlib.sha256(payload.encode()).hexdigest() == row['evidenceSha256'],
                'Observation identity mismatch')
        facts = decode(payload); require(isinstance(facts, dict), 'Observation must be an object')
        facts_by_stage[stage] = facts
        if actual != 'passed':
            continue
        require(stage not in ('advertised', 'configured', 'physical_qualification'), 'Saved-RAW adapter cannot certify a camera stage')
        if stage == 'source_validation':
            artifact(facts['source']); require(integer(facts['frames']) and facts['frames'] >= 2, 'Missing source frames')
            require(facts['allFrameChecksumsChecked'] is True and facts['sourceBinding']['fingerprint'], 'Source evidence missing')
            require(integer(facts['timestampSpanNs']) and facts['timestampSpanNs'] > 0 and facts['durationUnit'] == 'ns' and
                    facts['durationDomain'] == 'source_sensor_timestamp_span', 'Source duration units/domain missing')
            require(facts['source']['sha256'] == context.get('sourceSha256') and facts['frames'] == context.get('expectedFrames') and
                    facts['sourceBinding'] == context.get('sourceBinding'), 'Source/context binding mismatch')
        elif stage == 'profile_validation':
            artifact(facts['profile']); require(facts['sourceBindingChecked'] is True, 'Profile binding not checked')
            require(facts['calibrationStatus'] in ('synthetic', 'provisional', 'measured'), 'Unknown supplied profile category')
            require(facts['profile']['sha256'] == context.get('profileSha256'), 'Profile/context identity mismatch')
            require(all(integer(facts[k]) and facts[k] > 0 and facts[k] == context.get(k) for k in ('width', 'height')), 'Profile geometry mismatch')
        elif stage == 'codec_qualification':
            q = facts['qualification']; require(q['status'] == 'qualified' and facts['codec'] == context.get('codec'), 'Wrong selected codec')
            require(ramp(q['positive']) and q['positive']['passed'] is True, 'Positive ramp failed')
            require(not ramp(q['eightBitNegative']) and q['eightBitNegative']['passed'] is False, 'Missing negative control rejection')
        elif stage == 'encoded_output':
            require(integer(facts['encoder']['frames']) and facts['encoder']['frames'] == context.get('expectedFrames') and facts['encoder']['name'] == context.get('codec'), 'Incomplete encoding or different codec')
            require(integer(facts['byteCount']) and facts['byteCount'] > 0 and facts['name'] == f'logc3-{attempt}.partial.mp4', 'Wrong output/attempt identity')
        elif stage == 'decoded_verification':
            v = facts['verification']; signal(v)
            require(integer(v['decodedFrames']) and v['decodedFrames'] == context.get('expectedFrames'), 'Incomplete frame decoding')
            require(all(integer(v[k]) and v[k] == context.get(k) for k in ('width', 'height')), 'Decoded geometry differs')
            require(all(number(v[k]) and 0 <= v[k] <= 4 for k in ('maximumFrameMeanLumaCodeError', 'maximumFrameMeanChromaCodeError')), 'Pixel comparison failed')
            require(integer(v['maximumCodeError']) and 0 <= v['maximumCodeError'] <= 64 and v['meanErrorLimitCodes'] == 4 and v['peakErrorLimitCodes'] == 64,
                    'Pixel error or threshold mismatch')
            require(number(v.get('measuredFps')) and integer(context.get('fps')) and context['fps'] > 0 and v['measuredFps'] == context['fps'], 'Output frame rate mismatch')
            artifact(v['mediaIdentity']); require(v['mediaIdentity']['name'] == f'logc3-{attempt}.partial.mp4', 'Decoded output belongs to another attempt')
        elif stage == 'source_preservation':
            for name in ('source', 'profile'):
                require(digest(facts[name + 'Before']) and facts[name + 'Before'] == facts[name + 'After'] == context.get(name + 'Sha256'),
                        'Source/profile changed or identity differs')
        elif stage == 'publication':
            require(facts['renamedWithoutOverwrite'] is True and facts['name'] == f'logc3-{attempt}.mp4' and
                    integer(facts['byteCount']) and facts['byteCount'] > 0, 'Publication not established')
    require(set(observations) == {r['evidenceRef'] for r in records if r.get('evidenceRef') is not None}, 'Unbound observation')
    verified = report['closed'] and all(outcomes[s] == 'passed' for s in OUTPUT)
    published = verified and outcomes['publication'] == 'passed'
    classification = report.get('classification', {})
    require(classification.get('verifiedOutput') is verified and classification.get('publishedOutput') is published and
            classification.get('physicalCameraCertified') is False, 'Classification contradicts evidence')
    require(classification.get('issues') == [], 'Producer rejected its own evidence')
    return {'attemptId': attempt, 'sourceRevision': revision, 'closed': report['closed'], 'outcomes': outcomes,
            'verifiedOutput': verified, 'publishedOutput': published, 'physicalCameraCertified': False,
            'scope': 'Saved-RAW report consistency, not sensor/ownership attestation'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path, help='An attempt JSON or app-evidence.tar')
    parser.add_argument('--expected-revision')
    args = parser.parse_args()
    try:
        if args.path.suffix == '.json':
            require(args.path.stat().st_size <= 4_000_000, 'Report too large')
            results = [validate(decode(args.path.read_bytes()), args.expected_revision)]
        else:
            results = []
            with tarfile.open(args.path) as archive:
                seen = set()
                for member in archive:
                    if not member.name.startswith('files/exports/raw-development-evidence/') or not member.name.endswith('.json'):
                        continue
                    require(member.isfile() and 0 < member.size <= 4_000_000 and '..' not in PurePosixPath(member.name).parts, 'Invalid report member')
                    require(member.name not in seen, 'Duplicate report member'); seen.add(member.name)
                    results.append(validate(decode(archive.extractfile(member).read()), args.expected_revision))
            require(results, 'No production development attempts were retained')
            require(len({r['attemptId'] for r in results}) == len(results), 'Duplicate attempt identities')
        print(json.dumps({'status': 'passed', 'reports': results, 'physicalCameraCertified': False}, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, tarfile.TarError) as error:
        print(json.dumps({'status': 'failed', 'reason': str(error), 'physicalCameraCertified': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
