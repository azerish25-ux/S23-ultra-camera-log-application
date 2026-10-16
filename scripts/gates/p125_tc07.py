"""TC-P125-07 Resume boundary duplication.

Host fixture. Chunk assembly emits the intended timeline once. Duplicated
overlap frames fail cadence integrity.
"""

from __future__ import annotations

from collections import Counter


CASE_ID = "TC-P125-07"
NAME = "Resume boundary duplication"
INTERVENTION = "Assemble chunks whose temporal overlap contains repeated or omitted output frames."
EXPECTED = "Emit the exact intended timeline once and maintain declared temporal continuity."
NEGATIVE = "A playable movie with duplicated overlap frames must fail cadence integrity."
REPEAT = "Repeat fractional rates, audio-bearing clips, and scene cuts at boundaries."
DUP_TOKEN = "duplicated-overlap-frames"
CADENCE_TOKEN = "cadence-integrity"
OMIT_TOKEN = "omitted-boundary-frames"
ORDER_TOKEN = "timeline-mismatch"
REPEATS = ("fractional-rates", "audio-bearing", "scene-cuts")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "intendedFrames",
    "assembledFrames",
    "overlapStart",
    "overlapEnd",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _frames(value: object, label: str) -> list[int]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty list")
    parsed: list[int] = []
    for index, item in enumerate(value):
        if type(item) is not int or item < 0:
            raise ValueError(f"{label}[{index}] must be a non-negative integer")
        parsed.append(item)
    return parsed


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    intended = _frames(payload["intendedFrames"], "intendedFrames")
    assembled = _frames(payload["assembledFrames"], "assembledFrames")
    start = payload["overlapStart"]
    end = payload["overlapEnd"]
    if type(start) is not int or type(end) is not int or start < 0 or end < start:
        raise ValueError("overlap must be a non-empty non-negative range")
    rejected: list[str] = []
    if assembled != intended:
        counts = Counter(assembled)
        overlap_dups = [frame for frame, count in counts.items() if count > 1 and start <= frame <= end]
        other_dups = [frame for frame, count in counts.items() if count > 1 and frame not in overlap_dups]
        if overlap_dups:
            rejected.append(DUP_TOKEN)
            rejected.append(CADENCE_TOKEN)
        elif other_dups:
            rejected.append(CADENCE_TOKEN)
        intended_counts = Counter(intended)
        omitted = [frame for frame, count in intended_counts.items() if counts[frame] < count]
        if omitted:
            rejected.append(OMIT_TOKEN)
        if not rejected:
            rejected.append(ORDER_TOKEN)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    if DUP_TOKEN in rejected or CADENCE_TOKEN in rejected:
        reasons.append(NEGATIVE)
    if OMIT_TOKEN in rejected:
        reasons.append("omitted boundary frames were not emitted")
    if not rejected:
        reasons.append("intended timeline emitted once")
    preserved = [
        evidence,
        {
            "intendedFrames": intended,
            "assembledFrames": assembled,
            "overlapStart": start,
            "overlapEnd": end,
            "emittedOnce": assembled == intended,
        },
    ]
    return _result("rejected" if rejected else "recorded", reasons, rejected, preserved)


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 capture was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if not reasons or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    return result
