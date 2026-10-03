"""TC-P055-03 boundary and halo support.

Intervention: Place an impulse or edge at the image boundary, row-buffer
limit, or tile seam.
Expected: Apply the documented border policy without stale reads, missing
support, or discontinuities.
Negative: Reading outside retained rows or ignoring required halos must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P055-03"
INTERVENTION = (
    "Place an impulse or edge at the image boundary, row-buffer limit, or tile seam."
)
EXPECTED = (
    "Apply the documented border policy without stale reads, missing support, or discontinuities."
)
NEGATIVE = "Reading outside retained rows or ignoring required halos must fail."
REPEAT = "Repeat at all four corners and each kernel-support boundary."

_SITES = (
    "corner-tl",
    "corner-tr",
    "corner-bl",
    "corner-br",
    "row-buffer",
    "tile-seam",
    "kernel-support",
    "edge",
)
_FEATURES = ("impulse", "edge")
_POLICIES = ("documented-replicate", "documented-reflect")
_PAYLOAD_KEYS = (
    "site",
    "feature",
    "borderPolicy",
    "readOutside",
    "haloIgnored",
    "retainedRows",
    "requiredHalo",
    "sampleValue",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_SIGNED = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")


def evaluate(payload: dict) -> dict:
    """Apply the documented border policy or reject a halo violation."""
    site, feature, policy, outside, ignored, rows, halo, sample = _payload(payload)
    preserved = [
        f"site:{site}",
        f"feature:{feature}",
        f"policy:{policy}",
        f"rows:{rows}",
        f"halo:{halo}",
        f"value:{sample}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [f"repeat coverage includes {REPEAT}"]
    if outside:
        rejected.append("outside-retained-rows")
    if ignored:
        rejected.append("ignored-halo")
    if halo > rows:
        rejected.append("missing-support")
    if rejected:
        decision = "rejected"
        reasons.append(NEGATIVE)
        questions.append(f"{site} value {sample} was retained")
    else:
        decision = "border_applied"
        reasons.append(f"{policy} applied at {site} for {feature}")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    site = payload["site"]
    if site not in _SITES:
        raise ValueError("site is unsupported")
    feature = payload["feature"]
    if feature not in _FEATURES:
        raise ValueError("feature must be impulse or edge")
    policy = payload["borderPolicy"]
    if policy not in _POLICIES:
        raise ValueError("borderPolicy is unsupported")
    outside = payload["readOutside"]
    ignored = payload["haloIgnored"]
    if type(outside) is not bool or type(ignored) is not bool:
        raise ValueError("readOutside and haloIgnored must be bools")
    rows = payload["retainedRows"]
    halo = payload["requiredHalo"]
    if type(rows) is not int or rows < 1:
        raise ValueError("retainedRows must be a positive int")
    if type(halo) is not int or halo < 1:
        raise ValueError("requiredHalo must be a positive int")
    sample = payload["sampleValue"]
    if not isinstance(sample, str) or _SIGNED.fullmatch(sample) is None or sample == "-0":
        raise ValueError("sampleValue must be a canonical signed decimal")
    return site, feature, policy, outside, ignored, rows, halo, sample


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P055-03 must not yield qualified or allowed")
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
