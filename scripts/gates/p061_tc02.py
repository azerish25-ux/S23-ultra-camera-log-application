"""TC-P061-02 eight-bit data in ten-bit storage.

Intervention: Quantize the source or intermediate to eight bits before packing
into a Main10 output.
Expected: Fail useful precision qualification despite the ten-bit container
and profile indication.
Negative: Bitstream depth metadata alone must not establish ten-bit image fidelity.
"""

from __future__ import annotations


CASE_ID = "TC-P061-02"
INTERVENTION = (
    "Quantize the source or intermediate to eight bits before packing into a Main10 output."
)
EXPECTED = (
    "Fail useful precision qualification despite the ten-bit container and profile indication."
)
NEGATIVE = "Bitstream depth metadata alone must not establish ten-bit image fidelity."
REPEAT = "Repeat at camera input, GPU texture, bitmap conversion, and codec input boundaries."

_BOUNDARIES = ("camera-input", "gpu-texture", "bitmap-conversion", "codec-input")
_PAYLOAD_KEYS = (
    "boundary",
    "container",
    "containerDepth",
    "imageBits",
    "profileSaysTenBit",
    "quantizedToEight",
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


def evaluate(payload: dict) -> dict:
    """Reject eight-bit samples packed into Main10. Depth metadata is not fidelity."""
    boundary, container, depth, image_bits, profile, quantized, code = _payload(payload)
    preserved = [
        f"boundary:{boundary}",
        f"container:{container}",
        f"container-depth:{depth}",
        f"image-bits:{image_bits}",
        f"code:{code}",
        f"profile-says-ten-bit:{str(profile).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION, f"repeat coverage includes {REPEAT}"]
    questions = ["host fixture does not qualify ten-bit image fidelity"]
    eight_bit = quantized or image_bits == 8
    if eight_bit:
        rejected = ["eight-bit-in-main10", "precision-not-qualified"]
        reasons.append("eight-bit data was packed into a ten-bit container")
        if profile or depth == 10:
            rejected.append("bitstream-depth-not-fidelity")
            reasons.append(NEGATIVE)
        decision = "rejected"
    else:
        rejected = []
        decision = "withheld"
        reasons.append("useful precision qualification was not granted")
        reasons.append("ten-bit container and profile indication were not treated as fidelity")
        questions.append("stored width is ten bits in this payload and is still not a qualification")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    boundary = payload["boundary"]
    if boundary not in _BOUNDARIES:
        raise ValueError("boundary is unsupported")
    container = payload["container"]
    if container != "Main10":
        raise ValueError("container must be Main10")
    depth = payload["containerDepth"]
    if type(depth) is not int or depth != 10:
        raise ValueError("containerDepth must be the integer 10")
    image_bits = payload["imageBits"]
    if type(image_bits) is not int or image_bits not in {8, 10}:
        raise ValueError("imageBits must be 8 or 10")
    profile = payload["profileSaysTenBit"]
    if type(profile) is not bool:
        raise ValueError("profileSaysTenBit must be a bool")
    quantized = payload["quantizedToEight"]
    if type(quantized) is not bool:
        raise ValueError("quantizedToEight must be a bool")
    code = payload["code"]
    if type(code) is not int or isinstance(code, bool) or not 0 <= code <= 1023:
        raise ValueError("code must be an int from 0 through 1023")
    return boundary, container, depth, image_bits, profile, quantized, code


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P061-02 must not yield qualified or allowed")
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
