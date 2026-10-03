"""TC-P063-01 wrong LogC domain coefficients.

Using a coefficient set from another input convention while keeping the
LogC3 label fails black, grey, branch, and inverse checks. Sensor-signal
coefficients on exposure-domain values fail. This host case does not
qualify a physical S23.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P063-01"
INTERVENTION = (
    "Use a coefficient set belonging to a different input convention while retaining the LogC3 label."
)
EXPECTED = (
    "Fail independent black, grey, branch, and inverse tests before producing an accepted export."
)
NEGATIVE = "Using sensor-signal coefficients on exposure-domain values must fail."
REPEAT = "Repeat near the branch cut and with highlights above scene-linear one."

_SETS = ("logc3-exposure", "sensor-signal")
_DOMAINS = ("exposure", "sensor-signal")
_LOCI = ("black", "grey", "branch", "inverse", "branch-cut", "highlight")
_BELONGS = {"exposure": "logc3-exposure", "sensor-signal": "sensor-signal"}
_CHECKS = ("black", "grey", "branch", "inverse")
_PAYLOAD_KEYS = (
    "sampleId",
    "label",
    "coefficientSet",
    "valueDomain",
    "locus",
    "sceneLinear",
    "exportAccepted",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Fail mismatched LogC coefficients before an accepted export."""
    sample, label, coefficient_set, domain, locus, scene, accepted = _payload(payload)
    preserved = [
        sample,
        f"label:{label}",
        f"coefficients:{coefficient_set}",
        f"domain:{domain}",
        f"locus:{locus}",
        f"scene-linear:{scene}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}"]
    rejected: list[str] = []
    mismatched = coefficient_set != _BELONGS[domain]
    sensor_on_exposure = coefficient_set == "sensor-signal" and domain == "exposure"
    if sensor_on_exposure:
        rejected.append("sensor-signal-on-exposure")
        reasons.append(NEGATIVE)
    if mismatched:
        rejected.extend(f"failed-{name}" for name in _CHECKS)
        reasons.append("black, grey, branch, and inverse tests failed before an accepted export")
        if accepted:
            rejected.append("accepted-export-blocked")
            reasons.append("an accepted export was refused after the independent tests failed")
        decision = "rejected"
    else:
        decision = "withheld"
        reasons.append("matching coefficients are not an accepted export and not a qualification")
        questions.append("independent black, grey, branch, and inverse tests were not a device measurement")
        if accepted:
            questions.append("exportAccepted does not certify the host fixture")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    sample = payload["sampleId"]
    if not isinstance(sample, str) or _TOKEN.fullmatch(sample) is None:
        raise ValueError("sampleId must be a token")
    label = payload["label"]
    if label != "LogC3":
        raise ValueError("label must remain LogC3")
    coefficient_set = payload["coefficientSet"]
    if coefficient_set not in _SETS:
        raise ValueError("coefficientSet is unsupported")
    domain = payload["valueDomain"]
    if domain not in _DOMAINS:
        raise ValueError("valueDomain is unsupported")
    locus = payload["locus"]
    if locus not in _LOCI:
        raise ValueError("locus is unsupported")
    scene = payload["sceneLinear"]
    if not isinstance(scene, str) or _DECIMAL.fullmatch(scene) is None:
        raise ValueError("sceneLinear must be a canonical decimal")
    number = Decimal(scene)
    if locus == "highlight" and number <= 1:
        raise ValueError("highlight must be above scene-linear one")
    if locus == "branch-cut" and not (Decimal(0) < number < 1):
        raise ValueError("branch-cut must lie strictly between zero and one")
    accepted = payload["exportAccepted"]
    if type(accepted) is not bool:
        raise ValueError("exportAccepted must be a bool")
    return sample, label, coefficient_set, domain, locus, scene, accepted


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P063-01 must not yield qualified or allowed")
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
