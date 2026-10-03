"""TC-P063-02 eight-bit data in ten-bit storage.

Quantizing to eight bits before a Main10 pack fails useful precision even
when the bitstream says ten-bit. Depth metadata alone is not image fidelity.
This host case does not qualify a physical S23.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P063-02"
INTERVENTION = "Quantize the source or intermediate to eight bits before packing into a Main10 output."
EXPECTED = "Fail useful precision qualification despite the ten-bit container and profile indication."
NEGATIVE = "Bitstream depth metadata alone must not establish ten-bit image fidelity."
REPEAT = "Repeat at camera input, GPU texture, bitmap conversion, and codec input boundaries."

_BOUNDARIES = ("camera-input", "gpu-texture", "bitmap-conversion", "codec-input")
_CONTAINERS = ("Main10", "Main")
_PROFILES = ("Main10", "Main")
_DEPTHS = ("8", "10")
_PAYLOAD_KEYS = (
    "sampleId",
    "boundary",
    "container",
    "profile",
    "bitstreamDepth",
    "quantizedToEight",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")


def evaluate(payload: dict) -> dict:
    """Fail eight-bit data packed as ten-bit, including a depth-metadata claim."""
    sample, boundary, container, profile, depth, quantized = _payload(payload)
    preserved = [
        sample,
        f"boundary:{boundary}",
        f"container:{container}",
        f"profile:{profile}",
        f"bitstream-depth:{depth}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}"]
    rejected: list[str] = []
    if quantized:
        rejected.append("eight-bit-quantized")
        rejected.append("bitstream-depth-not-fidelity")
        reasons.append(NEGATIVE)
        reasons.append(
            f"{container} profile {profile} with bitstream depth {depth} does not show useful precision"
        )
        questions.append(f"boundary {boundary} kept the eight-bit quantization in the inventory")
        decision = "precision_failed"
    else:
        decision = "withheld"
        reasons.append("absence of eight-bit quantization is not ten-bit fidelity qualification")
        questions.append("bitstream depth metadata was not treated as image fidelity")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    sample = payload["sampleId"]
    if not isinstance(sample, str) or _TOKEN.fullmatch(sample) is None:
        raise ValueError("sampleId must be a token")
    boundary = payload["boundary"]
    if boundary not in _BOUNDARIES:
        raise ValueError("boundary is unsupported")
    container = payload["container"]
    if container not in _CONTAINERS:
        raise ValueError("container is unsupported")
    profile = payload["profile"]
    if profile not in _PROFILES:
        raise ValueError("profile is unsupported")
    depth = payload["bitstreamDepth"]
    if depth not in _DEPTHS:
        raise ValueError("bitstreamDepth must be 8 or 10")
    quantized = payload["quantizedToEight"]
    if type(quantized) is not bool:
        raise ValueError("quantizedToEight must be a bool")
    return sample, boundary, container, profile, depth, quantized


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P063-02 must not yield qualified or allowed")
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
