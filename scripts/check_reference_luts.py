#!/usr/bin/env python3
"""Check the actual exported reference LUT bytes with an independent FFmpeg consumer."""
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import struct
import subprocess
import sys
import tarfile
import tempfile

NAMES = ('linear-bt2020-to-reference-log.cube', 'reference-log-to-linear-bt2020.cube')
PREFIX = 'files/exports/colour-reference-v0-1/'


def verify_directory(directory: Path) -> dict:
    tables = []
    for name in NAMES:
        lines = (directory / name).read_text().splitlines()
        if 'LUT_1D_SIZE 8192' not in lines or 'DOMAIN_MIN 0.0 0.0 0.0' not in lines or 'DOMAIN_MAX 1.0 1.0 1.0' not in lines:
            raise ValueError('Wrong LUT size or domain')
        rows = [list(map(float, line.split())) for line in lines if line and line[0].isdigit()]
        if len(rows) != 8192 or any(len(row) != 3 or not all(math.isfinite(x) and 0 <= x <= 1 for x in row) or row[0] != row[1] or row[1] != row[2] for row in rows):
            raise ValueError('Invalid reference RGB entries')
        values = [row[0] for row in rows]
        if values[0] != 0 or values[-1] != 1 or any(a > b for a, b in zip(values, values[1:])):
            raise ValueError('Invalid reference endpoints/monotonicity')
        tables.append(values)
    width = 10001
    ramp = [i / (width - 1) for i in range(width)]
    payload = struct.pack('<' + 'f' * width * 3, *(ramp * 3))
    def run(names):
        filters = ','.join(f"lut1d=file='{directory / name}':interp=linear" for name in names)
        process = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo',
            '-pixel_format', 'gbrpf32le', '-video_size', f'{width}x1', '-framerate', '1', '-i', 'pipe:0',
            '-vf', filters, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'gbrpf32le', 'pipe:1'],
            input=payload, capture_output=True, check=True, timeout=45)
        if len(process.stdout) != len(payload):
            raise ValueError('FFmpeg returned an incomplete float frame')
        return struct.unpack('<' + 'f' * width * 3, process.stdout)
    forward = run([NAMES[0]]); inverse = run([NAMES[1]]); roundtrip = run(NAMES)
    expected_forward = [math.log1p(63 * x) / math.log(64) for x in ramp] * 3
    expected_inverse = [math.expm1(x * math.log(64)) / 63 for x in ramp] * 3
    def error(actual, expected):
        if not all(math.isfinite(x) for x in actual):
            raise ValueError('Nonfinite FFmpeg pixels')
        return max(abs(a - b) for a, b in zip(actual, expected))
    errors = dict(forward=error(forward, expected_forward), inverse=error(inverse, expected_inverse), roundtrip=error(roundtrip, ramp * 3))
    thresholds = dict(forward=3e-6, inverse=4e-7, roundtrip=8e-7)
    if any(errors[key] > thresholds[key] for key in errors):
        raise ValueError(f'Independent LUT consumer mismatch: {errors}')
    return dict(status='passed', consumer='FFmpeg lut1d / linear / planar float RGB', maximumErrors=errors,
                tolerances=thresholds, customLogRecordingEnabled=False, physicalCameraCertified=False,
                scope='Exported mathematical reference assets only; not an HLG-file correction or calibrated camera Log workflow')


def verify_archive(archive: Path, expected_commit: str | None = None) -> dict:
    with tempfile.TemporaryDirectory(prefix='s23log-reference-') as temporary:
        directory = Path(temporary)
        required = set(NAMES) | {'manifest.json', 'README.txt', 'reference-vectors.csv'}
        with tarfile.open(archive) as tar:
            for member in tar:
                path = PurePosixPath(member.name)
                if path.is_absolute() or '..' in path.parts or member.issym() or member.islnk():
                    raise ValueError('Unsafe archive entry')
                if member.name not in {PREFIX + name for name in required}:
                    continue
                if not member.isfile() or not 0 < member.size <= 2 * 1024 * 1024:
                    raise ValueError('Invalid reference asset size/type')
                destination = directory / path.name
                if destination.exists():
                    raise ValueError('Duplicate reference asset')
                destination.write_bytes(tar.extractfile(member).read())
        if {p.name for p in directory.iterdir()} != required:
            raise ValueError('Missing reference export')
        manifest = json.loads((directory / 'manifest.json').read_text())
        if manifest.get('referenceVersion') != 'S23Log-reference-0.1' or manifest.get('customLogRecordingEnabled') is not False or manifest.get('physicalCameraCertified') is not False:
            raise ValueError('Wrong reference contract')
        if manifest.get('schemaVersion') != 1 or manifest.get('lutSize') != 8192 or manifest.get('interpolation') != 'linear' or manifest.get('primaries') != 'BT2020' or manifest.get('domain') != [0, 1]:
            raise ValueError('Incomplete reference domain/interpolation contract')
        if expected_commit is not None and manifest.get('appCommit') != expected_commit:
            raise ValueError('Reference export is from another source revision')
        identities = manifest.get('files', [])
        if len(identities) != 4 or {item.get('name') for item in identities} != required - {'manifest.json'}:
            raise ValueError('Missing or duplicate reference identities')
        for item in identities:
            payload = (directory / item['name']).read_bytes(); identity = item.get('identity', {})
            if identity.get('algorithm') != 'SHA-256' or identity.get('byteCount') != len(payload) or identity.get('sha256') != hashlib.sha256(payload).hexdigest():
                raise ValueError('Reference identity mismatch')
        result = verify_directory(directory); result['appCommit'] = manifest.get('appCommit'); result['identitiesMatched'] = True
        return result


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('Usage: check_reference_luts.py app-evidence.tar')
        print(json.dumps(verify_archive(Path(sys.argv[1]), os.environ.get("GITHUB_SHA")), indent=2, allow_nan=False))
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError, subprocess.SubprocessError) as error:
        print(f'Reference LUT validation failed: {error}', file=sys.stderr); sys.exit(1)
