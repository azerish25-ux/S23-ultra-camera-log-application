"""TC-P062-01 wrong LogC domain coefficients.

Intervention: Use a coefficient set belonging to a different input convention
while retaining the LogC3 label.
Expected: Fail independent black, grey, branch, and inverse tests before
producing an accepted export.
Negative: Using sensor-signal coefficients on exposure-domain values must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P062-01"
INTERVENTION = (
    "Use a coefficient set belonging to a different input convention while retaining the LogC3 label."
)
EXPECTED = (
    "Fail independent black, grey, branch, and inverse tests before producing an accepted export."
)
NEGATIVE = "Using sensor-signal coefficients on exposure-domain values must fail."
REPEAT = "Repeat near the branch cut and with highlights above scene-linear one."

_LABEL = "LogC3"
_SETS = ("exposure-convention", "sensor-signal", "other-convention")
_DOMAINS = ("exposure", "sensor-signal")
_LOCI = ("black", "grey", "branch-cut", "highlight-above-one", "inverse")
_EXPOSURE_CUT = Decimal("0.01")
_SENSOR_CUT = Decimal("0.05")
_PAYLOAD_KEYS = (
    "sampleId",
    "retainedLabel",
    "coefficientSet",
    "valueDomain",
    "locus",
    "scene",
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
_SCENE = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Fail mismatched LogC labels before any accepted export."""
    sample, label, coefficients, domain, locus, scene = _payload(payload)
    reference = "exposure-convention" if domain == "exposure" else "sensor-signal"
    number = Decimal(scene)
    black_ok = _encode(Decimal(0), coefficients) == _encode(Decimal(0), reference)
    grey_ok = _encode(Decimal("0.18"), coefficients) == _encode(Decimal("0.18"), reference)
    branch_ok = coefficients == reference and _pieces_differ(reference)
    inverse_ok = _inverse(_encode(number, coefficients), reference) == number
    preserved = [
        sample,
        f"label:{label}",
        f"coefficients:{coefficients}",
        f"domain:{domain}",
        f"locus:{locus}",
        f"scene:{scene}",
        "black:" + ("pass" if black_ok else "fail"),
        "grey:" + ("pass" if grey_ok else "fail"),
        "branch:" + ("pass" if branch_ok else "fail"),
        "inverse:" + ("pass" if inverse_ok else "fail"),
        "accepted-export:not-produced",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [REPEAT, "host coefficients are not ARRI LogC3 and are not sensor-derived Log"]
    failed = [
        name
        for name, ok in (
            ("black", black_ok),
            ("grey", grey_ok),
            ("branch", branch_ok),
            ("inverse", inverse_ok),
        )
        if not ok
    ]
    sensor_on_exposure = coefficients == "sensor-signal" and domain == "exposure"
    if sensor_on_exposure:
        rejected.append("sensor-signal-on-exposure")
        reasons.append(NEGATIVE)
    if coefficients != reference:
        rejected.append("logc3-label-retained")
        reasons.append(f"retained {label} label does not match {coefficients} on {domain}")
    if failed:
        reasons.append("failed " + ", ".join(failed) + " before an accepted export")
        decision = "rejected"
    else:
        reasons.append("host checks passed; an accepted export was not produced")
        decision = "withheld"
    return _result(decision, reasons, rejected, preserved, questions)


def _encode(scene: Decimal, kind: str) -> Decimal:
    if kind == "exposure-convention":
        if scene < _EXPOSURE_CUT:
            return scene * 5 + Decimal("0.09")
        return scene * Decimal("0.2") + Decimal("0.15")
    if kind == "sensor-signal":
        if scene < _SENSOR_CUT:
            return scene
        return scene * Decimal("0.5") + Decimal("0.5")
    return scene * Decimal("0.1") + Decimal("0.3")


def _inverse(code: Decimal, kind: str) -> Decimal:
    if kind == "exposure-convention":
        if code < Decimal("0.14"):
            return (code - Decimal("0.09")) / 5
        return (code - Decimal("0.15")) / Decimal("0.2")
    if code < _SENSOR_CUT:
        return code
    return (code - Decimal("0.5")) / Decimal("0.5")


def _pieces_differ(kind: str) -> bool:
    if kind == "exposure-convention":
        below = _EXPOSURE_CUT * 5 + Decimal("0.09")
        above = _EXPOSURE_CUT * Decimal("0.2") + Decimal("0.15")
        return below != above
    below = _SENSOR_CUT
    above = _SENSOR_CUT * Decimal("0.5") + Decimal("0.5")
    return below != above


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    sample = payload["sampleId"]
    if not isinstance(sample, str) or _TOKEN.fullmatch(sample) is None:
        raise ValueError("sampleId must be a token")
    label = payload["retainedLabel"]
    if label != _LABEL:
        raise ValueError("retainedLabel must be LogC3")
    coefficients = payload["coefficientSet"]
    if coefficients not in _SETS:
        raise ValueError("coefficientSet is unsupported")
    domain = payload["valueDomain"]
    if domain not in _DOMAINS:
        raise ValueError("valueDomain is unsupported")
    locus = payload["locus"]
    if locus not in _LOCI:
        raise ValueError("locus is unsupported")
    scene = payload["scene"]
    if not isinstance(scene, str) or _SCENE.fullmatch(scene) is None:
        raise ValueError("scene must be a canonical non-negative decimal")
    number = Decimal(scene)
    cut = _EXPOSURE_CUT if domain == "exposure" else _SENSOR_CUT
    if locus == "black" and number != 0:
        raise ValueError("black locus requires scene 0")
    if locus == "grey" and scene != "0.18":
        raise ValueError("grey locus requires scene 0.18")
    if locus == "branch-cut" and abs(number - cut) > Decimal("0.005"):
        raise ValueError("branch-cut locus must be near the domain cut")
    if locus == "highlight-above-one" and number <= 1:
        raise ValueError("highlight locus must be above scene-linear one")
    return sample, label, coefficients, domain, locus, scene


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P062-01 must not yield qualified or allowed")
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
