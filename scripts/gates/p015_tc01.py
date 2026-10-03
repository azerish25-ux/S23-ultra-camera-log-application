"""TC-P015-01 partial characteristic failure.

One throwing camera-characteristic query must not erase the device inventory.
Unaffected formats and routes stay in preservedResults. The failed property is
named. An erase-all claim is rejected and is never qualified or allowed.
"""

from __future__ import annotations

CASE_ID = "TC-P015-01"
INTERVENTION = (
    "Make one camera characteristic query throw while unrelated formats and routes remain readable."
)
EXPECTED = (
    "Retain unaffected capabilities and report the failed property explicitly "
    "rather than returning an empty device inventory."
)
NEGATIVE = "A single exception that erases every candidate must fail."
REPEAT = (
    "Repeat across route metadata, timing arrays, dynamic-range profiles, and optional codec queries."
)
FAILED_PROPERTIES = (
    "route_metadata",
    "timing_arrays",
    "dynamic_range_profiles",
    "optional_codec",
)
_CAPABILITY_FIELDS = ("id", "kind", "readable", "queryError")
_PAYLOAD_KEYS = ("capabilities", "failedProperty", "eraseAllCandidates")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep readable capabilities when one property query throws."""
    capabilities, failed_property, erase_all = _payload(payload)
    readable = [item for item in capabilities if item["readable"]]
    unreadable = [item for item in capabilities if not item["readable"]]
    preserved = [item["id"] for item in readable]
    rejected = [failed_property]
    rejected.extend(item["id"] for item in unreadable)
    reasons = [
        f"failed property {failed_property} reported explicitly",
        "unaffected capabilities retained",
    ]
    if erase_all:
        decision = "rejected"
        rejected.insert(0, "erase-all-candidates")
        reasons.insert(0, "a single exception must not erase every candidate")
    else:
        decision = "partial"
        reasons.append("a throwing characteristic query does not drop readable streams")
    if readable and not preserved:
        raise ValueError("a failed characteristic query must not erase healthy capabilities")
    if erase_all and not preserved:
        raise ValueError("erase-all must fail while unaffected capabilities exist")
    if decision in _FORBIDDEN:
        raise ValueError("TC-P015-01 must not decide qualified or allowed")
    open_questions = [failed_property]
    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object) -> tuple[list[dict], str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    failed = payload["failedProperty"]
    if failed not in FAILED_PROPERTIES:
        raise ValueError("failedProperty is not a known characteristic")
    erase_all = payload["eraseAllCandidates"]
    if type(erase_all) is not bool:
        raise ValueError("eraseAllCandidates must be a bool")
    capabilities = payload["capabilities"]
    if not isinstance(capabilities, list) or not capabilities:
        raise ValueError("capabilities must be a non-empty list")
    seen: set[str] = set()
    checked: list[dict] = []
    for index, item in enumerate(capabilities):
        if not isinstance(item, dict) or set(item) != set(_CAPABILITY_FIELDS):
            raise ValueError(f"capabilities[{index}] has invalid fields")
        identity = item["id"]
        if not isinstance(identity, str) or not identity.strip() or identity != identity.strip():
            raise ValueError(f"capabilities[{index}] id must be a non-empty string")
        if identity in seen:
            raise ValueError("duplicate capability id: " + identity)
        seen.add(identity)
        kind = item["kind"]
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError(f"capabilities[{index}] kind must be a non-empty string")
        readable = item["readable"]
        if type(readable) is not bool:
            raise ValueError(f"capabilities[{index}] readable must be a bool")
        query_error = item["queryError"]
        if readable:
            if query_error is not None:
                raise ValueError(f"capabilities[{index}] readable capability cannot have queryError")
        elif not isinstance(query_error, str) or not query_error.strip():
            raise ValueError(f"capabilities[{index}] queryError must be a non-empty string")
        checked.append(item)
    if not any(item["readable"] for item in checked):
        raise ValueError("at least one unrelated capability must remain readable")
    return checked, failed, erase_all


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in _FORBIDDEN:
        raise ValueError("decision must not be qualified or allowed")
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
