"""TC-P057-01 wrong LogC domain coefficients.

Intervention: Use a coefficient set belonging to a different input convention
while retaining the LogC3 label.
Expected: Fail independent black, grey, branch, and inverse tests before
producing an accepted export.
Negative: Using sensor-signal coefficients on exposure-domain values must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal, localcontext


CASE_ID = "TC-P057-01"
INTERVENTION = (
    "Use a coefficient set belonging to a different input convention while retaining "
    "the LogC3 label."
)
EXPECTED = (
    "Fail independent black, grey, branch, and inverse tests before producing an "
    "accepted export."
)
NEGATIVE = "Using sensor-signal coefficients on exposure-domain values must fail."

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
    "a": Decimal("200"),
    "b": Decimal("-0.729169"),
    "c": Decimal("0.247190"),
    "d": Decimal("0.385537"),
    "e": Decimal("193.235573"),
    "f": Decimal("-0.662201"),
}
_TABLES = {"exposure-domain": _EXPOSURE, "sensor-signal": _SENSOR}
_PROBES = ("black", "grey", "branch", "inverse", "highlight")
_PAYLOAD_KEYS = ("convention", "label", "probe", "exposure")
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
_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")
_ROUND = Decimal("0.000000000001")
_GAP = Decimal("0.0000003")


def evaluate(payload: dict) -> dict:
    """Reject sensor-signal coefficients labeled as exposure-domain LogC3."""
    convention, label, probe, exposure = _payload(payload)
    reference = _encode(exposure, _EXPOSURE)
    preserved = [
        f"convention:{convention}",
        f"label:{label}",
        f"probe:{probe}",
        f"exposure:{exposure}",
        f"exposure-domain:{reference}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = ["host coefficient check is not an accepted camera export"]
    if label != "LogC3":
        reasons.append("a non-LogC3 label is not an accepted export")
        return _result("rejected", reasons, ["label-not-logc3"], preserved, questions)
    failed = _failures(convention)
    if convention != "exposure-domain":
        reasons.append(NEGATIVE)
        reasons.append(f"probe {probe} was repeated against the exposure-domain oracle")
        questions.append("sensor-signal input is not the exposure-domain convention")
        return _result(
            "rejected",
            reasons,
            ["sensor-signal-on-exposure-domain", *failed],
            preserved,
            questions,
        )
    reasons.append("exposure-domain checks passed and no accepted export was produced")
    questions.append(f"probe {probe} did not authorize an export")
    return _result("withheld", reasons, [], preserved, questions)


def _encode(exposure: Decimal, table: dict[str, Decimal]) -> str:
    if exposure > table["cut"]:
        argument = table["a"] * exposure + table["b"]
        if argument <= 0:
            raise ValueError("log argument must stay positive")
        with localcontext() as ctx:
            ctx.prec = 50
            encoded = table["c"] * argument.ln() / Decimal(10).ln() + table["d"]
    else:
        encoded = table["e"] * exposure + table["f"]
    return format(encoded, "f")


def _failures(convention: str) -> list[str]:
    table = _TABLES[convention]
    failed: list[str] = []
    if Decimal(_encode(Decimal(0), table)) != _EXPOSURE["f"]:
        failed.append("black")
    grey_gap = abs(Decimal(_encode(Decimal("0.18"), table)) - Decimal(_encode(Decimal("0.18"), _EXPOSURE)))
    if grey_gap > Decimal("0.000000000000001"):
        failed.append("grey")
    branch_gap = abs(
        Decimal(_encode(_EXPOSURE["cut"], table)) - Decimal(_encode(_EXPOSURE["cut"], _EXPOSURE))
    )
    if branch_gap > _GAP:
        failed.append("branch")
    inverse_failed = False
    for raw in (Decimal("-0.01"), Decimal("0.18"), Decimal("16")):
        encoded = Decimal(_encode(raw, table))
        back = _decode(encoded, _EXPOSURE)
        if abs(back - raw) > _ROUND:
            inverse_failed = True
    if inverse_failed:
        failed.append("inverse")
    return failed


def _decode(encoded: Decimal, table: dict[str, Decimal]) -> Decimal:
    join = table["e"] * table["cut"] + table["f"]
    with localcontext() as ctx:
        ctx.prec = 50
        if encoded > join:
            return (Decimal(10) ** ((encoded - table["d"]) / table["c"]) - table["b"]) / table["a"]
        return (encoded - table["f"]) / table["e"]


def _payload(payload: object) -> tuple[str, str, str, Decimal]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    convention = payload["convention"]
    if convention not in _TABLES:
        raise ValueError("convention is unknown")
    label = payload["label"]
    if label not in {"LogC3", "other"}:
        raise ValueError("label is unknown")
    probe = payload["probe"]
    if probe not in _PROBES:
        raise ValueError("probe is unknown")
    exposure = payload["exposure"]
    if not isinstance(exposure, str) or _DECIMAL.fullmatch(exposure) is None:
        raise ValueError("exposure must be a canonical decimal string")
    number = Decimal(exposure)
    if number < Decimal("-1") or number > Decimal("64"):
        raise ValueError("exposure is outside the host domain")
    return convention, label, probe, number


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("decision cannot be qualified or allowed")
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
