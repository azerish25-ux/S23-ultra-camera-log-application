"""TC-P030-01 track startup permutation.

Intervention: Reorder video and audio format callbacks and first sample arrival
around a user Stop event.
Expected: Wait for required tracks or terminate honestly within bounds, without
deadlock or fabricated success.
Negative: Starting a selected-audio take with video alone and hiding the
omission must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P030-01"
INTERVENTION = (
    "Reorder video and audio format callbacks and first sample arrival around a user Stop event."
)
EXPECTED = (
    "Wait for required tracks or terminate honestly within bounds, without deadlock or "
    "fabricated success."
)
NEGATIVE = "Starting a selected-audio take with video alone and hiding the omission must fail."

_TRACKS = ("video", "audio")
_EVENTS = ("video_format", "audio_format", "video_sample", "audio_sample", "stop")
_PAYLOAD_KEYS = (
    "selectedTracks",
    "order",
    "pendingSamples",
    "boundMs",
    "elapsedMs",
    "hideOmission",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "waiting", "terminated", "tracks_observed")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Judge a startup ordering without fabricating a successful take."""
    selected, order, pending, bound_ms, elapsed_ms, hide = _payload(payload)
    stop_at = order.index("stop") if "stop" in order else None
    prefix = order if stop_at is None else order[:stop_at]
    ready = {
        track: (f"{track}_format" in prefix and f"{track}_sample" in prefix) for track in _TRACKS
    }
    arrived = [track for track in selected if ready[track]]
    missing = [track for track in selected if track not in arrived]
    hidden = hide and "audio" in selected and "audio" not in arrived and "video" in arrived

    if hidden:
        decision = "rejected"
    elif missing and stop_at is None and elapsed_ms < bound_ms:
        decision = "waiting"
    elif missing and (stop_at is not None or elapsed_ms >= bound_ms):
        decision = "terminated"
    elif stop_at is None:
        decision = "waiting"
    else:
        decision = "tracks_observed"

    rejected: list[str] = []
    if hidden:
        rejected = ["hidden-audio-omission", "video-only-selected-audio-take"]
    elif decision == "terminated":
        rejected = [f"missing-{track}" for track in missing]

    preserved = [f"selected:{track}" for track in selected]
    preserved.extend(f"event:{event}" for event in order)
    preserved.append(f"pending:{pending}")
    preserved.extend(f"arrived:{track}" for track in arrived)

    reasons = [EXPECTED, "startup does not fabricate success"]
    if decision == "rejected":
        reasons.append(NEGATIVE)
    elif decision == "waiting":
        reasons.append("required tracks are still pending inside the stop bound")
    elif decision == "terminated":
        reasons.append("terminated honestly within bounds without a fabricated success")
    else:
        reasons.append("required tracks were observed before stop; this is not a success badge")

    questions: list[str] = []
    if decision == "waiting" and missing:
        questions.append("required tracks still pending")
    elif decision == "waiting":
        questions.append("user stop not observed")
    elif decision == "terminated":
        questions.extend(f"missing {track}" for track in missing)
    elif decision == "rejected":
        questions.append("audio omission was hidden")
    elif pending:
        questions.append(f"{pending} samples still pending")

    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[list[str], list[str], int, int, int, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    selected = payload["selectedTracks"]
    if (
        not isinstance(selected, list)
        or not selected
        or len(selected) != len(set(selected))
        or any(track not in _TRACKS for track in selected)
    ):
        raise ValueError("selectedTracks must be a unique non-empty video/audio list")
    order = payload["order"]
    if not isinstance(order, list) or not order or any(event not in _EVENTS for event in order):
        raise ValueError("order must be a non-empty list of known events")
    if order.count("stop") > 1:
        raise ValueError("stop may occur at most once")
    pending = payload["pendingSamples"]
    bound_ms = payload["boundMs"]
    elapsed_ms = payload["elapsedMs"]
    if type(pending) is not int or pending < 0:
        raise ValueError("pendingSamples must be a non-negative int")
    if type(bound_ms) is not int or bound_ms <= 0:
        raise ValueError("boundMs must be a positive int")
    if type(elapsed_ms) is not int or elapsed_ms < 0:
        raise ValueError("elapsedMs must be a non-negative int")
    hide = payload["hideOmission"]
    if type(hide) is not bool:
        raise ValueError("hideOmission must be a bool")
    if hide and "audio" not in selected:
        raise ValueError("hideOmission applies only when audio is selected")
    return list(selected), list(order), pending, bound_ms, elapsed_ms, hide


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("startup decision cannot be qualified or allowed")
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
