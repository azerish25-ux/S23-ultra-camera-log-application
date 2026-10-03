"""TC-P060-02 eight-bit data in ten-bit storage.

Intervention: Quantize the source or intermediate to eight bits before packing
into a Main10 output.
Expected: Fail useful precision qualification despite the ten-bit container
and profile indication.
Negative: Bitstream depth metadata alone must not establish ten-bit image fidelity.
"""

from __future__ import annotations


CASE_ID = "TC-P060-02"
INTERVENTION = "Quantize the source or intermediate to eight bits before packing into a Main10 output."
EXPECTED = "Fail useful precision qualification despite the ten-bit container and profile indication."
NEGATIVE = "Bitstream depth metadata alone must not establish ten-bit image fidelity."
REPEAT = "Repeat at camera input, GPU texture, bitmap conversion, and codec input boundaries."

_BOUNDARIES = ("camera-input", "gpu-texture", "bitmap-conversion", "codec-input")
_CONTAINERS = ("Main10", "Main")
_PROFILES = ("Main10", "Main")
_DEPTHS = ("8", "10")
_QUANT = ("eight-bit", "ten-bit")
_PAYLOAD_KEYS = (
    "boundary",
    "container",
    "profile",
    "spsBitDepth",
    "sourceQuantization",
    "depthMetadataOnly",
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
    """Reject eight-bit quantization and SPS-depth-only ten-bit claims."""
    boundary, container, profile, depth, quantization, metadata_only, code = _payload(payload)
    stored = (code >> 2) << 2 if quantization == "eight-bit" else code
    preserved = [
        f"boundary:{boundary}",
        f"container:{container}",
        f"profile:{profile}",
        f"sps:{depth}",
        f"quantization:{quantization}",
        f"code:{code}",
        f"stored:{stored}",
    ]
    reasons = [EXPECTED, INTERVENTION, f"boundary {boundary} stored {stored} from {code}"]
    rejected: list[str] = []
    questions = [f"repeat coverage includes {REPEAT}"]
    if metadata_only:
        rejected.append("bitstream-depth-metadata")
        reasons.append(NEGATIVE)
        decision = "rejected"
    elif quantization == "eight-bit":
        rejected.append("eight-bit-quantized")
        reasons.append("eight-bit quantization expanded into a ten-bit container failed precision")
        if depth == "10" and container == "Main10":
            reasons.append(NEGATIVE)
        decision = "precision_failed"
    else:
        decision = "withheld"
        reasons.append("a ten-bit code on this host fixture is not ten-bit image fidelity")
        questions.append("SPS depth was not accepted as fidelity")
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
    if container not in _CONTAINERS:
        raise ValueError("container is unsupported")
    profile = payload["profile"]
    if profile not in _PROFILES:
        raise ValueError("profile is unsupported")
    depth = payload["spsBitDepth"]
    if depth not in _DEPTHS:
        raise ValueError("spsBitDepth must be 8 or 10")
    quantization = payload["sourceQuantization"]
    if quantization not in _QUANT:
        raise ValueError("sourceQuantization is unsupported")
    metadata_only = payload["depthMetadataOnly"]
    if type(metadata_only) is not bool:
        raise ValueError("depthMetadataOnly must be a bool")
    code_text = payload["code"]
    if not isinstance(code_text, str) or not code_text.isdigit() or (len(code_text) > 1 and code_text[0] == "0"):
        raise ValueError("code must be a canonical integer string")
    code = int(code_text)
    if not 0 <= code <= 1023:
        raise ValueError("code out of ten-bit range")
    return boundary, container, profile, depth, quantization, metadata_only, code


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P060-02 must not yield qualified or allowed")
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
