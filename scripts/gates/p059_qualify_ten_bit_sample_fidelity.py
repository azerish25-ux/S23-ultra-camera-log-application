#!/usr/bin/env python3
"""P059 ten-bit sample fidelity on a host fixture.

A high-resolution code ramp is compared after a Main10 pack and unpack.
The fixture ramp is eight-bit quantized and then expanded into ten-bit
sample containers. SPS bit depth and the Main10 profile stay in the
inventory. They do not establish useful ten-bit precision.

The deliberate mutant — accept ten-bit fidelity from SPS bit depth alone —
is rejected. This module does not probe a device, does not qualify a
physical S23, and does not execute TC-P059-01 through TC-P059-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P059"
CASE_ID = "P059"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-ten-bit-sample-fidelity-fixture"
METHOD = (
    "Encode and decode a high-resolution code ramp, compare numeric values, and run a "
    "deliberately eight-bit-degraded negative control through the same route. Inspect "
    "SPS and decoded sample layout. Qualification binds the codec, configuration, and "
    "software build."
)
FIXTURE = (
    "A Main10 stream carrying an eight-bit-quantized ramp expanded into ten-bit sample "
    "containers."
)
ORACLE = (
    "The negative control fails precision criteria even though its bitstream advertises "
    "ten-bit storage."
)
MUTANT = "Accept ten-bit fidelity from SPS bit depth alone."
HOST_LIMIT = "this host record does not qualify a physical S23"
DECLARED_TEST = "numeric-comparison"
MUTANT_TEST = "sps-bit-depth-alone"
SOLE_TESTS = (DECLARED_TEST, MUTANT_TEST)
QUANTIZATIONS = ("eight-bit-expanded", "ten-bit-native")
ALIGNMENTS = ("msb", "lsb")
PROFILES = ("Main10", "Main")
DEPTH_CODES = ("0", "2", "4")
CHROMA_CODES = ("0", "1", "2", "3")
CHROMA_NAMES = {"0": "mono", "1": "4:2:0", "2": "4:2:2", "3": "4:4:4"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
UINT = re.compile(r"0|[1-9][0-9]*")
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "codec",
    "profile",
    "configuration",
    "softwareBuild",
    "quantization",
    "sps",
    "layout",
    "referenceRamp",
    "decoded",
    "packedWords",
}
SPS_KEYS = {"bitDepthLumaMinus8", "bitDepthChromaMinus8", "chromaFormatIdc"}
LAYOUT_KEYS = {"container", "alignment", "rowStride", "width", "height"}
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "withheld", "precision_failed"}


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


def quantize_eight(code: int) -> int:
    """Expand an eight-bit quantization into a ten-bit container (code >> 2) << 2."""
    require(0 <= code <= 1023, "code out of ten-bit range")
    return (code >> 2) << 2


def pack_msb(code: int) -> int:
    """Place a ten-bit code in the high bits of a sixteen-bit P010 word."""
    require(0 <= code <= 1023, "code out of ten-bit range")
    return code << 6


def eight_bit_pattern(reference: list[int], decoded: list[int]) -> bool:
    """True when decoded codes are the eight-bit expansion and at least one differs."""
    if len(reference) != len(decoded) or not reference:
        return False
    expanded = [quantize_eight(code) for code in reference]
    return decoded == expanded and any(code != got for code, got in zip(reference, decoded))


def _token(value: object, label: str) -> str:
    require(isinstance(value, str) and TOKEN.fullmatch(value) is not None,
            label + " must be a lowercase token")
    return value


def _uint(value: object, label: str, limit: int) -> int:
    require(isinstance(value, str) and UINT.fullmatch(value) is not None,
            label + " must be a canonical non-negative integer string")
    number = int(value)
    require(0 <= number <= limit, label + " is out of range")
    return number


def _codes(value: object, label: str) -> list[int]:
    require(isinstance(value, list), label + " must be a list")
    require(4 <= len(value) <= 32, label + " must contain 4 to 32 codes")
    return [_uint(item, f"{label}[{index}]", 1023) for index, item in enumerate(value)]


def _words(value: object, label: str, count: int) -> list[int]:
    require(isinstance(value, list) and len(value) == count, label + " length must match the ramp")
    return [_uint(item, f"{label}[{index}]", 65535) for index, item in enumerate(value)]


def _sps(value: object) -> dict[str, str]:
    item = exact_keys(value, SPS_KEYS, "sps")
    luma = item["bitDepthLumaMinus8"]
    chroma = item["bitDepthChromaMinus8"]
    fmt = item["chromaFormatIdc"]
    require(luma in DEPTH_CODES, "bitDepthLumaMinus8 must be 0, 2, or 4")
    require(chroma in DEPTH_CODES, "bitDepthChromaMinus8 must be 0, 2, or 4")
    require(fmt in CHROMA_CODES, "chromaFormatIdc must be 0, 1, 2, or 3")
    return {
        "bitDepthLumaMinus8": luma,
        "bitDepthChromaMinus8": chroma,
        "chromaFormatIdc": fmt,
    }


def _layout(value: object) -> dict[str, Any]:
    item = exact_keys(value, LAYOUT_KEYS, "layout")
    require(item["container"] == "P010", "layout container must be P010")
    alignment = item["alignment"]
    require(alignment in ALIGNMENTS, "layout alignment must be msb or lsb")
    width = _uint(item["width"], "layout width", 16384)
    height = _uint(item["height"], "layout height", 16384)
    stride = _uint(item["rowStride"], "layout rowStride", 16384)
    require(width >= 16 and height >= 1 and stride >= 1, "layout dimensions must be positive")
    return {
        "container": "P010",
        "alignment": alignment,
        "rowStride": stride,
        "width": width,
        "height": height,
    }


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P059 precision fixture shape."""
    exact_keys(document, DOCUMENT_KEYS, "precision document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P059")
    require(document["mapId"] == MAP_ID, "mapId must be s23-ten-bit-sample-fidelity-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "precision document needs the P059 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    require(document["codec"] == "hevc", "codec must be hevc")
    require(document["profile"] in PROFILES, "profile must be Main10 or Main")
    _token(document["configuration"], "configuration")
    _token(document["softwareBuild"], "softwareBuild")
    require(document["quantization"] in QUANTIZATIONS, "quantization is unsupported")
    _sps(document["sps"])
    _layout(document["layout"])
    reference = _codes(document["referenceRamp"], "referenceRamp")
    decoded = _codes(document["decoded"], "decoded")
    require(len(reference) == len(decoded), "decoded length must match referenceRamp")
    _words(document["packedWords"], "packedWords", len(decoded))


def _load(document: dict) -> dict[str, Any]:
    reference = _codes(document["referenceRamp"], "referenceRamp")
    decoded = _codes(document["decoded"], "decoded")
    return {
        "codec": document["codec"],
        "profile": document["profile"],
        "configuration": document["configuration"],
        "softwareBuild": document["softwareBuild"],
        "quantization": document["quantization"],
        "sps": _sps(document["sps"]),
        "layout": _layout(document["layout"]),
        "reference": reference,
        "decoded": decoded,
        "words": _words(document["packedWords"], "packedWords", len(decoded)),
    }


def _preserved(loaded: dict[str, Any]) -> list[str]:
    layout = loaded["layout"]
    sps = loaded["sps"]
    luma = int(sps["bitDepthLumaMinus8"]) + 8
    chroma = int(sps["bitDepthChromaMinus8"]) + 8
    unique = len(set(loaded["decoded"]))
    mismatches = sum(
        1 for ref, got in zip(loaded["reference"], loaded["decoded"]) if ref != got
    )
    preserved = [
        f"codec:{loaded['codec']}",
        f"profile:{loaded['profile']}",
        f"configuration:{loaded['configuration']}",
        f"softwareBuild:{loaded['softwareBuild']}",
        f"binding:{loaded['codec']}|{loaded['configuration']}|{loaded['softwareBuild']}",
        f"sps-luma-depth:{luma}",
        f"sps-chroma-depth:{chroma}",
        f"chroma-format:{CHROMA_NAMES[sps['chromaFormatIdc']]}",
        f"layout:{layout['container']}:{layout['alignment']}",
        f"size:{layout['width']}x{layout['height']}",
        f"stride:{layout['rowStride']}",
        f"quantization:{loaded['quantization']}",
        f"unique-decoded:{unique}",
        f"mismatch-count:{mismatches}",
    ]
    preserved.extend(
        f"pair:{index}:{ref}->{got}"
        for index, (ref, got) in enumerate(zip(loaded["reference"], loaded["decoded"]))
    )
    preserved.extend(f"word:{index}:{word}" for index, word in enumerate(loaded["words"]))
    return preserved


def _questions(loaded: dict[str, Any]) -> list[str]:
    luma = int(loaded["sps"]["bitDepthLumaMinus8"]) + 8
    questions = [
        "host fixture is not a physical S23 measurement",
        (
            f"qualification would bind {loaded['codec']}, {loaded['configuration']}, "
            f"and {loaded['softwareBuild']} and is not claimed"
        ),
    ]
    if luma == 10:
        questions.append("SPS bit depth 10 does not establish ten-bit image fidelity")
    return questions


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS and decision not in _FORBIDDEN,
            "P059 must not decide qualified or allowed")
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


