"""TC-P058-03 range and matrix contradiction.

Intervention: Provide a sidecar and stream whose range, YUV matrix, transfer,
or RGB gamut disagree.
Expected: Reject contradictory accepted metadata and require a documented
interoperable interpretation.
Negative: Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically.
"""

from __future__ import annotations

CASE_ID = "TC-P058-03"
INTERVENTION = (
    "Provide a sidecar and stream whose range, YUV matrix, transfer, or RGB gamut disagree."
)
EXPECTED = "Reject contradictory accepted metadata and require a documented interoperable interpretation."
NEGATIVE = "Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically."

_RANGES = ("full", "video")
_MATRICES = ("BT.709", "BT.2020")
_PRIMARIES = ("Rec.709", "AWG3", "Rec.2020")
_TRANSFERS = ("LogC3", "HLG", "Rec.709")
_PAYLOAD_KEYS = (
    "streamRange",
    "sidecarRange",
    "streamYuv",
    "sidecarYuv",
    "streamPrimaries",
    "sidecarPrimaries",
    "streamTransfer",
    "sidecarTransfer",
    "impliedFromYuv",
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


def evaluate(payload: dict) -> dict:
    """Reject contradictory metadata. A YUV id does not imply RGB primaries."""
    (
        stream_range,
        sidecar_range,
        stream_yuv,
        sidecar_yuv,
        stream_primaries,
        sidecar_primaries,
        stream_transfer,
        sidecar_transfer,
        implied,
        documented,
    ) = _payload(payload)
    preserved = [
        f"stream-range:{stream_range}",
        f"sidecar-range:{sidecar_range}",
        f"stream-yuv:{stream_yuv}",
        f"sidecar-yuv:{sidecar_yuv}",
        f"stream-primaries:{stream_primaries}",
        f"sidecar-primaries:{sidecar_primaries}",
        f"stream-transfer:{stream_transfer}",
        f"sidecar-transfer:{sidecar_transfer}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions: list[str] = []
    if stream_range != sidecar_range:
        rejected.append("range-contradiction")
    if stream_yuv != sidecar_yuv:
        rejected.append("yuv-contradiction")
    if stream_primaries != sidecar_primaries:
        rejected.append("gamut-contradiction")
    if stream_transfer != sidecar_transfer:
        rejected.append("transfer-contradiction")
    if implied:
        rejected.append("yuv-implied-primaries")
        reasons.append(NEGATIVE)
    if rejected:
        decision = "rejected"
        reasons.append("contradictory metadata was not accepted")
        if not documented:
            questions.append("documented interoperable interpretation required")
        else:
            questions.append("documented interpretation does not accept the contradiction")
    elif not documented:
        decision = "withheld"
        questions.append("documented interoperable interpretation required")
        reasons.append("consistent fields still need a documented interpretation")
    else:
        decision = "interpretation_recorded"
        reasons.append("documented interpretation recorded; YUV coefficients were not treated as primaries")
        questions.append("recorded interpretation is not physical qualification")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    stream_range = payload["streamRange"]
    sidecar_range = payload["sidecarRange"]
    if stream_range not in _RANGES or sidecar_range not in _RANGES:
        raise ValueError("range must be full or video")
    stream_yuv = payload["streamYuv"]
    sidecar_yuv = payload["sidecarYuv"]
    if stream_yuv not in _MATRICES or sidecar_yuv not in _MATRICES:
        raise ValueError("YUV matrix is unsupported")
    stream_primaries = payload["streamPrimaries"]
    sidecar_primaries = payload["sidecarPrimaries"]
    if stream_primaries not in _PRIMARIES or sidecar_primaries not in _PRIMARIES:
        raise ValueError("primaries are unsupported")
    stream_transfer = payload["streamTransfer"]
    sidecar_transfer = payload["sidecarTransfer"]
    if stream_transfer not in _TRANSFERS or sidecar_transfer not in _TRANSFERS:
        raise ValueError("transfer is unsupported")
    implied = payload["impliedFromYuv"]
    documented = payload["interpretationDocumented"]
    if type(implied) is not bool or type(documented) is not bool:
        raise ValueError("flags must be bools")
    return (
        stream_range,
        sidecar_range,
        stream_yuv,
        sidecar_yuv,
        stream_primaries,
        sidecar_primaries,
        stream_transfer,
        sidecar_transfer,
        implied,
        documented,
    )


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P058-03 must not yield qualified or allowed")
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
