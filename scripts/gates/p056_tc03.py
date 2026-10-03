"""TC-P056-03 boundary and halo support.

Intervention: Place an impulse or edge at the image boundary, row-buffer limit,
or tile seam.
Expected: Apply the documented border policy without stale reads, missing
support, or discontinuities.
Negative: Reading outside retained rows or ignoring required halos must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P056-03"
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
    "kernel-boundary",
    "tile-seam",
    "row-buffer",
)
_POLICIES = ("replicate", "mirror", "constant")
_PAYLOAD_KEYS = (
    "site",
    "borderPolicy",
    "readOutside",
    "haloIgnored",
    "staleRead",
    "discontinuity",
    "support",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")


def evaluate(payload: dict) -> dict:
    """Apply the border policy. Outside reads, ignored halos, and stale rows fail."""
    site, policy, outside, halo, stale, discontinuity, support = _payload(payload)
    preserved = [
        f"site:{site}",
        f"policy:{policy}",
        f"support:{support}",
    ]
    rejected: list[str] = []
    questions: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"border policy {policy} at {site}"]
    if support < 1:
        rejected.append("missing-support")
        reasons.append("kernel support is missing")
    if outside:
        rejected.append("outside-retained-rows")
        reasons.append(NEGATIVE)
    if halo:
        rejected.append("ignored-halo")
        reasons.append("required halo was ignored")
    if stale:
        rejected.append("stale-read")
        reasons.append("row buffer read was stale")
    if discontinuity:
        rejected.append("discontinuity")
        reasons.append("border policy introduced a discontinuity")
    if rejected:
        decision = "rejected"
        questions.append(f"{site} failed the border policy")
    else:
        decision = "border-applied"
        reasons.append("retained rows and halo support were honored")
        questions.append(f"{site} used {policy}")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, bool, bool, bool, bool, int]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    site = payload["site"]
    if site not in _SITES:
        raise ValueError("site is unsupported")
    policy = payload["borderPolicy"]
    if policy not in _POLICIES:
        raise ValueError("borderPolicy is unsupported")
    flags = []
    for name in ("readOutside", "haloIgnored", "staleRead", "discontinuity"):
        value = payload[name]
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
        flags.append(value)
    support = payload["support"]
    if type(support) is not int or support < 0:
        raise ValueError("support must be a non-negative int")
    if not _TOKEN.fullmatch(site):
        raise ValueError("site must be a token")
    return (site, policy, flags[0], flags[1], flags[2], flags[3], support)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P056-03 must not yield qualified or allowed")
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
