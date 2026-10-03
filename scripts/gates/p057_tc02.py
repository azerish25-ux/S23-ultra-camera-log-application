"""TC-P057-02 eight-bit data in ten-bit storage.

Intervention: Quantize the source or intermediate to eight bits before packing
into a Main10 output.
Expected: Fail useful precision qualification despite the ten-bit container
and profile indication.
Negative: Bitstream depth metadata alone must not establish ten-bit image fidelity.
"""

from __future__ import annotations


CASE_ID = "TC-P057-02"
INTERVENTION = (
    "Quantize the source or intermediate to eight bits before packing into a Main10 output."
)
EXPECTED = (
    "Fail useful precision qualification despite the ten-bit container and profile indication."
)
NEGATIVE = "Bitstream depth metadata alone must not establish ten-bit image fidelity."

_BOUNDARIES = ("camera-input", "gpu-texture", "bitmap-conversion", "codec-input")
_PAYLOAD_KEYS = (
    "boundary",
    "sourceBits",
    "containerBits",
    "profileIndicatesTenBit",
    "quantizedBeforePack",
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


def evaluate(payload: dict) -> dict:
    """Reject eight-bit quantization packed into a ten-bit container."""
    boundary, source_bits, container_bits, profile, quantized = _payload(payload)
    preserved = [
        f"boundary:{boundary}",
        f"source-bits:{source_bits}",
        f"container-bits:{container_bits}",
        f"profile-ten-bit:{str(profile).lower()}",
        f"quantized-before-pack:{str(quantized).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = ["host precision check is not ten-bit image fidelity"]
    early = quantized or source_bits == 8
    if container_bits == 10 and early:
        reasons.append(NEGATIVE)
        reasons.append(f"useful precision failed at {boundary}")
        claims = ["eight-bit-in-ten-bit-container"]
        if profile:
            claims.append("depth-metadata-not-fidelity")
        questions.append("ten-bit container metadata does not restore source precision")
        return _result("rejected", reasons, claims, preserved, questions)
    if container_bits != 10:
        reasons.append("container is not a Main10 output")
        return _result("rejected", reasons, ["container-not-main10"], preserved, questions)
    reasons.append("ten-bit path was not promoted to a precision qualification")
    questions.append(f"{boundary} still needs a measured precision check")
    return _result("withheld", reasons, [], preserved, questions)


def _payload(payload: object) -> tuple[str, int, int, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    boundary = payload["boundary"]
    if boundary not in _BOUNDARIES:
        raise ValueError("boundary is unknown")
    source_bits = payload["sourceBits"]
    container_bits = payload["containerBits"]
    if type(source_bits) is not int or source_bits not in {8, 10}:
        raise ValueError("sourceBits must be 8 or 10")
    if type(container_bits) is not int or container_bits not in {8, 10}:
        raise ValueError("containerBits must be 8 or 10")
    profile = payload["profileIndicatesTenBit"]
    quantized = payload["quantizedBeforePack"]
    if type(profile) is not bool or type(quantized) is not bool:
        raise ValueError("profile and quantize flags must be bools")
    return boundary, source_bits, container_bits, profile, quantized


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
