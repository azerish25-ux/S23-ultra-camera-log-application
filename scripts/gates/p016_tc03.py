"""TC-P016-03 incompatible output combination on the first slice.

Individually supported outputs are not coexistence. A violated camera
constraint rejects the whole simultaneous selection. The inventory of sizes
stays. This host case does not qualify a physical S23.
"""

from __future__ import annotations

CASE_ID = "TC-P016-03"
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
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_COEXISTENCE = "independent support is not coexistence"
_ORACLE_PRESERVED = ("file-retained", "playback:separate", "cadence:separate")
_NOT_ENDURANCE = "not-endurance-certified"


def evaluate(payload: dict) -> dict:
    """Reject a simultaneous selection that violates declared constraints."""
    outputs, constraints_violated, variant = _payload(payload)
    preserved = [_size_token(item) for item in outputs]
    if constraints_violated:
        decision = "rejected"
        reasons = [f"variant {variant}", _COEXISTENCE]
        rejected = [item["id"] for item in outputs]
        if decision != "rejected":
            raise ValueError(NEGATIVE)
    elif any(not item["supportedAlone"] for item in outputs):
        decision = "rejected"
        reasons = [
            f"variant {variant}",
            "individually unsupported output rejects the combination",
        ]
        rejected = [item["id"] for item in outputs if not item["supportedAlone"]]
    else:
        decision = "compatible"
        reasons = [
            f"variant {variant}",
            "simultaneous combination is inside declared constraints",
        ]
        rejected = []
        if any("proves coexistence" in item for item in reasons):
            raise ValueError("independent support must not be treated as coexistence")

    if constraints_violated and decision != "rejected":
        raise ValueError("violated constraints must be rejected")
    if not preserved:
        raise ValueError("output inventory must be preserved")
    return _finish(decision, reasons, rejected, preserved, [])


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


def _payload(payload: object) -> tuple[list[dict], bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != {"outputs", "constraintsViolated", "variant"}:
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
    if not isinstance(item["id"], str) or item["id"] == "":
        raise ValueError("id must be a non-empty string")
    if not isinstance(item["format"], str) or item["format"] == "":
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
