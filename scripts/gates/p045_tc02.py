"""TC-P045-02 signed dark residuals.

Intervention: Introduce values below the estimated black level and a small
persistent row or column bias.
Expected: Preserve signed statistics and expose the structured error rather
than hiding it through clipping.
Negative: Clamping residuals to zero before noise analysis must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal

CASE_ID = "TC-P045-02"
INTERVENTION = (
    "Introduce values below the estimated black level and a small persistent "
    "row or column bias."
)
EXPECTED = (
    "Preserve signed statistics and expose the structured error rather than "
    "hiding it through clipping."
)
NEGATIVE = "Clamping residuals to zero before noise analysis must fail."

_BIAS = ("none", "row", "column")
_PAYLOAD_KEYS = (
    "captureId",
    "exposure",
    "gain",
    "blackLevel",
    "residuals",
    "biasAxis",
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
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+/-]{0,63}")
_SIGNED = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Keep signed dark residuals visible. Clamping them to zero is rejected."""
    capture, exposure, gain, black, residuals, bias, clamp = _payload(payload)
    numbers = [Decimal(item) for item in residuals]
    signed_min = min(numbers)
    signed_max = max(numbers)
    preserved = [
        f"capture:{capture}",
        f"exposure:{exposure}",
        f"gain:{gain}",
        f"black:{black}",
        f"bias:{bias}",
        f"signed-min:{_canonical(signed_min)}",
        f"signed-max:{_canonical(signed_max)}",
    ]
    preserved.extend(f"residual:{item}" for item in residuals)
    reasons = [EXPECTED, INTERVENTION]
    questions: list[str] = []
    if clamp:
        decision = "rejected"
        rejected = ["clamped-residuals", "hidden-signed-dark"]
        reasons.append(NEGATIVE)
        reasons.append("signed residuals were not replaced with zeros")
        questions.append("clamped noise analysis was rejected")
    else:
        decision = "exposed"
        rejected = []
        reasons.append("signed statistics were preserved")
        if bias == "none":
            questions.append("no structured row or column bias declared")
        else:
            rejected.append(f"structured-bias:{bias}")
            reasons.append(f"structured {bias} bias remains visible")
            questions.append(f"structured {bias} bias exposed")
    return _result(decision, reasons, rejected, preserved, questions)


def _canonical(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def _payload(payload: object) -> tuple[str, str, str, str, list[str], str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    capture = payload["captureId"]
    exposure = payload["exposure"]
    gain = payload["gain"]
    for name, value in (("captureId", capture), ("exposure", exposure), ("gain", gain)):
        if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
            raise ValueError(f"{name} must be a token")
    black = payload["blackLevel"]
    if not isinstance(black, str) or _DECIMAL.fullmatch(black) is None:
        raise ValueError("blackLevel must be a canonical decimal string")
    residuals = payload["residuals"]
    if type(residuals) is not list or not 1 <= len(residuals) <= 64:
        raise ValueError("residuals must be a list of one to sixty-four samples")
    if any(not isinstance(item, str) or _SIGNED.fullmatch(item) is None or item == "-0" for item in residuals):
        raise ValueError("residuals must be canonical signed decimals")
    if not any(item.startswith("-") for item in residuals):
        raise ValueError("residuals must include a value below the black level")
    bias = payload["biasAxis"]
    if bias not in _BIAS:
        raise ValueError("biasAxis must be none, row, or column")
    clamp = payload["clampResiduals"]
    if type(clamp) is not bool:
        raise ValueError("clampResiduals must be a bool")
    return capture, exposure, gain, black, list(residuals), bias, clamp


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P045-02 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
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
