#!/usr/bin/env python3
"""Independent marker and packet-cadence analysis for a P016 MP4."""
from __future__ import annotations

import array
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
from typing import Any

from p016_evidence_contract import MARKER_PROTOCOL, QualificationError, require


def _percentile(values: list[float], fraction: float) -> float:
    require(values, "cannot calculate a percentile of no samples")
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _event_starts(times: list[float], values: list[float], threshold: float,
                  minimum_samples: int, merge_gap_seconds: float) -> list[float]:
    require(len(times) == len(values) and times, "invalid event series")
    events: list[float] = []
    run_start: int | None = None
    for index, value in enumerate(values + [-math.inf]):
        active = value >= threshold
        if active and run_start is None:
            run_start = index
        elif not active and run_start is not None:
            if index - run_start >= minimum_samples:
                event_time = times[run_start]
                if not events or event_time - events[-1] >= merge_gap_seconds:
                    events.append(event_time)
            run_start = None
    return events


def detect_marker_from_series(video_times: list[float], brightness: list[float],
                              audio_times: list[float], rms: list[float]) -> dict[str, Any]:
    require(len(video_times) == len(brightness) and len(video_times) >= 30,
            "insufficient decoded video samples for marker detection")
    require(len(audio_times) == len(rms) and len(audio_times) >= 100,
            "insufficient decoded audio samples for marker detection")
    video_low = _percentile(brightness, 0.30)
    video_high = _percentile(brightness, 0.995)
    require(video_high - video_low >= 18.0, "no independently detectable full-frame flash contrast")
    flash_threshold = video_low + (video_high - video_low) * 0.62
    frame_period = statistics.median([b - a for a, b in zip(video_times, video_times[1:]) if b > a])
    require(math.isfinite(frame_period) and 0 < frame_period <= 0.2, "invalid decoded frame cadence")
    flashes = _event_starts(video_times, brightness, flash_threshold,
                            max(2, int(round(0.08 / frame_period))), 2.0)

    audio_low = _percentile(rms, 0.30)
    audio_high = _percentile(rms, 0.995)
    require(audio_high >= max(0.02, audio_low * 4.0), "no independently detectable tone contrast")
    tone_threshold = audio_low + (audio_high - audio_low) * 0.58
    audio_period = statistics.median([b - a for a, b in zip(audio_times, audio_times[1:]) if b > a])
    require(math.isfinite(audio_period) and 0 < audio_period <= 0.1, "invalid decoded audio analysis cadence")
    tones = _event_starts(audio_times, rms, tone_threshold,
                          max(3, int(round(0.08 / audio_period))), 2.0)

    pairs: list[tuple[float, float]] = []
    used: set[int] = set()
    for flash in flashes:
        choices = [(abs(tone - flash), index, tone) for index, tone in enumerate(tones) if index not in used]
        if not choices:
            continue
        distance, index, tone = min(choices)
        if distance <= 1.5:
            used.add(index)
            pairs.append((flash, tone))
    require(len(pairs) >= 2, "fewer than two paired flash/tone events were detected")
    pair_times = [(flash + tone) / 2 for flash, tone in pairs]
    intervals = [b - a for a, b in zip(pair_times, pair_times[1:])]
    require(any(7.0 <= interval <= 23.0 for interval in intervals),
            "detected events do not match the repeating ten-second protocol")
    offsets = [tone - flash for flash, tone in pairs]
    return {
        "protocol": MARKER_PROTOCOL,
        "verified": True,
        "flashEventsSeconds": flashes,
        "toneEventsSeconds": tones,
        "pairedEvents": [{"videoSeconds": v, "audioSeconds": a, "offsetSeconds": a - v} for v, a in pairs],
        "pairedEventCount": len(pairs),
        "interEventIntervalsSeconds": intervals,
        "offsetRangeSeconds": max(offsets) - min(offsets) if len(offsets) > 1 else 0.0,
        "flashThreshold": flash_threshold,
        "toneThreshold": tone_threshold,
        "physicalLipSyncVerified": False,
        "scope": "Repeated visible/acoustic event detection; playback-display, speaker, acoustic path and camera latencies are not calibrated lip-sync proof.",
    }


def _run(command: list[str], timeout: int = 360, binary: bool = False) -> bytes | str:
    completed = subprocess.run(command, capture_output=True, check=True, timeout=timeout,
                               text=not binary)
    stderr = completed.stderr if isinstance(completed.stderr, str) else completed.stderr.decode(errors="replace")
    if stderr.strip():
        raise QualificationError(f"external decoder reported errors: {stderr.strip()}")
    return completed.stdout


