"""TC-P044-02 signed dark residuals.

Intervention: Introduce values below the estimated black level and a small
persistent row or column bias.
Expected: Preserve signed statistics and expose the structured error rather
than hiding it through clipping.
Negative: Clamping residuals to zero before noise analysis must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P044-02"
INTERVENTION = (
    "Introduce values below the estimated black level and a small persistent row or column bias."
)
EXPECTED = (
    "Preserve signed statistics and expose the structured error rather than hiding it through clipping."
)
NEGATIVE = "Clamping residuals to zero before noise analysis must fail."

_STRUCTURES = ("none", "row", "column")
_PAYLOAD_KEYS = (
    "captureId",
    "exposureTimeMs",
    "gain",
    "residuals",
    "structure",
    "clampToZero",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "structured_error", "signed_retained")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep signed dark residuals. Clamping them before analysis fails."""
    capture, exposure_ms, gain, residuals, structure, clamp = _payload(payload)
    signed_min = min(residuals)
    signed_sum = sum(residuals)
    preserved = [
        f"capture:{capture}",
        f"exposure-ms:{exposure_ms}",
        f"gain:{gain}",
        f"structure:{structure}",
        f"signed-min:{signed_min}",
        f"signed-sum:{signed_sum}",
    ]
    preserved.extend(f"residual:{value}" for value in residuals)
    reasons = [EXPECTED, "signed statistics preserved"]
    if clamp:
        decision = "rejected"
        rejected = ["clamped-residuals-before-noise"]
        reasons.append(NEGATIVE)
        questions = ["clamping before noise analysis failed"]
    else:
        rejected = []
        if signed_min < 0:
            rejected.append("below-black")
        if structure == "row":
            rejected.append("row-bias")
        elif structure == "column":
            rejected.append("column-bias")
        decision = "structured_error" if rejected else "signed_retained"
        if rejected:
            reasons.append("structured error exposed without clipping")
        questions = [item.replace("-", " ") for item in rejected]
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, int, int, list[int], str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    capture = payload["captureId"]
    if not isinstance(capture, str) or not capture or capture != capture.strip():
        raise ValueError("captureId must be a non-empty string")
    exposure_ms = payload["exposureTimeMs"]
    gain = payload["gain"]
    if type(exposure_ms) is not int or exposure_ms <= 0:
        raise ValueError("exposureTimeMs must be a positive int")
    if type(gain) is not int or gain <= 0:
        raise ValueError("gain must be a positive int")
    residuals = payload["residuals"]
    if (
        not isinstance(residuals, list)
        or not residuals
        or any(type(item) is not int for item in residuals)
    ):
        raise ValueError("residuals must be a non-empty list of ints")
    structure = payload["structure"]
    if structure not in _STRUCTURES:
        raise ValueError("structure must be none, row, or column")
    clamp = payload["clampToZero"]
    if type(clamp) is not bool:
        raise ValueError("clampToZero must be a bool")
    return capture, exposure_ms, gain, list(residuals), structure, clamp


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("dark-residual decision cannot be qualified or allowed")
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
