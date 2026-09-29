#!/usr/bin/env python3
"""Decode test-only flashes/tones and audit real microphone timing separately from media integrity."""
import argparse
import array
import json
import math
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile


def command(args: list[str]) -> bytes:
    result = subprocess.run(args, capture_output=True, check=True, timeout=90)
    if result.stderr.strip():
        raise ValueError(result.stderr.decode(errors="replace"))
    return result.stdout


def starts(times: list[float], active: list[bool]) -> list[float]:
    if len(times) != len(active) or any(not math.isfinite(t) for t in times):
        raise ValueError("Invalid decoded event timeline")
    return [t for i, (t, yes) in enumerate(zip(times, active)) if yes and (i == 0 or not active[i - 1])]


def evaluate(video: list[float], audio: list[float], expected: list[float], fps: int,
             priming_samples: int | None = None) -> dict:
    if fps not in (24, 30) or len(expected) != 2 or len(video) != 2 or len(audio) != 2:
        raise ValueError("Expected two flashes and tones at 24/30 fps")
    if any(not math.isfinite(x) for x in video + audio + expected):
        raise ValueError("Invalid event time")
    frame = 1 / fps
    if any(abs(t - e) > frame for t, e in zip(video, expected)):
        raise ValueError("Video content differs from the declared marker timeline")
    offsets = [a - v for a, v in zip(audio, video)]
    # AAC priming may not survive MP4 metadata. Permit a bounded two-AAC-block
    # uncertainty, report it explicitly, and independently require <= one frame
    # of drift. This is NOT a physical or unqualified one-frame lip-sync claim.
    if priming_samples is not None and (not isinstance(priming_samples, int) or not 0 <= priming_samples <= 2048):
        raise ValueError("Invalid AAC priming declaration")
    allowance = (priming_samples if priming_samples is not None else 2048) / 48000
    if any(x < -frame or x > frame + allowance for x in offsets):
        raise ValueError(f"Marker offset exceeds frame/priming bounds: {offsets}")
    if abs(offsets[1] - offsets[0]) > frame:
        raise ValueError(f"Marker drift exceeds one video frame: {offsets}")
    return {"passed": True, "videoEventsSeconds": video, "audioEventsSeconds": audio,
            "uncorrectedOffsetsSeconds": offsets, "markerDriftSeconds": abs(offsets[1] - offsets[0]),
            "frameToleranceSeconds": frame, "primingAllowanceSeconds": allowance,
            "primingKnown": priming_samples is not None, "physicalLipSyncVerified": False}


