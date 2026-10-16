"""TC-P121-07 Resume boundary duplication.

Host fixture. Chunk assembly must emit the intended timeline once. Overlap
frames that repeat, or boundary frames that disappear, fail cadence integrity
even if the movie would still play.
"""

from __future__ import annotations

from collections import Counter


CASE_ID = "TC-P121-07"
NAME = "Resume boundary duplication"
INTERVENTION = "Assemble chunks whose temporal overlap contains repeated or omitted output frames."
EXPECTED = "Emit the exact intended timeline once and maintain declared temporal continuity."
NEGATIVE = "A playable movie with duplicated overlap frames must fail cadence integrity."
REPEAT = "Repeat fractional rates, audio-bearing clips, and scene cuts at boundaries."
DUPLICATE_TOKEN = "duplicated-overlap-frames"
OMITTED_TOKEN = "omitted-boundary-frames"
REPEATS = ("fractional-rate", "audio-bearing", "scene-cut")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "intendedFrames",
    "assembledFrames",
    "overlapFrames",
    "audioPresent",
    "sceneCutFrame",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Compare assembled frames with the intended timeline. Do not forgive overlap."""
    fields = _payload(payload)
    intended = fields["intendedFrames"]
    assembled = fields["assembledFrames"]
    overlap = fields["overlapFrames"]
    intended_counts = Counter(intended)
    assembled_counts = Counter(assembled)
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}"]
    duplicated = [frame for frame in overlap if assembled_counts[frame] > intended_counts[frame]]
    omitted = [frame for frame in intended if assembled_counts[frame] < intended_counts[frame]]
    if duplicated:
        rejected.append(DUPLICATE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("duplicated overlap frames: " + ",".join(str(frame) for frame in duplicated))
    if omitted:
        rejected.append(OMITTED_TOKEN)
        reasons.append("omitted boundary frames: " + ",".join(str(frame) for frame in omitted))
    if assembled != intended and not duplicated and not omitted:
        rejected.append("timeline-order-changed")
        reasons.append("assembled order is not the intended timeline")
    if fields["sceneCutFrame"] is not None and fields["sceneCutFrame"] in duplicated:
        reasons.append("scene cut frame was repeated")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("intended timeline emitted once")
        if fields["audioPresent"]:
            reasons.append("audio-bearing cadence retained")
    preserved = [
        fields["evidenceId"],
        {
            "intendedFrames": intended,
            "assembledFrames": assembled,
            "overlapFrames": overlap,
            "audioPresent": fields["audioPresent"],
            "sceneCutFrame": fields["sceneCutFrame"],
            "emittedOnce": assembled == intended,
        },
    ]
    questions = ["physical S23 capture was not run", REPEAT]
    return _result(decision, reasons, rejected, preserved, questions)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _frames(value: object, label: str) -> list[int]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty list")
    frames: list[int] = []
    for index, item in enumerate(value):
        if type(item) is not int or item < 0:
            raise ValueError(f"{label} {index} must be a non-negative integer")
        frames.append(item)
    return frames


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    if type(payload["audioPresent"]) is not bool:
        raise ValueError("audioPresent must be a bool")
    if repeat == "audio-bearing" and not payload["audioPresent"]:
        raise ValueError("audio-bearing repeat requires audio")
    if repeat != "audio-bearing" and payload["audioPresent"]:
        raise ValueError("audio present only on the audio-bearing repeat")
    intended = _frames(payload["intendedFrames"], "intendedFrames")
    for left, right in zip(intended, intended[1:]):
        if right != left + 1:
            raise ValueError("intended timeline is not continuous")
    if len(set(intended)) != len(intended):
        raise ValueError("intended frames must be unique")
    assembled = _frames(payload["assembledFrames"], "assembledFrames")
    overlap = _frames(payload["overlapFrames"], "overlapFrames")
    if any(frame not in intended for frame in overlap):
        raise ValueError("overlap frame is outside the intended timeline")
    scene = payload["sceneCutFrame"]
    if repeat == "scene-cut":
        if type(scene) is not int or scene not in intended:
            raise ValueError("sceneCutFrame must be an intended frame")
    elif scene is not None:
        raise ValueError("sceneCutFrame is only used for a scene-cut repeat")
    return {
        "evidenceId": _text(payload["evidenceId"], "evidenceId"),
        "repeat": repeat,
        "intendedFrames": intended,
        "assembledFrames": assembled,
        "overlapFrames": overlap,
        "audioPresent": payload["audioPresent"],
        "sceneCutFrame": scene,
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
