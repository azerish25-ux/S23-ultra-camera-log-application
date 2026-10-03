"""TC-P011-03 incompatible output combination.

Individually supported outputs are not proof they can be selected together.
Selecting every supported stream at once is rejected. Container timestamps
do not make that combination a native fixed 24 cadence.
"""

from __future__ import annotations

import math


CASE_ID = "TC-P011-03"
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
_OUTPUT_KEYS = ("id", "supportedAlone")
_PAYLOAD_KEYS = (
    "outputs",
    "constraintsViolated",
    "selectAll",
    "variant",
    "aeMin",
    "aeMax",
    "requestedFps",
    "containerTimestampsAssigned",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed", "native_fixed_24"}


def evaluate(payload: dict) -> dict:
    """Reject a simultaneous selection that independent support does not prove."""
    outputs, violated, select_all, variant, ae_min, ae_max, requested, timestamps = _payload(payload)
    preserved = [f"alone:{item['id']}" for item in outputs]
    preserved.append(f"ae:{_text(ae_min)}-{_text(ae_max)}")
    preserved.append(f"requested:{_text(requested)}")
    ids = [item["id"] for item in outputs]
    reasons = [f"variant {variant}"]
    if select_all or violated:
        decision = "rejected"
        rejected = list(ids)
        reasons.append("independent support is not coexistence")
        if select_all:
            reasons.append("selecting every individually supported stream simultaneously is rejected")
        if violated:
            reasons.append("declared camera constraints reject this simultaneous combination")
    elif any(not item["supportedAlone"] for item in outputs):
        decision = "rejected"
        rejected = [item["id"] for item in outputs if not item["supportedAlone"]]
        reasons.append("individually unsupported output rejects the combination")
    else:
        decision = "withheld"
        rejected = []
        reasons.append("a proper subset is not a simultaneous coexistence certificate")
    if timestamps:
        rejected.append("native-fixed-24")
        reasons.append("container timestamps do not certify native fixed 24")
    if select_all and decision != "rejected":
        raise ValueError(NEGATIVE)
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object):
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    variant = payload["variant"]
    if variant not in VARIANTS:
        raise ValueError("variant must be mixed_preview, raw_plus_encoder, or alternate_lens")
    violated = payload["constraintsViolated"]
    select_all = payload["selectAll"]
    timestamps = payload["containerTimestampsAssigned"]
    if type(violated) is not bool or type(select_all) is not bool or type(timestamps) is not bool:
        raise ValueError("constraintsViolated, selectAll, and containerTimestampsAssigned must be bools")
    outputs = payload["outputs"]
    if not isinstance(outputs, list) or not outputs:
        raise ValueError("outputs must be a non-empty list")
    parsed = [_output(item) for item in outputs]
    ids = [item["id"] for item in parsed]
    if len(ids) != len(set(ids)):
        raise ValueError("output ids must be unique")
    ae_min = _rate(payload["aeMin"], "aeMin")
    ae_max = _rate(payload["aeMax"], "aeMax")
    if _cmp(ae_min, ae_max) > 0:
        raise ValueError("aeMin must not exceed aeMax")
    requested = _rate(payload["requestedFps"], "requestedFps")
    return parsed, violated, select_all, variant, ae_min, ae_max, requested, timestamps


def _output(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != set(_OUTPUT_KEYS):
        raise ValueError("invalid output fields")
    identity = value["id"]
    if not isinstance(identity, str) or not identity or identity != identity.strip():
        raise ValueError("output id must be a non-empty string")
    if type(value["supportedAlone"]) is not bool:
        raise ValueError("supportedAlone must be a bool")
    return {"id": identity, "supportedAlone": value["supportedAlone"]}


def _rate(value: object, context: str) -> tuple[int, int]:
    if not isinstance(value, dict) or set(value) != {"numerator", "denominator"}:
        raise ValueError(context + " must be a numerator/denominator object")
    numerator = value["numerator"]
    denominator = value["denominator"]
    if type(numerator) is not int or type(denominator) is not int:
        raise ValueError(context + " must use ints")
    if numerator <= 0 or denominator <= 0:
        raise ValueError(context + " must be positive")
    if math.gcd(numerator, denominator) != 1:
        raise ValueError(context + " must be reduced")
    return numerator, denominator


def _text(rate: tuple[int, int]) -> str:
    return f"{rate[0]}/{rate[1]}"


def _cmp(left: tuple[int, int], right: tuple[int, int]) -> int:
    gap = left[0] * right[1] - right[0] * left[1]
    return (gap > 0) - (gap < 0)


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in _FORBIDDEN:
        raise ValueError("TC-P011-03 must not yield qualified, allowed, or native_fixed_24")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
