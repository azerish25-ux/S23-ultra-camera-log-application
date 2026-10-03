#!/usr/bin/env python3
"""P057 LogC3 EI800 exposure-domain reference arithmetic.

Forward and inverse use the published EI800 exposure-domain coefficients from
ARRI, "ALEXA Log C Curve: Usage in VFX", 2017-03 (SUP 3.x LogC3), including
the signed linear branch at and below the cut. The encoding EI is not the
phone ISO. Valid negatives and highlights are not clipped.

The deliberate mutant — the normalised sensor-signal coefficient table fed
exposure-domain input — fails the black, middle-grey, branch, and inverse
oracles. This module does not probe a device, does not qualify a physical
S23, and does not execute TC-P057-01 through TC-P057-08.
"""

from __future__ import annotations

import math
import re
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from typing import Any, Callable


PHASE = "P057"
CASE_ID = "P057"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-logc3-ei800-reference-fixture"
SOURCE = "ARRI, ALEXA Log C Curve: Usage in VFX, 2017-03"
METHOD = (
    "Use the published EI800 exposure-domain coefficients and an explicit signed "
    "linear branch. Separate the encoding EI convention from the phone ISO. Test "
    "black, middle grey, branch continuity within coefficient rounding, monotonicity, "
    "and inverse round trips."
)
FIXTURE = (
    "Signed exposures around zero, values bracketing the branch cut, middle grey, "
    "and highlights well above scene-linear one."
)
ORACLE = (
    "The independent numerical reference agrees within declared arithmetic tolerances "
    "without clipping valid intermediate values."
)
MUTANT = "Use the sensor-signal coefficient table for exposure-domain input."
HOST_LIMIT = "this host record does not qualify a physical S23"
ENCODING_EI = "800"
EI200_EXPOSURE_BLACK = "0.092782"
CONVENTION_EXPOSURE = "exposure-domain"
CONVENTION_SENSOR = "sensor-signal"
CONVENTIONS = (CONVENTION_EXPOSURE, CONVENTION_SENSOR)
SELECTOR = "encoding-ei"
MID_GREY = Decimal("0.18")
DOMAIN_MIN = Decimal("-1")
DOMAIN_MAX = Decimal("64")
QUANTUM = Decimal("1e-15")
ANCHOR_BLACK = "black"
ANCHOR_GREY = "middle-grey"
ANCHOR_BRANCH = "branch"
ANCHOR_INVERSE = "inverse"

