"""TC-P059-03 range and matrix contradiction.

Intervention: Provide a sidecar and stream whose range, YUV matrix, transfer,
or RGB gamut disagree.
Expected: Reject contradictory accepted metadata and require a documented
interoperable interpretation.
Negative: Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically.
"""

from __future__ import annotations


CASE_ID = "TC-P059-03"
INTERVENTION = (
    "Provide a sidecar and stream whose range, YUV matrix, transfer, or RGB gamut disagree."
)
EXPECTED = (
    "Reject contradictory accepted metadata and require a documented interoperable interpretation."
)
NEGATIVE = "Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically."

_RANGES = ("full", "video")
_MATRICES = ("bt709", "bt2020")
_GAMUTS = ("bt709", "bt2020", "unspecified")
_TRANSFERS = ("bt709", "hlg", "pq")
_REPEATS = ("none", "full-video", "incorrect-hlg")
_INTERPS = ("documented", "missing")
_PAYLOAD_KEYS = (
    "rangeSidecar",
    "rangeStream",
    "yuvMatrix",
    "rgbGamut",
    "transferSidecar",
    "transferStream",
    "inferRgbFromYuv",
    "interpretation",
    "repeat",
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
    """Reject contradictory color metadata and any automatic YUV-to-RGB implication."""
    (
        range_sidecar,
        range_stream,
        matrix,
        gamut,
        transfer_sidecar,
        transfer_stream,
        infer,
        interpretation,
        repeat,
    ) = _payload(payload)
    preserved = [
        "range-sidecar:" + range_sidecar,
        "range-stream:" + range_stream,
        "yuv-matrix:" + matrix,
        "rgb-gamut:" + gamut,
        "transfer-sidecar:" + transfer_sidecar,
        "transfer-stream:" + transfer_stream,
        "interpretation:" + interpretation,
        "repeat:" + repeat,
    ]
    rejected: list[str] = []
    if range_sidecar != range_stream:
        rejected.append("range-contradiction")
    if transfer_sidecar != transfer_stream:
        rejected.append("transfer-contradiction")
    if gamut != "unspecified" and gamut != matrix:
        rejected.append("matrix-gamut-contradiction")
    if infer:
        rejected.append("yuv-implies-rgb")
    if interpretation == "missing":
        rejected.append("interpretation-missing")
    reasons = [EXPECTED, INTERVENTION]
    if infer:
        reasons.append(NEGATIVE)
    if rejected:
        reasons.append("contradictory metadata was not accepted")
        return _result(
            "rejected",
            reasons,
            rejected,
            preserved,
            ["a documented interoperable interpretation is required"],
        )
    reasons.append("agreement was recorded and was not treated as automatic primaries")
    return _result(
        "withheld",
        reasons,
        [],
        preserved,
        ["documented agreement is not a physical color qualification"],
    )


def _payload(payload: object) -> tuple[str, str, str, str, str, str, bool, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    range_sidecar = payload["rangeSidecar"]
    range_stream = payload["rangeStream"]
    if range_sidecar not in _RANGES or range_stream not in _RANGES:
        raise ValueError("range must be full or video")
    matrix = payload["yuvMatrix"]
    if matrix not in _MATRICES:
        raise ValueError("yuvMatrix is unsupported")
    gamut = payload["rgbGamut"]
    if gamut not in _GAMUTS:
        raise ValueError("rgbGamut is unsupported")
    transfer_sidecar = payload["transferSidecar"]
    transfer_stream = payload["transferStream"]
    if transfer_sidecar not in _TRANSFERS or transfer_stream not in _TRANSFERS:
        raise ValueError("transfer is unsupported")
    infer = payload["inferRgbFromYuv"]
    if type(infer) is not bool:
        raise ValueError("inferRgbFromYuv must be a bool")
    interpretation = payload["interpretation"]
    if interpretation not in _INTERPS:
        raise ValueError("interpretation must be documented or missing")
    repeat = payload["repeat"]
    if repeat not in _REPEATS:
        raise ValueError("repeat is unsupported")
    return (
        range_sidecar,
        range_stream,
        matrix,
        gamut,
        transfer_sidecar,
        transfer_stream,
        infer,
        interpretation,
        repeat,
    )


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P059-03 must not yield qualified or allowed")
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
