"""TC-P073-05 overfit reference image.

Intervention: Tune a stock interpretation to one attractive frame and evaluate it
on withheld exposure and scene conditions.
Expected: Report generalization failures rather than selecting only favorable comparisons.
Negative: A single successful still must not qualify a stock library.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P073-05"
INTERVENTION = (
    "Tune a stock interpretation to one attractive frame and evaluate it on withheld "
    "exposure and scene conditions."
)
EXPECTED = "Report generalization failures rather than selecting only favorable comparisons."
NEGATIVE = "A single successful still must not qualify a stock library."
REPEAT = "Repeat with skin, foliage, fabric, night lighting, and broad highlights."

_SUBJECTS = ("skin", "foliage", "fabric", "night", "highlights")
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")
_PAYLOAD_KEYS = (
    "subject",
    "tunedFrame",
    "withheldExposure",
    "withheldScene",
    "favorableOnly",
    "generalizationFailed",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld", "generalization_reported"}


def evaluate(payload: dict) -> dict:
    """Report held-out failures and refuse to qualify a library from one still."""
    subject, frame, withheld_exposure, withheld_scene, favorable, failed = _payload(payload)
    preserved = [
        f"subject:{subject}",
        frame,
        f"withheld-exposure:{str(withheld_exposure).lower()}",
        f"withheld-scene:{str(withheld_scene).lower()}",
        f"failed:{str(failed).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}", f"repeat site {subject}"]
    rejected: list[str] = []
    if favorable:
        rejected.append("favorable-only")
    if not failed and not (withheld_exposure and withheld_scene):
        rejected.append("single-still")
    if rejected:
        decision = "rejected"
        if "single-still" in rejected:
            reasons.append(NEGATIVE)
        if "favorable-only" in rejected:
            reasons.append("favorable comparisons were selected instead of reporting the full evaluation")
        reasons.append(f"{frame} remains in the inventory for {subject}")
    elif failed:
        decision = "generalization_reported"
        reasons.append(f"generalization failure on {subject} is reported for {frame}")
    else:
        decision = "withheld"
        reasons.append("held-out exposure and scene remain open; a stock library is not qualified")
        questions.append(NEGATIVE)
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    subject = payload["subject"]
    if subject not in _SUBJECTS:
        raise ValueError("subject is unsupported")
    frame = payload["tunedFrame"]
    if not isinstance(frame, str) or _TOKEN.fullmatch(frame) is None:
        raise ValueError("tunedFrame must be a token")
    flags = []
    for name in ("withheldExposure", "withheldScene", "favorableOnly", "generalizationFailed"):
        value = payload[name]
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
        flags.append(value)
    return subject, frame, flags[0], flags[1], flags[2], flags[3]


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in {"qualified", "allowed"}:
        raise ValueError("TC-P073-05 must not yield qualified or allowed")
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
