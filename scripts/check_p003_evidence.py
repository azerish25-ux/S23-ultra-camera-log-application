#!/usr/bin/env python3
"""Run all three independent production consumers without merging their evidence scopes."""
from __future__ import annotations
import argparse
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
import check_development_evidence as saved
import check_recording_evidence as recording
import check_live_evidence as live
from verify_research_contract import require


def compare(developed, ordinary, sessions, revision):
    """Input is each consumer's re-derived verdict, not its producer's summary."""
    require(developed and ordinary and sessions,'An unrun adapter cannot satisfy P003 integration')
    ids=set()
    for family,rows in [('saved_raw',developed),('ordinary',ordinary),('live',sessions)]:
        for r in rows:
            require(r.get('sourceRevision')==revision and r.get('physicalCameraCertified') is False,'Cross-adapter revision/physical claim mismatch')
            require(r.get('attemptId') not in ids,'Attempt identity reused across adapters');ids.add(r['attemptId'])
            if family=='ordinary':require(r.get('fullDecodeVerified') is False,'Sample decode was promoted to full-file decode')
            if family=='live':require(r.get('pixelSourceComparison') is False,'Unretained live RAW was promoted to source-pixel comparison')
    return {'status':'passed','sourceRevision':revision,'adapterCounts':{'savedRaw':len(developed),'ordinary':len(ordinary),'live':len(sessions)},
        'savedRaw':developed,'ordinary':ordinary,'live':sessions,'physicalCameraCertified':False,
        'scope':'Cross-adapter report consistency only; unavailable hardware and failed attempts remain in their original families'}


def verify(path, revision):
    developed=[]
    with tarfile.open(path) as archive:
        members=archive.getmembers()
        require(len(members)<=10000 and len({m.name for m in members})==len(members),'Repeated/excessive archive members')
        for m in members:
            p=PurePosixPath(m.name)
            require(not p.is_absolute() and '..' not in p.parts and not m.issym() and not m.islnk(),'Unsafe archive member')
            if not m.name.startswith('files/exports/raw-development-evidence/') or not m.name.endswith('.json'):continue
            require(m.isfile() and 0<m.size<=4_000_000 and len(developed)<1024,'Invalid saved-RAW evidence')
            developed.append(saved.validate(saved.decode(archive.extractfile(m).read()),revision))
    ordinary=recording.archive_reports(path,revision,True)
    sessions=live.archive_reports(path,revision,True)
    return compare(developed,ordinary['reports'],sessions['reports'],revision)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=Path);p.add_argument('--expected-revision',required=True);a=p.parse_args()
    try:
        result=verify(a.archive,a.expected_revision);print(json.dumps(result,indent=2,allow_nan=False));return 0
    except (ValueError,KeyError,TypeError,OSError,tarfile.TarError) as e:
        print(json.dumps({'status':'failed','reason':str(e),'physicalCameraCertified':False}));return 1

if __name__=='__main__':raise SystemExit(main())
