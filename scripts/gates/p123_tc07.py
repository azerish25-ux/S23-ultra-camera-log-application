"""TC-P123-07 Resume boundary duplication.

Host fixture. Overlapping chunks emit each intended frame once. A playable
assembly that repeats the overlap fails cadence integrity. Omitted boundary
frames fail the same declared timeline.
"""

from __future__ import annotations

import math


CASE_ID = "TC-P123-07"
NAME = "Resume boundary duplication"
INTERVENTION = "Assemble chunks whose temporal overlap contains repeated or omitted output frames."
EXPECTED = "Emit the exact intended timeline once and maintain declared temporal continuity."
NEGATIVE = "A playable movie with duplicated overlap frames must fail cadence integrity."
REPEAT = "Repeat fractional rates, audio-bearing clips, and scene cuts at boundaries."
REPEATS = ("fractional-rate", "audio-bearing", "scene-cut")
PAYLOAD_KEYS = (
    "evidenceId",
    "chunks",
    "assembledFrames",
    "declaredContinuity",
    "rate",
    "audioBearing",
    "sceneCutAtBoundary",
    "repeat",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def chunk_union(chunks: list[dict]) -> list[int]:
    """Frames covered by the chunks, each index once, in first-seen order."""
    seen: set[int] = set()
    frames: list[int] = []
    for chunk in chunks:
        for frame in range(chunk["start"], chunk["end"] + 1):
            if frame not in seen:
                seen.add(frame)
                frames.append(frame)
    return frames


def evaluate(payload: dict) -> dict:
    """Reject duplicated overlap frames and omitted boundary frames."""
    fields = _payload(payload)
    intended = chunk_union(fields["chunks"])
    assembled = fields["assembledFrames"]
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}"]
    duplicates = sorted({frame for frame in assembled if assembled.count(frame) > 1})
    if duplicates:
        rejected.append("duplicated-overlap-frames")
        rejected.append("cadence-integrity")
        reasons.append(NEGATIVE)
        reasons.append("duplicated frames " + ",".join(str(frame) for frame in duplicates))
    missing = [frame for frame in intended if frame not in assembled]
    extra = [frame for frame in assembled if frame not in intended]
    if missing:
        rejected.append("omitted-boundary-frame")
        reasons.append("omitted frames " + ",".join(str(frame) for frame in missing))
    if extra and "duplicated-overlap-frames" not in rejected:
        rejected.append("assembled-timeline-mismatch")
        reasons.append("assembled frames are not the intended timeline")
    elif assembled != intended and "duplicated-overlap-frames" not in rejected and "omitted-boundary-frame" not in rejected:
        rejected.append("assembled-timeline-mismatch")
        reasons.append("assembled order does not match the intended timeline")
    if not fields["declaredContinuity"]:
        rejected.append("temporal-continuity-not-declared")
        reasons.append("declared temporal continuity is required")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("intended timeline emitted once")
    preserved = [
        fields["evidenceId"],
        intended,
        list(assembled),
        {
            "declaredContinuity": fields["declaredContinuity"],
            "rate": fields["rate"],
            "audioBearing": fields["audioBearing"],
            "sceneCutAtBoundary": fields["sceneCutAtBoundary"],
        },
    ]
    return _result(decision, reasons, rejected, preserved, ["physical S23 capture was not run", REPEAT])


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    chunks = payload["chunks"]
    if not isinstance(chunks, list) or len(chunks) < 2:
        raise ValueError("chunks must contain at least two ranges")
    parsed = []
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, dict) or set(chunk) != {"start", "end"}:
            raise ValueError(f"chunk {index} keys are invalid")
        start = chunk["start"]
        end = chunk["end"]
        if type(start) is not int or type(end) is not int or start < 0 or end < start:
            raise ValueError(f"chunk {index} range is invalid")
        if parsed and start > parsed[-1]["end"] + 1:
            raise ValueError("chunks are not a continuous boundary")
        parsed.append({"start": start, "end": end})
    if not any(parsed[index]["end"] >= parsed[index + 1]["start"] for index in range(len(parsed) - 1)):
        raise ValueError("chunks must overlap at a boundary")
    assembled = payload["assembledFrames"]
    if not isinstance(assembled, list) or not assembled:
        raise ValueError("assembledFrames must be a non-empty list")
    if any(type(frame) is not int or frame < 0 for frame in assembled):
        raise ValueError("assembled frame must be a non-negative integer")
    rate = payload["rate"]
    if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(float(rate)) or float(rate) <= 0:
        raise ValueError("rate must be a positive finite number")
    rate = float(rate)
    audio = _bool(payload["audioBearing"], "audioBearing")
    scene = _bool(payload["sceneCutAtBoundary"], "sceneCutAtBoundary")
    if repeat == "fractional-rate" and rate == float(int(rate)):
        raise ValueError("fractional rate expected")
    if repeat == "audio-bearing" and not audio:
        raise ValueError("audio-bearing repeat requires audio")
    if repeat == "scene-cut" and not scene:
        raise ValueError("scene-cut repeat requires a scene cut at the boundary")
    return {
        "evidenceId": evidence,
        "chunks": parsed,
        "assembledFrames": list(assembled),
        "declaredContinuity": _bool(payload["declaredContinuity"], "declaredContinuity"),
        "rate": rate,
        "audioBearing": audio,
        "sceneCutAtBoundary": scene,
        "repeat": repeat,
    }


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if not reasons or not preserved or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    return result