def _structural(loaded: dict[str, Any]) -> list[str]:
    claims: list[str] = []
    layout = loaded["layout"]
    luma = int(loaded["sps"]["bitDepthLumaMinus8"]) + 8
    if loaded["profile"] == "Main10" and luma != 10:
        claims.append("profile-depth-contradiction")
    if not any(code % 4 != 0 for code in loaded["reference"]):
        claims.append("ramp-not-high-resolution")
    if layout["alignment"] == "lsb":
        claims.append("low-six-bit-alignment")
    elif any(word != pack_msb(code) for word, code in zip(loaded["words"], loaded["decoded"])):
        claims.append("unpacked-word-mismatch")
    if layout["rowStride"] < layout["width"]:
        claims.append("stride-below-width")
    return claims


def assess(document: dict, sole_test: str = DECLARED_TEST) -> dict:
    """Compare the ramp. Reject ten-bit fidelity inferred from SPS depth alone.

    sole_test "sps-bit-depth-alone" is the mutant. It is rejected even when
    the SPS luma depth is 10. Mismatch pairs stay in preservedResults.
    """
    validate_document(document)
    require(sole_test in SOLE_TESTS, "sole_test must be numeric-comparison or sps-bit-depth-alone")
    loaded = _load(document)
    preserved = _preserved(loaded)
    luma = int(loaded["sps"]["bitDepthLumaMinus8"]) + 8
    mismatches = [
        index for index, (ref, got) in enumerate(zip(loaded["reference"], loaded["decoded"]))
        if ref != got
    ]
    pattern = eight_bit_pattern(loaded["reference"], loaded["decoded"])
    claims: list[str] = []
    if pattern:
        claims.append("eight-bit-quantized-ramp")
    elif mismatches:
        claims.append("numeric-mismatch")
    elif loaded["quantization"] == "eight-bit-expanded":
        claims.append("quantization-label-contradiction")
    structural = _structural(loaded)
    claims.extend(structural)
    reasons = [
        f"compared {len(loaded['reference'])} ramp codes and found {len(mismatches)} mismatches",
        f"SPS advertises {luma}-bit storage on profile {loaded['profile']}",
        f"layout {loaded['layout']['container']} {loaded['layout']['alignment']} "
        f"{loaded['layout']['width']}x{loaded['layout']['height']} stride {loaded['layout']['rowStride']}",
    ]
    if pattern:
        reasons.append(ORACLE)
        reasons.append("eight-bit quantization expanded into ten-bit containers failed precision criteria")
    elif not mismatches and not structural and sole_test != MUTANT_TEST:
        reasons.append("numeric codes matched the reference ramp on this host fixture")
        reasons.append("a host numeric match is not ten-bit fidelity and SPS depth was not accepted as fidelity")
    if sole_test == MUTANT_TEST:
        claims.insert(0, "sps-bit-depth-alone")
        reasons.append(MUTANT)
        reasons.append("SPS bit depth was not accepted as ten-bit image fidelity")
    if sole_test == MUTANT_TEST or structural or (claims and "eight-bit-quantized-ramp" not in claims):
        decision = "rejected"
    elif "eight-bit-quantized-ramp" in claims:
        decision = "precision_failed"
    else:
        decision = "withheld"
    reasons.append(HOST_LIMIT)
    return _result(decision, reasons, claims, preserved, _questions(loaded))
