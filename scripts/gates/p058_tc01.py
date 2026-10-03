"""TC-P058-01 wrong LogC domain coefficients.

Intervention: Use a coefficient set belonging to a different input convention
while retaining the LogC3 label.
Expected: Fail independent black, grey, branch, and inverse tests before
producing an accepted export.
Negative: Using sensor-signal coefficients on exposure-domain values must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal

CASE_ID = "TC-P058-01"
INTERVENTION = (
    "Use a coefficient set belonging to a different input convention while retaining the LogC3 label."
)
EXPECTED = (
    "Fail independent black, grey, branch, and inverse tests before producing an accepted export."
)
NEGATIVE = "Using sensor-signal coefficients on exposure-domain values must fail."

_DOMAINS = ("logc3-encoded", "sensor-signal", "exposure")
_REGIONS = ("black", "grey", "branch", "inverse", "highlight", "mid")
_CHECKS = ("pass", "fail")
_PAYLOAD_KEYS = (
    "label",
    "coefficientDomain",
    "valueDomain",
    "region",
    "sceneLinear",
    "branchCut",
    "blackCheck",
    "greyCheck",
    "branchCheck",
    "inverseCheck",
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
_NEAR = Decimal("0.01")


def evaluate(payload: dict) -> dict:
    """Fail a LogC3 label that is wearing another coefficient convention."""
    label, coeff, values, region, scene, cut, black, grey, branch, inverse = _payload(payload)
    preserved = [
        f"label:{label}",
        f"coefficients:{coeff}",
        f"values:{values}",
        f"region:{region}",
        f"scene-linear:{scene}",
        f"branch-cut:{cut}",
        f"input-black:{black}",
        f"input-grey:{grey}",
        f"input-branch:{branch}",
        f"input-inverse:{inverse}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions: list[str] = []
    scene_value = Decimal(scene)
    cut_value = Decimal(cut)
    if region == "branch" and abs(scene_value - cut_value) <= _NEAR:
        reasons.append(f"sample {scene} is near branch cut {cut}")
    if region == "highlight" and scene_value > 1:
        reasons.append("highlight above scene-linear one")
    mismatch = coeff != "logc3-encoded" or values != coeff
    negative = coeff == "sensor-signal" and values == "exposure"
    if mismatch or negative:
        decision = "rejected"
        rejected.extend(["black", "grey", "branch", "inverse", "wrong-domain-coefficients"])
        reasons.append("black, grey, branch, and inverse tests failed")
        reasons.append("accepted export was not produced")
        questions.append("LogC3 label retained with a different coefficient convention")
        if negative:
            rejected.append("sensor-signal-on-exposure")
            reasons.append(NEGATIVE)
        if region == "highlight" and scene_value > 1:
            rejected.append("highlight-above-one")
    else:
        failed = [
            name
            for name, status in (
                ("black", black),
                ("grey", grey),
                ("branch", branch),
                ("inverse", inverse),
            )
            if status != "pass"
        ]
        if failed:
            decision = "rejected"
            rejected.extend(failed)
            reasons.append("independent checks failed before any export")
        else:
            decision = "checks_recorded"
            reasons.append("independent checks passed; this is not an accepted export")
            questions.append("host record is not an accepted LogC3 export")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    label = payload["label"]
    if label != "LogC3":
        raise ValueError("label must be LogC3")
    coeff = payload["coefficientDomain"]
    values = payload["valueDomain"]
    if coeff not in _DOMAINS or values not in _DOMAINS:
        raise ValueError("domain is unsupported")
    region = payload["region"]
    if region not in _REGIONS:
        raise ValueError("region is unsupported")
    scene = payload["sceneLinear"]
    cut = payload["branchCut"]
    if not isinstance(scene, str) or _DECIMAL.fullmatch(scene) is None:
        raise ValueError("sceneLinear must be a canonical decimal")
    if not isinstance(cut, str) or _DECIMAL.fullmatch(cut) is None or Decimal(cut) <= 0:
        raise ValueError("branchCut must be a positive canonical decimal")
    checks = []
    for name in ("blackCheck", "greyCheck", "branchCheck", "inverseCheck"):
        status = payload[name]
        if status not in _CHECKS:
            raise ValueError(name + " must be pass or fail")
        checks.append(status)
    return (label, coeff, values, region, scene, cut, *checks)


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed", "accepted"}:
        raise ValueError("TC-P058-01 must not yield qualified, allowed, or accepted")
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
