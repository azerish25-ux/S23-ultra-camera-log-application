"""TC-P015-04 firmware cache staleness.

A previously successful probe becomes historical when build, app protocol,
route, codec identity, or the codec capability response changes. The marketing
model name is not a cache key and must not bypass that change.
"""

from __future__ import annotations

CASE_ID = "TC-P015-04"
INTERVENTION = "Change device build or codec identity while retaining a previously successful cached probe."
EXPECTED = "Require requalification for affected tuples and preserve the old report only as historical evidence."
NEGATIVE = "A marketing-model-name cache hit must not bypass the changed environment."
REPEAT = "Repeat with changed app probe protocol and with unchanged hardware but updated codec software."
VARIANTS = ("build_changed", "protocol_changed", "codec_software", "unchanged")
_VARIANT_FIELD = {
    "build_changed": "buildFingerprint",
    "protocol_changed": "appProtocolVersion",
    "codec_software": "codecIdentity",
    "unchanged": None,
}
_RECORD_FIELDS = (
    "tupleId",
    "reportId",
    "buildFingerprint",
    "appProtocolVersion",
    "route",
    "codecIdentity",
    "codecCapabilityResponse",
    "marketingName",
    "previouslySuccessful",
)
_PAYLOAD_KEYS = ("cached", "current", "variant")
_IDENTITY = (
    "buildFingerprint",
    "appProtocolVersion",
    "route",
    "codecIdentity",
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


def evaluate(payload: dict) -> dict:
    """Requalify when the environment changes. Ignore the marketing model name."""
    cached, current, variant = _payload(payload)
    changes = [field for field in _IDENTITY if cached[field] != current[field]]
    response_changed = cached["codecCapabilityResponse"] != current["codecCapabilityResponse"]
    same_marketing = cached["marketingName"] == current["marketingName"]
    if changes or response_changed:
        decision = "requalify"
        reasons = [
            "requalification required for affected tuples",
            "old report preserved only as historical evidence",
            "repeat " + variant,
        ]
        if same_marketing:
            reasons.append("marketing-model-name cache hit does not bypass the changed environment")
        rejected = ["marketing-name-cache-hit"]
        preserved = [f"historical:{cached['reportId']}"]
        questions = ["requalification pending"]
    else:
        decision = "cache_valid"
        reasons = [
            "build, protocol, route, and codec identity match the cached probe",
            "cache validity is not physical S23 qualification",
            "repeat " + variant,
        ]
        rejected = []
        preserved = [f"historical:{cached['reportId']}", cached["tupleId"]]
        questions = []
    if decision in _FORBIDDEN:
        raise ValueError("TC-P015-04 must not decide qualified or allowed")
    if (changes or response_changed) and decision != "requalify":
        raise ValueError("changed environment requires requalification")
    if same_marketing and (changes or response_changed) and decision in _FORBIDDEN | {"cache_valid"}:
        raise ValueError("marketing-model-name cache hit must not bypass the changed environment")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[dict, dict, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    variant = payload["variant"]
    if variant not in VARIANTS:
        raise ValueError("variant is not a known staleness repeat")
    cached = _record(payload["cached"], "cached")
    current = _record(payload["current"], "current")
    if not cached["previouslySuccessful"]:
        raise ValueError("cached probe must be a previously successful measurement")
    field = _VARIANT_FIELD[variant]
    if field is None:
        drifted = [name for name in _IDENTITY if cached[name] != current[name]]
        if drifted or cached["codecCapabilityResponse"] != current["codecCapabilityResponse"]:
            raise ValueError("unchanged variant requires matching identity and capability response")
    elif cached[field] == current[field]:
        raise ValueError(variant + " requires " + field + " to change")
    return cached, current, variant


def _record(value: object, context: str) -> dict:
    if not isinstance(value, dict) or set(value) != set(_RECORD_FIELDS):
        raise ValueError(context + " has invalid fields")
    for field in _RECORD_FIELDS:
        if field == "previouslySuccessful":
            if type(value[field]) is not bool:
                raise ValueError(context + " previouslySuccessful must be a bool")
            continue
        text = value[field]
        if not isinstance(text, str) or not text.strip() or text != text.strip():
            raise ValueError(context + " " + field + " must be a non-empty string")
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
