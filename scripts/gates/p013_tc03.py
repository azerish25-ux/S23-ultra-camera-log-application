"""TC-P013-03 incompatible codec-output combination.

Individually supported outputs are not proof they can be selected together.
A violated camera constraint rejects the whole combination and keeps every
output in the inventory.
"""

from __future__ import annotations

CASE_ID = "TC-P013-03"
INTERVENTION = (
    "Provide individually supported outputs whose simultaneous combination "
    "violates the declared camera constraints."
)
EXPECTED = (
    "Reject or replan the complete combination without pretending independent "
    "support proves coexistence."
)
NEGATIVE = "Selecting every individually supported stream simultaneously must fail."
VARIANTS = ("mixed_preview", "raw_plus_encoder", "alternate_lens")
_OUTPUT_FIELDS = ("id", "format", "width", "height", "supportedAlone")
_PAYLOAD_KEYS = ("outputs", "constraintsViolated", "variant")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_COEXISTENCE = "independent support is not coexistence"


def evaluate(payload: dict) -> dict:
    """Reject a simultaneous combination that the declared constraints forbid."""
    outputs, constraints_violated, _variant = _payload(payload)
    preserved = [_size_token(item) for item in outputs]
    if constraints_violated:
        decision = "rejected"
        reasons = [_COEXISTENCE, NEGATIVE, INTERVENTION]
        rejected = [item["id"] for item in outputs]
    elif any(not item["supportedAlone"] for item in outputs):
        decision = "rejected"
        reasons = ["individually unsupported output rejects the combination"]
        rejected = [item["id"] for item in outputs if not item["supportedAlone"]]
    else:
        decision = "compatible"
        reasons = ["simultaneous combination is inside declared constraints"]
        reasons.append("compatible is not physical qualification")
        rejected = []

    if decision in {"allowed", "qualified"}:
        raise ValueError("independent support must not be allowed or qualified")
    if constraints_violated and decision != "rejected":
        raise ValueError("violated constraints must be rejected")
    if not preserved:
        raise ValueError("output inventory must be preserved")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> tuple[list[dict], bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("payload keys must be outputs, constraintsViolated, and variant")
    variant = payload["variant"]
    if variant not in VARIANTS:
        raise ValueError("variant must be mixed_preview, raw_plus_encoder, or alternate_lens")
    violated = payload["constraintsViolated"]
    if type(violated) is not bool:
        raise ValueError("constraintsViolated must be a bool")
    outputs = payload["outputs"]
    if not isinstance(outputs, list) or not outputs:
        raise ValueError("outputs must be a non-empty list")
    parsed = [_output(item) for item in outputs]
    ids = [item["id"] for item in parsed]
    if len(ids) != len(set(ids)):
        raise ValueError("output ids must be unique")
    return parsed, violated, variant


def _output(item: object) -> dict:
    if not isinstance(item, dict):
        raise ValueError("output must be a dict")
    if set(item) != set(_OUTPUT_FIELDS):
        raise ValueError("invalid output fields")
    if not isinstance(item["id"], str) or item["id"] == "" or item["id"] != item["id"].strip():
        raise ValueError("id must be a non-empty string")
    if not isinstance(item["format"], str) or item["format"] == "" or item["format"] != item["format"].strip():
        raise ValueError("format must be a non-empty string")
    for key in ("width", "height"):
        value = item[key]
        if type(value) is not int or value <= 0:
            raise ValueError(f"{key} must be a positive int")
    if type(item["supportedAlone"]) is not bool:
        raise ValueError("supportedAlone must be a bool")
    return item


def _size_token(item: dict) -> str:
    return f"{item['width']}x{item['height']}:{item['format']}"


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision not in {"rejected", "compatible"}:
        raise ValueError("unexpected TC-P013-03 decision")
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
