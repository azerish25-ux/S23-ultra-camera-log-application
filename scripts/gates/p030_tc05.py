"""TC-P030-05 drain timeout.

Intervention: Prevent one selected encoder from completing EOS after the other
track has finished.
Expected: Terminate within the declared bound and retain inspectable partial
output with the correct incomplete status.
Negative: Waiting forever or silently labelling truncated audio complete must
fail.
"""

from __future__ import annotations

CASE_ID = "TC-P030-05"
INTERVENTION = (
    "Prevent one selected encoder from completing EOS after the other track has finished."
)
EXPECTED = (
    "Terminate within the declared bound and retain inspectable partial output with the "
    "correct incomplete status."
)
NEGATIVE = "Waiting forever or silently labelling truncated audio complete must fail."

_FAILURES = ("none", "codec_failure", "stopped_microphone", "blocked_mux")
_PAYLOAD_KEYS = (
    "boundMs",
    "elapsedMs",
    "videoEos",
    "audioEos",
    "failureMode",
    "waitForever",
    "labelTruncatedAudioComplete",
    "partialOutput",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "incomplete", "drained")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Stop at the drain bound and keep partial output labelled incomplete."""
    bound_ms, elapsed_ms, video_eos, audio_eos, failure, wait, label, partial = _payload(payload)
    preserved = list(partial)
    preserved.append(f"bound:{bound_ms}")
    preserved.append(f"elapsed:{elapsed_ms}")
    preserved.append(f"videoEos:{str(video_eos).lower()}")
    preserved.append(f"audioEos:{str(audio_eos).lower()}")

    rejected: list[str] = []
    if wait:
        rejected.append("wait-forever")
    if label:
        rejected.append("truncated-audio-labelled-complete")
    if elapsed_ms > bound_ms:
        rejected.append("bound-exceeded")
    if failure != "none":
        rejected.append(failure)
    both_done = video_eos and audio_eos and failure == "none"

    if wait or label or elapsed_ms > bound_ms:
        decision = "rejected"
    elif not both_done:
        decision = "incomplete"
    else:
        decision = "drained"

    reasons = [EXPECTED]
    if decision == "rejected":
        reasons.append(NEGATIVE)
        reasons.append("partial output remains inspectable")
    elif decision == "incomplete":
        reasons.append("incomplete status retained with the partial output")
        if elapsed_ms <= bound_ms:
            reasons.append(f"terminated at bound {bound_ms}ms")
    else:
        reasons.append("both tracks drained inside the bound; this is not a completion certificate")

    questions: list[str] = []
    if not partial:
        questions.append("partial output missing")
    if decision == "incomplete":
        questions.append("output is incomplete")
    if decision == "rejected":
        questions.append("drain was not an honest bounded termination")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[int, int, bool, bool, str, bool, bool, list[str]]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    bound_ms = payload["boundMs"]
    elapsed_ms = payload["elapsedMs"]
    if type(bound_ms) is not int or bound_ms <= 0:
        raise ValueError("boundMs must be a positive int")
    if type(elapsed_ms) is not int or elapsed_ms < 0:
        raise ValueError("elapsedMs must be a non-negative int")
    video_eos = _bool(payload["videoEos"], "videoEos")
    audio_eos = _bool(payload["audioEos"], "audioEos")
    failure = payload["failureMode"]
    if failure not in _FAILURES:
        raise ValueError("failureMode is not a known drain failure")
    wait = _bool(payload["waitForever"], "waitForever")
    label = _bool(payload["labelTruncatedAudioComplete"], "labelTruncatedAudioComplete")
    partial = payload["partialOutput"]
    if not isinstance(partial, list) or len(partial) != len(set(partial)):
        raise ValueError("partialOutput must be unique non-empty strings")
    if any(not isinstance(item, str) or not item for item in partial):
        raise ValueError("partialOutput must be unique non-empty strings")
    return bound_ms, elapsed_ms, video_eos, audio_eos, failure, wait, label, list(partial)


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("drain decision cannot be qualified or allowed")
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
