"""TC-P061-03 range and matrix contradiction.

Intervention: Provide a sidecar and stream whose range, YUV matrix, transfer,
or RGB gamut disagree.
Expected: Reject contradictory accepted metadata and require a documented
interoperable interpretation.
Negative: Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P061-03"
INTERVENTION = (
    "Provide a sidecar and stream whose range, YUV matrix, transfer, or RGB gamut disagree."
)
EXPECTED = (
    "Reject contradictory accepted metadata and require a documented interoperable interpretation."
)
NEGATIVE = "Rec.709 YUV coefficients must not imply Rec.709 RGB primaries automatically."
REPEAT = "Repeat with full/video level confusion and an incorrect HLG transfer tag."

_RANGES = ("full", "video")
_MATRICES = ("BT.709", "BT.2020")
_TRANSFERS = ("HLG", "Rec.709", "PQ")
_GAMUTS = ("Rec.709", "Rec.2020")
_PAYLOAD_KEYS = (
    "sidecarRange",
    "streamRange",
    "sidecarMatrix",
    "streamMatrix",
    "sidecarTransfer",
    "streamTransfer",
    "sidecarGamut",
    "streamGamut",
    "documentedInterpretation",
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
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")


def evaluate(payload: dict) -> dict:
    """Reject contradictory sidecar and stream metadata. Do not infer primaries."""
    fields, documented, infer = _payload(payload)
    sidecar = (
        f"{fields['sidecarRange']}/{fields['sidecarMatrix']}/"
        f"{fields['sidecarTransfer']}/{fields['sidecarGamut']}"
    )
    stream = (
        f"{fields['streamRange']}/{fields['streamMatrix']}/"
        f"{fields['streamTransfer']}/{fields['streamGamut']}"
    )
    preserved = [
        f"sidecar:{sidecar}",
        f"stream:{stream}",
        f"interpretation:{documented or 'absent'}",
    ]
    reasons = [EXPECTED, INTERVENTION, f"repeat coverage includes {REPEAT}"]
    questions: list[str] = []
    rejected: list[str] = []
    disagree = any(
        fields[f"sidecar{name}"] != fields[f"stream{name}"]
        for name in ("Range", "Matrix", "Transfer", "Gamut")
    )
    if disagree:
        rejected.append("contradictory-metadata")
        reasons.append("sidecar and stream metadata disagree and were not accepted")
    if infer:
        rejected.append("yuv-not-rgb-primaries")
        reasons.append(NEGATIVE)
        if fields["streamMatrix"] == "BT.709":
            reasons.append("BT.709 YUV coefficients were not treated as Rec.709 RGB primaries")
    if disagree and not documented:
        questions.append("documented interoperable interpretation required")
        decision = "rejected"
    elif disagree and documented:
        questions.append("interpretation is bound to " + documented)
        reasons.append("contradictory metadata stays rejected; the sidecar document is not acceptance")
        decision = "interpretation_required"
    elif rejected:
        decision = "rejected"
    else:
        decision = "withheld"
        reasons.append("metadata agrees only where both sides state it; this is not qualification")
        questions.append("agreement is explicit and is not an implied primary")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    fields = {
        "sidecarRange": _choice(payload["sidecarRange"], _RANGES, "sidecarRange"),
        "streamRange": _choice(payload["streamRange"], _RANGES, "streamRange"),
        "sidecarMatrix": _choice(payload["sidecarMatrix"], _MATRICES, "sidecarMatrix"),
        "streamMatrix": _choice(payload["streamMatrix"], _MATRICES, "streamMatrix"),
        "sidecarTransfer": _choice(payload["sidecarTransfer"], _TRANSFERS, "sidecarTransfer"),
        "streamTransfer": _choice(payload["streamTransfer"], _TRANSFERS, "streamTransfer"),
        "sidecarGamut": _choice(payload["sidecarGamut"], _GAMUTS, "sidecarGamut"),
        "streamGamut": _choice(payload["streamGamut"], _GAMUTS, "streamGamut"),
    }
    documented = payload["documentedInterpretation"]
    if documented != "" and (not isinstance(documented, str) or _TOKEN.fullmatch(documented) is None):
        raise ValueError("documentedInterpretation must be empty or a token")
    infer = payload["inferPrimariesFromYuv"]
    if type(infer) is not bool:
        raise ValueError("inferPrimariesFromYuv must be a bool")
    return fields, documented, infer


def _choice(value: object, allowed: tuple[str, ...], label: str) -> str:
    if value not in allowed:
        raise ValueError(label + " is unsupported")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P061-03 must not yield qualified or allowed")
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
