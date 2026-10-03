"""TC-P013-01 partial characteristic failure on a codec-route inventory.

One throwing characteristic query must not erase readable formats or routes.
The failed property is reported. The negative control, an exception that
erases every candidate, is rejected and is never qualified or allowed.
"""

from __future__ import annotations

CASE_ID = "TC-P013-01"
INTERVENTION = (
    "Make one camera characteristic query throw while unrelated formats and "
    "routes remain readable."
)
EXPECTED = (
    "Retain unaffected capabilities and report the failed property explicitly "
    "rather than returning an empty device inventory."
)
NEGATIVE = "A single exception that erases every candidate must fail."
FAILED_PROPERTIES = (
    "route_metadata",
    "timing_arrays",
    "dynamic_range_profiles",
    "optional_codec",
)
INTERFACES = ("surface", "byte_buffer", "image", "encoder", "decoder")
_CANDIDATE_FIELDS = ("candidateId", "codecName", "interface", "format", "queryError")
_PAYLOAD_KEYS = ("candidates", "failedProperty", "eraseAll")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_ERASED = "erased-inventory"


def evaluate(payload: dict) -> dict:
    """Keep readable codec routes when one characteristic query throws."""
    candidates, failed_property, erase_all = _payload(payload)
    readable: list[str] = []
    failed: list[str] = []
    for candidate in candidates:
        identity = _identity(candidate)
        if candidate["queryError"] is None:
            readable.append(identity)
        else:
            failed.append(identity)

    preserved = list(readable) + [f"unreadable:{item}" for item in failed]
    rejected = [failed_property, *failed]
    reasons = [
        f"failed property {failed_property} reported without clearing the device inventory",
        INTERVENTION,
    ]
    if readable:
        reasons.append("unaffected capabilities retained")
    reasons.append("a single throwing query does not erase readable candidates")

    if erase_all:
        decision = "rejected"
        rejected.append(_ERASED)
        reasons.append(NEGATIVE)
    else:
        decision = "partial"

    if not preserved:
        raise ValueError("device inventory must not be empty")
    if readable and any(item not in preserved for item in readable):
        raise ValueError("a failed characteristic query must not erase readable candidates")
    if erase_all and decision in {"qualified", "allowed", "partial"}:
        raise ValueError("erasing every candidate must fail")
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P013-01 must not decide qualified or allowed")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> tuple[list[dict], str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("payload keys must be candidates, failedProperty, and eraseAll")
    failed = payload["failedProperty"]
    if failed not in FAILED_PROPERTIES:
        raise ValueError(
            "failedProperty must be route_metadata, timing_arrays, "
            "dynamic_range_profiles, or optional_codec"
        )
    erase_all = payload["eraseAll"]
    if type(erase_all) is not bool:
        raise ValueError("eraseAll must be a bool")
    candidates = payload["candidates"]
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("candidates must be a non-empty list")
    parsed = [_candidate(item) for item in candidates]
    identities = [_identity(item) for item in parsed]
    if len(identities) != len(set(identities)):
        raise ValueError("candidate identities must be unique")
    return parsed, failed, erase_all


def _candidate(item: object) -> dict:
    if not isinstance(item, dict):
        raise ValueError("candidate must be a dict")
    if set(item) != set(_CANDIDATE_FIELDS):
        raise ValueError("invalid candidate fields")
    for key in ("candidateId", "codecName", "format"):
        value = item[key]
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError(f"{key} must be a non-empty string")
    if item["interface"] not in INTERFACES:
        raise ValueError("interface must be surface, byte_buffer, image, encoder, or decoder")
    query = item["queryError"]
    if query is not None and (
        not isinstance(query, str) or not query.strip() or query != query.strip()
    ):
        raise ValueError("queryError must be a non-empty string or null")
    return item


def _identity(candidate: dict) -> str:
    return f"{candidate['candidateId']}:{candidate['interface']}:{candidate['format']}"


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision not in {"partial", "rejected"}:
        raise ValueError("unexpected TC-P013-01 decision")
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
