#!/usr/bin/env python3
"""P029 cadence analyzer and source-to-output time mapping.

Original timestamp intervals, duplicates, discontinuities, duration, and count
stay in the result. Packet order is not rewritten into presentation order when
a codec reorders frames. A named retiming operation may carry mapping metadata.
It is development, not a repair that becomes native capture.

The deliberate mutant — approving cadence from total frames divided by duration
— is rejected when a per-frame gap remains, even if that quotient restores the
average. This module does not probe a device, does not qualify a physical S23,
and does not execute TC-P029-01 through TC-P029-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P029"
CASE_ID = "P029"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-cadence-fixture"
METHOD = (
    "Analyze original timestamp intervals, duplicates, discontinuities, duration, and count. "
    "Keep packet ordering distinct from presentation ordering when codec reordering exists. "
    "Any retiming is a named development operation with mapping metadata, not repair disguised "
    "as native capture."
)
FIXTURE = (
    "A source containing one forty-eight-millisecond gap and a later short interval that "
    "restores the average frame rate."
)
ORACLE = (
    "The per-frame integrity gate reports the gap even when the final average falls within "
    "tolerance."
)
MUTANT = "Approve cadence using only total frames divided by duration."
RETIMING_OPERATION = "constant_frame_rate_development"

HEX40 = re.compile(r"^[0-9a-f]{40}$")
CANONICAL_UINT = re.compile(r"0|[1-9][0-9]*")

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "nominalIntervalMs",
    "toleranceMs",
    "frames",
    "retiming",
}
FRAME_KEYS = {
    "id",
    "packetIndex",
    "presentationIndex",
    "timestampMs",
    "duplicate",
    "contentId",
}
RETIMING_KEYS = {
    "operation",
    "mappingId",
    "sourceFrameIds",
    "outputIntervalMs",
    "claimNativeCapture",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"cadence_defect", "rejected", "withheld"}
_FORBIDDEN = {"qualified", "allowed"}


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


def _positive_uint(value: object, label: str) -> str:
    text = _uint(value, label)
    require(text != "0", label + " must be positive")
    return text


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def _index(value: object, label: str, count: int) -> int:
    require(type(value) is int and not isinstance(value, bool), label + " must be an int")
    require(0 <= value < count, label + " must be inside the frame permutation")
    return value


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def frame_token(frame: dict) -> str:
    """Stable inventory token. The original timestamp is not rewritten."""
    flag = "1" if frame["duplicate"] else "0"
    return (
        f"{frame['id']}#p{frame['packetIndex']}/r{frame['presentationIndex']}"
        f"@{frame['timestampMs']}ms:{frame['contentId']}:dup{flag}"
    )


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS and decision not in _FORBIDDEN,
            "P029 must not decide qualified or allowed")
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


def _frame(value: object, index: int, count: int, seen_ids: set[str]) -> dict:
    item = exact_keys(value, FRAME_KEYS, f"frame {index}")
    ident = _text(item["id"], f"frame {index} id")
    require(ident not in seen_ids, "duplicate frame id: " + ident)
    seen_ids.add(ident)
    _index(item["packetIndex"], f"frame {index} packetIndex", count)
    _index(item["presentationIndex"], f"frame {index} presentationIndex", count)
    _uint(item["timestampMs"], f"frame {index} timestampMs")
    _bool(item["duplicate"], f"frame {index} duplicate")
    _text(item["contentId"], f"frame {index} contentId")
    return item


def _permutation(frames: list[dict], key: str) -> None:
    indexes = [item[key] for item in frames]
    require(sorted(indexes) == list(range(len(frames))),
            key + " values must be a permutation of 0..n-1")


def _retiming(value: object, known_ids: set[str]) -> dict | None:
    if value is None:
        return None
    item = exact_keys(value, RETIMING_KEYS, "retiming")
    require(item["operation"] == RETIMING_OPERATION,
            "retiming operation must be constant_frame_rate_development")
    _text(item["mappingId"], "retiming mappingId")
    sources = item["sourceFrameIds"]
    require(isinstance(sources, list) and sources, "retiming sourceFrameIds must be a non-empty list")
    require(len(sources) == len(set(sources)), "retiming sourceFrameIds must be unique")
    for source in sources:
        require(isinstance(source, str) and source in known_ids,
                "retiming names an unknown source frame")
    _positive_uint(item["outputIntervalMs"], "retiming outputIntervalMs")
    _bool(item["claimNativeCapture"], "retiming claimNativeCapture")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P029 cadence fixture schema."""
    exact_keys(document, DOCUMENT_KEYS, "cadence document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P029")
    require(document["mapId"] == MAP_ID, "mapId must be s23-cadence-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "cadence document needs the P029 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    _positive_uint(document["nominalIntervalMs"], "nominalIntervalMs")
    _uint(document["toleranceMs"], "toleranceMs")
    frames = document["frames"]
    require(isinstance(frames, list) and len(frames) >= 2, "frames must contain at least two frames")
    seen: set[str] = set()
    parsed = [_frame(item, index, len(frames), seen) for index, item in enumerate(frames)]
    _permutation(parsed, "packetIndex")
    _permutation(parsed, "presentationIndex")
    _retiming(document["retiming"], seen)


def _packet_order(frames: list[dict]) -> list[dict]:
    return sorted(frames, key=lambda item: item["packetIndex"])


def _presentation_order(frames: list[dict]) -> list[dict]:
    return sorted(frames, key=lambda item: item["presentationIndex"])


def source_intervals(document: dict) -> list[int]:
    """Original intervals in packet order, in milliseconds.

    Presentation order is not consulted. A codec reorder cannot hide a gap by
    changing which frame is displayed next.
    """
    validate_document(document)
    packet = _packet_order(document["frames"])
    return [
        int(right["timestampMs"]) - int(left["timestampMs"])
        for left, right in zip(packet, packet[1:])
    ]


def frames_divided_by_duration_would_approve(document: dict) -> bool:
    """The mutant: one quotient from frame count and duration, no per-frame gaps.

    Implied interval is duration / (frame_count - 1), which is what total span
    divided across the steps between frames reports. Individual intervals are
    ignored. True means that quotient sits within tolerance of nominal. It is
    not a cadence decision and must not be copied into assess.
    """
    validate_document(document)
    packet = _packet_order(document["frames"])
    nominal = int(document["nominalIntervalMs"])
    tolerance = int(document["toleranceMs"])
    duration = int(packet[-1]["timestampMs"]) - int(packet[0]["timestampMs"])
    steps = len(packet) - 1
    if steps <= 0 or duration <= 0:
        return False
    return abs(duration - nominal * steps) <= tolerance * steps


def _interval_rows(packet: list[dict]) -> list[tuple[dict, dict, int]]:
    rows: list[tuple[dict, dict, int]] = []
    for left, right in zip(packet, packet[1:]):
        rows.append((left, right, int(right["timestampMs"]) - int(left["timestampMs"])))
    return rows


def assess(document: dict) -> dict:
    """Report per-frame cadence defects even when the average is in tolerance.

    Preserved results keep every original frame token, both orderings, every
    packet-order interval, duration, and count. A mean that matches nominal
    does not delete a forty-eight-millisecond gap. Decision is never qualified
    or allowed. Retiming metadata is kept beside the source and does not become
    native capture.
    """
    validate_document(document)
    frames = document["frames"]
    packet = _packet_order(frames)
    presentation = _presentation_order(frames)
    nominal = int(document["nominalIntervalMs"])
    tolerance = int(document["toleranceMs"])
    rows = _interval_rows(packet)
    duration = int(packet[-1]["timestampMs"]) - int(packet[0]["timestampMs"])
    count = len(packet)
    mean_approves = frames_divided_by_duration_would_approve(document)

    preserved = [frame_token(item) for item in packet]
    preserved.append(f"duration:{duration}ms")
    preserved.append(f"count:{count}")
    preserved.append(f"nominal:{nominal}ms")
    preserved.append(f"tolerance:{tolerance}ms")
    preserved.append("packet-order:" + ",".join(item["id"] for item in packet))
    preserved.append("presentation-order:" + ",".join(item["id"] for item in presentation))
    for left, right, delta in rows:
        preserved.append(f"interval:{left['id']}->{right['id']}:{delta}ms")

    gaps = [(left, right, delta) for left, right, delta in rows if delta > nominal + tolerance]
    shorts = [
        (left, right, delta)
        for left, right, delta in rows
        if 0 <= delta < nominal - tolerance
    ]
    reversals = [row for row in rows if row[2] < 0]
    zeros = [row for row in rows if row[2] == 0]
    duplicates = [item for item in frames if item["duplicate"] is True]
    content_ids: dict[str, list[str]] = {}
    for item in frames:
        content_ids.setdefault(item["contentId"], []).append(item["id"])
    repeated = [content for content, ids in content_ids.items() if len(ids) > 1]

    rejected: list[str] = []
    if gaps or shorts or reversals or zeros or duplicates or repeated:
        rejected.append("source-cadence-defect")
    for _left, _right, delta in gaps:
        rejected.append(f"gap:{delta}ms")
        if delta == 48:
            rejected.append("forty-eight-millisecond-gap")
    if shorts:
        rejected.append("short-interval")
    if reversals:
        rejected.append("timestamp-reversal")
    if zeros or duplicates:
        rejected.append("duplicate-timestamp")
    if repeated:
        rejected.append("repeated-image-content")

    reordered = [item["id"] for item in packet] != [item["id"] for item in presentation]
    questions: list[str] = []
    if reordered:
        questions.append("packet ordering is distinct from presentation ordering")

    retiming = document["retiming"]
    native_claim = retiming is not None and retiming["claimNativeCapture"] is True
    if retiming is not None:
        preserved.append(
            "retiming:"
            f"{retiming['operation']}:{retiming['mappingId']}:{retiming['outputIntervalMs']}ms"
        )
        preserved.append(
            "claim-native:" + ("true" if retiming["claimNativeCapture"] else "false")
        )
        questions.append("retiming is a named development operation, not native capture")
    if native_claim:
        rejected.append("retiming-disguised-as-native")

    defect = "source-cadence-defect" in rejected
    if defect and mean_approves:
        rejected.append("frames-divided-by-duration")
        questions.append("average within tolerance does not hide the source gap")

    if native_claim:
        decision = "rejected"
    elif defect:
        decision = "cadence_defect"
    else:
        decision = "withheld"
        questions.append("host fixture does not certify fixed cadence")

    later_short = False
    if gaps and shorts:
        first_gap_at = min(left["packetIndex"] for left, _right, _delta in gaps)
        later_short = any(left["packetIndex"] > first_gap_at for left, _right, _delta in shorts)

    reasons = [ORACLE]
    if gaps:
        reasons.append("per-frame integrity reports the gap")
    if any(delta == 48 for _left, _right, delta in gaps):
        reasons.append("forty-eight-millisecond gap remains visible")
    if later_short:
        reasons.append("a later short interval is recorded and does not repair the gap")
    if defect and mean_approves:
        reasons.append("the final average falls within tolerance")
        reasons.append("source discontinuities are not replaced by the average")
        reasons.append("approving cadence from total frames divided by duration is rejected")
        reasons.append(MUTANT)
    elif defect:
        reasons.append("the final average is outside tolerance and the per-frame defect remains")
    if reordered:
        reasons.append("packet ordering stays distinct from presentation ordering")
    if retiming is not None and not native_claim:
        reasons.append("source-to-output mapping is development metadata, not native capture")
    if native_claim:
        reasons.append("retiming must not be disguised as native capture")
    reasons.append(f"analyzed count {count} and duration {duration}ms")
    if decision == "withheld":
        reasons.append(
            "uniform host intervals are not fixed cadence and not physical S23 qualification"
        )
    reasons.append("original timestamp evidence is preserved")
    return _result(decision, reasons, rejected, preserved, questions)
