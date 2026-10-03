"""TC-P012-01 dynamic-range profile discovery: partial characteristic failure.

Preserve every readable advertised format and size. One throwing characteristic
query must not erase the device inventory. Naming the failed property is not
operational qualification and is not an allowed decision.
"""

from __future__ import annotations

INTERVENTION = 'Make one camera characteristic query throw while unrelated formats and routes remain readable.'
EXPECTED = 'Retain unaffected capabilities and report the failed property explicitly rather than returning an empty device inventory.'
NEGATIVE = 'A single exception that erases every candidate must fail.'

def _assert_case_contract() -> None:
    if not isinstance(INTERVENTION, str) or not INTERVENTION:
        raise ValueError("intervention missing")
    if not isinstance(EXPECTED, str) or not EXPECTED:
        raise ValueError("expected missing")
    if not isinstance(NEGATIVE, str) or not NEGATIVE:
        raise ValueError("negative missing")
    if "must fail" not in NEGATIVE and "must not" not in NEGATIVE:
        raise ValueError("negative control missing")


CASE_ID = "TC-P012-01"
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


def evaluate(payload: dict) -> dict:
    """Inventory profile routes. A failed property or query does not clear the rest.

    Decision is ``partial`` when any stream has ``queryError`` or ``failedProperty``
    is set; otherwise ``inventoried``. A validated payload always sets
    ``failedProperty``, so a readable map stays partial rather than qualified.
    """
    _assert_case_contract()
    streams, failed_property = _payload(payload)
    reasons: list[str] = []
    rejected: list[str] = [failed_property]
    preserved: list[str] = []
    open_questions: list[str] = []
    query_failed = False
    seen_rejected: set[str] = set()

    for stream in streams:
        identity = _identity(stream)
        if stream["queryError"] is not None:
            query_failed = True
            if identity not in seen_rejected:
                rejected.append(identity)
                seen_rejected.add(identity)
        else:
            preserved.append(identity)

    property_set = failed_property in FAILED_PROPERTIES
    if query_failed or property_set:
        decision = "partial"
    else:
        decision = "inventoried"

    reasons.append(
        f"failed property {failed_property} reported without clearing the device inventory"
    )
    if preserved:
        reasons.append("readable formats and sizes retained")
    if query_failed:
        reasons.append("a throwing characteristic query does not drop readable streams")
    reasons.append("advertisement is not operational qualification")

    healthy = sum(stream["queryError"] is None for stream in streams)
    if healthy and len(preserved) != healthy:
        raise ValueError("a failed characteristic query must not erase healthy streams")
    if healthy and not preserved:
        raise ValueError("preservedResults empty while a stream is healthy")
    if decision == "allowed":
        raise ValueError("TC-P012-01 must not decide allowed")
    if decision != "allowed" and not reasons:
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
        if not isinstance(stream[key], bool):
            raise ValueError(f"{key} must be a bool")
    samples = stream["samples"]
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 0:
        raise ValueError("samples must be a non-negative int")
    query = stream["queryError"]
    if query is not None and (not isinstance(query, str) or not query):
        raise ValueError("queryError must be a non-empty string or null")
    return stream


def _positive_int(value: object, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive int")


def _identity(stream: dict) -> str:
    return f"{stream['width']}x{stream['height']}:{stream['format']}@{stream['logicalId']}"
