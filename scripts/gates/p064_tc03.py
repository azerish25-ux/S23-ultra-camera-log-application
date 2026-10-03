"""TC-P064-03 range and matrix contradiction.

Intervention: Provide a sidecar and stream whose range, YUV matrix, transfer,
or RGB gamut disagree.
Expected: Reject contradictory accepted metadata and require a documented
interoperable interpretation.
Negative: Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically.
"""

from __future__ import annotations


CASE_ID = "TC-P064-03"
INTERVENTION = (
    "Provide a sidecar and stream whose range, YUV matrix, transfer, or RGB gamut disagree."
)
EXPECTED = "Reject contradictory accepted metadata and require a documented interoperable interpretation."
NEGATIVE = "Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically."
REPEAT = "Repeat with full/video level confusion and an incorrect HLG transfer tag."

_RANGES = ("full", "video")
_MATRICES = ("BT.709", "BT.2020")
_TRANSFERS = ("Rec.709", "HLG", "LogC3")
_GAMUTS = ("Rec.709", "Rec.2020", "AWG3")
_PAIRS = (
    ("streamRange", "sidecarRange", "range-contradiction", _RANGES),
    ("streamMatrix", "sidecarMatrix", "matrix-contradiction", _MATRICES),
    ("streamTransfer", "sidecarTransfer", "transfer-contradiction", _TRANSFERS),
    ("streamGamut", "sidecarGamut", "gamut-contradiction", _GAMUTS),
)
_PAYLOAD_KEYS = (
    "streamRange",
    "sidecarRange",
    "streamMatrix",
    "sidecarMatrix",
    "streamTransfer",
    "sidecarTransfer",
    "streamGamut",
    "sidecarGamut",
    "impliedPrimariesFromYuv",
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
    """Reject contradictory metadata and refuse to infer RGB primaries from YUV."""
    fields, implied, documented = _payload(payload)
    preserved = [f"{key}:{value}" for key, value in fields.items()]
    preserved.append(f"implied-primaries:{_flag(implied)}")
    preserved.append(f"documented-interpretation:{_flag(documented)}")
    reasons = [EXPECTED, INTERVENTION]
    questions = [REPEAT]
    rejected: list[str] = []
    for left, right, claim, _allowed in _PAIRS:
        if fields[left] != fields[right]:
            rejected.append(claim)
            reasons.append(f"{left} {fields[left]} disagrees with {right} {fields[right]}")
    if implied:
        claim = "rec709-yuv-not-rgb-primaries" if fields["streamMatrix"] == "BT.709" else "yuv-not-rgb-primaries"
        rejected.append(claim)
        reasons.append(NEGATIVE)
        questions.append("YUV coefficients were not copied onto RGB primaries")
    contradictory = any(
        item in rejected
        for item in ("range-contradiction", "matrix-contradiction", "transfer-contradiction", "gamut-contradiction")
    )
    if implied:
        decision = "rejected"
        reasons.append("implied primaries are not a documented interpretation")
    elif contradictory and documented:
        decision = "interpretation_required"
        reasons.append("contradictory metadata stays rejected; interpretation is not accepted metadata")
        questions.append("documented interoperable interpretation required")
    elif contradictory:
        decision = "rejected"
        questions.append("documented interoperable interpretation required")
        reasons.append("contradictory accepted metadata rejected")
    else:
        decision = "withheld"
        reasons.append("stream and sidecar agree in this host fixture and are not a qualification")
        questions.append("agreement is not physical interoperability")
    return _result(decision, reasons, rejected, preserved, questions)


def _flag(value: bool) -> str:
    return "true" if value else "false"


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    fields = {}
    allowed = {left: choices for left, _right, _claim, choices in _PAIRS}
    allowed.update({right: choices for _left, right, _claim, choices in _PAIRS})
    for key in (
        "streamRange",
        "sidecarRange",
        "streamMatrix",
        "sidecarMatrix",
        "streamTransfer",
        "sidecarTransfer",
        "streamGamut",
        "sidecarGamut",
    ):
        value = payload[key]
        if value not in allowed[key]:
            raise ValueError(key + " is unsupported")
        fields[key] = value
    implied = payload["impliedPrimariesFromYuv"]
    documented = payload["documentedInterpretation"]
    if type(implied) is not bool:
        raise ValueError("impliedPrimariesFromYuv must be a bool")
    if type(documented) is not bool:
        raise ValueError("documentedInterpretation must be a bool")
    return fields, implied, documented


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P064-03 must not yield qualified or allowed")
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
