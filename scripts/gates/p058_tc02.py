"""TC-P058-02 eight-bit data in ten-bit storage.

Intervention: Quantize the source or intermediate to eight bits before packing
into a Main10 output.
Expected: Fail useful precision qualification despite the ten-bit container
and profile indication.
Negative: Bitstream depth metadata alone must not establish ten-bit image fidelity.
"""

from __future__ import annotations

CASE_ID = "TC-P058-02"
INTERVENTION = "Quantize the source or intermediate to eight bits before packing into a Main10 output."
EXPECTED = "Fail useful precision qualification despite the ten-bit container and profile indication."
NEGATIVE = "Bitstream depth metadata alone must not establish ten-bit image fidelity."

_BOUNDARIES = ("camera-input", "gpu-texture", "bitmap", "codec-input")
_PAYLOAD_KEYS = (
    "container",
    "containerBitDepth",
    "profileIndicatesTenBit",
    "quantizedBits",
    "boundary",
    "distinctCodes",
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
    """Reject eight-bit samples packed as Main10. Depth metadata is not fidelity."""
    container, depth, profile, quantized, boundary, codes = _payload(payload)
    preserved = [
        container,
        f"boundary:{boundary}",
        f"container-bits:{depth}",
        f"quantized:{quantized}",
        "profile-ten-bit:" + ("true" if profile else "false"),
        f"codes:{codes}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [f"boundary {boundary} was recorded and not promoted by the container"]
    metadata_claims_ten = depth == 10 or profile
    eight_bit_population = quantized == 8 or codes <= 256
    if eight_bit_population:
        decision = "rejected"
        if quantized == 8:
            rejected.append("eight-bit-quantized")
        if codes <= 256:
            rejected.append("code-population-is-eight-bit")
        if metadata_claims_ten:
            rejected.append("metadata-is-not-fidelity")
            reasons.append(NEGATIVE)
        reasons.append("useful precision qualification failed")
    else:
        decision = "precision_withheld"
        reasons.append("a ten-bit container and profile indication are not ten-bit image fidelity")
        questions.append("useful precision remains unqualified")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    container = payload["container"]
    if container != "Main10":
        raise ValueError("container must be Main10")
    depth = payload["containerBitDepth"]
    quantized = payload["quantizedBits"]
    if type(depth) is not int or depth not in {8, 10}:
        raise ValueError("containerBitDepth must be 8 or 10")
    if type(quantized) is not int or quantized not in {8, 10}:
        raise ValueError("quantizedBits must be 8 or 10")
    profile = payload["profileIndicatesTenBit"]
    if type(profile) is not bool:
        raise ValueError("profileIndicatesTenBit must be a bool")
    boundary = payload["boundary"]
    if boundary not in _BOUNDARIES:
        raise ValueError("boundary is unsupported")
    codes = payload["distinctCodes"]
    if type(codes) is not int or codes < 1:
        raise ValueError("distinctCodes must be a positive int")
    return container, depth, profile, quantized, boundary, codes


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P058-02 must not yield qualified or allowed")
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
