"""TC-P060-01 wrong LogC domain coefficients.

Intervention: Use a coefficient set belonging to a different input convention
while retaining the LogC3 label.
Expected: Fail independent black, grey, branch, and inverse tests before
producing an accepted export.
Negative: Using sensor-signal coefficients on exposure-domain values must fail.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


CASE_ID = "TC-P060-01"
INTERVENTION = (
    "Use a coefficient set belonging to a different input convention while retaining the LogC3 label."
)
EXPECTED = (
    "Fail independent black, grey, branch, and inverse tests before producing an accepted export."
)
NEGATIVE = "Using sensor-signal coefficients on exposure-domain values must fail."
REPEAT = "Repeat near the branch cut and with highlights above scene-linear one."

_EXPOSURE = {
    "cut": Decimal("0.010591"),
    "a": Decimal("5.555556"),
    "b": Decimal("0.052272"),
    "c": Decimal("0.247190"),
    "d": Decimal("0.385537"),
    "e": Decimal("5.367655"),
    "f": Decimal("0.092809"),
}
_SENSOR = {
    "cut": Decimal("0.004201"),
    "a": Decimal("200.0"),
    "b": Decimal("-0.729169"),
    "c": Decimal("0.247190"),
    "d": Decimal("0.385537"),
    "e": Decimal("193.235573"),
    "f": Decimal("-0.662201"),
}
_SETS = {"exposure-ei800": _EXPOSURE, "sensor-ei800": _SENSOR}
_DOMAINS = {"exposure": "exposure-ei800", "sensor-signal": "sensor-ei800"}
_LOCI = {
    "black": "0",
    "grey": "0.18",
    "branch-below": "0.010590",
    "branch-above": "0.010592",
    "highlight": "4",
    "inverse": "0.18",
}
_PROBES = {
    "black": Decimal("0"),
    "grey": Decimal("0.18"),
    "branch-below": Decimal("0.010590"),
    "branch-above": Decimal("0.010592"),
    "highlight": Decimal("4"),
}
_PAYLOAD_KEYS = ("label", "inputDomain", "coefficientSet", "locus", "sceneValue")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_QUANT = Decimal("0.000001")


def _q(value: Decimal) -> str:
    return format(value.quantize(_QUANT, rounding=ROUND_HALF_UP), "f")


def _forward(scene: Decimal, coeffs: dict[str, Decimal]) -> Decimal:
    if scene > coeffs["cut"]:
        return coeffs["c"] * (coeffs["a"] * scene + coeffs["b"]).ln() / Decimal(10).ln() + coeffs["d"]
    return coeffs["e"] * scene + coeffs["f"]


def _inverse(code: Decimal, coeffs: dict[str, Decimal]) -> Decimal:
    if code > coeffs["e"] * coeffs["cut"] + coeffs["f"]:
        return (Decimal(10) ** ((code - coeffs["d"]) / coeffs["c"]) - coeffs["b"]) / coeffs["a"]
    return (code - coeffs["f"]) / coeffs["e"]


def evaluate(payload: dict) -> dict:
    """Reject sensor-signal LogC3 coefficients applied to exposure-domain values."""
    label, domain, coefficient_set, locus, scene_value = _payload(payload)
    applied = _SETS[coefficient_set]
    exposure = _EXPOSURE
    scene = Decimal(scene_value)
    failed: list[str] = []
    exposure_codes = {name: _forward(value, exposure) for name, value in _PROBES.items()}
    applied_codes = {name: _forward(value, applied) for name, value in _PROBES.items()}
    if _q(exposure_codes["black"]) != _q(applied_codes["black"]):
        failed.append("black")
    if _q(exposure_codes["grey"]) != _q(applied_codes["grey"]):
        failed.append("grey")
    if _q(exposure_codes["branch-below"]) != _q(applied_codes["branch-below"]) or _q(
        exposure_codes["branch-above"]
    ) != _q(applied_codes["branch-above"]):
        failed.append("branch")
    if _q(exposure_codes["highlight"]) != _q(applied_codes["highlight"]):
        failed.append("highlight")
    inverse_scene = _PROBES["grey"]
    decoded = _inverse(exposure_codes["grey"], applied)
    if abs(decoded - inverse_scene) > _QUANT:
        failed.append("inverse")
    reasons = [EXPECTED, INTERVENTION, f"locus {locus} scene {scene_value}"]
    rejected: list[str] = []
    questions = [f"repeat coverage includes {REPEAT}", "no accepted LogC export was produced"]
    pairing = _DOMAINS[domain]
    if coefficient_set == "sensor-ei800" and domain == "exposure":
        rejected.append("sensor-signal-coefficients-on-exposure-domain")
        reasons.append(NEGATIVE)
    elif coefficient_set != pairing:
        rejected.append("domain-coefficient-mismatch")
        reasons.append("the LogC3 label does not make a mismatched coefficient set valid")
    if failed and "sensor-signal-coefficients-on-exposure-domain" not in rejected:
        if coefficient_set == "sensor-ei800":
            rejected.append("sensor-signal-coefficients-on-exposure-domain")
            reasons.append(NEGATIVE)
    if failed:
        reasons.append("independent tests failed: " + ",".join(failed))
        decision = "rejected"
    elif rejected:
        decision = "rejected"
    else:
        decision = "withheld"
        reasons.append("exposure-domain checks matched and an accepted export was still withheld")
    preserved = [
        f"label:{label}",
        f"domain:{domain}",
        f"coefficients:{coefficient_set}",
        f"locus:{locus}",
        f"scene:{scene_value}",
        f"failed:{','.join(failed) if failed else 'none'}",
        f"inverse-decoded:{_q(decoded)}",
    ]
    for name in _PROBES:
        preserved.append(f"exposure-{name}:{_q(exposure_codes[name])}")
        preserved.append(f"applied-{name}:{_q(applied_codes[name])}")
    if scene != inverse_scene:
        preserved.append(f"locus-code:{_q(_forward(scene, applied))}")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    label = payload["label"]
    if label != "LogC3":
        raise ValueError("label must be LogC3")
    domain = payload["inputDomain"]
    if domain not in _DOMAINS:
        raise ValueError("inputDomain is unsupported")
    coefficient_set = payload["coefficientSet"]
    if coefficient_set not in _SETS:
        raise ValueError("coefficientSet is unsupported")
    locus = payload["locus"]
    if locus not in _LOCI:
        raise ValueError("locus is unsupported")
    scene_value = payload["sceneValue"]
    if scene_value != _LOCI[locus]:
        raise ValueError("sceneValue does not match the locus")
    return label, domain, coefficient_set, locus, scene_value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P060-01 must not yield qualified or allowed")
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
