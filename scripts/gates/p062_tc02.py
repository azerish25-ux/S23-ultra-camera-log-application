"""TC-P062-02 eight-bit data in ten-bit storage.

Intervention: Quantize the source or intermediate to eight bits before packing
into a Main10 output.
Expected: Fail useful precision qualification despite the ten-bit container
and profile indication.
Negative: Bitstream depth metadata alone must not establish ten-bit image fidelity.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P062-02"
INTERVENTION = "Quantize the source or intermediate to eight bits before packing into a Main10 output."
EXPECTED = "Fail useful precision qualification despite the ten-bit container and profile indication."
NEGATIVE = "Bitstream depth metadata alone must not establish ten-bit image fidelity."
REPEAT = "Repeat at camera input, GPU texture, bitmap conversion, and codec input boundaries."

_BOUNDARIES = ("camera-input", "gpu-texture", "bitmap-conversion", "codec-input")
_PAYLOAD_KEYS = (
    "sampleId",
    "boundary",
    "code",
    "quantizedToEight",
    "numericComparison",
    "container",
    "profile",
    "depthMetadata",
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
    """Reject eight-bit quantization and metadata-only ten-bit claims."""
    sample, boundary, code, quantized, compared, container, profile, depth = _payload(payload)
    stored = (code >> 2) << 2 if quantized else code
    preserved = [
        sample,
        f"boundary:{boundary}",
        f"source:{code}",
        f"stored:{stored}",
        f"container:{container}",
        f"profile:{profile}",
        f"depth-metadata:{depth}",
        "precision-qualified:no",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [REPEAT, "host case does not qualify ten-bit fidelity"]
    if quantized:
        rejected.append("eight-bit-before-pack")
        rejected.append("metadata-not-fidelity")
        reasons.append(NEGATIVE)
        reasons.append(f"source {code} was stored as eight-bit expansion {stored} in {container}")
        decision = "precision_failed"
    elif not compared:
        rejected.append("metadata-not-fidelity")
        reasons.append(NEGATIVE)
        reasons.append(f"{profile} depth metadata {depth} is not a numeric comparison")
        decision = "rejected"
    else:
        reasons.append("a numeric comparison was recorded and still does not qualify ten-bit fidelity")
        decision = "withheld"
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
    code = payload["code"]
    if type(code) is not int or isinstance(code, bool) or not 0 <= code <= 1023:
        raise ValueError("code must be an int from 0 through 1023")
    quantized = payload["quantizedToEight"]
    compared = payload["numericComparison"]
    if type(quantized) is not bool or type(compared) is not bool:
        raise ValueError("quantizedToEight and numericComparison must be bools")
    if payload["container"] != "Main10" or payload["profile"] != "Main10" or payload["depthMetadata"] != "10":
        raise ValueError("container, profile, and depth metadata must indicate Main10 ten-bit")
    return sample, boundary, code, quantized, compared, "Main10", "Main10", "10"


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P062-02 must not yield qualified or allowed")
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
