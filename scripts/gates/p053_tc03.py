"""TC-P053-03 boundary and halo support.

Intervention: Place an impulse or edge at the image boundary, row-buffer limit,
or tile seam.
Expected: Apply the documented border policy without stale reads, missing
support, or discontinuities.
Negative: Reading outside retained rows or ignoring required halos must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P053-03"
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
    "boundary",
)
_POLICIES = ("replicate", "constant-zero", "mirror")
_PAYLOAD_KEYS = (
    "site",
    "borderPolicy",
    "readOutside",
    "staleRead",
    "discontinuity",
    "haloSupport",
    "requiredHalo",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "border_applied")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Apply a declared border policy. Fail stale reads and missing halos."""
    site, policy, outside, stale, discontinuity, halo, required = _payload(payload)
    preserved = [
        f"site:{site}",
        f"policy:{policy}",
        f"halo:{halo}",
        f"required-halo:{required}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if outside:
        rejected.append("outside-retained-rows")
    if stale:
        rejected.append("stale-read")
    if halo < required:
        rejected.append("missing-halo")
    if discontinuity:
        rejected.append("discontinuity")
    if rejected:
        if outside or halo < required:
            reasons.append(NEGATIVE)
        else:
            reasons.append("border support failed")
        return _result("rejected", reasons, rejected, preserved, list(rejected))
    reasons.append(f"{policy} border policy applied at {site}")
    return _result(
        "border_applied",
        reasons,
        [],
        preserved,
        ["border policy is not a physical sensor readout"],
    )


def _payload(payload: object) -> tuple[str, str, bool, bool, bool, int, int]:
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
    flags = (payload["readOutside"], payload["staleRead"], payload["discontinuity"])
    if any(type(item) is not bool for item in flags):
        raise ValueError("read flags must be bools")
    halo = payload["haloSupport"]
    required = payload["requiredHalo"]
    if type(halo) is not int or type(required) is not int or halo < 0 or required < 0:
        raise ValueError("halo sizes must be non-negative ints")
    return site, policy, flags[0], flags[1], flags[2], halo, required


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("border decision cannot be qualified or allowed")
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
