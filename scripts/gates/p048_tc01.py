"""TC-P048-01 neutral target invalidity.

Intervention: Replace the approved neutral patch with a clipped, textured,
specular, or incorrectly identified region.
Expected: Reject scale calibration or retain an explicitly provisional result
rather than fabricating a measured profile.
Negative: Whole-image average brightness cannot substitute for a known neutral
target.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P048-01"
INTERVENTION = (
    "Replace the approved neutral patch with a clipped, textured, specular, or "
    "incorrectly identified region."
)
EXPECTED = (
    "Reject scale calibration or retain an explicitly provisional result rather than "
    "fabricating a measured profile."
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
    "partial_clip",
)
_PAYLOAD_KEYS = ("patchId", "defect", "wholeFrameMean", "knownNeutral", "substituteMean")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "provisional")
_FORBIDDEN = {"qualified", "allowed"}
_MEAN = re.compile(r"[1-9][0-9]*")


def evaluate(payload: dict) -> dict:
    """Reject an invalid neutral stand-in. Never substitute the frame mean."""
    patch_id, defect, mean, known, substitute = _payload(payload)
    preserved = [
        f"patch:{patch_id}",
        f"defect:{defect}",
        f"whole-frame-mean:{mean}",
        f"known-neutral:{str(known).lower()}",
    ]
    reasons = [EXPECTED]
    if substitute:
        decision = "rejected"
        rejected = ["whole-frame-mean-substitution"]
        reasons.append(NEGATIVE)
        questions = ["whole-image average cannot replace a known neutral target"]
    elif defect != "none" or not known:
        decision = "rejected"
        label = defect if defect != "none" else "unknown-neutral"
        rejected = [f"invalid-neutral:{label}"]
        reasons.append("scale calibration rejected rather than fabricating a measured profile")
        questions = [f"neutral target invalid:{label}"]
    else:
        decision = "provisional"
        rejected = []
        reasons.append("explicitly provisional; not a measured profile")
        questions = ["provisional scale is not a confident measurement"]
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    patch_id = payload["patchId"]
    if not isinstance(patch_id, str) or not patch_id or patch_id != patch_id.strip():
        raise ValueError("patchId must be a non-empty string")
    defect = payload["defect"]
    if defect not in _DEFECTS:
        raise ValueError("defect is unknown")
    mean = payload["wholeFrameMean"]
    if not isinstance(mean, str) or _MEAN.fullmatch(mean) is None:
        raise ValueError("wholeFrameMean must be a canonical positive integer string")
    known = payload["knownNeutral"]
    substitute = payload["substituteMean"]
    if type(known) is not bool or type(substitute) is not bool:
        raise ValueError("knownNeutral and substituteMean must be bools")
    return patch_id, defect, mean, known, substitute


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("neutral-target decision cannot be qualified or allowed")
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
