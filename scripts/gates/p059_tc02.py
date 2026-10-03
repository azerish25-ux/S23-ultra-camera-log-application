"""TC-P059-02 eight-bit data in ten-bit storage.

Intervention: Quantize the source or intermediate to eight bits before packing
into a Main10 output.
Expected: Fail useful precision qualification despite the ten-bit container
and profile indication.
Negative: Bitstream depth metadata alone must not establish ten-bit image fidelity.
"""

from __future__ import annotations


CASE_ID = "TC-P059-02"
INTERVENTION = (
    "Quantize the source or intermediate to eight bits before packing into a Main10 output."
)
EXPECTED = (
    "Fail useful precision qualification despite the ten-bit container and profile indication."
)
NEGATIVE = "Bitstream depth metadata alone must not establish ten-bit image fidelity."

_BOUNDARIES = ("camera-input", "gpu-texture", "bitmap-conversion", "codec-input")
_PROFILES = ("Main10", "Main")
_DEPTHS = (8, 10, 12)
_PAYLOAD_KEYS = (
    "boundary",
    "container",
    "profile",
    "spsBitDepth",
    "quantizedBits",
    "code",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "withheld", "precision_failed")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Fail useful precision when eight-bit data is packed into Main10."""
    boundary, container, profile, sps_depth, quantized, code = _payload(payload)
    preserved = [
        "boundary:" + boundary,
        "container:" + container,
        "profile:" + profile,
        f"sps-bit-depth:{sps_depth}",
        f"quantized-bits:{quantized}",
        f"code:{code}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if quantized <= 8:
        decision = "precision_failed"
        rejected.append("eight-bit-quantized")
        reasons.append(
            f"{quantized}-bit values packed at {boundary} do not meet useful precision"
        )
        if sps_depth >= 10 and profile == "Main10":
            rejected.append("metadata-is-not-fidelity")
            reasons.append(NEGATIVE)
        questions = ["ten-bit container metadata was not treated as image fidelity"]
    elif sps_depth != quantized:
        decision = "rejected"
        rejected.append("depth-contradiction")
        reasons.append("stored sample precision and bitstream depth disagree")
        questions = ["depth contradiction blocks a precision claim"]
    else:
        decision = "withheld"
        reasons.append("matching storage width on this host fixture is not ten-bit fidelity")
        reasons.append("bitstream depth metadata was not accepted by itself")
        questions = ["host fixture does not qualify ten-bit image fidelity"]
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, int, int, int]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    boundary = payload["boundary"]
    if boundary not in _BOUNDARIES:
        raise ValueError("boundary is unsupported")
    if payload["container"] != "Main10":
        raise ValueError("container must be Main10")
    profile = payload["profile"]
    if profile not in _PROFILES:
        raise ValueError("profile is unsupported")
    sps_depth = payload["spsBitDepth"]
    quantized = payload["quantizedBits"]
    if sps_depth not in _DEPTHS or type(sps_depth) is not int:
        raise ValueError("spsBitDepth must be 8, 10, or 12")
    if quantized not in _DEPTHS or type(quantized) is not int:
        raise ValueError("quantizedBits must be 8, 10, or 12")
    code = payload["code"]
    if type(code) is not int or not 0 <= code <= 1023:
        raise ValueError("code must be an int from 0 through 1023")
    return boundary, "Main10", profile, sps_depth, quantized, code


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P059-02 must not yield qualified or allowed")
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
