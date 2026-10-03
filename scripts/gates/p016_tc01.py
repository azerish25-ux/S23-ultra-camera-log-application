"""TC-P016-01 partial characteristic failure on the first slice.

One throwing characteristic query must not erase readable formats and routes.
The failed property is reported. The baseline take record stays in the result.
This host case does not qualify a physical S23.
"""

from __future__ import annotations

CASE_ID = "TC-P016-01"
INTERVENTION = (
    "Make one camera characteristic query throw while unrelated formats and routes remain readable."
)
EXPECTED = (
    "Retain unaffected capabilities and report the failed property explicitly "
    "rather than returning an empty device inventory."
)
NEGATIVE = "A single exception that erases every candidate must fail."
FAILED_PROPERTIES = ("route_metadata", "timing", "dynamic_range", "codec")
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
    """Keep readable streams when one characteristic query throws."""
    streams, failed_property = _payload(payload)
    rejected: list[str] = [failed_property]
    preserved: list[str] = []
    seen_rejected: set[str] = set()
    query_failed = False

    for stream in streams:
        identity = _identity(stream)
        if stream["queryError"] is not None:
            query_failed = True
            if identity not in seen_rejected:
                rejected.append(identity)
                seen_rejected.add(identity)
        else:
            preserved.append(identity)

    healthy = [ _identity(stream) for stream in streams if stream["queryError"] is None ]
    if healthy and preserved != healthy:
        raise ValueError("a single exception must not erase readable candidates")
    if any(item not in preserved for item in healthy):
        raise ValueError(NEGATIVE)

    reasons = [
        f"failed property {failed_property} reported without clearing the device inventory",
        "advertisement is not operational qualification",
    ]
    if preserved:
        reasons.append("readable formats and sizes retained")
    if query_failed:
        reasons.append("a throwing characteristic query does not drop readable streams")
    return _finish("partial", reasons, rejected, preserved, [])


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
        raise ValueError("failure must not return an empty device inventory")
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


def _payload(payload: object) -> tuple[list[dict], str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != {"streams", "failedProperty"}:
        raise ValueError("payload keys must be streams and failedProperty")
    failed = payload["failedProperty"]
    if failed not in FAILED_PROPERTIES:
        raise ValueError(
            "failedProperty must be route_metadata, timing, dynamic_range, or codec"
        )
    streams = payload["streams"]
    if not isinstance(streams, list):
        raise ValueError("streams must be a list")
    return [_stream(item) for item in streams], failed


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
        if type(key) is not str or type(stream[key]) is not bool:
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
