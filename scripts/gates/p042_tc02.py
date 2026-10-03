"""TC-P042-02 signed dark residuals.

Values below the black level and a row or column bias stay signed. Clamping
those residuals to zero before noise analysis is rejected and does not erase
the signed sum.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P042-02"
INTERVENTION = (
    "Introduce values below the estimated black level and a small persistent "
    "row or column bias."
)
EXPECTED = (
    "Preserve signed statistics and expose the structured error rather than "
    "hiding it through clipping."
)
NEGATIVE = "Clamping residuals to zero before noise analysis must fail."

_STRUCTURES = ("none", "row", "column")
_REPEATS = ("exposure", "gain", "independent_capture")
_SIGNED = re.compile(r"0|-?[1-9][0-9]*")
_UINT = re.compile(r"[1-9][0-9]*")
_GAIN = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?")
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_PAYLOAD_KEYS = (
    "residuals",
    "structure",
    "repeat",
    "clamp",
    "exposureNs",
    "gain",
    "captureId",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "signed_retained", "withheld")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep the signed sum. Clamping is a failed noise analysis."""
    residuals, structure, repeat, clamp, exposure, gain, capture = _payload(payload)
    signed = sum(residuals)
    preserved = [f"residual:{value}" for value in residuals]
    preserved.append(f"signed-sum:{signed}")
    preserved.append(f"capture:{capture}")
    preserved.append(f"exposure:{exposure}ns")
    preserved.append(f"gain:{gain}")
    preserved.append(f"repeat:{repeat}")
    if clamp:
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "residuals were not clamped before the signed sum"],
            ["clamped-residuals"],
            preserved,
            [f"repeat {repeat} kept the signed inventory"],
        )
    claims: list[str] = []
    if structure == "row":
        claims.append("row-bias")
    elif structure == "column":
        claims.append("column-bias")
    if signed < 0 or claims:
        reasons = [EXPECTED, INTERVENTION, f"signed sum {signed} on repeat {repeat}"]
        if claims:
            reasons.append(f"structured error {structure} remains visible")
        return _result(
            "signed_retained",
            reasons,
            claims,
            preserved,
            [f"repeat {repeat} did not clip the residuals"],
        )
    return _result(
        "withheld",
        [EXPECTED, f"no signed defect on repeat {repeat}"],
        [],
        preserved,
        ["non-negative residuals are not a read-noise certificate"],
    )


def _payload(payload: object) -> tuple[list[int], str, str, bool, str, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    raw = payload["residuals"]
    if not isinstance(raw, list) or not raw or len(raw) > 16:
        raise ValueError("residuals must be a non-empty list of at most 16")
    residuals: list[int] = []
    for index, item in enumerate(raw):
        if not isinstance(item, str) or _SIGNED.fullmatch(item) is None:
            raise ValueError(f"residuals[{index}] must be a canonical signed integer")
        residuals.append(int(item))
    structure = _choice(payload["structure"], _STRUCTURES, "structure")
    repeat = _choice(payload["repeat"], _REPEATS, "repeat")
    clamp = payload["clamp"]
    if type(clamp) is not bool:
        raise ValueError("clamp must be a bool")
    exposure = payload["exposureNs"]
    if not isinstance(exposure, str) or _UINT.fullmatch(exposure) is None:
        raise ValueError("exposureNs must be a canonical positive integer string")
    gain = payload["gain"]
    if not isinstance(gain, str) or _GAIN.fullmatch(gain) is None:
        raise ValueError("gain must be a canonical decimal string")
    capture = _token(payload["captureId"], "captureId")
    return residuals, structure, repeat, clamp, exposure, gain, capture


def _choice(value: object, allowed: tuple[str, ...], label: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{label} is not an allowed value")
    return value


def _token(value: object, label: str) -> str:
    if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
        raise ValueError(f"{label} must be a token")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P042-02 must not yield qualified or allowed")
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