# Published six-decimal SUP 3.x EI800 tables. Exposure is scene-linear with
# 0.18 at middle grey. Sensor-signal is a different input convention.
EXPOSURE_COEFFICIENTS = {
    "cut": "0.010591",
    "a": "5.555556",
    "b": "0.052272",
    "c": "0.247190",
    "d": "0.385537",
    "e": "5.367655",
    "f": "0.092809",
}
SENSOR_COEFFICIENTS = {
    "cut": "0.004201",
    "a": "200",
    "b": "-0.729169",
    "c": "0.247190",
    "d": "0.385537",
    "e": "193.235573",
    "f": "-0.662201",
}
TOLERANCE = {
    "roundTrip": "0.000000000001",
    "branchGap": "0.0000003",
    "midGrey": "0.000000000000001",
    "oracle": "0.000000000001",
}
COEFF_KEYS = ("cut", "a", "b", "c", "d", "e", "f")
ROLES = (
    "signed-negative",
    "black",
    "signed-positive",
    "branch-cut",
    "branch-above",
    "middle-grey",
    "highlight",
)
HEX40 = re.compile(r"^[0-9a-f]{40}$")
IDENT = re.compile(r"[a-z0-9-]{1,32}")
DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")
UINT = re.compile(r"0|[1-9][0-9]*")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "source",
    "encodingEi",
    "phoneIso",
    "convention",
    "coefficientSelector",
    "tolerance",
    "coefficients",
    "samples",
}
SAMPLE_KEYS = {"id", "exposure", "role"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "reference_agreed"}
_FORBIDDEN = {"qualified", "allowed"}
_TABLES = {
    CONVENTION_EXPOSURE: EXPOSURE_COEFFICIENTS,
    CONVENTION_SENSOR: SENSOR_COEFFICIENTS,
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def canonical(value: Decimal) -> str:
    """Shortest half-even decimal at 15 places. Not a clipped code."""
    require(isinstance(value, Decimal) and value.is_finite(), "value must be a finite Decimal")
    if value == 0:
        return "0"
    quantized = value.quantize(QUANTUM, rounding=ROUND_HALF_EVEN)
    text = format(quantized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def _decimal_text(value: object, label: str) -> Decimal:
    require(isinstance(value, str) and DECIMAL.fullmatch(value) is not None,
            label + " must be a canonical decimal string")
    return Decimal(value)


def _coeffs(table: dict[str, str]) -> dict[str, Decimal]:
    return {key: Decimal(table[key]) for key in COEFF_KEYS}


def _encode_decimal(exposure: Decimal, table: dict[str, str]) -> Decimal:
    """Signed linear branch at and below cut. Log argument is never clamped."""
    coeff = _coeffs(table)
    require(DOMAIN_MIN <= exposure <= DOMAIN_MAX, "exposure is outside the host domain")
    if exposure > coeff["cut"]:
        argument = coeff["a"] * exposure + coeff["b"]
        require(argument > 0, "log argument must stay positive without clipping")
        with localcontext() as ctx:
            ctx.prec = 50
            ctx.rounding = ROUND_HALF_EVEN
            return coeff["c"] * argument.ln() / Decimal(10).ln() + coeff["d"]
    return coeff["e"] * exposure + coeff["f"]


def _decode_decimal(encoded: Decimal, table: dict[str, str]) -> Decimal:
    coeff = _coeffs(table)
    join = coeff["e"] * coeff["cut"] + coeff["f"]
    with localcontext() as ctx:
        ctx.prec = 50
        ctx.rounding = ROUND_HALF_EVEN
        if encoded > join:
            return (Decimal(10) ** ((encoded - coeff["d"]) / coeff["c"]) - coeff["b"]) / coeff["a"]
        return (encoded - coeff["f"]) / coeff["e"]


def _exposure(value: str) -> Decimal:
    number = _decimal_text(value, "exposure")
    require(DOMAIN_MIN <= number <= DOMAIN_MAX, "exposure is outside the host domain")
    return number


def encode(exposure: str) -> str:
    """Encode an exposure-domain value with the EI800 exposure table."""
    return canonical(_encode_decimal(_exposure(exposure), EXPOSURE_COEFFICIENTS))


def decode(encoded: str) -> str:
    """Inverse of encode using the EI800 exposure table. Not a clip."""
    return canonical(_decode_decimal(_decimal_text(encoded, "encoded"), EXPOSURE_COEFFICIENTS))


def encode_with(exposure: str, convention: str) -> str:
    """Encode with an explicit convention. Sensor-signal is the mutant table."""
    require(convention in CONVENTIONS, "convention is unknown")
    return canonical(_encode_decimal(_exposure(exposure), _TABLES[convention]))


def decode_with(encoded: str, convention: str) -> str:
    require(convention in CONVENTIONS, "convention is unknown")
    return canonical(_decode_decimal(_decimal_text(encoded, "encoded"), _TABLES[convention]))


def independent_encode(exposure: str) -> str:
    """Float math.log10 reference. It does not call encode()."""
    number = _exposure(exposure)
    coeff = _coeffs(EXPOSURE_COEFFICIENTS)
    x = float(number)
    cut = float(coeff["cut"])
    if x > cut:
        argument = float(coeff["a"]) * x + float(coeff["b"])
        require(argument > 0, "independent log argument must stay positive")
        encoded = float(coeff["c"]) * math.log10(argument) + float(coeff["d"])
    else:
        encoded = float(coeff["e"]) * x + float(coeff["f"])
    require(math.isfinite(encoded), "independent reference was non-finite")
    return canonical(Decimal(encoded))


def branch_discontinuity() -> str:
    """Absolute gap between the two exposure branches evaluated at the cut."""
    coeff = _coeffs(EXPOSURE_COEFFICIENTS)
    cut = coeff["cut"]
    linear = coeff["e"] * cut + coeff["f"]
    argument = coeff["a"] * cut + coeff["b"]
    require(argument > 0, "branch log argument must stay positive")
    with localcontext() as ctx:
        ctx.prec = 50
        log_value = coeff["c"] * argument.ln() / Decimal(10).ln() + coeff["d"]
    return canonical(abs(linear - log_value))


def exposure_oracle_failures(convention: str) -> list[str]:
    """Checks that fail when this convention is applied to exposure-domain input."""
    require(convention in CONVENTIONS, "convention is unknown")
    table = _TABLES[convention]
    exposure = _coeffs(EXPOSURE_COEFFICIENTS)
    tol_round = Decimal(TOLERANCE["roundTrip"])
    tol_gap = Decimal(TOLERANCE["branchGap"])
    tol_grey = Decimal(TOLERANCE["midGrey"])
    failed: list[str] = []
    if _encode_decimal(Decimal(0), table) != exposure["f"]:
        failed.append(ANCHOR_BLACK)
    grey_delta = abs(
        _encode_decimal(MID_GREY, table) - _encode_decimal(MID_GREY, EXPOSURE_COEFFICIENTS)
    )
    if grey_delta > tol_grey:
        failed.append(ANCHOR_GREY)
    branch_delta = abs(
        _encode_decimal(exposure["cut"], table)
        - _encode_decimal(exposure["cut"], EXPOSURE_COEFFICIENTS)
    )
    if branch_delta > tol_gap:
        failed.append(ANCHOR_BRANCH)
    inverse_failed = False
    for raw in (Decimal("-0.01"), MID_GREY, Decimal("16")):
        encoded = _encode_decimal(raw, table)
        back = _decode_decimal(encoded, EXPOSURE_COEFFICIENTS)
        if abs(back - raw) > tol_round:
            inverse_failed = True
    if inverse_failed:
        failed.append(ANCHOR_INVERSE)
    return failed


def _role_holds(role: str, exposure: Decimal, cut: Decimal) -> bool:
    checks: dict[str, Callable[[Decimal], bool]] = {
        "signed-negative": lambda value: value < 0,
        "black": lambda value: value == 0,
        "signed-positive": lambda value: 0 < value < cut,
        "branch-cut": lambda value: value == cut,
        "branch-above": lambda value: cut < value < MID_GREY,
        "middle-grey": lambda value: value == MID_GREY,
        "highlight": lambda value: value > 1,
    }
    return checks[role](exposure)


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P057 exposure-domain fixture."""
    exact_keys(document, DOCUMENT_KEYS, "logc3 document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P057")
    require(document["mapId"] == MAP_ID, "mapId must be s23-logc3-ei800-reference-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "logc3 document needs the P057 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    require(document["source"] == SOURCE, "source attribution drifted")
    require(document["encodingEi"] == ENCODING_EI, "encodingEi must be the LogC3 EI800 convention")
    phone = document["phoneIso"]
    require(isinstance(phone, str) and UINT.fullmatch(phone) is not None, "phoneIso must be a canonical integer string")
    require(phone != document["encodingEi"], "phone ISO must stay separate from the encoding EI")
    require(document["convention"] == CONVENTION_EXPOSURE, "fixture convention must be exposure-domain")
    require(document["coefficientSelector"] == SELECTOR, "coefficients must be selected by encoding EI")
    tolerance = exact_keys(document["tolerance"], set(TOLERANCE), "tolerance")
    for key, expected in TOLERANCE.items():
        require(tolerance[key] == expected, "tolerance " + key + " drifted")
    coefficients = exact_keys(document["coefficients"], set(CONVENTIONS), "coefficients")
    for convention, expected in _TABLES.items():
        table = exact_keys(coefficients[convention], set(COEFF_KEYS), convention + " coefficients")
        for key in COEFF_KEYS:
            require(table[key] == expected[key], convention + " " + key + " drifted")
    samples = document["samples"]
    require(isinstance(samples, list) and samples, "samples must be a non-empty list")
    seen_ids: set[str] = set()
    seen_exposure: set[str] = set()
    roles: set[str] = set()
    cut = Decimal(EXPOSURE_COEFFICIENTS["cut"])
    near_zero = 0
    for index, item in enumerate(samples):
        sample = exact_keys(item, SAMPLE_KEYS, f"sample {index}")
        ident = sample["id"]
        require(isinstance(ident, str) and IDENT.fullmatch(ident) is not None, f"sample {index} id is not canonical")
        require(ident not in seen_ids, "duplicate sample id: " + ident)
        seen_ids.add(ident)
        exposure = sample["exposure"]
        number = _exposure(exposure)
        require(exposure not in seen_exposure, "duplicate exposure: " + exposure)
        seen_exposure.add(exposure)
        role = sample["role"]
        require(role in ROLES, f"sample {index} role is unknown")
        require(_role_holds(role, number, cut), f"sample {index} role does not match the exposure")
        roles.add(role)
        if number != 0 and abs(number) <= Decimal("0.02"):
            near_zero += 1
    missing = [role for role in ROLES if role not in roles]
    require(not missing, "missing sample roles: " + ", ".join(missing))
    require(near_zero >= 2, "fixture needs at least two signed exposures around zero")


def _questions(phone_iso: str) -> list[str]:
    return [
        "host fixture is not a physical S23 measurement",
        f"encoding EI {ENCODING_EI} is not phone ISO {phone_iso}",
        "reference agreement is not sensor-derived Log or cinema-camera equivalence",
        "ten-bit fidelity is not established by this arithmetic",
    ]


def _preserved(document: dict) -> list[str]:
    preserved = [
        f"source:{SOURCE}",
        f"encoding-ei:{document['encodingEi']}",
        f"phone-iso:{document['phoneIso']}",
        f"convention:{CONVENTION_EXPOSURE}",
        f"selector:{SELECTOR}",
        f"black:{EXPOSURE_COEFFICIENTS['f']}",
        f"mid-grey:{encode('0.18')}",
        f"branch-gap:{branch_discontinuity()}",
        "ei200-exposure-black-not-used:" + EI200_EXPOSURE_BLACK,
    ]
    ordered = sorted(document["samples"], key=lambda item: (Decimal(item["exposure"]), item["id"]))
    for sample in ordered:
        encoded = encode(sample["exposure"])
        preserved.append(
            f"sample:{sample['id']}:{sample['role']}:{sample['exposure']}->{encoded}"
        )
        preserved.append(f"round-trip:{sample['id']}:{decode(encoded)}")
    preserved.append("unclipped:signed-and-highlight")
    return preserved


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS and decision not in _FORBIDDEN, "P057 must not decide qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons),
            "reasons must be a non-empty list of strings")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def _agree(left: str, right: str, tolerance: str) -> bool:
    return abs(Decimal(left) - Decimal(right)) <= Decimal(tolerance)


def _check_curve(document: dict) -> None:
    require(exposure_oracle_failures(CONVENTION_EXPOSURE) == [],
            "exposure-domain table failed its own oracle")
    gap = Decimal(branch_discontinuity())
    require(gap <= Decimal(TOLERANCE["branchGap"]), "branch gap exceeds coefficient-rounding tolerance")
    eps = Decimal("0.000000000001")
    cut = Decimal(EXPOSURE_COEFFICIENTS["cut"])
    jump = abs(_encode_decimal(cut, EXPOSURE_COEFFICIENTS) - _encode_decimal(cut + eps, EXPOSURE_COEFFICIENTS))
    require(jump <= Decimal(TOLERANCE["branchGap"]), "branch step exceeds coefficient-rounding tolerance")
    grey = Decimal(encode("0.18"))
    require(abs(grey - Decimal("0.391006832034084")) <= Decimal(TOLERANCE["midGrey"]),
            "middle grey left the published EI800 anchor")
    require(encode("0") == EXPOSURE_COEFFICIENTS["f"], "black is not the published intercept")
    require(encode("0") != EI200_EXPOSURE_BLACK, "phone-ISO EI200 intercept replaced EI800")
    ladder = [Decimal("-0.02") + Decimal(index) * Decimal("0.001") for index in range(221)]
    ladder.extend([Decimal(1), Decimal(2), Decimal(4), Decimal(8), Decimal(16)])
    encoded_ladder = [_encode_decimal(value, EXPOSURE_COEFFICIENTS) for value in ladder]
    require(all(left < right for left, right in zip(encoded_ladder, encoded_ladder[1:])),
            "exposure curve is not strictly monotonic")
    oracle_tol = TOLERANCE["oracle"]
    round_tol = TOLERANCE["roundTrip"]
    for value in ladder[::10]:
        text = canonical(value)
        require(_agree(encode(text), independent_encode(text), oracle_tol),
                "independent reference disagreed at " + text)
        require(_agree(decode(encode(text)), text, round_tol), "round trip failed at " + text)
    for sample in document["samples"]:
        exposure = Decimal(sample["exposure"])
        encoded = _encode_decimal(exposure, EXPOSURE_COEFFICIENTS)
        if exposure < 0:
            require(encoded < _encode_decimal(Decimal(0), EXPOSURE_COEFFICIENTS),
                    "negative exposure was clipped")
        if exposure > 1:
            require(encoded > _encode_decimal(Decimal(1), EXPOSURE_COEFFICIENTS),
                    "highlight above scene-linear one was clipped")
        text = sample["exposure"]
        require(_agree(encode(text), independent_encode(text), oracle_tol),
                "independent reference disagreed at " + text)
        require(_agree(decode(encode(text)), text, round_tol), "round trip failed at " + text)
        clamped = min(Decimal(1), max(Decimal(0), exposure))
        if clamped != exposure:
            require(encoded != _encode_decimal(clamped, EXPOSURE_COEFFICIENTS),
                    "sample collapsed to a clamped copy")


def assess(document: dict) -> dict:
    """Agree the exposure-domain reference. Decision is never qualified or allowed."""
    validate_document(document)
    _check_curve(document)
    reasons = [
        ORACLE,
        SOURCE,
        "black encodes to the published EI800 intercept",
        "middle grey agrees within tolerance",
        "branch gap is within coefficient rounding",
        "curve is monotonic on the signed-to-highlight ladder",
        "inverse round trips stay inside the declared tolerance",
        "valid negatives and highlights were not clipped",
        f"encoding EI {ENCODING_EI} was not replaced by phone ISO {document['phoneIso']}",
        HOST_LIMIT,
    ]
    return _result("reference_agreed", reasons, [], _preserved(document), _questions(document["phoneIso"]))


def apply_sensor_signal_coefficients(document: dict) -> dict:
    """Reject the mutant. Exposure-domain inventory stays in preservedResults."""
    validate_document(document)
    failed = exposure_oracle_failures(CONVENTION_SENSOR)
    require(failed == [ANCHOR_BLACK, ANCHOR_GREY, ANCHOR_BRANCH, ANCHOR_INVERSE],
            "sensor-signal mutant did not fail the exposure-domain oracle")
    preserved = _preserved(document)
    require(any(item.startswith("sample:") and "->0.092809" in item for item in preserved),
            "mutant rejection dropped the exposure-domain black encoding")
    return _result(
        "rejected",
        [
            MUTANT,
            "sensor-signal coefficients on exposure-domain input failed black",
            "sensor-signal coefficients on exposure-domain input failed middle grey",
            "sensor-signal coefficients on exposure-domain input failed branch",
            "sensor-signal coefficients on exposure-domain input failed inverse",
            "sensor-signal encodings were not stored as the reference",
            ORACLE,
            HOST_LIMIT,
        ],
        ["sensor-signal-on-exposure-domain", ANCHOR_BLACK, ANCHOR_GREY, ANCHOR_BRANCH, ANCHOR_INVERSE],
        preserved,
        _questions(document["phoneIso"]) + ["sensor-signal is a different input convention"],
    )


def select_by_phone_iso(document: dict) -> dict:
    """Reject using the phone ISO as the LogC3 EI. The EI800 intercept stays."""
    validate_document(document)
    preserved = _preserved(document)
    require(encode("0") == EXPOSURE_COEFFICIENTS["f"], "EI800 intercept missing")
    require(encode("0") != EI200_EXPOSURE_BLACK, "EI200 intercept was selected")
    return _result(
        "rejected",
        [
            f"phone ISO {document['phoneIso']} does not select the LogC3 encoding EI",
            f"EI200 exposure intercept {EI200_EXPOSURE_BLACK} was not substituted",
            HOST_LIMIT,
        ],
        ["phone-iso-is-not-encoding-ei"],
        preserved,
        _questions(document["phoneIso"]),
    )
