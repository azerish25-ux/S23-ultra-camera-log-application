"""TC-P052-03 boundary and halo support.

Intervention: Place an impulse or edge at the image boundary, row-buffer
limit, or tile seam.
Expected: Apply the documented border policy without stale reads, missing
support, or discontinuities.
Negative: Reading outside retained rows or ignoring required halos must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P052-03"
INTERVENTION = (
    "Place an impulse or edge at the image boundary, row-buffer limit, or tile seam."
)
EXPECTED = (
    "Apply the documented border policy without stale reads, missing support, or discontinuities."
)
NEGATIVE = "Reading outside retained rows or ignoring required halos must fail."

_SITES = (
    "corner-tl",
    "corner-tr",
    "corner-bl",
    "corner-br",
    "kernel-left",
    "kernel-right",
    "kernel-top",
    "kernel-bottom",
    "row-buffer",
    "tile-seam",
)
_POLICY = "omit-missing"
_PAYLOAD_KEYS = (
    "site",
    "borderPolicy",
    "impulse",
    "readOutsideRows",
    "haloIgnored",
    "staleRead",
    "discontinuity",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Hold the omit-missing border. Outside reads and ignored halos fail."""
    site, policy, impulse, outside, halo, stale, gap = _payload(payload)
    preserved = [
        f"site:{site}",
        f"policy:{policy}",
        f"impulse:{impulse}",
        f"read-outside:{str(outside).lower()}",
        f"halo-ignored:{str(halo).lower()}",
        f"stale-read:{str(stale).lower()}",
        f"discontinuity:{str(gap).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = ["impulse value stays in the inventory"]
    if outside or halo:
        decision = "rejected"
        if outside:
            rejected.append("outside-rows")
        if halo:
            rejected.append("ignored-halo")
        reasons.append(NEGATIVE)
        questions.append("outside read or ignored halo rejected")
    elif stale or gap:
        decision = "rejected"
        if stale:
            rejected.append("stale-read")
        if gap:
            rejected.append("discontinuity")
        reasons.append("border policy was not free of stale reads and discontinuities")
    else:
        decision = "border-held"
        reasons.append("omit-missing border kept support inside retained rows")
        questions.append("border-held is not a physical kernel qualification")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, bool, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    site = payload["site"]
    if site not in _SITES:
        raise ValueError("site is unsupported")
    policy = payload["borderPolicy"]
    if policy != _POLICY:
        raise ValueError("borderPolicy must be omit-missing")
    impulse = payload["impulse"]
    if not isinstance(impulse, str) or _DECIMAL.fullmatch(impulse) is None:
        raise ValueError("impulse must be a canonical decimal")
    if Decimal(impulse) < 0:
        raise ValueError("impulse must be non-negative")
    flags = []
    for name in ("readOutsideRows", "haloIgnored", "staleRead", "discontinuity"):
        value = payload[name]
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
        flags.append(value)
    return (site, policy, impulse, *flags)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P052-03 must not yield qualified or allowed")
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
