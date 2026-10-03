#!/usr/bin/env python3
"""P032 physical audiovisual synchronization on a host fixture.

Visible and audible events are estimated independently of container packet
starts. A documented fixture distance removes sound travel before the initial
offset is compared with the offset at the end of the take. Measurement
uncertainty stays on the report. Matching first-packet timestamps are not a
lip-sync certificate.

The deliberate mutant — using those matching packet timestamps as the sole
synchronization test — is rejected. This module does not probe a device, does
not qualify a physical S23, and does not execute TC-P032-01 through TC-P032-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P032"
CASE_ID = "P032"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-physical-av-sync-fixture"
METHOD = (
    "Record repeatable visible and audible events under documented geometry, estimate "
    "offsets independently, and report measurement uncertainty. Use multiple events "
    "across a longer take to separate fixed offset from drift. Account for sound "
    "travel when the fixture distance matters."
)
FIXTURE = (
    "A flash-and-click recording with a constant offset at the beginning and increased "
    "offset near the end."
)
ORACLE = (
    "The report distinguishes initial synchronization error from drift and does not "
    "certify lip sync from container starts alone."
)
MUTANT = "Use matching first packet timestamps as the sole synchronization test."
INDEPENDENT = "independent-events"
MUTANT_TEST = "matching-first-packets"
SOLE_TESTS = (INDEPENDENT, MUTANT_TEST)
POSITIONS = ("beginning", "middle", "end")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
CANONICAL_UINT = re.compile(r"0|[1-9][0-9]*")
NS_PER_S = 1_000_000_000
HOST_LIMIT = "a host estimate does not qualify a physical S23"
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "geometry",
    "packetStarts",
    "events",
}
GEOMETRY_KEYS = {"fixtureDistanceMm", "speedOfSoundMmPerS", "documented"}
PACKET_KEYS = {"videoFirstNs", "audioFirstNs"}
EVENT_KEYS = {"id", "position", "visibleNs", "audibleNs", "uncertaintyNs"}
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "withheld", "sync_failed"}


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


def _uint(value: object, label: str) -> str:
    require(isinstance(value, str) and CANONICAL_UINT.fullmatch(value) is not None,
            label + " must be a canonical non-negative integer string")
    return value


def _positive(value: object, label: str) -> str:
    text = _uint(value, label)
    require(text != "0", label + " must be positive")
    return text


def _canonical(value: int) -> str:
    if value == 0:
        return "0"
    if value < 0:
        return "-" + str(-value)
    return str(value)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def event_token(event: dict) -> str:
    """Stable inventory token. Measured times are not rewritten."""
    return (
        f"{event['id']}@{event['position']}:visible={event['visibleNs']}"
        f":audible={event['audibleNs']}:u={event['uncertaintyNs']}"
    )


def sound_travel_ns(distance_mm: str, speed_mm_per_s: str) -> tuple[int, int]:
    """Integer sound-travel delay and the truncated remainder, both in nanoseconds."""
    distance = int(_positive(distance_mm, "fixtureDistanceMm"))
    speed = int(_positive(speed_mm_per_s, "speedOfSoundMmPerS"))
    numerator = distance * NS_PER_S
    return numerator // speed, numerator % speed


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS and decision not in _FORBIDDEN,
            "P032 must not decide qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons),
            "reasons must be a non-empty list of strings")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": _dedupe(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def _event(value: object, index: int, seen: set[str]) -> dict:
    item = exact_keys(value, EVENT_KEYS, f"event {index}")
    ident = _text(item["id"], f"event {index} id")
    require(ident not in seen, "duplicate event id: " + ident)
    seen.add(ident)
    position = _text(item["position"], f"event {index} position")
    require(position in POSITIONS, f"event {index} position must be beginning, middle, or end")
    _uint(item["visibleNs"], f"event {index} visibleNs")
    _uint(item["audibleNs"], f"event {index} audibleNs")
    _uint(item["uncertaintyNs"], f"event {index} uncertaintyNs")
    return item


def _geometry(value: object) -> dict:
    item = exact_keys(value, GEOMETRY_KEYS, "geometry")
    require(type(item["documented"]) is bool, "geometry documented must be a bool")
    if item["documented"]:
        _positive(item["fixtureDistanceMm"], "fixtureDistanceMm")
    else:
        _uint(item["fixtureDistanceMm"], "fixtureDistanceMm")
    _positive(item["speedOfSoundMmPerS"], "speedOfSoundMmPerS")
    return item


def _packets(value: object) -> dict:
    item = exact_keys(value, PACKET_KEYS, "packetStarts")
    _uint(item["videoFirstNs"], "packetStarts videoFirstNs")
    _uint(item["audioFirstNs"], "packetStarts audioFirstNs")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P032 physical-sync fixture shape."""
    exact_keys(document, DOCUMENT_KEYS, "sync document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P032")
    require(document["mapId"] == MAP_ID, "mapId must be s23-physical-av-sync-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "sync document needs the P032 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    _geometry(document["geometry"])
    _packets(document["packetStarts"])
    events = document["events"]
    require(isinstance(events, list) and events, "events must be a non-empty list")
    seen: set[str] = set()
    for index, item in enumerate(events):
        _event(item, index, seen)
    begins = [item for item in events if item["position"] == "beginning"]
    ends = [item for item in events if item["position"] == "end"]
    require(len(begins) == 1, "exactly one beginning event is required")
    require(len(ends) == 1, "exactly one end event is required")


def _corrected(event: dict, travel: int) -> int:
    return int(event["audibleNs"]) - int(event["visibleNs"]) - travel


def _measure(document: dict) -> dict[str, Any]:
    geometry = document["geometry"]
    packets = document["packetStarts"]
    events = document["events"]
    beginning = next(item for item in events if item["position"] == "beginning")
    end = next(item for item in events if item["position"] == "end")
    middles = [item for item in events if item["position"] == "middle"]
    documented = geometry["documented"] is True
    if documented:
        travel, remainder = sound_travel_ns(
            geometry["fixtureDistanceMm"], geometry["speedOfSoundMmPerS"]
        )
    else:
        travel, remainder = 0, 0
    initial = _corrected(beginning, travel) if documented else None
    end_offset = _corrected(end, travel) if documented else None
    begin_u = int(beginning["uncertaintyNs"])
    end_u = int(end["uncertaintyNs"])
    drift = (end_offset - initial) if documented else None
    return {
        "documented": documented,
        "travel": travel,
        "remainder": remainder,
        "initial": initial,
        "end_offset": end_offset,
        "drift": drift,
        "begin_u": begin_u,
        "end_u": end_u,
        "beginning": beginning,
        "end": end,
        "middles": middles,
        "video": packets["videoFirstNs"],
        "audio": packets["audioFirstNs"],
        "initial_outside": documented and abs(initial) > begin_u,
        "drift_outside": documented and abs(drift) > (begin_u + end_u),
    }


def _preserved(document: dict, measured: dict[str, Any]) -> list[str]:
    preserved = [f"container:video={measured['video']}:audio={measured['audio']}"]
    preserved.extend(event_token(item) for item in document["events"])
    if not measured["documented"]:
        preserved.append("sound-travel:unaccounted")
        return preserved
    preserved.append(f"sound-travel:{_canonical(measured['travel'])}ns")
    preserved.append(f"initial-offset:{_canonical(measured['initial'])}ns")
    preserved.append(f"end-offset:{_canonical(measured['end_offset'])}ns")
    preserved.append(f"drift:{_canonical(measured['drift'])}ns")
    return preserved


def assess(document: dict, sole_test: str = INDEPENDENT) -> dict:
    """Separate initial sync error from drift. Never certify container starts.

    sole_test "matching-first-packets" is the mutant. It is rejected even when
    the first video and audio packet timestamps are equal. Physical event
    tokens and the corrected offsets stay in preservedResults.
    """
    validate_document(document)
    require(sole_test in SOLE_TESTS, "sole_test must be independent-events or matching-first-packets")
    measured = _measure(document)
    preserved = _preserved(document, measured)
    rejected: list[str] = []
    questions = ["host fixture is not a physical S23 measurement"]
    reasons = [ORACLE]

    if measured["documented"]:
        reasons.append(
            f"initial synchronization error {_canonical(measured['initial'])}ns "
            f"after sound travel {_canonical(measured['travel'])}ns"
        )
        reasons.append(
            f"drift {_canonical(measured['drift'])}ns separates the end event from the initial error"
        )
        reasons.append(
            f"measurement uncertainty begin {measured['begin_u']}ns end {measured['end_u']}ns"
        )
        if measured["remainder"]:
            reasons.append(
                f"sound travel truncation remainder {measured['remainder']}ns widens the report"
            )
            questions.append(f"sound-travel truncation remainder {measured['remainder']}ns")
        if measured["initial_outside"]:
            rejected.append("initial-sync-error")
        if measured["drift_outside"]:
            rejected.append("drift")
        begin_u = measured["begin_u"]
        initial = measured["initial"]
        for middle in measured["middles"]:
            mid_offset = _corrected(middle, measured["travel"])
            mid_u = int(middle["uncertaintyNs"])
            if abs(mid_offset - initial) > (begin_u + mid_u):
                rejected.append("middle-drift")
                reasons.append(
                    f"middle event {middle['id']} offset {_canonical(mid_offset)}ns "
                    "disagrees with the initial error"
                )
    else:
        reasons.append("fixture distance is not documented so sound travel was not applied")
        questions.append("sound travel was not applied")

    reasons.append("matching first packet timestamps are not the synchronization test")
    aligned = measured["video"] == measured["audio"]
    if aligned:
        reasons.append("aligned container starts do not certify lip sync")
        rejected.append("container-start-lip-sync")
    else:
        reasons.append("container timing stays distinct from the physical offset")

    if sole_test == MUTANT_TEST:
        decision = "rejected"
        rejected.insert(0, "matching-first-packet-timestamps")
        reasons.append(MUTANT)
        questions.append("packet-only synchronization was rejected")
    elif not measured["documented"]:
        decision = "withheld"
    elif measured["initial_outside"] or measured["drift_outside"] or "middle-drift" in rejected:
        decision = "sync_failed"
        questions.append("physical sync gate failed")
    else:
        decision = "withheld"
        questions.append("offsets are inside reported uncertainty; lip sync is still not certified")

    reasons.append(HOST_LIMIT)
    return _result(decision, reasons, rejected, preserved, questions)
