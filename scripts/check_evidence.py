#!/usr/bin/env python3
"""Require real device reports plus fully decoded videos in the CI evidence bundle."""
import json
from pathlib import Path, PurePosixPath
import sys
import tarfile


def verify(archive: Path, videos: Path, require_audio: bool = False) -> dict:
    clips = json.loads(videos.read_text())
    if len(clips) < 12 or not all(c.get("fullDecodePassed") is True for c in clips):
        raise ValueError("Expected twelve independently decoded recordings")
    if max(c["packetSpanSeconds"] for c in clips) < 60:
        raise ValueError("No recording contains at least sixty seconds of packet timestamps")
    reports, probes, text_reports = [], [], set()
    # Read regular files only. Never extract device paths into the host filesystem.
    with tarfile.open(archive) as tar:
        for member in tar:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or member.issym() or member.islnk():
                raise ValueError("Unsafe path in device evidence")
            if not member.isfile():
                continue
            name = str(path)
            if name.startswith("files/exports/reports/") and name.endswith(".txt"):
                if member.size > 0:
                    text_reports.add(name[:-4])
            is_recording = name.startswith("files/exports/validation/recording-") and name.endswith(".json")
            is_probe = name.startswith("files/exports/reports/report-") and name.endswith(".json")
            if not (is_recording or is_probe):
                continue
            if not 0 < member.size <= 16 * 1024 * 1024:
                raise ValueError("Empty or oversized device report")
            with tar.extractfile(member) as source:
                report = json.load(source)
            if is_recording:
                if report.get("kind") != "recording-validation" or report.get("status") != "checked":
                    raise ValueError("A recording was rejected or lacks validation")
                if report.get("verification", {}).get("firstSyncFrameDecoded") is not True:
                    raise ValueError("Missing device-side decode evidence")
                if "container_and_output_checked" not in report.get("stages", []):
                    raise ValueError("Missing completed recording stage")
                reports.append(report)
            else:
                if report.get("schemaVersion") != 2:
                    raise ValueError("Unexpected probe schema")
                probes.append(name[:-5])
    if len(reports) != len(clips):
        raise ValueError("Recording report count does not match captured files")
    if not probes or not all(p in text_reports for p in probes):
        raise ValueError("Complete JSON/text capability reports were not preserved")
    if max(r["verification"].get("sampleSpanUs", 0) for r in reports) < 60_000_000:
        raise ValueError("Device reports contain no sixty-second recording")
    audio_clips = [c for c in clips if c.get("audioPresent") is True]
    audio_reports = [r for r in reports if r.get("videoOnly") is False]
    if require_audio:
        if len(audio_clips) < 6 or len(audio_reports) != len(audio_clips):
            raise ValueError("Missing repeated, sustained and stereo audio/video capture evidence")
        if not all(c.get("audioFullDecodePassed") is True for c in audio_clips):
            raise ValueError("Audio tracks were not independently decoded")
        if max(c.get("audioPacketSpanSeconds", 0) for c in audio_clips) < 60:
            raise ValueError("No sustained audio recording")
        if not any(c.get("audioStream", {}).get("channels") == 2 for c in audio_clips):
            raise ValueError("Stereo capture was not exercised")
        for report in audio_reports:
            if (report.get("schemaVersion") != 3 or report.get("physicalLipSyncVerified") is not False or
                "av_samples_written" not in report.get("stages", []) or
                report.get("verification", {}).get("firstAudioPcmDecoded") is not True or
                report.get("audio", {}).get("builtInRouteConfirmed") is not True or
                report.get("audio", {}).get("clock", {}).get("source") not in
                    {"audio_timestamp_monotonic", "read_completion_estimate_unverified"}):
                raise ValueError("Missing actual microphone/clock/decoded-audio evidence")
    return {"recordings": len(clips), "recordingReports": len(reports), "probeReports": len(probes),
            "longestPacketSpanSeconds": max(c["packetSpanSeconds"] for c in clips),
            "audioRecordings": len(audio_clips), "allAudioFullyDecoded": all(c.get("audioFullDecodePassed") is True for c in audio_clips) if audio_clips else None,
            "allVideosFullyDecoded": True, "physicalLipSyncVerified": False, "scope": "emulator evidence; not physical S23 Ultra validation"}


if __name__ == "__main__":
    try:
        if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and sys.argv[3] != "--require-audio"):
            raise ValueError("Usage: check_evidence.py app-evidence.tar ffprobe.json [--require-audio]")
        print(json.dumps(verify(Path(sys.argv[1]), Path(sys.argv[2]), len(sys.argv) == 4), indent=2, allow_nan=False))
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError) as error:
        print(f"Evidence validation failed: {error}", file=sys.stderr)
        sys.exit(1)