def inspect_marker(path: Path) -> dict[str, Any]:
    probe_text = _run([
        "ffprobe", "-v", "error", "-show_frames", "-show_streams",
        "-show_entries", "frame=media_type,best_effort_timestamp_time,nb_samples:stream=codec_type,sample_rate,channels",
        "-of", "json", str(path),
    ])
    require(isinstance(probe_text, str), "ffprobe did not return text")
    probe = json.loads(probe_text)
    streams = probe.get("streams", [])
    require(sum(s.get("codec_type") == "video" for s in streams) == 1 and
            sum(s.get("codec_type") == "audio" for s in streams) == 1,
            "marker analysis requires exactly one video and one audio stream")
    audio_stream = next(s for s in streams if s.get("codec_type") == "audio")
    require(int(audio_stream.get("sample_rate", 0)) == 48_000 and int(audio_stream.get("channels", 0)) == 1,
            "marker analysis requires the selected 48 kHz mono track")
    video_frames = [f for f in probe.get("frames", []) if f.get("media_type") == "video"]
    audio_frames = [f for f in probe.get("frames", []) if f.get("media_type") == "audio"]
    require(video_frames and audio_frames, "ffprobe returned no decodable frame timeline")
    video_times = [float(frame["best_effort_timestamp_time"]) for frame in video_frames]
    require(all(math.isfinite(value) for value in video_times) and
            all(b > a for a, b in zip(video_times, video_times[1:])),
            "decoded video frame timestamps are invalid")

    width, height = 32, 18
    gray = _run([
        "ffmpeg", "-nostdin", "-v", "error", "-xerror", "-err_detect", "explode", "-threads", "1",
        "-i", str(path), "-map", "0:v:0", "-an", "-vf", f"scale={width}:{height},format=gray",
        "-fps_mode", "passthrough", "-f", "rawvideo", "-",
    ], binary=True)
    require(isinstance(gray, bytes), "video decoder did not return bytes")
    pixels = width * height
    require(len(gray) == len(video_frames) * pixels,
            "decoded video bytes do not match the probed frame count")
    brightness = [sum(gray[index:index + pixels]) / pixels for index in range(0, len(gray), pixels)]

    pcm_bytes = _run([
        "ffmpeg", "-nostdin", "-v", "error", "-xerror", "-err_detect", "explode", "-threads", "1",
        "-i", str(path), "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "48000", "-f", "f32le", "-",
    ], binary=True)
    require(isinstance(pcm_bytes, bytes), "audio decoder did not return bytes")
    pcm = array.array("f")
    pcm.frombytes(pcm_bytes)
    if sys.byteorder != "little":
        pcm.byteswap()
    require(pcm, "decoded audio is empty")
    first_audio_time = float(audio_frames[0]["best_effort_timestamp_time"])
    window = 960
    audio_times: list[float] = []
    rms: list[float] = []
    for start in range(0, len(pcm) - window + 1, window):
        samples = pcm[start:start + window]
        audio_times.append(first_audio_time + start / 48_000)
        rms.append(math.sqrt(sum(sample * sample for sample in samples) / window))
    return detect_marker_from_series(video_times, brightness, audio_times, rms)


def inspect_cadence(path: Path, requested_fps: int) -> dict[str, Any]:
    require(requested_fps > 0, "requested fps must be positive")
    output = _run([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_packets",
        "-show_entries", "packet=pts_time,duration_time", "-of", "json", str(path),
    ])
    require(isinstance(output, str), "ffprobe did not return packet JSON")
    packets = json.loads(output).get("packets", [])
    require(len(packets) >= requested_fps * 10, "too few video packets for a physical cadence assessment")
    times = [float(packet["pts_time"]) for packet in packets]
    require(all(math.isfinite(value) for value in times), "non-finite video packet timestamp")
    require(sum(b <= a for a, b in zip(times, times[1:])) == 0,
            "non-monotonic video packet timestamps")
    intervals = [b - a for a, b in zip(times, times[1:])]
    expected = 1.0 / requested_fps
    large = [value for value in intervals if value > expected * 1.5]
    short = [value for value in intervals if value < expected * 0.5]
    measured = (len(times) - 1) / (times[-1] - times[0])
    rate_error = abs(measured - requested_fps) / requested_fps
    status = "pass" if not large and not short and rate_error <= 0.03 else "warning"
    return {
        "status": status,
        "requestedFps": requested_fps,
        "measuredPacketFps": measured,
        "relativeRateError": rate_error,
        "packetCount": len(times),
        "packetSpanSeconds": times[-1] - times[0],
        "largeIntervals": len(large),
        "shortIntervals": len(short),
        "maximumIntervalSeconds": max(intervals),
        "minimumIntervalSeconds": min(intervals),
        "timestampsStrictlyIncreasing": True,
        "scope": "Muxed video packet cadence; changing-content duplication still requires the visible marker and scene evidence.",
    }
