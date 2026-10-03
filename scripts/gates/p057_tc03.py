"""TC-P057-03 range and matrix contradiction.

Intervention: Provide a sidecar and stream whose range, YUV matrix, transfer,
or RGB gamut disagree.
Expected: Reject contradictory accepted metadata and require a documented
interoperable interpretation.
Negative: Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically.
"""

from __future__ import annotations


CASE_ID = "TC-P057-03"
INTERVENTION = (
    "Provide a sidecar and stream whose range, YUV matrix, transfer, or RGB gamut disagree."
)
EXPECTED = (
    "Reject contradictory accepted metadata and require a documented interoperable "
    "interpretation."
)
NEGATIVE = "Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically."

_RANGES = ("full", "video")
_MATRICES = ("rec709", "rec2020", "identity")
_PRIMARIES = ("rec709", "awg3", "rec2020")
_TRANSFERS = ("logc3", "hlg", "rec709")
_PAYLOAD_KEYS = (
    "sidecarRange",
    "streamRange",
    "yuvMatrix",
    "rgbPrimaries",
    "sidecarTransfer",
    "streamTransfer",
    "inferPrimariesFromYuv",
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
    """Reject contradictory metadata. YUV coefficients do not imply primaries."""
    fields = _payload(payload)
    preserved = [
        f"sidecar-range:{fields['sidecarRange']}",
        f"stream-range:{fields['streamRange']}",
        f"yuv:{fields['yuvMatrix']}",
        f"primaries:{fields['rgbPrimaries']}",
        f"sidecar-transfer:{fields['sidecarTransfer']}",
        f"stream-transfer:{fields['streamTransfer']}",
        f"infer-primaries:{str(fields['inferPrimariesFromYuv']).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = ["documented interoperable interpretation is still required"]
    rejected: list[str] = []
    if fields["sidecarRange"] != fields["streamRange"]:
        rejected.append("range-contradiction")
        reasons.append("full and video range tags disagree")
    if fields["sidecarTransfer"] != fields["streamTransfer"]:
        rejected.append("transfer-contradiction")
        reasons.append("sidecar and stream transfer tags disagree")
    if fields["yuvMatrix"] == "rec709" and fields["rgbPrimaries"] != "rec709":
        rejected.append("rec709-yuv-does-not-imply-rec709-rgb")
        reasons.append(NEGATIVE)
    if fields["inferPrimariesFromYuv"]:
        rejected.append("inferred-primaries")
        if NEGATIVE not in reasons:
            reasons.append(NEGATIVE)
        questions.append("YUV coefficients were not allowed to invent primaries")
    if rejected:
        return _result("rejected", reasons, rejected, preserved, questions)
    reasons.append("consistent tags were not treated as a qualified interpretation")
    questions.append("explicit agreement is not an automatic primaries implication")
    return _result("withheld", reasons, [], preserved, questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    if payload["sidecarRange"] not in _RANGES or payload["streamRange"] not in _RANGES:
        raise ValueError("range is unknown")
    if payload["yuvMatrix"] not in _MATRICES:
        raise ValueError("yuvMatrix is unknown")
    if payload["rgbPrimaries"] not in _PRIMARIES:
        raise ValueError("rgbPrimaries is unknown")
    if payload["sidecarTransfer"] not in _TRANSFERS or payload["streamTransfer"] not in _TRANSFERS:
        raise ValueError("transfer is unknown")
    if type(payload["inferPrimariesFromYuv"]) is not bool:
        raise ValueError("inferPrimariesFromYuv must be a bool")
    return payload


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
