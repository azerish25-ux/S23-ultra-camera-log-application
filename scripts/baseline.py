#!/usr/bin/env python3
"""P004: freeze and independently replay existing evidence, not certify a phone.

collect/verify are offline and never modify the checkout or supplied evidence.
fetch is explicit, bounded, checksum-verified and create-only. Reproduction runs
in the separate frozen-source workflow; it is never disguised as artifact replay.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_research_contract import canonical_hash, decode, fields, git, identity, relative_name, require, text

ROOT = Path(__file__).resolve().parents[1]
LOCK = 'docs/evidence/P004-baseline-lock.json'
MAX_INPUT = 128 * 1024 * 1024
MAX_EXPANDED = 512 * 1024 * 1024
REPOSITORY = 'azerish25-ux/S23-ultra-camera-log-application'
INPUT_NAMES = {'verification.zip', 'apk.zip', 'job.json', 'job.log'}
PHYSICAL = {'outcome': 'unavailable', 'certified': False,
            'reason': 'No physical S23 measurement is supplied by this software baseline.'}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_file(path: Path, limit: int = MAX_INPUT) -> bytes:
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Symlink input is not permitted')
    require(path.is_file() and 0 < path.stat().st_size <= limit, 'Missing or oversized prerequisite: ' + str(path))
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    require(len(data) <= limit, 'Input grew beyond limit')
    return data


def zip_files(data: bytes) -> dict[str, bytes]:
    """Read bounded regular members without extractall, duplicate keys or links."""
    result = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        require(len(members) <= 10000 and sum(m.file_size for m in members) <= MAX_EXPANDED,
                'Archive exceeds member/expansion budget')
        seen = set()
        for member in members:
            name = relative_name(member.filename.rstrip('/'))
            require(name not in seen, 'Duplicate archive path: ' + name)
            seen.add(name)
            mode = (member.external_attr >> 16) & 0o170000
            require(mode in {0, 0o100000, 0o040000} and not member.flag_bits & 1,
                    'Linked, special or encrypted archive member')
            if not member.is_dir():
                require(mode != 0o040000, 'Directory disguised as a file')
                result[name] = archive.read(member)
        require(not any(p in result for name in result for p in
                        [str(x) for x in Path(name).parents if str(x) != '.']), 'File/directory path collision')
    return result


def object_id(kind: str, data: bytes) -> str:
    return hashlib.sha1(kind.encode() + b' ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def tree_id(files: dict[str, tuple[str, str]]) -> str:
    tree = {}
    for path, value in files.items():
        node = tree
        parts = relative_name(path).split('/')
        for part in parts[:-1]:
            require(not isinstance(node.get(part), tuple), 'Source path collision')
            node = node.setdefault(part, {})
        require(parts[-1] not in node, 'Duplicate source path')
        node[parts[-1]] = value

    def encode(node):
        data = bytearray()
        for name in sorted(node, key=lambda n: (n + ('/' if isinstance(node[n], dict) else '')).encode()):
            entry = node[name]
            mode, sha = ('40000', encode(entry)) if isinstance(entry, dict) else entry
            data.extend(mode.encode() + b' ' + name.encode() + b'\0' + bytes.fromhex(sha))
        return object_id('tree', bytes(data))
    return encode(tree)


def source_inventory(verification: dict, expected: dict) -> tuple[dict, dict]:
    require(verification['evidence/commit.txt'].decode().strip() == expected['revision'], 'Source revision mismatch')
    sources = zip_files(verification['evidence/S23Log-source.zip'])
    manifest = {}
    for line in verification['evidence/git-tree.txt'].decode().splitlines():
        header, path = line.split('\t', 1)
        mode, kind, blob = header.split()
        relative_name(path)
        require(path not in manifest and mode in {'100644', '100755'} and kind == 'blob' and identity(blob, 40),
                'Invalid or repeated source tree entry')
        manifest[path] = (mode, blob)
    require(set(sources) == set(manifest), 'Source archive membership differs from Git tree')
    for path, data in sources.items():
        require(object_id('blob', data) == manifest[path][1], 'Source blob mismatch: ' + path)
    require(tree_id(manifest) == expected['tree'], 'Source tree differs from frozen tree')
    inventory = {p: {'mode': manifest[p][0], 'gitBlob': manifest[p][1], 'sha256': digest(d), 'bytes': len(d)}
                 for p, d in sorted(sources.items())}
    return inventory, sources


def junit_cases(payload: bytes, family: str, member: str) -> tuple[list, list]:
    """Keep individual failures even when an aggregate is corrupt."""
    require(len(payload) <= 4 * 1024 * 1024, 'JUnit document exceeds budget')
    xml = payload.decode('utf-8-sig')
    require('<!DOCTYPE' not in xml.upper() and '<!ENTITY' not in xml.upper(), 'XML entities are not evidence')
    rows, issues, seen = [], [], set()

    def visit(node, depth=0):
        require(depth < 20 and node.tag in {'testsuite', 'testsuites'}, 'Unsupported JUnit structure')
        counts = dict.fromkeys(('tests', 'failures', 'errors', 'skipped'), 0)
        for child in node:
            if child.tag in {'testsuite', 'testsuites'}:
                nested = visit(child, depth + 1)
                for key in counts:
                    counts[key] += nested[key]
            elif child.tag == 'testcase':
                name, cls = child.get('name'), child.get('classname')
                require(text(name) and text(cls) and (cls, name) not in seen, 'Missing/duplicate test identity')
                seen.add((cls, name))
                labels = [tag for tag in ('failure', 'error', 'skipped') if child.find(tag) is not None]
                require(len(labels) <= 1, 'Conflicting per-test outcomes')
                label = labels[0] if labels else 'passed'
                counts['tests'] += 1
                if labels:
                    counts[{'failure': 'failures', 'error': 'errors', 'skipped': 'skipped'}[label]] += 1
                duration = None
                if child.get('time') is not None:
                    value = float(child.get('time'))
                    require(math.isfinite(value) and value >= 0, 'Invalid test duration')
                    duration = {'value': value, 'unit': 's', 'domain': 'test_elapsed'}
                rows.append({'family': family, 'class': cls, 'name': name, 'member': member,
                             'outcome': {'failure': 'failed', 'error': 'failed', 'skipped': 'not_run'}.get(label, 'passed'),
                             'duration': duration, 'detail': '' if not labels else ET.tostring(child.find(label), encoding='unicode')})
            else:
                require(child.tag in {'properties', 'system-out', 'system-err'}, 'Unsupported JUnit element')
        for key, value in counts.items():
            raw = node.get(key, '-1' if key == 'tests' else '0')
            if not raw.isdecimal() or int(raw) != value:
                issues.append(member + ': aggregate ' + key + ' differs from individual cases')
        return counts
    visit(ET.fromstring(xml))
    return rows, issues


def clean_log(data: bytes) -> str:
    result = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', data.decode('utf-8-sig'))
    return re.sub(r'^\d{4}-\d\d-\d\dT[\d:.]+Z ', '', result, flags=re.M)


def host_cases(data: bytes) -> tuple[list, list]:
    log = clean_log(data)
    rows, issues = [], []
    pending = None
    diagnostics = []
    verdict = re.compile(r"^(ok|FAIL|ERROR|skipped(?: .*)?)$")
    def finish(outcome):
        name = pending
        rows.append({'family': 'host', 'class': name.split('(', 1)[1].rsplit(')', 1)[0],
                     'name': name.split(' ', 1)[0], 'member': 'job.log',
                     'outcome': 'passed' if outcome == 'ok' else 'not_run' if outcome.startswith('skipped') else 'failed',
                     'duration': None, 'detail': '\n'.join(diagnostics + [outcome])})
    for line in log.splitlines():
        header = re.match(r'^(test\S+ \([^\r\n]+\)) \.\.\. (.*)$', line)
        if header:
            if pending is not None:
                issues.append('Missing terminal outcome for host test: ' + pending)
            pending, suffix = header.groups()
            diagnostics = []
            if verdict.fullmatch(suffix):
                finish(suffix)
                pending = None
            elif suffix:
                diagnostics.append(suffix)
        elif pending is not None:
            if verdict.fullmatch(line):
                finish(line)
                pending = None
            else:
                diagnostics.append(line)
    if pending is not None:
        issues.append('Unterminated host test: ' + pending)
    totals = re.findall(r'^Ran (\d+) tests? in [\d.]+s$', log, re.M)
    if len(totals) != 1 or int(totals[0]) != len(rows) or len({(r['class'], r['name']) for r in rows}) != len(rows):
        issues.append('Host log lacks one complete, unique per-test inventory')
    if any(r['outcome'] == 'failed' for r in rows) and re.search(r'^OK(?: \(.*\))?$', log, re.M):
        issues.append('Host summary contradicts failed individual case')
    return rows, issues


def permission_outcome(data: bytes) -> tuple[str, list[str]]:
    """Separate explicit failure from absent/unfinished isolated instrumentation."""
    log = clean_log(data)
    successes = re.findall(r'^OK \(1 test\)\s*$', log, re.M)
    failed = bool(re.search(r'^FAILURES!!!|^INSTRUMENTATION_FAILED:|^INSTRUMENTATION_STATUS_CODE: -(?:1|2)\s*$', log, re.M))
    issues = []
    if len(successes) > 1 or (successes and failed):
        issues.append('Contradictory isolated permission instrumentation verdicts')
    return ('failed' if failed else 'passed' if len(successes) == 1 else 'not_run'), issues


def verify_report(claimed: dict, observed: dict) -> dict:
    """A report is accepted only if every field re-derives from original inputs."""
    issues = []
    if canonical_hash(claimed) != canonical_hash(observed):
        issues.append('Claimed report differs from independently collected evidence; no cases, units or limits may be omitted')
    return {'status': 'failed' if issues else 'passed', 'issues': issues, 'observed': observed}


def validate_lock(lock: dict) -> None:
    fields(lock, 'schemaVersion baselineId repository source run inputs expectedCounts scope')
    require(lock['schemaVersion'] == 1 and type(lock['schemaVersion']) is int and text(lock['baselineId']), 'Unknown baseline protocol')
    require(lock['repository'] == REPOSITORY and text(lock['scope']), 'Missing repository/provenance scope')
    fields(lock['source'], 'revision tree')
    require(all(identity(v, 40) for v in lock['source'].values()), 'Invalid source identity')
    fields(lock['run'], 'id jobId attempt workflowRevision')
    require(all(type(lock['run'][k]) is int and lock['run'][k] > 0 for k in ('id', 'jobId', 'attempt')) and
            identity(lock['run']['workflowRevision'], 40), 'Invalid run identity')
    require(set(lock['inputs']) == INPUT_NAMES, 'Missing baseline input provenance')
    for name, descriptor in lock['inputs'].items():
        fields(descriptor, 'sha256 bytes apiPath owner purpose')
        require(identity(descriptor['sha256']) and type(descriptor['bytes']) is int and
                0 < descriptor['bytes'] <= MAX_INPUT and text(descriptor['owner']) and text(descriptor['purpose']),
                'Missing input identity/ownership: ' + name)
        require(re.fullmatch(r'/actions/(artifacts/\d+/zip|jobs/\d+(/logs)?)', descriptor['apiPath']) is not None,
                'Unapproved input API endpoint')
    require(set(lock['expectedCounts']) == {'host', 'jvm', 'emulator', 'permission'}, 'Missing execution inventory')
    require(all(type(v) is int and v > 0 for v in lock['expectedCounts'].values()), 'Invalid expected test count')


def run_consumer(script: Path, arguments: list[str]) -> dict:
    """Only called for the fixed allowlist below, after source-tree verification."""
    result = subprocess.run([sys.executable, '-I', '-B', str(script), *arguments],
                            cwd=script.parent.parent, capture_output=True, timeout=180)
    require(result.returncode == 0, 'Consumer rejected evidence: ' + script.name + ': ' + result.stderr.decode(errors='replace')[-1500:])
    return decode(result.stdout)


def replay(sources: dict, verification: dict, source_revision: str) -> dict:
    require(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Missing prerequisite: FFmpeg and ffprobe for full-file decode')
    with tempfile.TemporaryDirectory(prefix='s23-baseline-') as temp:
        root = Path(temp)
        # All names and bytes were checked above. No downloaded report chooses a command.
        for name, data in sources.items():
            if name.startswith('scripts/'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        archive = root / 'app-evidence.tar'
        archive.write_bytes(verification['evidence/emulator/app-evidence.tar'])
        videos = root / 'videos'
        videos.mkdir()
        for name, data in verification.items():
            if name.startswith('evidence/emulator/videos/') and name.endswith('.mp4'):
                (videos / Path(name).name).write_bytes(data)
        require(any(videos.iterdir()), 'Missing recorded video bytes')
        script = root / 'scripts'
        ffprobe = run_consumer(script / 'check_video.py', [str(videos), '--min-duration', '1'])
        ffprobe_file = root / 'ffprobe.json'
        ffprobe_file.write_text(json.dumps(ffprobe))
        original = run_consumer(script / 'check_evidence.py', [str(archive), str(ffprobe_file), '--require-audio', '--require-identity'])
        classified = run_consumer(script / 'check_p003_evidence.py', [str(archive), '--expected-revision', source_revision])
        live = run_consumer(script / 'check_live_log.py', [str(archive)])
        raw = run_consumer(script / 'check_raw_development.py', [str(archive)])
        return {'recordings': original, 'p003': classified, 'liveBackend': live, 'savedRawBackend': raw,
                'externalFullDecode': True, 'physicalCameraCertified': False}


def collect(lock: dict, folder: Path) -> dict:
    validate_lock(lock)
    inputs = {}
    for name, descriptor in lock['inputs'].items():
        data = read_file(folder / name)
        require(len(data) == descriptor['bytes'] and digest(data) == descriptor['sha256'], 'Input checksum mismatch: ' + name)
        inputs[name] = data
    verification = zip_files(inputs['verification.zip'])
    inventory, sources = source_inventory(verification, lock['source'])
    job = decode(inputs['job.json'])
    for key, expected in [('id', lock['run']['jobId']), ('run_id', lock['run']['id']),
                          ('run_attempt', lock['run']['attempt']), ('head_sha', lock['run']['workflowRevision'])]:
        require(job.get(key) == expected, 'Job/source provenance mismatch: ' + key)
    rows, issues = host_cases(verification.get('evidence/reproduction/host.log', inputs['job.log']))
    for name, data in sorted(verification.items()):
        family = 'jvm' if name.startswith('app/build/test-results/') else 'emulator' if name.startswith('app/build/outputs/androidTest-results/') else None
        if family and name.endswith('.xml'):
            cases, errors = junit_cases(data, family, name)
            rows.extend(cases)
            issues.extend(errors)
    permission_bytes = verification.get('evidence/emulator/permission-instrumentation.txt', b'')
    permission, permission_issues = permission_outcome(permission_bytes)
    issues.extend(permission_issues)
    rows.append({'family': 'permission', 'class': 'com.s23log.probe.AudioPermissionTest', 'name': 'isolated_instrumentation',
                 'member': 'evidence/emulator/permission-instrumentation.txt', 'outcome': permission,
                 'duration': None, 'detail': permission_bytes.decode()})
    if len({(r['family'], r['class'], r['name']) for r in rows}) != len(rows):
        issues.append('Duplicate case identity across test files')
    counts = {family: dict(Counter(r['outcome'] for r in rows if r['family'] == family)) for family in lock['expectedCounts']}
    for family, expected in lock['expectedCounts'].items():
        if sum(counts[family].values()) != expected:
            issues.append('Incomplete ' + family + ' execution inventory')
    steps = [{'number': s['number'], 'name': s['name'], 'status': s['status'], 'conclusion': s['conclusion']} for s in job['steps']]
    require(steps and len({s['number'] for s in steps}) == len(steps), 'Missing/duplicate workflow step')
    if job.get('status') != 'completed':
        issues.append('Workflow has not completed')
    if job.get('conclusion') == 'success' and (any(r['outcome'] == 'failed' for r in rows) or
            any(s['conclusion'] in {'failure', 'cancelled', 'timed_out'} for s in steps)):
        issues.append('Workflow success contradicts raw failed cases or steps')
    apks = zip_files(inputs['apk.zip'])
    require(len(apks) == 1 and next(iter(apks)).endswith('.apk'), 'APK archive must contain exactly one APK')
    apk_name, apk_data = next(iter(apks.items()))
    require({'AndroidManifest.xml', 'classes.dex'} <= set(zip_files(apk_data)), 'APK is missing application payload')
    observations = replay(sources, verification, lock['source']['revision'])
    # Re-run observations, not a copied aggregate, are authoritative.
    for member, key in [('p003-cross-adapter-summary.json', 'p003'), ('live-log-summary.json', 'liveBackend'),
                        ('raw-development-summary.json', 'savedRawBackend'), ('summary.json', 'recordings')]:
        original = decode(verification['evidence/emulator/' + member])
        if canonical_hash(original) != canonical_hash(observations[key]):
            issues.append('Retained aggregate contradicts replay: ' + member)
    log = clean_log(inputs['job.log'])
    tools = [line for line in log.splitlines() if re.search(
        r'^(Resolved Java |git version |Gradle \d|Kotlin:|JVM:|Launcher JVM:|Daemon JVM:|Successfully installed numpy-|Android emulator version|Version: 20\d{6}\.)', line)]
    policy_files = {p: row['sha256'] for p, row in inventory.items() if
                    p.startswith(('scripts/check_', 'gradle/', '.github/scripts/')) or
                    p in {'app/build.gradle.kts', 'build.gradle.kts', 'scripts/requirements-raw.txt', '.github/workflows/android.yml'}}
    start = datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00'))
    elapsed = (end - start).total_seconds()
    require(math.isfinite(elapsed) and elapsed >= 0, 'Invalid job time domain')
    report = {'schemaVersion': 1, 'baselineId': lock['baselineId'], 'scope': lock['scope'],
              'source': lock['source'], 'sourceFiles': inventory, 'inputProvenance': lock['inputs'],
              'job': {**lock['run'], 'conclusion': job['conclusion'], 'steps': steps,
                      'duration': {'value': elapsed, 'unit': 's', 'domain': 'workflow_wall_clock'}},
              'tests': sorted(rows, key=lambda r: (r['family'], r['member'], r['class'], r['name'])), 'counts': counts,
              'apk': {'member': apk_name, 'sha256': digest(apk_data), 'bytes': len(apk_data),
                      'signatureScope': 'Original CI signing checks; artifact replay is not a new apksigner run.'},
              'toolsObservedInLog': sorted(set(tools)), 'policySourceHashes': policy_files,
              'buildConfiguration': {p: sources[p].decode() for p in ('build.gradle.kts', 'gradle/wrapper/gradle-wrapper.properties', 'scripts/requirements-raw.txt') if p in sources},
              'resolvedEnvironment': {p: {'sha256': digest(d), 'text': d.decode()} for p, d in verification.items() if p in {
                  'evidence/reproduction/tools.txt', 'evidence/reproduction/sdk-packages.txt', 'evidence/reproduction/gradle-dependencies.txt'}},
              'replayed': observations, 'physical': PHYSICAL.copy(), 'issues': issues,
              'limitations': ['Not bit-for-bit build reproducibility: debug keys and packaging may differ.',
                             'Original dependency inventory is incomplete: version ranges, runner image and SDK packages may resolve differently.',
                             'A hash establishes byte identity, not measurement honesty or physical S23 calibration.']}
    report['softwareResult'] = ('failed' if job['conclusion'] != 'success' or any(r['outcome'] == 'failed' for r in rows)
                                else 'incomplete' if issues or any(r['outcome'] == 'not_run' for r in rows) else 'passed')
    report['status'] = 'failed' if issues else 'passed'
    # Detect concurrent input edits after collection without touching their bytes.
    for name, descriptor in lock['inputs'].items():
        require(digest(read_file(folder / name)) == descriptor['sha256'], 'Input changed during collection: ' + name)
    return report


def verify_reference(reference: dict, report: dict) -> None:
    require(reference['baselineId'] == report['baselineId'] and reference['source'] == report['source'],
            'Reference identifies a different baseline')
    for key in ('counts', 'apk', 'physical'):
        require(reference[key] == report[key], 'Reference contradicts collected ' + key)
    require(reference['sourceFileCount'] == len(report['sourceFiles']), 'Reference omits source files')
    require(reference['canonicalReportSha256'] == canonical_hash(report), 'Reference digest differs from collected report')


def compare_runs(original: dict, reproduced: dict) -> dict:
    require(original['source'] == reproduced['source'], 'Cannot compare different source revisions')
    require(original['policySourceHashes'] == reproduced['policySourceHashes'], 'Changed acceptance policy is not reproduction')
    def outcomes(report):
        return sorted((r['family'], r['class'], r['name'], r['outcome']) for r in report['tests'])
    same = outcomes(original) == outcomes(reproduced)
    same_result = original['softwareResult'] == reproduced['softwareResult']
    require(original['physical'] == reproduced['physical'] == PHYSICAL, 'Physical scope changed between reports')
    return {'status': 'passed' if same and same_result and original['status'] == reproduced['status'] == 'passed' else 'failed',
            'sameTestOutcomes': same, 'sameSoftwareResult': same_result, 'originalSoftwareResult': original['softwareResult'],
            'reproducedSoftwareResult': reproduced['softwareResult'],
            'sameApkBytes': original['apk']['sha256'] == reproduced['apk']['sha256'],
            'originalTools': original['toolsObservedInLog'], 'reproducedTools': reproduced['toolsObservedInLog'],
            'resolvedEnvironmentAvailable': {'original': sorted(original['resolvedEnvironment']), 'reproduced': sorted(reproduced['resolvedEnvironment'])},
            'originalBackend': original['replayed']['liveBackend'], 'reproducedBackend': reproduced['replayed']['liveBackend'],
            'physicalCameraCertified': False, 'scope': 'Comparison of recorded software cases, not image/performance equivalence.'}


def workspace(root: Path, expected: str | None, lock_path: Path) -> str:
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    require(expected is None or head == expected, 'Working HEAD changed; preserve and reconcile collaborator changes')
    # Frozen record is append-only once committed. Future baselines use new files.
    relative = lock_path.absolute().relative_to(root.absolute()).as_posix()
    exists = subprocess.run(['git', '-C', str(root), 'cat-file', '-e', 'HEAD^:' + relative], capture_output=True)
    if exists.returncode == 0:
        require(decode(git(root, 'show', 'HEAD^:' + relative)) == decode(read_file(lock_path)),
                'Historical baseline lock was changed; create a separately reviewed baseline')
    return head


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        require(urllib.parse.urlsplit(newurl).scheme == 'https', 'Non-HTTPS download redirect')
        result = super().redirect_request(req, fp, code, msg, headers, newurl)
        if result is not None and urllib.parse.urlsplit(req.full_url).netloc != urllib.parse.urlsplit(newurl).netloc:
            result.remove_header('Authorization')
        return result


def fetch(lock: dict, folder: Path) -> None:
    validate_lock(lock)
    folder.mkdir(parents=True, exist_ok=True)
    require(not any(p.is_symlink() for p in (folder, *folder.parents)), 'Symlink output directory')
    opener = urllib.request.build_opener(SafeRedirect())
    for name, item in lock['inputs'].items():
        path = folder / name
        if path.exists():
            require(digest(read_file(path)) == item['sha256'], 'Refusing to overwrite different input: ' + name)
            continue
        headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
        if os.environ.get('GH_TOKEN'):
            headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
        req = urllib.request.Request('https://api.github.com/repos/' + REPOSITORY + item['apiPath'], headers=headers)
        with opener.open(req, timeout=90) as response:
            data = response.read(MAX_INPUT + 1)
        require(len(data) == item['bytes'] and digest(data) == item['sha256'], 'Downloaded bytes differ from frozen input: ' + name)
        with path.open('xb') as stream:
            stream.write(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('collect', 'verify', 'fetch', 'compare'))
    parser.add_argument('--lock', type=Path, default=ROOT / LOCK)
    parser.add_argument('--inputs', type=Path)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--other', type=Path)
    parser.add_argument('--reference', type=Path, help='Frozen summary/digest to check after collection')
    parser.add_argument('--expected-head')
    args = parser.parse_args()
    try:
        if args.operation == 'compare':
            require(args.report is not None and args.other is not None, 'compare needs --report and --other')
            result = compare_runs(decode(read_file(args.report)), decode(read_file(args.other)))
        else:
            lock_bytes = read_file(args.lock)
            lock = decode(lock_bytes)
            require(args.inputs is not None, 'Missing --inputs directory')
            head = workspace(ROOT, args.expected_head, args.lock) if args.expected_head else None
            if args.operation == 'fetch':
                fetch(lock, args.inputs)
                result = {'status': 'passed', 'scope': 'Checksum-verified input acquisition only'}
            else:
                observed = collect(lock, args.inputs)
                if args.reference is not None:
                    verify_reference(decode(read_file(args.reference)), observed)
                if args.operation == 'verify':
                    require(args.report is not None, 'verify needs --report')
                    result = verify_report(decode(read_file(args.report)), observed)
                    if observed['status'] != 'passed':
                        result['status'] = 'failed'
                else:
                    result = observed
            require(read_file(args.lock) == lock_bytes, 'Baseline lock changed during verification')
            require(head is None or git(ROOT, 'rev-parse', 'HEAD').decode().strip() == head, 'HEAD moved during verification')
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result['status'] == 'passed' else 1
    except (ValueError, KeyError, TypeError, OSError, ET.ParseError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        print(json.dumps({'status': 'failed', 'reason': str(error), 'physicalCameraCertified': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
