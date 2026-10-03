"""TC-P047-02 signed dark residuals.

Intervention: Introduce values below the estimated black level and a small
persistent row or column bias.
Expected: Preserve signed statistics and expose the structured error rather
than hiding it through clipping.
Negative: Clamping residuals to zero before noise analysis must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P047-02"
INTERVENTION = (
    "Introduce values below the estimated black level and a small persistent "
    "row or column bias."
)
EXPECTED = (
    "Preserve signed statistics and expose the structured error rather than "
    "hiding it through clipping."
)
NEGATIVE = "Clamping residuals to zero before noise analysis must fail."

_TOKEN = "abcdefghijklmnopqrstuvwxyz0123456789-:+."
_PAYLOAD_KEYS = (
    "exposureTime",
    "gain",
    "captureId",
    "residualMin",
    "rowBias",
    "columnBias",
    "clampResidualsToZero",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "signed_retained")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep signed dark residuals. Clamping them to zero fails the case."""
    exposure, gain, capture, residual, row_bias, column_bias, clamp = _payload(payload)
    preserved = [
        "exposure:" + exposure,
        "gain:" + gain,
        "capture:" + capture,
        "residualMin:" + residual,
        "rowBias:" + row_bias,
        "columnBias:" + column_bias,
    ]
    questions = _structure(residual, row_bias, column_bias)
    if clamp:
        return _result(
            "rejected",
            [
                NEGATIVE,
                EXPECTED,
                "signed residuals were not replaced with zero",
            ],
            ["clamped-residuals"],
            preserved,
            questions,
        )
    return _result(
        "signed_retained",
        [
            EXPECTED,
            "signed statistics preserved",
            "structured error exposed without clipping",
        ],
        [],
        preserved,
        questions,
    )


def _structure(residual: str, row_bias: str, column_bias: str) -> list[str]:
    questions: list[str] = []
    if residual[0] == "-":
        questions.append("below-black:" + residual)
    if row_bias != "0":
        questions.append("row-bias:" + row_bias)
    if column_bias != "0":
        questions.append("column-bias:" + column_bias)
    return questions


def _payload(payload: object) -> tuple[str, str, str, str, str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    clamp = payload["clampResidualsToZero"]
    if type(clamp) is not bool:
        raise ValueError("clampResidualsToZero must be a bool")
    return (
        _positive(payload["exposureTime"], "exposureTime"),
        _positive(payload["gain"], "gain"),
        _token(payload["captureId"], "captureId"),
        _signed(payload["residualMin"], "residualMin"),
        _signed(payload["rowBias"], "rowBias"),
        _signed(payload["columnBias"], "columnBias"),
        clamp,
    )


def _token(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or any(char not in _TOKEN for char in value):
        raise ValueError(label + " must be a canonical token")
    return value


def _positive(value: object, label: str) -> str:
    text = _unsigned(value, label)
    if text == "0":
        raise ValueError(label + " must be positive")
    return text


def _signed(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(label + " must be a signed canonical decimal")
    if value[0] == "-":
        body = value[1:]
        if not body or body == "0":
            raise ValueError(label + " must be a signed canonical decimal")
        _unsigned(body, label)
        return value
    return _unsigned(value, label)


def _unsigned(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(label + " must be a canonical decimal string")
    if "." in value:
        whole, frac = value.split(".", 1)
        if (
            not frac
            or frac[-1] == "0"
            or not _digits(whole)
            or not _digits(frac)
            or (len(whole) > 1 and whole[0] == "0")
        ):
            raise ValueError(label + " must be a canonical decimal string")
        return value
    if not _digits(value) or (len(value) > 1 and value[0] == "0"):
        raise ValueError(label + " must be a canonical decimal string")
    return value


def _digits(value: str) -> bool:
    return bool(value) and all("0" <= char <= "9" for char in value)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("dark residual decision cannot be qualified or allowed")
    if not reasons or any(type(item) is not str or not item for item in reasons):
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
