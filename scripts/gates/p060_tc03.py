"""TC-P060-03 range and matrix contradiction.

Intervention: Provide a sidecar and stream whose range, YUV matrix, transfer,
or RGB gamut disagree.
Expected: Reject contradictory accepted metadata and require a documented
interoperable interpretation.
Negative: Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P060-03"
INTERVENTION = (
    "Provide a sidecar and stream whose range, YUV matrix, transfer, or RGB gamut disagree."
)
EXPECTED = "Reject contradictory accepted metadata and require a documented interoperable interpretation."
NEGATIVE = "Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically."
REPEAT = "Repeat with full/video level confusion and an incorrect HLG transfer tag."

_RANGES = ("limited", "full")
_MATRICES = ("bt709", "bt2020", "identity")
_TRANSFERS = ("bt709", "hlg", "pq", "logc3")
_GAMUTS = ("bt709", "bt2020", "p3")
_TOKEN = re.compile(r"^[a-z0-9-]{1,40}$")
_PAYLOAD_KEYS = (
    "sidecarRange",
    "streamRange",
    "sidecarMatrix",
    "streamMatrix",
    "sidecarTransfer",
    "streamTransfer",
    "sidecarGamut",
    "streamGamut",
    "inferPrimariesFromYuv",
    "documentedInterpretation",
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
    """Reject contradictory metadata and YUV-to-primary inference."""
    fields = _payload(payload)
    conflicts: list[str] = []
    for name, side, stream in (
        ("range", fields["sidecarRange"], fields["streamRange"]),
        ("matrix", fields["sidecarMatrix"], fields["streamMatrix"]),
        ("transfer", fields["sidecarTransfer"], fields["streamTransfer"]),
        ("gamut", fields["sidecarGamut"], fields["streamGamut"]),
    ):
        if side != stream:
            conflicts.append(name)
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = [f"repeat coverage includes {REPEAT}"]
    if conflicts:
        rejected.append("contradictory-metadata")
        reasons.append("sidecar and stream disagree on " + ",".join(conflicts))
    if fields["inferPrimariesFromYuv"]:
        rejected.append("yuv-does-not-imply-primaries")
        reasons.append(NEGATIVE)
        if fields["sidecarMatrix"] == "bt709":
            reasons.append("Rec.709 YUV coefficients were not treated as Rec.709 RGB primaries")
    interpretation = fields["documentedInterpretation"]
    if rejected:
        decision = "rejected"
        if not interpretation:
            questions.append("a documented interoperable interpretation is still required")
    elif not interpretation:
        decision = "withheld"
        questions.append("a documented interoperable interpretation is required")
        reasons.append("consistent tags still need a documented interpretation")
    else:
        decision = "interpretation_recorded"
        reasons.append(f"documented interpretation {interpretation} was recorded and is not qualification")
    preserved = [
        f"range:{fields['sidecarRange']}|{fields['streamRange']}",
        f"matrix:{fields['sidecarMatrix']}|{fields['streamMatrix']}",
        f"transfer:{fields['sidecarTransfer']}|{fields['streamTransfer']}",
        f"gamut:{fields['sidecarGamut']}|{fields['streamGamut']}",
        f"infer:{'yes' if fields['inferPrimariesFromYuv'] else 'no'}",
        f"interpretation:{interpretation or 'missing'}",
        f"conflicts:{','.join(conflicts) if conflicts else 'none'}",
    ]
    return _result(decision, reasons, rejected, preserved, questions)


def _choice(value: object, allowed: tuple[str, ...], name: str) -> str:
    if value not in allowed:
        raise ValueError(f"{name} is unsupported")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    interpretation = payload["documentedInterpretation"]
    if interpretation != "" and (not isinstance(interpretation, str) or _TOKEN.fullmatch(interpretation) is None):
        raise ValueError("documentedInterpretation must be empty or a token")
    infer = payload["inferPrimariesFromYuv"]
    if type(infer) is not bool:
        raise ValueError("inferPrimariesFromYuv must be a bool")
    return {
        "sidecarRange": _choice(payload["sidecarRange"], _RANGES, "sidecarRange"),
        "streamRange": _choice(payload["streamRange"], _RANGES, "streamRange"),
        "sidecarMatrix": _choice(payload["sidecarMatrix"], _MATRICES, "sidecarMatrix"),
        "streamMatrix": _choice(payload["streamMatrix"], _MATRICES, "streamMatrix"),
        "sidecarTransfer": _choice(payload["sidecarTransfer"], _TRANSFERS, "sidecarTransfer"),
        "streamTransfer": _choice(payload["streamTransfer"], _TRANSFERS, "streamTransfer"),
        "sidecarGamut": _choice(payload["sidecarGamut"], _GAMUTS, "sidecarGamut"),
        "streamGamut": _choice(payload["streamGamut"], _GAMUTS, "streamGamut"),
        "inferPrimariesFromYuv": infer,
        "documentedInterpretation": interpretation,
    }


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P060-03 must not yield qualified or allowed")
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
