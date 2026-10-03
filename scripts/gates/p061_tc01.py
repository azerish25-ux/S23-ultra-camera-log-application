"""TC-P061-01 wrong LogC domain coefficients.

Intervention: Use a coefficient set belonging to a different input convention
while retaining the LogC3 label.
Expected: Fail independent black, grey, branch, and inverse tests before
producing an accepted export.
Negative: Using sensor-signal coefficients on exposure-domain values must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P061-01"
INTERVENTION = (
    "Use a coefficient set belonging to a different input convention while retaining the LogC3 label."
)
EXPECTED = (
    "Fail independent black, grey, branch, and inverse tests before producing an accepted export."
)
NEGATIVE = "Using sensor-signal coefficients on exposure-domain values must fail."
REPEAT = "Repeat near the branch cut and with highlights above scene-linear one."

_SETS = ("logc3-exposure", "logc3-sensor", "other-convention")
_DOMAINS = ("exposure", "sensor-signal")
_LOCI = ("black", "grey", "branch", "inverse", "branch-cut", "highlight-above-one")
_SET_DOMAIN = {
    "logc3-exposure": "exposure",
    "logc3-sensor": "sensor-signal",
    "other-convention": "other",
}
_CHECKS = ("black", "grey", "branch", "inverse")
_PAYLOAD_KEYS = (
    "label",
    "coefficientSet",
    "valueDomain",
    "locus",
    "sceneLinear",
    "acceptedExportRequested",
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
_TOLERANCE = Decimal("1e-9")
_POINTS = (
    ("black", Decimal(0)),
    ("grey", Decimal("0.18")),
    ("branch", Decimal("0.01")),
)


def _log10(value: Decimal) -> Decimal:
    return value.ln() / Decimal(10).ln()


def encode(domain: str, scene: Decimal) -> Decimal:
    """Fixture curves. These are not an ARRI measurement and not a camera profile."""
    if domain == "exposure":
        if scene <= Decimal("0.01"):
            return scene * Decimal(20)
        return Decimal("0.3") + Decimal("0.25") * _log10(scene / Decimal("0.01"))
    if domain == "sensor-signal":
        return Decimal("0.09") + Decimal("0.2") * _log10(Decimal(1) + scene * Decimal(8))
    if domain == "other":
        return scene + Decimal(1)
    raise ValueError("unsupported coefficient domain")


def decode(domain: str, encoded: Decimal) -> Decimal:
    """Inverse of encode. A domain mismatch does not recover the scene value."""
    if domain == "exposure":
        if encoded <= Decimal("0.2"):
            return encoded / Decimal(20)
        return Decimal("0.01") * (Decimal(10) ** ((encoded - Decimal("0.3")) / Decimal("0.25")))
    if domain == "sensor-signal":
        expo = (encoded - Decimal("0.09")) / Decimal("0.2")
        return (Decimal(10) ** expo - Decimal(1)) / Decimal(8)
    if domain == "other":
        return encoded - Decimal(1)
    raise ValueError("unsupported coefficient domain")


def failed_checks(coefficient_set: str, value_domain: str) -> list[str]:
    """Black, grey, branch, and inverse, each compared across domains."""
    coeff = _SET_DOMAIN[coefficient_set]
    failed: list[str] = []
    for name, scene in _POINTS:
        if abs(encode(coeff, scene) - encode(value_domain, scene)) > _TOLERANCE:
            failed.append(name)
    grey = Decimal("0.18")
    recovered = decode(coeff, encode(value_domain, grey))
    if abs(recovered - grey) > _TOLERANCE:
        failed.append("inverse")
    return failed


def evaluate(payload: dict) -> dict:
    """Reject a LogC3 label whose coefficients belong to another convention."""
    label, coefficient_set, value_domain, locus, scene, export_requested = _payload(payload)
    failed = failed_checks(coefficient_set, value_domain)
    preserved = [
        f"label:{label}",
        f"coefficients:{coefficient_set}",
        f"domain:{value_domain}",
        f"locus:{locus}",
        f"scene:{scene}",
        "checks:" + ",".join(
            f"{name}:{'fail' if name in failed else 'pass'}" for name in _CHECKS
        ),
    ]
    reasons = [EXPECTED, INTERVENTION, f"repeat coverage includes {REPEAT}"]
    rejected: list[str] = []
    questions = ["host fixture coefficients are not a measured LogC3 profile"]
    if coefficient_set == "logc3-sensor" and value_domain == "exposure":
        rejected.append("sensor-signal-on-exposure")
        reasons.append(NEGATIVE)
    elif coefficient_set == "logc3-exposure" and value_domain == "sensor-signal":
        rejected.append("exposure-coefficients-on-sensor")
        reasons.append("exposure-domain coefficients do not describe sensor-signal values")
    elif coefficient_set == "other-convention":
        rejected.append("other-convention")
        reasons.append("the coefficient set is a different input convention")
    rejected.extend(failed)
    if failed:
        rejected.append("accepted-export-blocked")
        reasons.append("black, grey, branch, and inverse failed; accepted export was not produced")
        decision = "rejected"
        if export_requested:
            questions.append("requested export stayed blocked")
    else:
        decision = "withheld"
        reasons.append("domain checks passed and this host fixture still does not accept an export")
        questions.append("accepted export is not produced by this host fixture")
        if export_requested:
            questions.append("requested export was not accepted")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    label = payload["label"]
    if label != "LogC3":
        raise ValueError("label must remain LogC3")
    coefficient_set = payload["coefficientSet"]
    if coefficient_set not in _SETS:
        raise ValueError("coefficientSet is unsupported")
    value_domain = payload["valueDomain"]
    if value_domain not in _DOMAINS:
        raise ValueError("valueDomain is unsupported")
    locus = payload["locus"]
    if locus not in _LOCI:
        raise ValueError("locus is unsupported")
    scene_text = payload["sceneLinear"]
    if not isinstance(scene_text, str) or _SIGNED.fullmatch(scene_text) is None or scene_text == "-0":
        raise ValueError("sceneLinear must be a canonical decimal")
    if scene_text.startswith("-"):
        raise ValueError("sceneLinear must not be negative")
    scene = Decimal(scene_text)
    if not _locus_matches(locus, scene):
        raise ValueError("sceneLinear does not match locus")
    export_requested = payload["acceptedExportRequested"]
    if type(export_requested) is not bool:
        raise ValueError("acceptedExportRequested must be a bool")
    return label, coefficient_set, value_domain, locus, scene_text, export_requested


def _locus_matches(locus: str, scene: Decimal) -> bool:
    if locus == "black":
        return scene == 0
    if locus in {"grey", "inverse"}:
        return scene == Decimal("0.18")
    if locus == "branch":
        return scene == Decimal("0.01")
    if locus == "branch-cut":
        return Decimal("0.005") <= scene <= Decimal("0.02")
    if locus == "highlight-above-one":
        return scene > 1
    return False


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P061-01 must not yield qualified or allowed")
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
