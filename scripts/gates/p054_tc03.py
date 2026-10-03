"""TC-P054-03 boundary and halo support.

Intervention: Place an impulse or edge at the image boundary, row-buffer
limit, or tile seam.
Expected: Apply the documented border policy without stale reads, missing
support, or discontinuities.
Negative: Reading outside retained rows or ignoring required halos must fail.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P054-03"
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
    "interior",
)
_FEATURES = ("impulse", "edge")
_POLICIES = ("replicate", "mirror", "constant-zero")
_PAYLOAD_KEYS = (
    "site",
    "feature",
    "borderPolicy",
    "halo",
    "retainedRows",
    "readOutside",
    "haloIgnored",
    "staleRead",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_UINT = re.compile(r"0|[1-9][0-9]*")
_POSITIVE = re.compile(r"[1-9][0-9]*")


def evaluate(payload: dict) -> dict:
    """Apply the declared border policy. Outside reads and ignored halos fail."""
    site, feature, policy, halo, rows, outside, ignored, stale = _payload(payload)
    preserved = [
        site,
        feature,
        policy,
        f"halo:{halo}",
        f"rows:{rows}",
    ]
    reasons = [EXPECTED, INTERVENTION, f"border policy {policy} at {site}"]
    rejected: list[str] = []
    questions = [f"{feature} at {site} uses halo {halo}"]
    if rows < halo:
        rejected.append("missing-halo-support")
        reasons.append("retained rows do not cover the required halo")
    if outside:
        rejected.append("outside-retained-rows")
        reasons.append(NEGATIVE)
    if ignored:
        rejected.append("halo-ignored")
        reasons.append("required halo was ignored")
    if stale:
        rejected.append("stale-read")
        reasons.append("stale row-buffer read")
    if rejected:
        decision = "rejected"
        questions.append("border failure did not drop the site from the inventory")
    else:
        decision = "border-held"
        reasons.append("documented border policy held without a stale or outside read")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, int, int, bool, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    site = payload["site"]
    if site not in _SITES:
        raise ValueError("site is unsupported")
    feature = payload["feature"]
    if feature not in _FEATURES:
        raise ValueError("feature is unsupported")
    policy = payload["borderPolicy"]
    if policy not in _POLICIES:
        raise ValueError("borderPolicy is unsupported")
    halo = _positive(payload["halo"], "halo")
    rows = _uint(payload["retainedRows"], "retainedRows")
    outside = _bool(payload["readOutside"], "readOutside")
    ignored = _bool(payload["haloIgnored"], "haloIgnored")
    stale = _bool(payload["staleRead"], "staleRead")
    return site, feature, policy, halo, rows, outside, ignored, stale


def _uint(value: object, label: str) -> int:
    if not isinstance(value, str) or _UINT.fullmatch(value) is None:
        raise ValueError(f"{label} must be a canonical non-negative integer string")
    return int(value)


def _positive(value: object, label: str) -> int:
    if not isinstance(value, str) or _POSITIVE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a canonical positive integer string")
    return int(value)


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P054-03 must not yield qualified or allowed")
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
