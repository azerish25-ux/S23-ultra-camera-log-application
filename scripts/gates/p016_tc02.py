"""TC-P016-02 advertised but unusable route on the first slice.

Advertisement stays historical. A configure request, session rejection,
startup timeout, or emitted stream that differs from the request does not
create a recording badge and does not qualify a physical S23.
"""

from __future__ import annotations

CASE_ID = "TC-P016-02"
INTERVENTION = (
    "Return an advertised candidate that fails actual configuration or produces no qualifying samples."
)
EXPECTED = (
    "Keep advertisement as historical evidence but deny operational qualification "
    "for the failed exact tuple."
)
NEGATIVE = "A configure request alone must not create a supported recording badge."
FAILURE_MODES = ("none", "session_rejected", "startup_timeout", "stream_mismatch")
_STREAM_FIELDS = (
    "logicalId",
    "format",
    "width",
    "height",
    "advertised",
    "configured",
    "samples",
    "queryError",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_ORACLE_PRESERVED = ("file-retained", "playback:separate", "cadence:separate")
_NOT_ENDURANCE = "not-endurance-certified"


def evaluate(payload: dict) -> dict:
    """Deny operational qualification when the advertised tuple was not sampled."""
    stream, failure_mode = _payload(payload)
    identity = _identity(stream)
    advertised_token = _advertised_token(stream)
    advertised = stream["advertised"]
    configured = stream["configured"]
    samples = stream["samples"]
    unusable = (not configured) or samples == 0 or failure_mode != "none"
    sampled = advertised and configured and samples > 0 and failure_mode == "none"

    if sampled:
        decision = "operational"
        preserved = [identity]
        rejected: list[str] = []
        reasons = [
            f"{identity} has configured samples",
            "configured sampled tuple is operational evidence only",
            "this record is not a physical S23 qualification",
        ]
    elif advertised and unusable:
        decision = "advertised_only"
        preserved = [advertised_token]
        rejected = _unusable_claims(stream, failure_mode)
        reasons = [
            "advertisement is not operational qualification",
            f"operational qualification denied for {identity}",
        ]
        if configured and samples == 0 and failure_mode == "none":
            reasons.append("configure request alone is not a recording badge")
        elif failure_mode == "session_rejected":
            reasons.append("session rejection denies operational qualification")
        elif failure_mode == "startup_timeout":
            reasons.append("startup timeout denies operational qualification")
        elif failure_mode == "stream_mismatch":
            reasons.append("emitted stream differs from the request")
        else:
            reasons.append("no qualifying samples")
        if decision in {"qualified", "allowed", "operational"}:
            raise ValueError("advertised unusable stream must not be operational, qualified, or allowed")
    else:
        decision = "rejected"
        preserved = []
        rejected = [identity]
        if failure_mode != "none":
            rejected.append(failure_mode)
        if samples == 0:
            rejected.append("no-samples")
        reasons = [f"{identity} is not advertised for qualification"]

    if decision == "allowed":
        raise ValueError("TC-P016-02 must not decide allowed")
    return _finish(decision, reasons, rejected, preserved, [])


def _unusable_claims(stream: dict, failure_mode: str) -> list[str]:
    claims: list[str] = []
    if failure_mode != "none":
        claims.append(failure_mode)
    if stream["samples"] == 0 or (failure_mode == "none" and not stream["configured"]):
        claims.append("no-samples")
    if not claims:
        claims.append("no-samples")
    return claims


def _finish(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError(f"{CASE_ID} must not decide qualified or allowed")
    kept = list(preserved)
    for token in _ORACLE_PRESERVED:
        if token not in kept:
            kept.append(token)
    if not kept:
        raise ValueError("preservedResults must keep unaffected evidence")
    questions = list(open_questions)
    if _NOT_ENDURANCE not in questions:
        questions.append(_NOT_ENDURANCE)
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": kept,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result


def _payload(payload: object) -> tuple[dict, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != {"stream", "failureMode"}:
        raise ValueError("payload keys must be stream and failureMode")
    failure = payload["failureMode"]
    if failure not in FAILURE_MODES:
        raise ValueError(
            "failureMode must be none, session_rejected, startup_timeout, or stream_mismatch"
        )
    return _stream(payload["stream"]), failure


def _stream(stream: object) -> dict:
    if not isinstance(stream, dict):
        raise ValueError("stream must be a dict")
    if set(stream) != set(_STREAM_FIELDS):
        raise ValueError("invalid stream fields")
    logical = stream["logicalId"]
    if not isinstance(logical, str) or not logical:
        raise ValueError("logicalId must be a non-empty string")
    fmt = stream["format"]
    if not isinstance(fmt, str) or not fmt:
        raise ValueError("format must be a non-empty string")
    _positive_int(stream["width"], "width")
    _positive_int(stream["height"], "height")
    for key in ("advertised", "configured"):
        if type(stream[key]) is not bool:
            raise ValueError(f"{key} must be a bool")
    samples = stream["samples"]
    if type(samples) is not int or samples < 0:
        raise ValueError("samples must be a non-negative int")
    query = stream["queryError"]
    if query is not None and (not isinstance(query, str) or not query):
        raise ValueError("queryError must be a non-empty string or null")
    return stream


def _positive_int(value: object, name: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive int")


def _identity(stream: dict) -> str:
    return f"{stream['width']}x{stream['height']}:{stream['format']}@{stream['logicalId']}"


def _advertised_token(stream: dict) -> str:
    return f"advertised:{stream['width']}x{stream['height']}:{stream['format']}"
