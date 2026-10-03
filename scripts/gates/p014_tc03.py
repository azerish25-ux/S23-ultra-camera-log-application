"""TC-P014-03 high-resolution experiment matrix: incompatible output combination.

Individually supported streams are not proof of a simultaneous combination.
A violated stream-map constraint rejects the whole combination.
"""

from __future__ import annotations

CASE_ID = "TC-P014-03"
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


def evaluate(payload: dict) -> dict:
    """Decide whether a simultaneous output combination is actually supported."""
    outputs, constraints_violated, _variant = _payload(payload)
    preserved = [_size_token(item) for item in outputs]
    if constraints_violated:
        decision = "rejected"
        reasons = [_COEXISTENCE]
        rejected = [item["id"] for item in outputs]
    elif any(not item["supportedAlone"] for item in outputs):
        decision = "rejected"
        reasons = ["individually unsupported output rejects the combination"]
        rejected = [item["id"] for item in outputs if not item["supportedAlone"]]
    else:
        decision = "compatible"
        reasons = ["simultaneous combination is inside declared constraints"]
        rejected = []

    if decision in {"allowed", "qualified"}:
        raise ValueError("independent support must not be allowed or qualified")
    if constraints_violated and decision != "rejected":
        raise ValueError("violated constraints must be rejected")
    if not reasons:
        raise ValueError("reasons required")

    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": [],
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
        raise ValueError(
            "variant must be mixed_preview, raw_plus_encoder, or alternate_lens"
        )
    violated = payload["constraintsViolated"]
    if not isinstance(violated, bool):
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
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{key} must be a positive int")
    if not isinstance(item["supportedAlone"], bool):
        raise ValueError("supportedAlone must be a bool")
    return item


def _size_token(item: dict) -> str:
    return f"{item['width']}x{item['height']}:{item['format']}"
