"""TC-P015-03 incompatible output combination.

Individually supported outputs are not proof they can be selected together.
A violated constraint, or an attempt to select every supported stream at once,
rejects the combination. The output inventory stays in preservedResults.
The decision is never qualified or allowed.
"""

from __future__ import annotations

CASE_ID = "TC-P015-03"
INTERVENTION = (
    "Provide individually supported outputs whose simultaneous combination "
    "violates the declared camera constraints."
)
EXPECTED = (
    "Reject or replan the complete combination without pretending independent "
    "support proves coexistence."
)
NEGATIVE = "Selecting every individually supported stream simultaneously must fail."
REPEAT = "Repeat with mixed preview profiles, RAW plus encoder outputs, and alternate lens routes."
VARIANTS = ("mixed_preview", "raw_plus_encoder", "alternate_lens")
_OUTPUT_FIELDS = ("id", "supportedAlone")
_PAYLOAD_KEYS = ("outputs", "constraintsViolated", "selectAll", "variant")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}
_COEXISTENCE = "independent support is not coexistence"


def evaluate(payload: dict) -> dict:
    """Reject a simultaneous combination that the declared constraints do not allow."""
    outputs, constraints_violated, select_all, variant = _payload(payload)
    preserved = [item["id"] for item in outputs]
    reasons = [f"variant {variant}", _COEXISTENCE]
    if constraints_violated or select_all:
        decision = "rejected"
        rejected = [item["id"] for item in outputs]
        rejected.append("coexistence")
        reasons.append("complete combination rejected; replan without assuming coexistence")
        if select_all:
            reasons.append("selecting every individually supported stream simultaneously fails")
            rejected.append("select-all")
        open_questions = ["replan required"]
    elif any(not item["supportedAlone"] for item in outputs):
        decision = "rejected"
        rejected = [item["id"] for item in outputs if not item["supportedAlone"]]
        reasons.append("an individually unsupported output rejects the combination")
        open_questions = []
    else:
        decision = "within_constraints"
        rejected = []
        reasons.append("declared constraints are intact; this is not physical coexistence proof")
        open_questions = []
    if decision in _FORBIDDEN:
        raise ValueError("independent support must not be qualified or allowed")
    if (constraints_violated or select_all) and decision != "rejected":
        raise ValueError("violated or select-all combination must be rejected")
    if not preserved:
        raise ValueError("output inventory must be preserved")
    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object) -> tuple[list[dict], bool, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    variant = payload["variant"]
    if variant not in VARIANTS:
        raise ValueError("variant is not a known combination")
    if type(payload["constraintsViolated"]) is not bool:
        raise ValueError("constraintsViolated must be a bool")
    if type(payload["selectAll"]) is not bool:
        raise ValueError("selectAll must be a bool")
    outputs = payload["outputs"]
    if not isinstance(outputs, list) or len(outputs) < 2:
        raise ValueError("outputs must list at least two streams")
    seen: set[str] = set()
    checked: list[dict] = []
    for index, item in enumerate(outputs):
        if not isinstance(item, dict) or set(item) != set(_OUTPUT_FIELDS):
            raise ValueError(f"outputs[{index}] has invalid fields")
        identity = item["id"]
        if not isinstance(identity, str) or not identity.strip() or identity != identity.strip():
            raise ValueError(f"outputs[{index}] id must be a non-empty string")
        if identity in seen:
            raise ValueError("duplicate output id: " + identity)
        seen.add(identity)
        if type(item["supportedAlone"]) is not bool:
            raise ValueError(f"outputs[{index}] supportedAlone must be a bool")
        checked.append(item)
    return checked, payload["constraintsViolated"], payload["selectAll"], variant


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
