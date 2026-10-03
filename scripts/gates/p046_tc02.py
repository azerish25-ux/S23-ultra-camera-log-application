"""TC-P046-02 signed dark residuals.

Intervention: Introduce values below the estimated black level and a small
persistent row or column bias.
Expected: Preserve signed statistics and expose the structured error rather
than hiding it through clipping.
Negative: Clamping residuals to zero before noise analysis must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P046-02"
INTERVENTION = (
    "Introduce values below the estimated black level and a small persistent row or column bias."
)
EXPECTED = (
    "Preserve signed statistics and expose the structured error rather than hiding it "
    "through clipping."
)
NEGATIVE = "Clamping residuals to zero before noise analysis must fail."

_PAYLOAD_KEYS = (
    "captureId",
    "exposureMs",
    "gain",
    "residuals",
    "rowBias",
    "columnBias",
    "clampBeforeAnalysis",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "bias_exposed", "signed_retained")
_FORBIDDEN = {"qualified", "allowed"}
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")


def evaluate(payload: dict) -> dict:
    """Keep signed dark residuals. Clamping them before analysis fails."""
    capture_id, exposure_ms, gain, residuals, row_bias, column_bias, clamp = _payload(payload)
    preserved = [
        f"capture:{capture_id}",
        f"exposure:{exposure_ms}",
        f"gain:{gain}",
    ]
    preserved.extend(f"residual:{index}:{value}" for index, value in enumerate(residuals))
    preserved.extend(
        [
            f"row-bias:{row_bias}",
            f"column-bias:{column_bias}",
            f"signed-min:{min(residuals)}",
            f"signed-max:{max(residuals)}",
        ]
    )
    reasons = [EXPECTED]
    structured = any(value < 0 for value in residuals) or row_bias != 0 or column_bias != 0
    if clamp:
        decision = "rejected"
        rejected = ["clamped-before-analysis"]
        reasons.append(NEGATIVE)
        questions = ["clamping before noise analysis was refused"]
    elif structured:
        decision = "bias_exposed"
        rejected = []
        reasons.append(
            f"signed residual min {min(residuals)} max {max(residuals)} "
            f"row bias {row_bias} column bias {column_bias}"
        )
        questions = []
        if any(value < 0 for value in residuals):
            questions.append("values below the estimated black level")
        if row_bias != 0 or column_bias != 0:
            questions.append("structured row or column bias")
    else:
        decision = "signed_retained"
        rejected = []
        reasons.append("signed statistics retained with no structured bias")
        questions = []
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, int, int, list[int], int, int, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    capture_id = payload["captureId"]
    if not isinstance(capture_id, str) or _TOKEN.fullmatch(capture_id) is None:
        raise ValueError("captureId must be a token")
    exposure_ms = payload["exposureMs"]
    gain = payload["gain"]
    if type(exposure_ms) is not int or exposure_ms <= 0:
        raise ValueError("exposureMs must be a positive int")
    if type(gain) is not int or gain <= 0:
        raise ValueError("gain must be a positive int")
    residuals = payload["residuals"]
    if (
        not isinstance(residuals, list)
        or not residuals
        or any(type(item) is not int for item in residuals)
    ):
        raise ValueError("residuals must be a non-empty list of ints")
    row_bias = payload["rowBias"]
    column_bias = payload["columnBias"]
    if type(row_bias) is not int or type(column_bias) is not int:
        raise ValueError("rowBias and columnBias must be ints")
    clamp = payload["clampBeforeAnalysis"]
    if type(clamp) is not bool:
        raise ValueError("clampBeforeAnalysis must be a bool")
    return capture_id, exposure_ms, gain, list(residuals), row_bias, column_bias, clamp


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
