"""TC-P063-03 range and matrix contradiction.

A sidecar that disagrees with the stream on range or transfer is rejected.
Rec.709 YUV coefficients do not imply Rec.709 RGB primaries. This host case
does not qualify a physical S23.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P063-03"
INTERVENTION = "Provide a sidecar and stream whose range, YUV matrix, transfer, or RGB gamut disagree."
EXPECTED = "Reject contradictory accepted metadata and require a documented interoperable interpretation."
NEGATIVE = "Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically."
REPEAT = "Repeat with full/video level confusion and an incorrect HLG transfer tag."

_RANGES = ("full", "video")
_MATRICES = ("BT.709", "BT.2020")
_PRIMARIES = ("Rec.709", "Rec.2020", "AWG3")
_TRANSFERS = ("LogC3", "HLG", "Rec.709")
_IMPLIED = {"BT.709": "Rec.709", "BT.2020": "Rec.2020"}
_PAYLOAD_KEYS = (
    "streamId",
    "streamRange",
    "sidecarRange",
    "yuvMatrix",
    "declaredPrimaries",
    "streamTransfer",
    "sidecarTransfer",
    "primariesFromYuv",
    "interpretationDocumented",
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
    """Reject contradictory metadata and a YUV-to-primaries implication."""
    (
        stream_id,
        stream_range,
        sidecar_range,
        matrix,
        primaries,
        stream_transfer,
        sidecar_transfer,
        from_yuv,
        documented,
    ) = _payload(payload)
    preserved = [
        stream_id,
        f"stream-range:{stream_range}",
        f"sidecar-range:{sidecar_range}",
        f"yuv:{matrix}",
        f"primaries:{primaries}",
        f"stream-transfer:{stream_transfer}",
        f"sidecar-transfer:{sidecar_transfer}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}"]
    rejected: list[str] = []
    if stream_range != sidecar_range or stream_transfer != sidecar_transfer:
        rejected.append("contradictory-metadata")
        reasons.append("sidecar and stream disagree")
    if from_yuv:
        rejected.append("yuv-implies-primaries")
        reasons.append(NEGATIVE)
        reasons.append(f"{matrix} coefficients do not imply { _IMPLIED[matrix] } primaries")
    if rejected:
        decision = "rejected"
        if documented:
            questions.append("documented interpretation was recorded; contradictory metadata stays rejected")
        else:
            questions.append("a documented interoperable interpretation is required")
    else:
        decision = "withheld"
        reasons.append("consistent metadata is not interoperability and not qualification")
        if primaries == _IMPLIED[matrix]:
            reasons.append(f"{primaries} primaries were declared independently of {matrix}")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    stream_id = payload["streamId"]
    if not isinstance(stream_id, str) or _TOKEN.fullmatch(stream_id) is None:
        raise ValueError("streamId must be a token")
    stream_range = payload["streamRange"]
    sidecar_range = payload["sidecarRange"]
    if stream_range not in _RANGES or sidecar_range not in _RANGES:
        raise ValueError("range must be full or video")
    matrix = payload["yuvMatrix"]
    if matrix not in _MATRICES:
        raise ValueError("yuvMatrix is unsupported")
    primaries = payload["declaredPrimaries"]
    if primaries not in _PRIMARIES:
        raise ValueError("declaredPrimaries is unsupported")
    stream_transfer = payload["streamTransfer"]
    sidecar_transfer = payload["sidecarTransfer"]
    if stream_transfer not in _TRANSFERS or sidecar_transfer not in _TRANSFERS:
        raise ValueError("transfer is unsupported")
    from_yuv = payload["primariesFromYuv"]
    documented = payload["interpretationDocumented"]
    if type(from_yuv) is not bool or type(documented) is not bool:
        raise ValueError("primariesFromYuv and interpretationDocumented must be bools")
    return (
        stream_id,
        stream_range,
        sidecar_range,
        matrix,
        primaries,
        stream_transfer,
        sidecar_transfer,
        from_yuv,
        documented,
    )


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P063-03 must not yield qualified or allowed")
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
