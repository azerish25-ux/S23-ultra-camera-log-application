"""TC-P013-02 advertised but unusable codec route.

Advertisement is historical evidence only. A configure request without
qualifying samples, a session rejection, a startup timeout, or an emitted
stream that differs from the request does not create a recording badge.
"""

from __future__ import annotations

CASE_ID = "TC-P013-02"
INTERVENTION = (
    "Return an advertised candidate that fails actual configuration or "
    "produces no qualifying samples."
)
EXPECTED = (
    "Keep advertisement as historical evidence but deny operational "
    "qualification for the failed exact tuple."
)
NEGATIVE = "A configure request alone must not create a supported recording badge."
FAILURE_MODES = ("none", "session_rejected", "startup_timeout", "stream_mismatch")
INTERFACES = ("surface", "byte_buffer", "image", "encoder", "decoder")
_CANDIDATE_FIELDS = (
    "candidateId",
    "codecName",
    "profile",
    "interface",
    "advertised",
    "configured",
    "samples",
    "exactTuple",
)
_PAYLOAD_KEYS = ("candidate", "failureMode")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_BADGE = "recording-badge"


def evaluate(payload: dict) -> dict:
    """Deny operational qualification for an advertised route that did not sample."""
    candidate, failure_mode = _payload(payload)
    historical = f"advertised:{candidate['candidateId']}:{candidate['profile']}"
    tuple_id = candidate["exactTuple"]
    advertised = candidate["advertised"]
    configured = candidate["configured"]
    samples = candidate["samples"]
    operational = advertised and configured and samples > 0 and failure_mode == "none"
    reasons: list[str] = [INTERVENTION]
    rejected: list[str] = []
    open_questions: list[str] = []

    if operational:
        decision = "sampled"
        preserved = [tuple_id, historical]
        reasons.append(f"{tuple_id} produced qualifying samples")
        reasons.append("sampled status is not a supported recording badge for other tuples")
        reasons.append("advertisement remains historical evidence")
    elif advertised:
        decision = "advertised_only"
        preserved = [historical]
        rejected.append(tuple_id)
        reasons.append(f"operational qualification denied for {tuple_id}")
        reasons.append("advertisement retained as historical evidence")
        if configured and samples == 0 and failure_mode == "none":
            rejected.append(_BADGE)
            reasons.append(NEGATIVE)
        elif failure_mode == "session_rejected":
            rejected.append(failure_mode)
            reasons.append("session rejection denies operational qualification")
        elif failure_mode == "startup_timeout":
            rejected.append(failure_mode)
            reasons.append("startup timeout denies operational qualification")
        elif failure_mode == "stream_mismatch":
            rejected.append(failure_mode)
            reasons.append("emitted stream differs from the request")
        else:
            rejected.append("no-samples")
            reasons.append("no qualifying samples")
        if samples == 0 and "no-samples" not in rejected and failure_mode == "none":
            rejected.append("no-samples")
    else:
        decision = "rejected"
        preserved = [historical] if candidate["profile"] else []
        rejected.append(tuple_id)
        if failure_mode != "none":
            rejected.append(failure_mode)
        reasons.append(f"{tuple_id} is not advertised for qualification")

    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P013-02 must not decide qualified or allowed")
    if advertised and not operational and decision in {"qualified", "allowed"}:
        raise ValueError("configure or failure evidence must not qualify the route")
    if configured and samples == 0 and failure_mode == "none" and decision in {"qualified", "allowed"}:
        raise ValueError(NEGATIVE)
    if not preserved:
        raise ValueError("advertisement evidence must be preserved")
    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object) -> tuple[dict, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("payload keys must be candidate and failureMode")
    failure = payload["failureMode"]
    if failure not in FAILURE_MODES:
        raise ValueError(
            "failureMode must be none, session_rejected, startup_timeout, or stream_mismatch"
        )
    return _candidate(payload["candidate"]), failure


def _candidate(item: object) -> dict:
    if not isinstance(item, dict):
        raise ValueError("candidate must be a dict")
    if set(item) != set(_CANDIDATE_FIELDS):
        raise ValueError("invalid candidate fields")
    for key in ("candidateId", "codecName", "profile", "exactTuple"):
        value = item[key]
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError(f"{key} must be a non-empty string")
    if item["interface"] not in INTERFACES:
        raise ValueError("interface must be surface, byte_buffer, image, encoder, or decoder")
    for key in ("advertised", "configured"):
        if type(item[key]) is not bool:
            raise ValueError(f"{key} must be a bool")
    samples = item["samples"]
    if type(samples) is not int or samples < 0:
        raise ValueError("samples must be a non-negative int")
    return item


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision not in {"advertised_only", "sampled", "rejected"}:
        raise ValueError("unexpected TC-P013-02 decision")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": open_questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
