#!/usr/bin/env python3
"""P028 host gate for two-track mux startup and drain.

Wait for every selected track format before the muxer starts. Pre-start
samples stay inside a bound. Each track reaches EOS on its own. Drain has a
maximum duration. The track that failed is recorded, and useful partial output
stays under an unverified label.

The mutant starts the muxer after the first track and ignores later selected
tracks. This module does not probe a device, does not qualify a physical S23,
and does not execute TC-P028-01 through TC-P028-08.
"""

from __future__ import annotations

import re
from typing import Any


BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
PHASE_ID = "P028"
CONTRACT_ID = "s23-two-track-startup-drain-fixture"
METHOD = (
    "Wait for all selected track formats before starting the muxer. "
    "Bound pre-start samples, coordinate EOS independently, and define maximum drain duration. "
    "Record which track failed and preserve useful partial output under an unverified label."
)
FIXTURE = (
    "Video format arrives immediately, audio format arrives late, then Stop occurs before audio EOS."
)
ORACLE = (
    "The state machine produces the correct incomplete or verified outcome "
    "without deadlock or fabricated audio samples."
)
MUTANT = "Start the muxer after the first track and ignore later selected tracks."
MUTANT_CLAIM = "mux-started-on-first-track"
TRACKS = ("video", "audio")
KINDS = ("format", "sample", "stop", "eos")
MUX_POLICIES = ("wait-for-all-formats", "start-on-first-track")
DRAIN_POLICIES = ("bounded", "wait-forever")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
FIXTURE_KEYS = {
    "schemaVersion",
    "phase",
    "contractId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "takeId",
    "selectedTracks",
    "maxPreStartSamples",
    "maxDrainDurationMs",
    "partialOutput",
    "muxPolicy",
    "drainPolicy",
    "events",
}
EVENT_KEYS = {"index", "kind", "track", "atMs", "fabricated"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
HOST_LIMIT = "host fixture does not qualify a physical S23"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def _text(value: object, label: str) -> str:
    require(isinstance(value, str) and bool(value) and value == value.strip(),
            label + " must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def validate_fixture(document: dict) -> None:
    """Raise ValueError unless document is the P028 two-track mux fixture."""
    exact_keys(document, FIXTURE_KEYS, "mux contract")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE_ID, "phase must be P028")
    require(document["contractId"] == CONTRACT_ID,
            "contractId must be s23-two-track-startup-drain-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "mux contract needs the P028 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    _text(document["takeId"], "takeId")
    _text(document["partialOutput"], "partialOutput")
    selected = document["selectedTracks"]
    require(isinstance(selected, list) and sorted(selected) == ["audio", "video"],
            "selectedTracks must be video and audio")
    require(len(selected) == len(set(selected)), "selectedTracks must be unique")
    pre = document["maxPreStartSamples"]
    drain = document["maxDrainDurationMs"]
    require(type(pre) is int and pre > 0, "maxPreStartSamples must be a positive int")
    require(type(drain) is int and drain > 0, "maxDrainDurationMs must be a positive int")
    require(document["muxPolicy"] in MUX_POLICIES, "muxPolicy is not a known startup policy")
    require(document["drainPolicy"] in DRAIN_POLICIES, "drainPolicy is not a known drain policy")
    events = document["events"]
    require(isinstance(events, list) and events, "events must be a non-empty list")
    seen_format: set[str] = set()
    seen_eos: set[str] = set()
    seen_stop = False
    last_ms: int | None = None
    for index, event in enumerate(events):
        exact_keys(event, EVENT_KEYS, f"event {index}")
        require(type(event["index"]) is int and event["index"] == index,
                f"event {index} index must be contiguous from zero")
        kind = event["kind"]
        require(kind in KINDS, f"event {index} kind is unknown")
        track = event["track"]
        at_ms = event["atMs"]
        require(type(at_ms) is int and at_ms >= 0, f"event {index} atMs must be a non-negative int")
        if last_ms is not None:
            require(at_ms >= last_ms, f"event {index} atMs moved backwards")
        last_ms = at_ms
        fabricated = _bool(event["fabricated"], f"event {index} fabricated")
        if kind == "stop":
            require(track == "session", f"event {index} stop track must be session")
            require(not seen_stop, "stop may occur once")
            require(fabricated is False, "stop cannot be fabricated")
            seen_stop = True
            continue
        require(track in TRACKS, f"event {index} track must be video or audio")
        require(track in selected, f"event {index} track is not selected")
        if kind == "format":
            require(fabricated is False, "format cannot be fabricated")
            require(track not in seen_format, f"duplicate format for {track}")
            seen_format.add(track)
        elif kind == "sample":
            require(track in seen_format, f"sample before {track} format")
        else:
            require(fabricated is False, "eos cannot be fabricated")
            require(track in seen_format, f"eos before {track} format")
            require(track not in seen_eos, f"duplicate eos for {track}")
            seen_eos.add(track)


def _ready(policy: str, formats: list[str], selected: list[str]) -> bool:
    if policy == "start-on-first-track":
        return bool(formats)
    return all(track in formats for track in selected)


def trace_mux(document: dict) -> dict[str, Any]:
    """Replay startup, pre-start samples, independent EOS, and the drain bound."""
    validate_fixture(document)
    selected = list(document["selectedTracks"])
    formats: list[str] = []
    mux_started = False
    mux_start_ms: int | None = None
    formats_at_mux: list[str] = []
    pre_start = 0
    counts = {track: 0 for track in selected}
    fabricated_audio = False
    fabricated_video = False
    stop_ms: int | None = None
    for event in document["events"]:
        kind = event["kind"]
        track = event["track"]
        if kind == "format":
            formats.append(track)
            if not mux_started and _ready(document["muxPolicy"], formats, selected):
                mux_started = True
                mux_start_ms = event["atMs"]
                formats_at_mux = list(formats)
        elif kind == "sample":
            counts[track] += 1
            if event["fabricated"] and track == "audio":
                fabricated_audio = True
            if event["fabricated"] and track == "video":
                fabricated_video = True
            if not mux_started:
                pre_start += 1
        elif kind == "stop":
            stop_ms = event["atMs"]
    limit: int | None = None
    if stop_ms is not None and document["drainPolicy"] == "bounded":
        limit = stop_ms + document["maxDrainDurationMs"]
    eos_tracks: list[str] = []
    for event in document["events"]:
        if event["kind"] != "eos":
            continue
        if limit is not None and event["atMs"] > limit:
            continue
        eos_tracks.append(event["track"])
    failed = [track for track in selected if track not in eos_tracks]
    if mux_started:
        ignored = [track for track in selected if track not in formats_at_mux]
    else:
        ignored = []
    early = document["muxPolicy"] == "start-on-first-track" or bool(ignored)
    deadlock = document["drainPolicy"] == "wait-forever" and stop_ms is not None and bool(failed)
    return {
        "muxStarted": mux_started,
        "muxStartMs": mux_start_ms,
        "formatsAtMux": formats_at_mux,
        "ignoredTracks": ignored,
        "preStartSamples": pre_start,
        "eosTracks": eos_tracks,
        "failedTracks": failed,
        "fabricatedAudio": fabricated_audio,
        "fabricatedVideo": fabricated_video,
        "deadlock": deadlock,
        "earlyMux": early,
        "stopMs": stop_ms,
        "sampleCounts": counts,
    }


def ignores_later_selected_tracks(document: dict) -> bool:
    """True when the muxer starts on the first format and leaves a selected track out.

    That is the mutant: start after the first track and ignore later selected tracks.
    """
    return bool(trace_mux(document)["earlyMux"])


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict[str, Any]:
    require(decision not in {"qualified", "allowed"}, "decision must not be qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons),
            "reasons must be a non-empty list of strings")
    result = {
        "caseId": PHASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def assess_mux(document: dict) -> dict[str, Any]:
    """Decide incomplete or protocol-complete without fabricating audio or deadlocking.

    decision is unverified_partial when a selected track misses EOS inside the
    drain bound and partial output is kept. decision is protocol_complete only
    when every selected format arrived before mux start, EOS landed inside the
    bound, and no audio sample was fabricated. decision is rejected for the
    first-track mutant, fabricated samples, a blown pre-start bound, or a
    drain that waits forever. preservedResults keep the partial output, the
    take id, and every selected track even when the decision fails.
    protocol_complete is not a physical verification.
    """
    trace = trace_mux(document)
    preserved = [document["partialOutput"], document["takeId"]]
    preserved.extend(document["selectedTracks"])
    for track in document["selectedTracks"]:
        preserved.append(f"{track}-samples:{trace['sampleCounts'][track]}")
    for track in trace["failedTracks"]:
        preserved.append("failed:" + track)

    rejected: list[str] = []
    reasons = ["two-track mux protocol assessed for " + document["takeId"]]
    questions = [HOST_LIMIT]
    if trace["earlyMux"]:
        rejected.append(MUTANT_CLAIM)
        ignored = ", ".join(trace["ignoredTracks"]) or "later-selected-track"
        reasons.append("muxer started before every selected track format; ignored " + ignored)
    if trace["fabricatedAudio"]:
        rejected.append("fabricated-audio")
        reasons.append("audio samples must not be fabricated to finish a track")
    if trace["fabricatedVideo"]:
        rejected.append("fabricated-video")
        reasons.append("video samples must not be fabricated")
    if trace["preStartSamples"] > document["maxPreStartSamples"]:
        rejected.append("pre-start-bound-exceeded")
        reasons.append("pre-start samples exceeded the declared bound")
    if trace["deadlock"]:
        rejected.append("deadlock")
        reasons.append("drain waited forever for a missing EOS")

    if rejected:
        decision = "rejected"
        questions.append("rejected startup or drain is not a verified recording")
    elif document["drainPolicy"] != "bounded":
        decision = "withheld"
        reasons.append("maximum drain duration is not in force")
        questions.append("drain duration withheld")
    elif trace["failedTracks"]:
        decision = "unverified_partial"
        reasons.append("partial output retained under an unverified label")
        reasons.append("failed tracks: " + ",".join(trace["failedTracks"]))
        questions.append("partial output is unverified")
    else:
        decision = "protocol_complete"
        reasons.append("muxer waited for every selected track format")
        reasons.append("selected tracks reached EOS inside the drain bound without fabricated audio")
        questions.append("protocol completion is not physical S23 qualification")
    return _result(decision, reasons, rejected, preserved, questions)
