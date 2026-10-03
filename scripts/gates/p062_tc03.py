"""TC-P062-03 range and matrix contradiction.

Intervention: Provide a sidecar and stream whose range, YUV matrix, transfer,
or RGB gamut disagree.
Expected: Reject contradictory accepted metadata and require a documented
interoperable interpretation.
Negative: Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P062-03"
INTERVENTION = "Provide a sidecar and stream whose range, YUV matrix, transfer, or RGB gamut disagree."
EXPECTED = "Reject contradictory accepted metadata and require a documented interoperable interpretation."
NEGATIVE = "Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically."
REPEAT = "Repeat with full/video level confusion and an incorrect HLG transfer tag."

_RANGES = ("full", "video")
_MATRICES = ("bt709", "bt2020", "identity")
_TRANSFERS = ("bt709", "hlg", "pq")
_GAMUTS = ("bt709", "bt2020", "display-p3")
_PAYLOAD_KEYS = (
    "sampleId",
    "sidecarRange",
    "streamRange",
    "sidecarMatrix",
    "streamMatrix",
    "sidecarTransfer",
    "streamTransfer",
    "sidecarGamut",
    "streamGamut",
    "yuvImpliesRgb",
    "interpretation",
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
_NOTE = re.compile(r"^[a-z0-9-]{0,64}$")


def evaluate(payload: dict) -> dict:
    """Reject contradictory metadata and Rec.709 YUV-to-RGB implication."""
    fields = _payload(payload)
    disagreements = [
        name
        for name, side, stream in (
            ("range", fields["sidecarRange"], fields["streamRange"]),
            ("matrix", fields["sidecarMatrix"], fields["streamMatrix"]),
            ("transfer", fields["sidecarTransfer"], fields["streamTransfer"]),
            ("gamut", fields["sidecarGamut"], fields["streamGamut"]),
        )
        if side != stream
    ]
    preserved = [
        fields["sampleId"],
        f"range:{fields['sidecarRange']}/{fields['streamRange']}",
        f"matrix:{fields['sidecarMatrix']}/{fields['streamMatrix']}",
        f"transfer:{fields['sidecarTransfer']}/{fields['streamTransfer']}",
        f"gamut:{fields['sidecarGamut']}/{fields['streamGamut']}",
        f"interpretation:{fields['interpretation'] or 'missing'}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [REPEAT]
    if disagreements:
        rejected.append("contradictory-metadata")
        reasons.append("sidecar and stream disagree on " + ", ".join(disagreements))
        reasons.append("a written interpretation does not repair contradictory metadata")
    if fields["yuvImpliesRgb"]:
        rejected.append("rec709-yuv-implies-rgb")
        reasons.append(NEGATIVE)
    if rejected:
        decision = "rejected"
        if not fields["interpretation"]:
            questions.append("documented interoperable interpretation is still required")
    elif not fields["interpretation"]:
        decision = "withheld"
        reasons.append("consistent tags still need a documented interoperable interpretation")
        questions.append("documented interoperable interpretation is missing")
    else:
        decision = "interpretation_documented"
        reasons.append("consistent tags keep interpretation " + fields["interpretation"])
        reasons.append("consistent metadata is not a qualified color pipeline")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    sample = payload["sampleId"]
    if not isinstance(sample, str) or _TOKEN.fullmatch(sample) is None:
        raise ValueError("sampleId must be a token")
    _choice(payload["sidecarRange"], _RANGES, "sidecarRange")
    _choice(payload["streamRange"], _RANGES, "streamRange")
    _choice(payload["sidecarMatrix"], _MATRICES, "sidecarMatrix")
    _choice(payload["streamMatrix"], _MATRICES, "streamMatrix")
    _choice(payload["sidecarTransfer"], _TRANSFERS, "sidecarTransfer")
    _choice(payload["streamTransfer"], _TRANSFERS, "streamTransfer")
    _choice(payload["sidecarGamut"], _GAMUTS, "sidecarGamut")
    _choice(payload["streamGamut"], _GAMUTS, "streamGamut")
    if type(payload["yuvImpliesRgb"]) is not bool:
        raise ValueError("yuvImpliesRgb must be a bool")
    note = payload["interpretation"]
    if not isinstance(note, str) or _NOTE.fullmatch(note) is None:
        raise ValueError("interpretation must be empty or a token")
    return payload


def _choice(value: object, allowed: tuple[str, ...], name: str) -> None:
    if value not in allowed:
        raise ValueError(name + " is unsupported")


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P062-03 must not yield qualified or allowed")
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
