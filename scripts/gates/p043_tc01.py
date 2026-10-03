"""TC-P043-01 neutral target invalidity.

Intervention: Replace the approved neutral patch with a clipped, textured,
specular, or incorrectly identified region.
Expected: Reject scale calibration or retain an explicitly provisional result
rather than fabricating a measured profile.
Negative: Whole-image average brightness cannot substitute for a known neutral
target.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P043-01"
INTERVENTION = (
    "Replace the approved neutral patch with a clipped, textured, specular, "
    "or incorrectly identified region."
)
EXPECTED = (
    "Reject scale calibration or retain an explicitly provisional result rather "
    "than fabricating a measured profile."
)
NEGATIVE = "Whole-image average brightness cannot substitute for a known neutral target."

_DEFECTS = (
    "none",
    "clipped",
    "textured",
    "specular",
    "misidentified",
    "dark",
    "colored",
    "mixed",
    "partial-clip",
)
_PROVISIONAL = {"textured", "dark", "colored", "mixed"}
_REJECTED = {"clipped", "specular", "misidentified", "partial-clip"}
_PAYLOAD_KEYS = (
    "patchId",
    "defect",
    "approvedNeutral",
    "wholeImageAverage",
    "useAverageAsNeutral",
    "claimMeasuredProfile",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "provisional", "neutral_recorded", "withheld")
_FORBIDDEN = {"qualified", "allowed"}
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Reject a fake neutral. Keep the patch id and the unused average."""
    patch, defect, approved, average, use_average, claim_measured = _payload(payload)
    preserved = [f"patch:{patch}", f"defect:{defect}", f"average:{average}"]
    rejected: list[str] = []
    questions = ["average brightness is not a neutral target"]
    if use_average:
        rejected.append("whole-image-average")
        if defect != "none":
            rejected.append(f"defect:{defect}")
        if claim_measured:
            rejected.append("fabricated-measured-profile")
        reasons = [NEGATIVE, EXPECTED, "scale calibration rejected"]
        decision = "rejected"
    elif defect != "none" and claim_measured:
        decision = "rejected"
        rejected.extend([f"defect:{defect}", "fabricated-measured-profile"])
        reasons = [EXPECTED, "a defective patch cannot become a measured profile"]
    elif defect in _REJECTED:
        decision = "rejected"
        rejected.append(f"defect:{defect}")
        reasons = [EXPECTED, "scale calibration rejected"]
    elif defect in _PROVISIONAL:
        decision = "provisional"
        rejected.append(f"defect:{defect}")
        reasons = [EXPECTED, "provisional result is not a measured profile"]
        questions.append(f"provisional:{defect}")
    elif defect == "none" and approved and not claim_measured:
        decision = "neutral_recorded"
        reasons = ["approved neutral patch recorded", "this record is not a measured S23 profile"]
        questions.append("neutral record is not physical qualification")
    else:
        decision = "withheld"
        reasons = [EXPECTED, "neutral scale was not fabricated"]
        questions.append("approved neutral patch missing")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, bool, str, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    patch = payload["patchId"]
    if not isinstance(patch, str) or not patch or patch != patch.strip():
        raise ValueError("patchId must be a non-empty string")
    defect = payload["defect"]
    if defect not in _DEFECTS:
        raise ValueError("defect is not a known neutral defect")
    approved = _bool(payload["approvedNeutral"], "approvedNeutral")
    average = payload["wholeImageAverage"]
    if not isinstance(average, str) or _DECIMAL.fullmatch(average) is None:
        raise ValueError("wholeImageAverage must be a canonical decimal string")
    use_average = _bool(payload["useAverageAsNeutral"], "useAverageAsNeutral")
    claim = _bool(payload["claimMeasuredProfile"], "claimMeasuredProfile")
    return patch, defect, approved, average, use_average, claim


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("neutral decision cannot be qualified or allowed")
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
