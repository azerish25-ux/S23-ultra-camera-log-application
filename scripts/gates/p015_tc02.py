"""TC-P015-02 advertised but unusable route.

Advertisement stays historical evidence. A configure request, a session
rejection, a startup timeout, or an emitted stream that differs from the
request does not create a supported recording badge and is not operational
qualification. The decision is never qualified or allowed.
"""

from __future__ import annotations

CASE_ID = "TC-P015-02"
INTERVENTION = (
    "Return an advertised candidate that fails actual configuration or produces no qualifying samples."
)
EXPECTED = (
    "Keep advertisement as historical evidence but deny operational qualification "
    "for the failed exact tuple."
)
NEGATIVE = "A configure request alone must not create a supported recording badge."
REPEAT = "Repeat with session rejection, startup timeout, and an emitted stream that differs from the request."
FAILURE_MODES = ("none", "session_rejection", "startup_timeout", "stream_differs")
_PAYLOAD_KEYS = (
    "tupleId",
    "advertised",
    "configured",
    "qualifyingSamples",
    "failureMode",
    "historicalAdvertisementId",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}
_BADGE = "supported-recording-badge"


def evaluate(payload: dict) -> dict:
    """Deny operational qualification for an advertised tuple that did not hold."""
    (
        tuple_id,
        advertised,
        configured,
        samples,
        failure_mode,
        historical_id,
    ) = _payload(payload)
    historical = f"historical:{historical_id}"
    unusable = (not configured) or samples == 0 or failure_mode != "none"
    configure_only = configured and samples == 0 and failure_mode == "none"
    reasons: list[str] = []
    rejected: list[str] = []
    if advertised and unusable:
        decision = "historical_only"
        preserved = [historical]
        rejected.append(tuple_id)
        reasons.append("advertisement kept as historical evidence")
        reasons.append(f"operational qualification denied for {tuple_id}")
        if configure_only:
            rejected.append(_BADGE)
            reasons.append("a configure request alone must not create a supported recording badge")
        elif failure_mode == "session_rejection":
            rejected.append(failure_mode)
            reasons.append("session rejection denies operational qualification")
        elif failure_mode == "startup_timeout":
            rejected.append(failure_mode)
            reasons.append("startup timeout denies operational qualification")
        elif failure_mode == "stream_differs":
            rejected.append(failure_mode)
            reasons.append("emitted stream differs from the request")
        else:
            reasons.append("no qualifying samples")
    elif advertised and configured and samples > 0 and failure_mode == "none":
        decision = "candidate"
        preserved = [historical, tuple_id]
        reasons.append(f"{tuple_id} has qualifying samples")
        reasons.append("candidate status is not a supported recording badge and not physical qualification")
    else:
        decision = "rejected"
        preserved = [tuple_id]
        rejected.append(tuple_id)
        reasons.append(f"{tuple_id} is not advertised for qualification")
    if decision in _FORBIDDEN:
        raise ValueError("TC-P015-02 must not decide qualified or allowed")
    if advertised and unusable and decision in _FORBIDDEN | {"candidate"}:
        raise ValueError("unusable advertisement must not be operationally qualified")
    if configure_only and _BADGE not in rejected:
        raise ValueError("configure request alone must not create a supported recording badge")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> tuple[str, bool, bool, int, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    tuple_id = _text(payload["tupleId"], "tupleId")
    historical_id = _text(payload["historicalAdvertisementId"], "historicalAdvertisementId")
    advertised = _bool(payload["advertised"], "advertised")
    configured = _bool(payload["configured"], "configured")
    samples = payload["qualifyingSamples"]
    if type(samples) is not int or samples < 0:
        raise ValueError("qualifyingSamples must be a non-negative int")
    failure_mode = payload["failureMode"]
    if failure_mode not in FAILURE_MODES:
        raise ValueError("failureMode is not a known mode")
    return tuple_id, advertised, configured, samples, failure_mode, historical_id


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in _FORBIDDEN or not reasons:
        raise ValueError("invalid decision or reasons")
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
