"""TC-P027-01 track startup permutation.

Reorder video and audio format callbacks and first sample arrival around a
user Stop event. Wait for required tracks or terminate honestly. Starting a
selected-audio take with video alone and hiding the omission must fail.

Host fixture only. This module does not qualify a physical S23.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P027-01"
INTERVENTION = (
    "Reorder video and audio format callbacks and first sample arrival around a user Stop event."
)
EXPECTED = (
    "Wait for required tracks or terminate honestly within bounds, without deadlock or "
    "fabricated success."
)
NEGATIVE = "Starting a selected-audio take with video alone and hiding the omission must fail."
ORDERS = (
    "video-format-audio-format-samples",
    "audio-format-video-format-samples",
    "stop-before-audio-sample",
    "samples-before-stop",
)
_TOKEN = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
_PAYLOAD_KEYS = {
    "order",
    "pendingSamples",
    "audioSelected",
    "videoPresent",
    "audioPresent",
    "stopRequested",
    "hidesAudioOmission",
    "withinBounds",
    "fabricatedSuccess",
    "takeId",
}
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Terminate honestly or wait. A hidden audio omission is rejected."""
    data = _payload(payload)
    pending = _pending_class(data["pendingSamples"])
    reasons = [
        f"order {data['order']}",
        f"pending {pending}",
        INTERVENTION,
    ]
    rejected: list[str] = []
    questions: list[str] = []
    if data["hidesAudioOmission"]:
        rejected.append("hidden-audio-omission")
        reasons.append(NEGATIVE)
    if data["fabricatedSuccess"]:
        rejected.append("fabricated-success")
        reasons.append("fabricated success is not an honest termination")
    if not data["withinBounds"]:
        rejected.append("unbounded-wait")
        reasons.append("startup did not stay within bounds")
    if data["audioSelected"] and not data["audioPresent"] and not data["hidesAudioOmission"]:
        questions.append("selected audio omitted; omission was not hidden")
    preserved = [data["takeId"], data["order"], f"pending-samples:{data['pendingSamples']}"]
    if data["videoPresent"]:
        preserved.append("video-track")
    if data["audioPresent"]:
        preserved.append("audio-track")
    if rejected:
        decision = "rejected"
    elif data["stopRequested"]:
        decision = "terminated"
        reasons.append(EXPECTED)
    elif data["audioSelected"] and not data["audioPresent"]:
        decision = "waiting"
        reasons.append("waiting for the selected audio track within bounds")
    else:
        decision = "tracks_ready"
        reasons.append("required tracks are present and startup stayed within bounds")
    return _result(decision, reasons, rejected, preserved, questions)


def _pending_class(count: int) -> str:
    if count == 0:
        return "zero"
    if count == 1:
        return "one"
    return "several"


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != _PAYLOAD_KEYS:
        raise ValueError("invalid payload keys")
    order = payload["order"]
    if order not in ORDERS:
        raise ValueError("order is not a declared startup permutation")
    pending = payload["pendingSamples"]
    if type(pending) is not int or pending < 0:
        raise ValueError("pendingSamples must be a non-negative int")
    audio_selected = _bool(payload["audioSelected"], "audioSelected")
    video_present = _bool(payload["videoPresent"], "videoPresent")
    audio_present = _bool(payload["audioPresent"], "audioPresent")
    hides = _bool(payload["hidesAudioOmission"], "hidesAudioOmission")
    if hides and not (audio_selected and video_present and not audio_present):
        raise ValueError("hidden omission requires selected audio, video present, and audio absent")
    take = payload["takeId"]
    if not isinstance(take, str) or _TOKEN.fullmatch(take) is None:
        raise ValueError("takeId must be a token")
    return {
        "order": order,
        "pendingSamples": pending,
        "audioSelected": audio_selected,
        "videoPresent": video_present,
        "audioPresent": audio_present,
        "stopRequested": _bool(payload["stopRequested"], "stopRequested"),
        "hidesAudioOmission": hides,
        "withinBounds": _bool(payload["withinBounds"], "withinBounds"),
        "fabricatedSuccess": _bool(payload["fabricatedSuccess"], "fabricatedSuccess"),
        "takeId": take,
    }


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P027-01 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
