"""TC-P073-06 unrequested beautification.

Intervention: Enable face smoothing or geometry alteration as an invisible part of
a stock look.
Expected: Reject hidden content alteration and preserve source texture unless an
explicit optional adjustment is selected.
Negative: A flattering result must not hide unrequested facial processing.
"""

from __future__ import annotations


CASE_ID = "TC-P073-06"
INTERVENTION = "Enable face smoothing or geometry alteration as an invisible part of a stock look."
EXPECTED = (
    "Reject hidden content alteration and preserve source texture unless an explicit "
    "optional adjustment is selected."
)
NEGATIVE = "A flattering result must not hide unrequested facial processing."
REPEAT = "Repeat with multiple people, skin tones, profile views, and moving faces."

_SUBJECTS = ("people", "skin-tone", "profile-view", "moving-face")
_PAYLOAD_KEYS = (
    "subject",
    "faceSmoothing",
    "geometryAlteration",
    "explicitOptional",
    "flattering",
    "texturePreserved",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld", "optional_adjustment", "texture_preserved"}


def evaluate(payload: dict) -> dict:
    """Reject hidden facial processing and keep source texture unless it is explicit."""
    subject, smoothing, geometry, explicit, flattering, texture = _payload(payload)
    preserved = [
        f"subject:{subject}",
        f"texture:{str(texture).lower()}",
        f"explicit:{str(explicit).lower()}",
        f"flattering:{str(flattering).lower()}",
        f"smoothing:{str(smoothing).lower()}",
        f"geometry:{str(geometry).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}", f"repeat site {subject}"]
    altered = smoothing or geometry
    rejected: list[str] = []
    if altered and not explicit:
        rejected.append("hidden-alteration")
        if flattering:
            rejected.append("flattering-concealment")
            reasons.append(NEGATIVE)
        else:
            reasons.append(f"hidden alteration on {subject} is rejected")
        reasons.append("source texture stays in the inventory")
        decision = "rejected"
    elif altered and explicit:
        decision = "optional_adjustment"
        reasons.append(f"explicit optional adjustment on {subject} is recorded and is not a hidden stock look")
        if not texture:
            questions.append("source texture changed only because the optional adjustment was selected")
        questions.append("an optional adjustment is not a qualified or allowed stock behavior")
    elif not texture:
        decision = "rejected"
        rejected.append("texture-lost")
        reasons.append(f"source texture on {subject} was dropped without an explicit adjustment")
    else:
        decision = "texture_preserved"
        reasons.append(f"source texture on {subject} is preserved")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    subject = payload["subject"]
    if subject not in _SUBJECTS:
        raise ValueError("subject is unsupported")
    flags = []
    for name in ("faceSmoothing", "geometryAlteration", "explicitOptional", "flattering", "texturePreserved"):
        value = payload[name]
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
        flags.append(value)
    return subject, flags[0], flags[1], flags[2], flags[3], flags[4]


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in {"qualified", "allowed"}:
        raise ValueError("TC-P073-06 must not yield qualified or allowed")
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
