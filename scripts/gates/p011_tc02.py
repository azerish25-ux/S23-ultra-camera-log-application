"""TC-P011-02 advertised but unusable route.

Advertisement is historical evidence. A configure request, session rejection,
startup timeout, or stream mismatch does not create a recording badge and
does not certify native fixed 24.
"""

from __future__ import annotations

import math


CASE_ID = "TC-P011-02"
INTERVENTION = (
    "Return an advertised candidate that fails actual configuration or produces no qualifying samples."
)
EXPECTED = (
    "Keep advertisement as historical evidence but deny operational qualification "
    "for the failed exact tuple."
)
NEGATIVE = "A configure request alone must not create a supported recording badge."
FAILURE_MODES = ("none", "session_rejected", "startup_timeout", "stream_mismatch")
_PAYLOAD_KEYS = (
    "candidateId",
    "advertised",
    "configured",
    "samples",
    "failureMode",
    "aeMin",
    "aeMax",
    "requestedFps",
    "containerTimestampsAssigned",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed", "native_fixed_24"}


def evaluate(payload: dict) -> dict:
    """Deny a recording badge when the advertised tuple was not actually sampled."""
    (
        candidate_id,
        advertised,
        configured,
        samples,
        failure_mode,
        ae_min,
        ae_max,
        requested,
        timestamps,
    ) = _payload(payload)
    inventory = [f"ae:{_text(ae_min)}-{_text(ae_max)}", f"requested:{_text(requested)}"]
    reasons = [f"candidate {candidate_id}"]
    rejected: list[str] = []
    usable = advertised and configured and samples > 0 and failure_mode == "none"
    unusable = (not configured) or samples == 0 or failure_mode != "none"
    if usable:
        decision = "sampled"
        preserved = [candidate_id, *inventory]
        reasons.append(f"{candidate_id} produced samples")
        reasons.append("samples are not a native fixed cadence certificate")
    elif advertised and unusable:
        decision = "advertised_only"
        preserved = [f"advertised:{candidate_id}", *inventory]
        reasons.append("advertisement is historical evidence, not operational qualification")
        reasons.append(f"operational qualification denied for {candidate_id}")
        if failure_mode == "session_rejected":
            rejected.append("session_rejected")
            reasons.append("session rejection denies operational qualification")
        elif failure_mode == "startup_timeout":
            rejected.append("startup_timeout")
            reasons.append("startup timeout denies operational qualification")
        elif failure_mode == "stream_mismatch":
            rejected.append("stream_mismatch")
            reasons.append("emitted stream differs from the request")
        if configured and samples == 0 and failure_mode == "none":
            rejected.append("recording-badge")
            reasons.append("configure request alone is not a recording badge")
        elif samples == 0:
            rejected.append("no-samples")
            reasons.append("no qualifying samples")
        if decision in _FORBIDDEN:
            raise ValueError(NEGATIVE)
    else:
        decision = "rejected"
        preserved = list(inventory)
        rejected.append(candidate_id)
        reasons.append(f"{candidate_id} is not advertised")
    if timestamps:
        rejected.append("native-fixed-24")
        reasons.append("container timestamps do not certify native fixed 24")
    if not preserved:
        raise ValueError("timing inventory must be preserved")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object):
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    candidate_id = payload["candidateId"]
    if not isinstance(candidate_id, str) or not candidate_id or candidate_id != candidate_id.strip():
        raise ValueError("candidateId must be a non-empty string")
    advertised = payload["advertised"]
    configured = payload["configured"]
    timestamps = payload["containerTimestampsAssigned"]
    if type(advertised) is not bool or type(configured) is not bool or type(timestamps) is not bool:
        raise ValueError("advertised, configured, and containerTimestampsAssigned must be bools")
    samples = payload["samples"]
    if type(samples) is not int or samples < 0:
        raise ValueError("samples must be a non-negative int")
    failure_mode = payload["failureMode"]
    if failure_mode not in FAILURE_MODES:
        raise ValueError("failureMode must be none, session_rejected, startup_timeout, or stream_mismatch")
    ae_min = _rate(payload["aeMin"], "aeMin")
    ae_max = _rate(payload["aeMax"], "aeMax")
    if _cmp(ae_min, ae_max) > 0:
        raise ValueError("aeMin must not exceed aeMax")
    requested = _rate(payload["requestedFps"], "requestedFps")
    return (
        candidate_id,
        advertised,
        configured,
        samples,
        failure_mode,
        ae_min,
        ae_max,
        requested,
        timestamps,
    )


def _rate(value: object, context: str) -> tuple[int, int]:
    if not isinstance(value, dict) or set(value) != {"numerator", "denominator"}:
        raise ValueError(context + " must be a numerator/denominator object")
    numerator = value["numerator"]
    denominator = value["denominator"]
    if type(numerator) is not int or type(denominator) is not int:
        raise ValueError(context + " must use ints")
    if numerator <= 0 or denominator <= 0:
        raise ValueError(context + " must be positive")
    if math.gcd(numerator, denominator) != 1:
        raise ValueError(context + " must be reduced")
    return numerator, denominator


def _text(rate: tuple[int, int]) -> str:
    return f"{rate[0]}/{rate[1]}"


def _cmp(left: tuple[int, int], right: tuple[int, int]) -> int:
    gap = left[0] * right[1] - right[0] * left[1]
    return (gap > 0) - (gap < 0)


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in _FORBIDDEN:
        raise ValueError("TC-P011-02 must not yield qualified, allowed, or native_fixed_24")
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