def inspect(path: Path, fixture: dict) -> dict:
    probe = json.loads(command(["ffprobe", "-v", "error", "-show_frames", "-show_streams", "-of", "json", str(path)]))
    vframes = [f for f in probe["frames"] if f.get("media_type") == "video"]
    aframes = [f for f in probe["frames"] if f.get("media_type") == "audio"]
    if not vframes or not aframes or len(probe["streams"]) != 2:
        raise ValueError("Synthetic file is not a decodable two-track clip")
    if any(s.get("sample_rate") != "48000" or s.get("channels") != 1 for s in probe["streams"] if s.get("codec_type") == "audio"):
        raise ValueError("Unexpected synthetic audio format")
    gray = command(["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(path), "-map", "0:v:0",
                    "-an", "-vf", "scale=16:16,format=gray", "-fps_mode", "passthrough", "-f", "rawvideo", "-"])
    if len(gray) != len(vframes) * 256:
        raise ValueError("Video decode/frame evidence mismatch")
    vt = [float(f["best_effort_timestamp_time"]) for f in vframes]
    vs = starts(vt, [sum(gray[i:i+256]) / 256 > 160 for i in range(0, len(gray), 256)])
    raw = command(["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(path), "-map", "0:a:0", "-vn", "-f", "f32le", "-"])
    pcm = array.array("f"); pcm.frombytes(raw)
    import sys
    if sys.byteorder != "little": pcm.byteswap()
    if len(pcm) != sum(int(f["nb_samples"]) for f in aframes):
        raise ValueError("Audio decode/sample evidence mismatch")
    # Use decoded-frame timestamps (including any decoder trim), not a fabricated zero origin.
    at: list[float] = []; active: list[bool] = []; cursor = 0
    for f in aframes:
        n = int(f["nb_samples"]); first = float(f["best_effort_timestamp_time"])
        for j in range(0, n, 240):
            chunk = pcm[cursor+j:cursor+min(n, j+240)]
            at.append(first + j / 48000)
            active.append(math.sqrt(sum(x*x for x in chunk) / len(chunk)) > 0.12)
        cursor += n
    aus = starts(at, active)
    return {"file": path.name, "fps": fixture["fps"], **evaluate(vs, aus, fixture["eventsSeconds"], fixture["fps"], fixture.get("audioEncoderDelaySamples"))}


def verify_archive(path: Path) -> dict:
    manifest = None; load = None; reports = []; fixtures = {}
    with tarfile.open(path, "r:*") as tar:
        for item in tar.getmembers():
            name = PurePosixPath(item.name)
            if name.is_absolute() or ".." in name.parts or not item.isfile():
                if item.isfile() or item.issym() or item.islnk(): raise ValueError("Unsafe archive member")
                continue
            fixture = str(name).startswith("files/exports/timing-fixtures/")
            if not (fixture or str(name).startswith("files/exports/validation/") or name.name == "acquisition-load-test.json"):
                continue
            if not 0 < item.size <= 16 * 1024 * 1024:
                raise ValueError("Invalid timing evidence size")
            data = tar.extractfile(item).read()
            if fixture and name.name == "manifest.json": manifest = json.loads(data)
            elif fixture and name.suffix == ".mp4": fixtures[name.name] = data
            elif name.name == "acquisition-load-test.json": load = json.loads(data)
            elif name.suffix == ".json": reports.append(json.loads(data))
    if not manifest or manifest.get("kind") != "synthetic-av-timing" or len(manifest.get("fixtures", [])) != 2:
        raise ValueError("Missing known-content timing fixtures")
    if not load or not all(load.get(k) is True for k in ("readerProgressed", "allReadPcmSubmitted", "readerTerminated")):
        raise ValueError("Missing real acquisition-under-load evidence")
    if load["acceptedDuringBlock"] <= load["acceptedBeforeBlock"] or load["encoderHandlerBlockedMs"] < 250:
        raise ValueError("Encoder block did not exercise independent acquisition")
    results = []
    with tempfile.TemporaryDirectory(prefix="s23-timing-") as directory:
        for f in manifest["fixtures"]:
            name = f["file"]
            if PurePosixPath(name).name != name or name not in fixtures or f.get("producer") != "synthetic_test_apk_only" or f.get("delayedWrites", 0) < 1:
                raise ValueError("Invalid or missing fixture")
            target = Path(directory) / name; target.write_bytes(fixtures[name]); results.append(inspect(target, f))
    if {r["fps"] for r in results} != {24, 30}: raise ValueError("Both frame rates must be tested")
    microphone = []
    for r in reports:
        if r.get("videoOnly") is not False: continue
        capture = r.get("audio", {}); acquisition = capture.get("acquisition", {}); handoff = acquisition.get("handoff", {})
        if (acquisition.get("dedicatedReader") is not True or acquisition.get("readerTerminated") is not True or
                capture.get("pcmFramesRead") != capture.get("pcmFramesQueued") or
                handoff.get("overflowCount") != 0 or handoff.get("unsubmittedAcceptedFrames") != 0 or "timingQuality" not in r):
            raise ValueError("Microphone acquisition accounting failed")
        microphone.append({"mode": r["audioMode"], "clock": capture["clock"], "acquisition": acquisition,
                           "timingQuality": r["timingQuality"], "avStartOffsetUs": r["verification"].get("avStartOffsetUs"),
                           "avEndOffsetUs": r["verification"].get("avEndOffsetUs")})
    if len(microphone) < 6: raise ValueError("Missing real microphone recordings")
    warnings = sum(m["timingQuality"]["status"] == "warning" for m in microphone)
    return {"commit": manifest["appCommit"], "syntheticFixtures": results, "acquisitionLoadTest": load,
            "microphoneRecordings": microphone, "microphoneTimingWarnings": warnings,
            "microphoneTimingStatus": "warning" if warnings else "no_warning_observed",
            "physicalLipSyncVerified": False,
            "scope": "Known-content codec/mux alignment with explicit AAC priming bounds; actual microphone evidence remains separately classified"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_archive(args.archive), indent=2, allow_nan=False))
