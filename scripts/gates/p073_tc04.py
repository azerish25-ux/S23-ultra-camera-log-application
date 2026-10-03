"""TC-P073-04 neutral and saturated stress.

Intervention: Render neutral steps beside extreme saturated lights under the same
stock profile.
Expected: Keep neutral behavior controlled and all outputs finite while documenting
unsupported spectral accuracy.
Negative: Unbounded cross-channel coupling or hidden per-face correction must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P073-04"
INTERVENTION = "Render neutral steps beside extreme saturated lights under the same stock profile."
EXPECTED = "Keep neutral behavior controlled and all outputs finite while documenting unsupported spectral accuracy."
NEGATIVE = "Unbounded cross-channel coupling or hidden per-face correction must fail."
REPEAT = "Repeat across exposure brackets and several independently captured scenes."

_BRACKETS = ("under", "nominal", "over")
_SPECTRAL = ("supported", "unsupported")
_TOKEN = re.compile(r"^[a-z0-9-]+$")
_PAYLOAD_KEYS = (
    "sceneId",
    "bracket",
    "neutralControlled",
    "outputsFinite",
    "spectralAccuracy",
    "unboundedCoupling",
    "hiddenPerFace",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld", "neutral_recorded"}


def evaluate(payload: dict) -> dict:
    """Keep neutrals finite and reject unbounded coupling or hidden per-face correction."""
    scene, bracket, neutral, finite, spectral, unbounded, hidden = _payload(payload)
    preserved = [
        scene,
        f"bracket:{bracket}",
        f"neutral:{str(neutral).lower()}",
        f"finite:{str(finite).lower()}",
        f"spectral:{spectral}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}", f"repeat site {bracket}", f"scene {scene}"]
    rejected: list[str] = []
    if unbounded:
        rejected.append("unbounded-coupling")
    if hidden:
        rejected.append("hidden-per-face")
    if not finite:
        rejected.append("non-finite-output")
    if not neutral:
        rejected.append("neutral-uncontrolled")
    if rejected:
        decision = "rejected"
        if unbounded or hidden:
            reasons.append(NEGATIVE)
        reasons.append(f"scene {scene} bracket {bracket} keeps its neutral inventory after rejection")
    elif spectral == "unsupported":
        decision = "neutral_recorded"
        reasons.append(f"neutral steps on {scene} stay controlled and finite")
        questions.append("spectral accuracy is unsupported")
    else:
        decision = "withheld"
        reasons.append("a supported spectral flag is not a measured film spectrum")
        questions.append("spectral accuracy was not established")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    scene = payload["sceneId"]
    if not isinstance(scene, str) or _TOKEN.fullmatch(scene) is None:
        raise ValueError("sceneId must be a token")
    bracket = payload["bracket"]
    if bracket not in _BRACKETS:
        raise ValueError("bracket is unsupported")
    spectral = payload["spectralAccuracy"]
    if spectral not in _SPECTRAL:
        raise ValueError("spectralAccuracy is unsupported")
    flags = []
    for name in ("neutralControlled", "outputsFinite", "unboundedCoupling", "hiddenPerFace"):
        value = payload[name]
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
        flags.append(value)
    return scene, bracket, flags[0], flags[1], spectral, flags[2], flags[3]


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in {"qualified", "allowed"}:
        raise ValueError("TC-P073-04 must not yield qualified or allowed")
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
