"""TC-P041-02 signed dark residuals.

Values below the estimated black level and a persistent row or column bias
stay signed. Clamping those residuals to zero before noise analysis fails.
"""

from __future__ import annotations

import re
from decimal import Decimal

CASE_ID = "TC-P041-02"
INTERVENTION = (
    "Introduce values below the estimated black level and a small persistent row or column bias."
)
EXPECTED = (
    "Preserve signed statistics and expose the structured error rather than hiding it through clipping."
)
NEGATIVE = "Clamping residuals to zero before noise analysis must fail."

_FINITE = re.compile(r"^(?:0|-?0\.[0-9]*[1-9]|-?[1-9][0-9]*(?:\.[0-9]*[1-9])?)$")
_UINT = re.compile(r"^[1-9][0-9]*$")
_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9-]{0,63}$")
_PAYLOAD_KEYS = (
    "captureId",
    "exposureNs",
    "gain",
    "residualMin",
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
_DECISIONS = {"rejected", "signed_residuals", "withheld"}
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep signed dark statistics. Clamping before analysis is rejected."""
    fields = _payload(payload)
    preserved = [
        f"capture:{fields['captureId']}",
        f"exposureNs:{fields['exposureNs']}",
        f"gain:{fields['gain']}",
        f"residualMin:{fields['residualMin']}",
        f"rowBias:{fields['rowBias']}",
        f"columnBias:{fields['columnBias']}",
    ]
    below = Decimal(fields["residualMin"]) < 0
    structured = fields["rowBias"] != "0" or fields["columnBias"] != "0"
    if fields["clampBeforeAnalysis"]:
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "signed residuals were not replaced with zero"],
            ["clamped-residuals"],
            preserved,
            ["structured error stays visible"],
        )
    if not below and not structured:
        return _result(
            "withheld",
            [EXPECTED, "no signed residual or structured bias was supplied"],
            [],
            preserved,
            ["dark statistics were not invented"],
        )
    questions = ["structured row or column bias"] if structured else []
    reasons = [EXPECTED, "signed statistics were preserved"]
    if below:
        reasons.append("residual minimum is below the estimated black level")
    if structured:
        reasons.append("row or column bias was exposed")
    return _result("signed_residuals", reasons, [], preserved, questions)


def _decimal(value: object, label: str) -> str:
    if not isinstance(value, str) or _FINITE.fullmatch(value) is None:
        raise ValueError(label + " must be a canonical finite decimal")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    capture = payload["captureId"]
    if not isinstance(capture, str) or _TOKEN.fullmatch(capture) is None:
        raise ValueError("captureId must be a token")
    exposure = payload["exposureNs"]
    if not isinstance(exposure, str) or _UINT.fullmatch(exposure) is None:
        raise ValueError("exposureNs must be a positive integer string")
    gain = _decimal(payload["gain"], "gain")
    if Decimal(gain) <= 0:
        raise ValueError("gain must be positive")
    residual = _decimal(payload["residualMin"], "residualMin")
    row = _decimal(payload["rowBias"], "rowBias")
    column = _decimal(payload["columnBias"], "columnBias")
    clamp = payload["clampBeforeAnalysis"]
    if type(clamp) is not bool:
        raise ValueError("clampBeforeAnalysis must be a bool")
    return {
        "captureId": capture,
        "exposureNs": exposure,
        "gain": gain,
        "residualMin": residual,
        "rowBias": row,
        "columnBias": column,
        "clampBeforeAnalysis": clamp,
    }


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P041-02 must not yield qualified or allowed")
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
