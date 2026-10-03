"""TC-P059-01 wrong LogC domain coefficients.

Intervention: Use a coefficient set belonging to a different input convention
while retaining the LogC3 label.
Expected: Fail independent black, grey, branch, and inverse tests before
producing an accepted export.
Negative: Using sensor-signal coefficients on exposure-domain values must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P059-01"
INTERVENTION = (
    "Use a coefficient set belonging to a different input convention while retaining the LogC3 label."
)
EXPECTED = (
    "Fail independent black, grey, branch, and inverse tests before producing an accepted export."
)
NEGATIVE = "Using sensor-signal coefficients on exposure-domain values must fail."

_SETS = ("exposure-logc3", "sensor-signal", "foreign-convention")
_DOMAINS = ("exposure", "sensor-signal")
_REPEATS = ("none", "branch-cut", "highlights-above-one")
_PAYLOAD_KEYS = (
    "label",
    "coefficientSet",
    "valueDomain",
    "repeat",
    "sceneLinear",
    "blackResidual",
    "greyResidual",
    "branchResidual",
    "inverseResidual",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "withheld")
_FORBIDDEN = {"qualified", "allowed"}
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
_TESTS = ("black", "grey", "branch", "inverse")


def evaluate(payload: dict) -> dict:
    """Fail LogC checks when the coefficient convention does not match the domain."""
    label, coefficient, domain, repeat, scene, residuals = _payload(payload)
    preserved = [
        "label:" + label,
        "coefficients:" + coefficient,
        "domain:" + domain,
        "repeat:" + repeat,
        "scene-linear:" + scene,
    ]
    preserved.extend(f"{name}:{residuals[name]}" for name in _TESTS)
    matched = (domain == "exposure" and coefficient == "exposure-logc3") or (
        domain == "sensor-signal" and coefficient == "sensor-signal"
    )
    sensor_on_exposure = coefficient == "sensor-signal" and domain == "exposure"
    rejected: list[str] = []
    if sensor_on_exposure:
        rejected.append("sensor-signal-on-exposure")
    if not matched:
        rejected.append("wrong-convention")
    for name in _TESTS:
        if residuals[name] != "0" or not matched:
            rejected.append(name)
    reasons = [EXPECTED, INTERVENTION]
    if sensor_on_exposure:
        reasons.append(NEGATIVE)
    if rejected:
        reasons.append("accepted export was not produced")
        reasons.append("black, grey, branch, and inverse checks were not passed through")
        return _result("rejected", reasons, rejected, preserved, ["accepted export was not produced"])
    reasons.append("matching coefficients on this host fixture still do not produce an accepted export")
    return _result(
        "withheld",
        reasons,
        [],
        preserved,
        ["host fixture does not certify a LogC3 coefficient set"],
    )


def _payload(payload: object) -> tuple[str, str, str, str, str, dict[str, str]]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    if payload["label"] != "LogC3":
        raise ValueError("label must remain LogC3")
    coefficient = payload["coefficientSet"]
    if coefficient not in _SETS:
        raise ValueError("coefficientSet is unsupported")
    domain = payload["valueDomain"]
    if domain not in _DOMAINS:
        raise ValueError("valueDomain is unsupported")
    repeat = payload["repeat"]
    if repeat not in _REPEATS:
        raise ValueError("repeat is unsupported")
    scene = payload["sceneLinear"]
    if not isinstance(scene, str) or _DECIMAL.fullmatch(scene) is None:
        raise ValueError("sceneLinear must be a canonical decimal string")
    residuals: dict[str, str] = {}
    for name in _TESTS:
        value = payload[name + "Residual"]
        if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
            raise ValueError(name + "Residual must be a canonical decimal string")
        residuals[name] = value
    return "LogC3", coefficient, domain, repeat, scene, residuals


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P059-01 must not yield qualified or allowed")
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
