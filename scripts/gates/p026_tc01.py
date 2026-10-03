"""TC-P026-01 track startup permutation.

Reorder video and audio format callbacks and first sample arrival around a
user Stop. Wait for required tracks or terminate honestly. Starting a
selected-audio take with video alone and hiding the omission must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P026-01"
INTERVENTION = (
    "Reorder video and audio format callbacks and first sample arrival around a user Stop event."
)
EXPECTED = (
    "Wait for required tracks or terminate honestly within bounds, without deadlock or fabricated success."
)
NEGATIVE = "Starting a selected-audio take with video alone and hiding the omission must fail."
ORDERINGS = (
    "video_then_audio_then_samples",
    "audio_then_video_then_samples",
    "samples_before_formats",
    "stop_between_callbacks",
)
PENDING_COUNTS = ("zero", "one", "several")
_PAYLOAD_KEYS = (
    "ordering",
    "pendingSamples",
    "audioSelected",
    "videoReady",
    "audioReady",
    "userStop",
    "hidesAudioOmission",
    "deadlocked",
    "fabricatedSuccess",
    "withinBounds",
    "takeId",
    "videoEvidence",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Wait, stop honestly, or reject a hidden audio omission."""
    fields = _payload(payload)
    reasons = [
        INTERVENTION,
        f"ordering {fields['ordering']}",
        f"pending {fields['pendingSamples']}",
    ]
    rejected: list[str] = []
    if fields["hidesAudioOmission"]:
        rejected.append("hidden-audio-omission")
        reasons.append(NEGATIVE)
    if fields["deadlocked"]:
        rejected.append("deadlock")
        reasons.append("startup deadlocked")
    if fields["fabricatedSuccess"]:
        rejected.append("fabricated-success")
        reasons.append("startup success was fabricated")
    if not fields["withinBounds"]:
        rejected.append("bounds-exceeded")
        reasons.append("startup exceeded its bound")
    waiting = (fields["audioSelected"] and not fields["audioReady"]) or not fields["videoReady"]
    if rejected:
        decision = "rejected"
    elif fields["userStop"]:
        decision = "terminated"
        reasons.append(EXPECTED)
        reasons.append("user Stop terminated startup without a fabricated success")
    elif waiting:
        decision = "waiting"
        reasons.append(EXPECTED)
        reasons.append("required tracks are still outstanding")
    else:
        decision = "tracks_ready"
        reasons.append("required tracks arrived inside bounds")
    preserved = [
        fields["takeId"],
        fields["videoEvidence"],
        "pending:" + fields["pendingSamples"],
        "audio-selected" if fields["audioSelected"] else "audio-not-selected",
    ]
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    ordering = payload["ordering"]
    if ordering not in ORDERINGS:
        raise ValueError("ordering is not a declared repeat")
    pending = payload["pendingSamples"]
    if pending not in PENDING_COUNTS:
        raise ValueError("pendingSamples must be zero, one, or several")
    return {
        "ordering": ordering,
        "pendingSamples": pending,
        "audioSelected": _bool(payload["audioSelected"], "audioSelected"),
        "videoReady": _bool(payload["videoReady"], "videoReady"),
        "audioReady": _bool(payload["audioReady"], "audioReady"),
        "userStop": _bool(payload["userStop"], "userStop"),
        "hidesAudioOmission": _bool(payload["hidesAudioOmission"], "hidesAudioOmission"),
        "deadlocked": _bool(payload["deadlocked"], "deadlocked"),
        "fabricatedSuccess": _bool(payload["fabricatedSuccess"], "fabricatedSuccess"),
        "withinBounds": _bool(payload["withinBounds"], "withinBounds"),
        "takeId": _token(payload["takeId"], "takeId"),
        "videoEvidence": _token(payload["videoEvidence"], "videoEvidence"),
    }


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P026-01 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
