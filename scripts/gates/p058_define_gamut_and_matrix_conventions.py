#!/usr/bin/env python3
"""P058 gamut and matrix conventions on a host fixture.

A working-space to AWG3 matrix, its direction, white point, decimal precision,
and YUV storage coefficients are separate facts. A YUV matrix identifier is
not RGB primaries and is not a transfer. LogC4 and other ARRI workflows stay
outside this profile.

The fixture is an AWG3 LogC3 file whose metadata says Rec.709 primaries only
because Rec.709 YUV coefficients were used. The validator rejects that
descriptor and requires an explicit sidecar. The mutant — treating matrix
coefficients and color primaries as interchangeable — is rejected.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P058-01 through TC-P058-08.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


PHASE = "P058"
CASE_ID = "P058"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-gamut-matrix-fixture"
METHOD = (
    "Specify working-space to AWG3 conversion, matrix direction, white point, "
    "numerical precision, and storage coefficients. Distinguish a YUV matrix "
    "identifier from RGB primaries and transfer. Keep LogC4 and other ARRI "
    "workflows outside this profile unless separately implemented."
)
FIXTURE = (
    "An AWG3 LogC3 file whose metadata incorrectly identifies Rec.709 primaries "
    "because Rec.709 YUV coefficients were used."
)
ORACLE = (
    "The signal validator rejects the contradictory descriptor and requires the "
    "explicit sidecar interpretation."
)
MUTANT = "Treat matrix coefficients and color primaries as interchangeable metadata."
PRECISION = "decimal-string"
PROFILE_DIRECTION = "working-to-AWG3"
PROFILE_WHITE = "D65"
PROFILE_PRIMARIES = "AWG3"
PROFILE_ENCODING = "LogC3"
HONEST = "distinguish"
MUTANT_MODE = "coefficients-as-primaries"
INTERPRETATIONS = {HONEST, MUTANT_MODE}
HOST_LIMIT = "host fixture does not qualify a physical S23 or ten-bit image fidelity"
MUTANT_ACCEPT = "interchangeable"

HEX40 = re.compile(r"^[0-9a-f]{40}$")
DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
SIGNED = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")

ENCODINGS = {"LogC3", "LogC4"}
PRIMARIES = {"AWG3", "Rec.709", "Rec.2020"}
TRANSFERS = {"LogC3", "HLG", "Rec.709", "LogC4"}
WHITE_POINTS = {"D65", "D60"}
DIRECTIONS = {"working-to-AWG3", "AWG3-to-working"}
RANGES = {"full", "video"}
DERIVED = {"yuv-coefficients", "explicit-primaries"}
STORAGE_TABLE = {
    "BT.709": ("0.2126", "0.7152", "0.0722"),
    "BT.2020": ("0.2627", "0.6780", "0.0593"),
}
IMPLIED_PRIMARIES = {"BT.709": "Rec.709", "BT.2020": "Rec.2020"}

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "signal",
    "conversion",
    "storage",
    "descriptor",
    "sidecar",
    "separateImplementation",
}
SIGNAL_KEYS = {"encoding", "primaries", "transfer", "whitePoint"}
CONVERSION_KEYS = {"direction", "precision", "whitePoint", "matrix"}
STORAGE_KEYS = {"id", "kr", "kg", "kb"}
DESCRIPTOR_KEYS = {"declaredPrimaries", "yuvMatrix", "transfer", "range", "derivedFrom"}
SIDECAR_KEYS = {
    "present",
    "explicit",
    "primaries",
    "transfer",
    "yuvMatrix",
    "matrixDirection",
    "whitePoint",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed", MUTANT_ACCEPT}


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
    """Render a Decimal without exponent notation or trailing zeros."""
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def _decimal(value: object, label: str, signed: bool = False) -> str:
    pattern = SIGNED if signed else DECIMAL
    require(
        isinstance(value, str) and pattern.fullmatch(value) is not None,
        label + " must be a canonical decimal string",
    )
    require(value != "-0", label + " must not be negative zero")
    return value


def _choice(value: object, allowed: set[str], label: str) -> str:
    require(value in allowed, label + " is unsupported")
    return value


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def implied_primaries(yuv_id: str) -> str:
    """Name the mutant would copy from a YUV matrix id onto RGB primaries."""
    require(yuv_id in IMPLIED_PRIMARIES, "unknown YUV matrix id")
    return IMPLIED_PRIMARIES[yuv_id]


def apply_matrix(matrix: list[str], rgb: list[str]) -> tuple[str, str, str]:
    """Apply a row-major 3x3 and return canonical decimal components."""
    require(type(matrix) is list and len(matrix) == 9, "matrix must have nine coefficients")
    require(type(rgb) is list and len(rgb) == 3, "rgb must have three components")
    coeffs = [Decimal(_decimal(item, "matrix coefficient", signed=True)) for item in matrix]
    channels = [Decimal(_decimal(item, "rgb component", signed=True)) for item in rgb]
    red, green, blue = channels
    mapped = (
        coeffs[0] * red + coeffs[1] * green + coeffs[2] * blue,
        coeffs[3] * red + coeffs[4] * green + coeffs[5] * blue,
        coeffs[6] * red + coeffs[7] * green + coeffs[8] * blue,
    )
    return tuple(canonical(item) for item in mapped)


def white_preserved(matrix: list[str]) -> bool:
    """True when equal working-space channels stay equal after the matrix."""
    red, green, blue = apply_matrix(matrix, ["1", "1", "1"])
    return red == green == blue


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision not in _FORBIDDEN, "P058 must not decide qualified, allowed, or interchangeable")
    require(
        bool(reasons) and all(isinstance(item, str) and item for item in reasons),
        "reasons must be a non-empty list of strings",
    )
    require(all(isinstance(item, str) and item for item in rejected), "rejectedClaims must be strings")
    require(all(isinstance(item, str) and item for item in preserved), "preservedResults must be strings")
    require(all(isinstance(item, str) and item for item in questions), "openQuestions must be strings")
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


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is a P058 gamut and matrix fixture."""
    exact_keys(document, DOCUMENT_KEYS, "gamut matrix")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P058")
    require(document["mapId"] == MAP_ID, "mapId must be s23-gamut-matrix-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "gamut matrix needs the P058 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    _bool(document["separateImplementation"], "separateImplementation")

    signal = exact_keys(document["signal"], SIGNAL_KEYS, "signal")
    _choice(signal["encoding"], ENCODINGS, "signal encoding")
    _choice(signal["primaries"], PRIMARIES, "signal primaries")
    _choice(signal["transfer"], TRANSFERS, "signal transfer")
    _choice(signal["whitePoint"], WHITE_POINTS, "signal white point")

    conversion = exact_keys(document["conversion"], CONVERSION_KEYS, "conversion")
    _choice(conversion["direction"], DIRECTIONS, "matrix direction")
    require(conversion["precision"] == PRECISION, "precision must be decimal-string")
    _choice(conversion["whitePoint"], WHITE_POINTS, "conversion white point")
    matrix = conversion["matrix"]
    require(type(matrix) is list and len(matrix) == 9, "matrix must be nine coefficients")
    for item in matrix:
        _decimal(item, "matrix coefficient", signed=True)

    storage = exact_keys(document["storage"], STORAGE_KEYS, "storage")
    _choice(storage["id"], set(STORAGE_TABLE), "storage id")
    triple = (
        _decimal(storage["kr"], "kr"),
        _decimal(storage["kg"], "kg"),
        _decimal(storage["kb"], "kb"),
    )
    require(triple == STORAGE_TABLE[storage["id"]], "storage coefficients must match the YUV matrix id")
    require(sum((Decimal(item) for item in triple), Decimal(0)) == 1, "YUV coefficients must sum to 1")

    descriptor = exact_keys(document["descriptor"], DESCRIPTOR_KEYS, "descriptor")
    _choice(descriptor["declaredPrimaries"], PRIMARIES, "declared primaries")
    _choice(descriptor["yuvMatrix"], set(STORAGE_TABLE), "descriptor YUV matrix")
    require(descriptor["yuvMatrix"] == storage["id"], "descriptor YUV matrix must match storage id")
    _choice(descriptor["transfer"], TRANSFERS, "descriptor transfer")
    _choice(descriptor["range"], RANGES, "descriptor range")
    _choice(descriptor["derivedFrom"], DERIVED, "derivedFrom")

    sidecar = exact_keys(document["sidecar"], SIDECAR_KEYS, "sidecar")
    present = _bool(sidecar["present"], "sidecar present")
    explicit = _bool(sidecar["explicit"], "sidecar explicit")
    require(not explicit or present, "an explicit sidecar must be present")
    _choice(sidecar["primaries"], PRIMARIES, "sidecar primaries")
    _choice(sidecar["transfer"], TRANSFERS, "sidecar transfer")
    _choice(sidecar["yuvMatrix"], set(STORAGE_TABLE), "sidecar YUV matrix")
    _choice(sidecar["matrixDirection"], DIRECTIONS, "sidecar matrix direction")
    _choice(sidecar["whitePoint"], WHITE_POINTS, "sidecar white point")


def coefficients_would_replace_primaries(document: dict) -> bool:
    """True when the mutant would treat the YUV id as the RGB primaries name.

    Rec.709 YUV coefficients naming Rec.709 primaries is the interchange.
    ``assess`` must not turn this predicate into ``interchangeable``,
    ``qualified``, or ``allowed``.
    """
    validate_document(document)
    descriptor = document["descriptor"]
    return (
        descriptor["derivedFrom"] == "yuv-coefficients"
        and descriptor["declaredPrimaries"] == implied_primaries(descriptor["yuvMatrix"])
    )


def _sidecar_token(sidecar: dict) -> str:
    if sidecar["present"] and sidecar["explicit"]:
        state = "explicit"
    elif sidecar["present"]:
        state = "present"
    else:
        state = "absent"
    return f"sidecar:{state}:{sidecar['primaries']}:{sidecar['yuvMatrix']}"


def _preserved(document: dict) -> list[str]:
    signal = document["signal"]
    conversion = document["conversion"]
    storage = document["storage"]
    descriptor = document["descriptor"]
    return [
        f"signal:{signal['primaries']}:{signal['encoding']}:{signal['whitePoint']}",
        f"transfer:{signal['transfer']}",
        f"direction:{conversion['direction']}",
        f"precision:{conversion['precision']}",
        f"conversion-white:{conversion['whitePoint']}",
        "matrix:" + ",".join(conversion["matrix"]),
        f"yuv:{storage['id']}:{storage['kr']},{storage['kg']},{storage['kb']}",
        f"declared-primaries:{descriptor['declaredPrimaries']}",
        f"descriptor-transfer:{descriptor['transfer']}",
        f"range:{descriptor['range']}",
        f"derived-from:{descriptor['derivedFrom']}",
        _sidecar_token(document["sidecar"]),
        "logc4:" + ("separate" if document["separateImplementation"] else "outside"),
    ]


def _sidecar_ok(document: dict) -> bool:
    signal = document["signal"]
    sidecar = document["sidecar"]
    return bool(
        sidecar["present"]
        and sidecar["explicit"]
        and signal["primaries"] == PROFILE_PRIMARIES
        and signal["encoding"] == PROFILE_ENCODING
        and sidecar["primaries"] == signal["primaries"]
        and sidecar["transfer"] == signal["transfer"]
        and sidecar["yuvMatrix"] == document["descriptor"]["yuvMatrix"]
        and sidecar["matrixDirection"] == PROFILE_DIRECTION
        and sidecar["whitePoint"] == signal["whitePoint"]
        and sidecar["primaries"] != implied_primaries(sidecar["yuvMatrix"])
    )


def assess(document: dict, interpretation: str = HONEST) -> dict:
    """Reject a contradictory descriptor and require an explicit sidecar.

    interpretation ``coefficients-as-primaries`` is the mutant. It is rejected
    even when YUV coefficients and the declared primaries name agree. The AWG3
    LogC3 identity, the matrix, and the YUV coefficients stay in
    preservedResults. The decision is never ``qualified``, ``allowed``, or
    ``interchangeable``.
    """
    validate_document(document)
    require(interpretation in INTERPRETATIONS, "interpretation must be distinguish or coefficients-as-primaries")
    signal = document["signal"]
    conversion = document["conversion"]
    storage = document["storage"]
    descriptor = document["descriptor"]
    preserved = _preserved(document)
    reasons = [
        ORACLE,
        "YUV matrix " + storage["id"] + " is not RGB primaries and is not the transfer",
    ]
    questions = [
        "host fixture is not a physical S23 measurement",
        "LogC4 and other ARRI workflows stay outside this profile",
    ]
    rejected: list[str] = []

    if signal["encoding"] == "LogC4":
        rejected.append("logc4-outside-profile")
        reasons.append("LogC4 is outside this profile")
        if document["separateImplementation"]:
            questions.append("a separate LogC4 implementation is not accepted by this gate")
        else:
            questions.append("LogC4 was not separately implemented")
    if signal["primaries"] != PROFILE_PRIMARIES:
        rejected.append("not-awg3")
        reasons.append("this profile converts working space to AWG3 only")
    if signal["encoding"] == PROFILE_ENCODING and signal["transfer"] != PROFILE_ENCODING:
        rejected.append("signal-transfer-mismatch")
        reasons.append("LogC3 encoding does not match the signal transfer")
    if conversion["direction"] != PROFILE_DIRECTION:
        rejected.append("reversed-matrix-direction")
        reasons.append("matrix direction must be working-space to AWG3")
    if (
        conversion["whitePoint"] != signal["whitePoint"]
        or signal["whitePoint"] != PROFILE_WHITE
        or conversion["whitePoint"] != PROFILE_WHITE
    ):
        rejected.append("white-point-mismatch")
        reasons.append("white point must be D65 on the signal and the conversion")
    if not white_preserved(conversion["matrix"]):
        rejected.append("white-not-preserved")
        reasons.append("equal working-space channels do not stay equal in AWG3")
    else:
        reasons.append("numerical white is preserved by the stored matrix")
    if descriptor["derivedFrom"] == "yuv-coefficients":
        rejected.append("yuv-not-rgb-primaries")
        reasons.append(
            f"{storage['id']} coefficients {storage['kr']},{storage['kg']},{storage['kb']} "
            "are storage coefficients, not RGB primaries"
        )
    if descriptor["declaredPrimaries"] != signal["primaries"]:
        rejected.append("contradictory-primaries")
        reasons.append(
            f"declared primaries {descriptor['declaredPrimaries']} contradict signal {signal['primaries']}"
        )
    if descriptor["transfer"] != signal["transfer"]:
        rejected.append("descriptor-transfer-contradiction")
        reasons.append("descriptor transfer disagrees with the signal transfer")

    contradictory = any(
        item in rejected
        for item in ("contradictory-primaries", "yuv-not-rgb-primaries", "descriptor-transfer-contradiction")
    )
    sidecar_ok = _sidecar_ok(document)
    if contradictory and not sidecar_ok:
        questions.append("explicit sidecar interpretation required")
        reasons.append("contradictory descriptor rejected")
    elif contradictory and sidecar_ok:
        questions.append("interpretation is bound to the explicit sidecar")
        reasons.append("embedded descriptor stays rejected; sidecar is the only interpretation")

    structural = {
        "logc4-outside-profile",
        "not-awg3",
        "signal-transfer-mismatch",
        "reversed-matrix-direction",
        "white-point-mismatch",
        "white-not-preserved",
    }
    if interpretation == MUTANT_MODE:
        rejected.insert(0, "coefficients-as-primaries")
        reasons.append(MUTANT)
        reasons.append("matrix coefficients and color primaries are not interchangeable")
        questions.append("mutant interpretation rejected")
        decision = "rejected"
    elif any(item in rejected for item in structural):
        decision = "rejected"
    elif contradictory and sidecar_ok:
        decision = "sidecar_required"
    elif contradictory:
        decision = "rejected"
    else:
        decision = "withheld"
        reasons.append("descriptor is consistent in this host fixture and is not a qualification")
        questions.append("consistent metadata is not physical S23 qualification")
    reasons.append(HOST_LIMIT)
    return _result(decision, reasons, rejected, preserved, questions)
