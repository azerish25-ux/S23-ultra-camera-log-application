"""TC-P049-03 boundary and halo support.

Intervention: Place an impulse or edge at the image boundary, row-buffer
limit, or tile seam.
Expected: Apply the documented border policy without stale reads, missing
support, or discontinuities.
Negative: Reading outside retained rows or ignoring required halos must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P049-03"
INTERVENTION = (
    "Place an impulse or edge at the image boundary, row-buffer limit, or tile seam."
)
EXPECTED = (
    "Apply the documented border policy without stale reads, missing support, or "
    "discontinuities."
)
NEGATIVE = "Reading outside retained rows or ignoring required halos must fail."

_SITES = (
    "corner-tl",
    "corner-tr",
    "corner-bl",
    "corner-br",
    "kernel-boundary",
    "row-buffer",
    "tile-seam",
    "interior",
)
_POLICIES = ("replicate-documented", "constant-zero")
_PAYLOAD_KEYS = ("site", "borderPolicy", "readOutsideRetained", "haloIgnored", "impulse")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "border_policy_applied")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Apply the documented border policy. Outside reads and ignored halos fail."""
    site, policy, outside, halo, impulse = _payload(payload)
    preserved = [
        f"site:{site}",
        f"policy:{policy}",
        f"impulse:{str(impulse).lower()}",
        "support:halo-required",
    ]
    rejected: list[str] = []
    reasons = [EXPECTED]
    if policy != "replicate-documented":
        rejected.append("undocumented-border-policy")
        reasons.append("constant-zero is not the documented border policy")
    if outside:
        rejected.append("outside-retained-rows")
        reasons.append(NEGATIVE)
    if halo:
        rejected.append("ignored-halo")
        if NEGATIVE not in reasons:
            reasons.append(NEGATIVE)
    if rejected:
        decision = "rejected"
        questions = ["unrelated site inventory retained after the border failure"]
    else:
        decision = "border_policy_applied"
        reasons.append("replicate-documented border policy applied")
        questions = ["halo support stayed inside retained rows"]
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    site = payload["site"]
    if site not in _SITES:
        raise ValueError("site is unknown")
    policy = payload["borderPolicy"]
    if policy not in _POLICIES:
        raise ValueError("borderPolicy is unknown")
    outside = payload["readOutsideRetained"]
    halo = payload["haloIgnored"]
    impulse = payload["impulse"]
    if type(outside) is not bool or type(halo) is not bool or type(impulse) is not bool:
        raise ValueError("flags must be bools")
    return site, policy, outside, halo, impulse


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("decision cannot be qualified or allowed")
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
