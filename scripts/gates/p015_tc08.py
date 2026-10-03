"""TC-P015-08 physical qualification boundary.

A short take is only the achieved slice. Missing duration or environmental
evidence leaves endurance and higher-resolution claims unqualified. A short
cold run must not extrapolate to unlimited recording. The decision is never
qualified or allowed.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P015-08"
INTERVENTION = (
    "Supply a short successful physical take but omit the longer duration and "
    "environmental evidence required by the gate."
)
EXPECTED = "Report the achieved slice accurately and leave endurance or higher-resolution claims unqualified."
NEGATIVE = "Extrapolating a short cold run into unlimited recording must fail."
REPEAT = "Repeat after thermal warm-up, with a different lens, and with a changed audio selection."
_PAYLOAD_KEYS = (
    "durationSec",
    "requiredEnduranceSec",
    "thermalWarm",
    "lensId",
    "audioSelection",
    "environmentalEvidence",
    "extrapolateUnlimited",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_UNLIMITED = "unlimited-recording"
_ENDURANCE = "endurance unqualified"
_HIGHER = "higher-resolution unqualified"
_FORBIDDEN = {"qualified", "allowed", "unlimited"}


def evaluate(payload: dict) -> dict:
    """Bound a physical take so a short cold run cannot certify unlimited recording."""
    duration, required, thermal_warm, lens_id, audio, evidence, extrapolate = _payload(payload)
    short = duration < required
    cold = not thermal_warm
    if short or not evidence or extrapolate:
        decision = "slice_only"
    else:
        decision = "observed"
    rejected: list[str] = []
    if extrapolate or (short and cold):
        rejected.append(_UNLIMITED)
    preserved = [_duration_text(duration), lens_id, audio]
    reasons = _reasons(decision, duration, required, thermal_warm, evidence, short, extrapolate)
    if decision == "slice_only":
        open_questions = [_ENDURANCE, _HIGHER]
    else:
        open_questions = [_HIGHER]
    if decision in _FORBIDDEN:
        raise ValueError("endurance decision cannot be qualified, allowed, or unlimited")
    if short and decision != "slice_only":
        raise ValueError("a short take must remain a slice")
    if extrapolate and (_UNLIMITED not in rejected or decision in _FORBIDDEN):
        raise ValueError("extrapolating a short cold run into unlimited recording must fail")
    if decision == "slice_only" and _ENDURANCE not in open_questions:
        raise ValueError("slice must leave endurance unqualified")
    if _HIGHER not in open_questions:
        raise ValueError("higher-resolution claims stay unqualified")
    return _result(decision, reasons, rejected, preserved, open_questions)


def _reasons(
    decision: str,
    duration: int | float,
    required: int | float,
    thermal_warm: bool,
    evidence: bool,
    short: bool,
    extrapolate: bool,
) -> list[str]:
    if decision == "slice_only":
        reasons = [f"achieved slice duration {duration}s"]
        if short:
            reasons.append(f"duration {duration}s is below required endurance {required}s")
        if not evidence:
            reasons.append("environmental evidence is missing")
        reasons.append("endurance and higher-resolution claims remain unqualified")
        if extrapolate or (short and not thermal_warm):
            reasons.append("short cold run does not extrapolate to unlimited recording")
        if thermal_warm and short:
            reasons.append("thermal warm-up does not extend a short slice into endurance")
    else:
        reasons = [
            f"achieved slice duration {duration}s met the recorded endurance gate",
            "observed endurance is not unlimited recording",
            "higher-resolution claims remain unqualified",
        ]
    if not reasons:
        raise ValueError("reasons required")
    return reasons


def _payload(payload: object) -> tuple[int | float, int | float, bool, str, str, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    duration = _seconds(payload["durationSec"], "durationSec", allow_zero=True)
    required = _seconds(payload["requiredEnduranceSec"], "requiredEnduranceSec", allow_zero=False)
    thermal_warm = _bool(payload["thermalWarm"], "thermalWarm")
    lens_id = _text(payload["lensId"], "lensId")
    audio = _text(payload["audioSelection"], "audioSelection")
    evidence = _bool(payload["environmentalEvidence"], "environmentalEvidence")
    extrapolate = _bool(payload["extrapolateUnlimited"], "extrapolateUnlimited")
    return duration, required, thermal_warm, lens_id, audio, evidence, extrapolate


def _seconds(value: object, label: str, allow_zero: bool) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if value < 0 or (not allow_zero and value <= 0):
        raise ValueError(f"{label} must be positive" if not allow_zero else f"{label} must be non-negative")
    return value


def _duration_text(value: int | float) -> str:
    if type(value) is int:
        return str(value) + "s"
    return format(value, "g") + "s"


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in _FORBIDDEN or not reasons:
        raise ValueError("invalid decision or reasons")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": open_questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
