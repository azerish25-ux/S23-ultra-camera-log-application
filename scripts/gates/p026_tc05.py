"""TC-P026-05 drain timeout.

One selected encoder does not complete EOS after the other track has
finished. Stop inside the declared bound and keep partial output with an
incomplete status. Waiting forever, or calling truncated audio complete,
must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P026-05"
INTERVENTION = "Prevent one selected encoder from completing EOS after the other track has finished."
EXPECTED = (
    "Terminate within the declared bound and retain inspectable partial output with the correct incomplete status."
)
NEGATIVE = "Waiting forever or silently labelling truncated audio complete must fail."
CAUSES = (
    "encoder_eos_withheld",
    "codec_failure",
    "stopped_microphone",
    "blocked_mux_writes",
)
_PAYLOAD_KEYS = (
    "cause",
    "boundMs",
    "elapsedMs",
    "otherTrackFinished",
    "waitedForever",
    "truncatedAudioComplete",
    "partialOutputId",
    "incompleteStatus",
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
    """Stop at the bound and keep an incomplete partial output."""
    fields = _payload(payload)
    reasons = [
        INTERVENTION,
        f"cause {fields['cause']}",
        f"elapsed {fields['elapsedMs']} bound {fields['boundMs']}",
    ]
    preserved = [
        fields["partialOutputId"],
        f"elapsed:{fields['elapsedMs']}",
        f"bound:{fields['boundMs']}",
    ]
    rejected: list[str] = []
    if fields["waitedForever"]:
        rejected.append("waited-forever")
        reasons.append(NEGATIVE)
    if fields["truncatedAudioComplete"]:
        rejected.append("truncated-audio-complete")
        reasons.append(NEGATIVE)
    if fields["elapsedMs"] > fields["boundMs"]:
        rejected.append("bound-exceeded")
        reasons.append("drain exceeded the declared bound")
    if not fields["incompleteStatus"]:
        rejected.append("missing-incomplete-status")
        reasons.append("partial output needs an incomplete status")
    if rejected:
        decision = "rejected"
    elif not fields["otherTrackFinished"]:
        decision = "withheld"
        reasons.append("the other track has not finished")
    else:
        decision = "incomplete"
        reasons.append(EXPECTED)
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    cause = payload["cause"]
    if cause not in CAUSES:
        raise ValueError("cause is not a declared repeat")
    bound = _non_negative(payload["boundMs"], "boundMs")
    if bound <= 0:
        raise ValueError("boundMs must be a positive int")
    elapsed = _non_negative(payload["elapsedMs"], "elapsedMs")
    return {
        "cause": cause,
        "boundMs": bound,
        "elapsedMs": elapsed,
        "otherTrackFinished": _bool(payload["otherTrackFinished"], "otherTrackFinished"),
        "waitedForever": _bool(payload["waitedForever"], "waitedForever"),
        "truncatedAudioComplete": _bool(payload["truncatedAudioComplete"], "truncatedAudioComplete"),
        "partialOutputId": _token(payload["partialOutputId"], "partialOutputId"),
        "incompleteStatus": _bool(payload["incompleteStatus"], "incompleteStatus"),
    }


def _token(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _non_negative(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative int")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P026-05 must not yield qualified or allowed")
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
