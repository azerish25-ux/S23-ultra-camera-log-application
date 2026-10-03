"""TC-P043-02 signed dark residuals.

Intervention: Introduce values below the estimated black level and a small
persistent row or column bias.
Expected: Preserve signed statistics and expose the structured error rather
than hiding it through clipping.
Negative: Clamping residuals to zero before noise analysis must fail.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P043-02"
INTERVENTION = (
    "Introduce values below the estimated black level and a small persistent "
    "row or column bias."
)
EXPECTED = (
    "Preserve signed statistics and expose the structured error rather than "
    "hiding it through clipping."
)
NEGATIVE = "Clamping residuals to zero before noise analysis must fail."

_AXES = ("none", "row", "column")
_PAYLOAD_KEYS = (
    "captureId",
    "exposureNs",
    "gain",
    "blackLevel",
    "sample",
    "biasAxis",
    "bias",
    "clampResiduals",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "structured_error", "residuals_recorded")
_FORBIDDEN = {"qualified", "allowed"}
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Keep the signed residual. Clamping it to zero is a failure."""
    capture, exposure, gain, black, sample, axis, bias, clamp = _payload(payload)
    signed = sample - black
    preserved = [
        f"capture:{capture}",
        f"exposureNs:{exposure}",
        f"gain:{gain}",
        f"signed:{signed}",
        f"bias:{axis}:{bias}",
    ]
    rejected: list[str] = []
    questions = ["signed residual was not replaced by zero"]
    if signed < 0:
        rejected.append("below-black")
    if axis != "none":
        rejected.append(f"{axis}-bias")
    if clamp:
        decision = "rejected"
        rejected.append("residuals-clamped")
        reasons = [NEGATIVE, EXPECTED, f"signed residual {signed} kept"]
        questions.append("noise analysis must see the signed residual")
    elif rejected:
        decision = "structured_error"
        reasons = [EXPECTED, f"signed residual {signed} exposed"]
    else:
        decision = "residuals_recorded"
        reasons = [f"signed residual {signed} recorded", "this record is not a physical dark frame"]
        questions.append("host residual is not a sensor measurement")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, int, str, int, int, str, int, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    capture = payload["captureId"]
    if not isinstance(capture, str) or not capture or capture != capture.strip():
        raise ValueError("captureId must be a non-empty string")
    exposure = payload["exposureNs"]
    if type(exposure) is not int or exposure <= 0:
        raise ValueError("exposureNs must be a positive int")
    gain = payload["gain"]
    if not isinstance(gain, str) or _DECIMAL.fullmatch(gain) is None:
        raise ValueError("gain must be a canonical decimal string")
    black = payload["blackLevel"]
    sample = payload["sample"]
    bias = payload["bias"]
    for label, value in (("blackLevel", black), ("sample", sample), ("bias", bias)):
        if type(value) is not int:
            raise ValueError(f"{label} must be an int")
    axis = payload["biasAxis"]
    if axis not in _AXES:
        raise ValueError("biasAxis must be none, row, or column")
    if axis == "none" and bias != 0:
        raise ValueError("bias requires a row or column axis")
    if axis != "none" and bias == 0:
        raise ValueError("row or column bias must be non-zero")
    clamp = _bool(payload["clampResiduals"], "clampResiduals")
    return capture, exposure, gain, black, sample, axis, bias, clamp


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("residual decision cannot be qualified or allowed")
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
