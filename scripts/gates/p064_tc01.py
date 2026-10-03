"""TC-P064-01 wrong LogC domain coefficients.

Intervention: Use a coefficient set belonging to a different input convention
while retaining the LogC3 label.
Expected: Fail independent black, grey, branch, and inverse tests before
producing an accepted export.
Negative: Using sensor-signal coefficients on exposure-domain values must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P064-01"
INTERVENTION = (
    "Use a coefficient set belonging to a different input convention while retaining the LogC3 label."
)
EXPECTED = (
    "Fail independent black, grey, branch, and inverse tests before producing an accepted export."
)
NEGATIVE = "Using sensor-signal coefficients on exposure-domain values must fail."
REPEAT = "Repeat near the branch cut and with highlights above scene-linear one."

_BRANCH = Decimal("0.18")
_NEAR = Decimal("0.02")
_SETS = ("logc3-exposure", "sensor-signal", "other-convention")
_DOMAINS = ("exposure", "sensor-signal")
_LOCI = ("black", "grey", "branch", "inverse", "branch-cut", "above-one")
_CHECKS = (("blackPass", "black-test"), ("greyPass", "grey-test"), ("branchPass", "branch-test"), ("inversePass", "inverse-test"))
_PAYLOAD_KEYS = (
    "label",
    "coefficientSet",
    "valueDomain",
    "locus",
    "blackPass",
    "greyPass",
    "branchPass",
    "inversePass",
    "sceneLinear",
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
    """Reject a LogC3 label that does not survive independent coefficient tests."""
    label, coefficient_set, domain, locus, flags, scene = _payload(payload)
    preserved = [
        label,
        f"coefficients:{coefficient_set}",
        f"domain:{domain}",
        f"locus:{locus}",
        f"scene-linear:{scene}",
        "checks:" + ",".join(f"{name}={'pass' if flag else 'fail'}" for name, flag in flags),
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [REPEAT]
    rejected: list[str] = []
    matched = coefficient_set == "logc3-exposure" and domain == "exposure"
    if coefficient_set == "sensor-signal" and domain == "exposure":
        rejected.append("sensor-signal-on-exposure-domain")
        reasons.append(NEGATIVE)
        questions.append("sensor-signal coefficients were not applied to exposure-domain values")
    if not matched:
        rejected.append("wrong-coefficient-convention")
        reasons.append("LogC3 label retained over a different input convention")
    for field, claim in _CHECKS:
        if not dict(flags)[field]:
            rejected.append(claim)
    if rejected:
        decision = "rejected"
        reasons.append("accepted export blocked until black, grey, branch, and inverse tests pass")
    else:
        decision = "withheld"
        reasons.append("independent checks passed; this host fixture does not produce an accepted export")
        questions.append("passing host checks is not an accepted physical export")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    label = payload["label"]
    if label != "LogC3":
        raise ValueError("label must retain LogC3")
    coefficient_set = payload["coefficientSet"]
    if coefficient_set not in _SETS:
        raise ValueError("coefficientSet is unsupported")
    domain = payload["valueDomain"]
    if domain not in _DOMAINS:
        raise ValueError("valueDomain is unsupported")
    locus = payload["locus"]
    if locus not in _LOCI:
        raise ValueError("locus is unsupported")
    flags = []
    for field, _claim in _CHECKS:
        flag = payload[field]
        if type(flag) is not bool:
            raise ValueError(field + " must be a bool")
        flags.append((field, flag))
    scene = payload["sceneLinear"]
    if not isinstance(scene, str) or _SIGNED.fullmatch(scene) is None or scene == "-0":
        raise ValueError("sceneLinear must be a canonical signed decimal")
    number = Decimal(scene)
    if locus == "above-one" and number <= 1:
        raise ValueError("above-one locus must be above scene-linear one")
    if locus == "branch-cut" and abs(number - _BRANCH) > _NEAR:
        raise ValueError("branch-cut locus must be near the branch cut")
    return label, coefficient_set, domain, locus, flags, scene


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P064-01 must not yield qualified or allowed")
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
