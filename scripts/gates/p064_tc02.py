"""TC-P064-02 eight-bit data in ten-bit storage.

Intervention: Quantize the source or intermediate to eight bits before packing
into a Main10 output.
Expected: Fail useful precision qualification despite the ten-bit container
and profile indication.
Negative: Bitstream depth metadata alone must not establish ten-bit image fidelity.
"""

from __future__ import annotations


CASE_ID = "TC-P064-02"
INTERVENTION = "Quantize the source or intermediate to eight bits before packing into a Main10 output."
EXPECTED = "Fail useful precision qualification despite the ten-bit container and profile indication."
NEGATIVE = "Bitstream depth metadata alone must not establish ten-bit image fidelity."
REPEAT = "Repeat at camera input, GPU texture, bitmap conversion, and codec input boundaries."

_BOUNDARIES = ("camera-input", "gpu-texture", "bitmap-conversion", "codec-input")
_PAYLOAD_KEYS = (
    "boundary",
    "quantizedToEight",
    "container",
    "containerBitDepth",
    "profileIndicatesTenBit",
    "bitstreamDepthMetadata",
    "usefulPrecisionEvidence",
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
    """Reject eight-bit samples packed as Main10 and metadata-only depth claims."""
    (
        boundary,
        quantized,
        container,
        depth,
        profile,
        bitstream,
        evidence,
    ) = _payload(payload)
    preserved = [
        f"boundary:{boundary}",
        f"container:{container}",
        f"container-bits:{depth}",
        f"profile-ten-bit:{_flag(profile)}",
        f"bitstream-depth:{bitstream}",
        f"quantized-eight:{_flag(quantized)}",
        f"useful-precision:{_flag(evidence)}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [REPEAT, f"boundary {boundary} kept in the inventory"]
    rejected: list[str] = []
    effective = evidence and not quantized
    if quantized:
        rejected.append("eight-bit-before-main10")
        reasons.append("eight-bit quantization before Main10 fails useful precision")
        if profile:
            reasons.append("profile indication does not restore useful precision")
    if bitstream == 10 and not effective:
        rejected.append("bitstream-depth-not-fidelity")
        reasons.append(NEGATIVE)
    if depth != 10:
        rejected.append("container-not-ten-bit")
        reasons.append("container depth is not ten-bit storage")
    if bitstream != depth:
        rejected.append("bitstream-container-disagreement")
        reasons.append("bitstream depth metadata disagrees with the container depth")
    if rejected:
        decision = "rejected"
        reasons.append("ten-bit container and profile do not qualify image fidelity")
    else:
        decision = "withheld"
        reasons.append("useful precision evidence recorded; this host fixture does not qualify ten-bit fidelity")
        questions.append("withheld precision evidence is not ten-bit fidelity")
    return _result(decision, reasons, rejected, preserved, questions)


def _flag(value: bool) -> str:
    return "true" if value else "false"


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    boundary = payload["boundary"]
    if boundary not in _BOUNDARIES:
        raise ValueError("boundary is unsupported")
    quantized = payload["quantizedToEight"]
    if type(quantized) is not bool:
        raise ValueError("quantizedToEight must be a bool")
    container = payload["container"]
    if container != "Main10":
        raise ValueError("container must be Main10")
    depth = payload["containerBitDepth"]
    if type(depth) is not int or depth not in {8, 10}:
        raise ValueError("containerBitDepth must be 8 or 10")
    profile = payload["profileIndicatesTenBit"]
    if type(profile) is not bool:
        raise ValueError("profileIndicatesTenBit must be a bool")
    bitstream = payload["bitstreamDepthMetadata"]
    if type(bitstream) is not int or bitstream not in {8, 10}:
        raise ValueError("bitstreamDepthMetadata must be 8 or 10")
    evidence = payload["usefulPrecisionEvidence"]
    if type(evidence) is not bool:
        raise ValueError("usefulPrecisionEvidence must be a bool")
    return boundary, quantized, container, depth, profile, bitstream, evidence


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P064-02 must not yield qualified or allowed")
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
