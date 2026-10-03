"""TC-P012-08 physical qualification boundary.

A short take does not certify endurance. Duration below the requirement, or
missing environmental evidence, is only a slice. A short cold run must not
extrapolate to unlimited recording. Observed endurance is still not unlimited.
The advertised stream size is always retained.
"""

from __future__ import annotations

INTERVENTION = 'Supply a short successful physical take but omit the longer duration and environmental evidence required by the gate.'
EXPECTED = 'Report the achieved slice accurately and leave endurance or higher-resolution claims unqualified.'
NEGATIVE = 'Extrapolating a short cold run into unlimited recording must fail.'

def _assert_case_contract() -> None:
    if not isinstance(INTERVENTION, str) or not INTERVENTION:
        raise ValueError("intervention missing")
    if not isinstance(EXPECTED, str) or not EXPECTED:
        raise ValueError("expected missing")
    if not isinstance(NEGATIVE, str) or not NEGATIVE:
        raise ValueError("negative missing")
    if "must fail" not in NEGATIVE and "must not" not in NEGATIVE:
        raise ValueError("negative control missing")


import math

CASE_ID = "TC-P012-08"
_PAYLOAD_KEYS = (
    "durationSec",
    "requiredEnduranceSec",
    "thermalWarm",
    "lensId",
    "audioSelection",
    "environmentalEvidence",
    "advertisedSize",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("slice_only", "endurance_observed")
_UNLIMITED_CLAIM = "unlimited-extrapolation"
_ENDURANCE_QUESTION = "endurance unqualified"


def evaluate(payload: dict) -> dict:
    """Bound a physical take so a short slice cannot certify endurance.

    Returns exactly caseId, decision, reasons, rejectedClaims,
    preservedResults, and openQuestions. Raises ValueError if payload is
    invalid. decision is slice_only or endurance_observed, never unlimited
    or qualified.
    """
    _assert_case_contract()
    duration, required, thermal_warm, lens_id, audio, evidence, advertised_size = _payload(
        payload
    )
    short = duration < required
    if short or not evidence:
        decision = "slice_only"
    else:
        decision = "endurance_observed"

    rejected: list[str] = []
    if short and not thermal_warm:
        rejected.append(_UNLIMITED_CLAIM)

    preserved = [duration, lens_id, audio, advertised_size]
    reasons = _reasons(decision, duration, required, thermal_warm, evidence, short)
    open_questions = [_ENDURANCE_QUESTION] if decision == "slice_only" else []

    if decision not in _DECISIONS or decision in {"unlimited", "qualified", "allowed"}:
        raise ValueError("endurance decision cannot be unlimited or qualified")
    if decision == "slice_only" and _ENDURANCE_QUESTION not in open_questions:
        raise ValueError("slice must leave endurance unqualified")

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


def _reasons(
    decision: str,
    duration: int | float,
    required: int | float,
    thermal_warm: bool,
    evidence: bool,
    short: bool,
) -> list[str]:
    if decision == "slice_only":
        reasons: list[str] = []
        if short:
            reasons.append(f"duration {duration}s is below required endurance {required}s")
        if not evidence:
            reasons.append("environmental evidence is missing")
        reasons.append("achieved slice does not certify endurance")
        if short and not thermal_warm:
            reasons.append("short cold run does not extrapolate to unlimited recording")
    else:
        reasons = [
            "required endurance was met with environmental evidence",
            "observed endurance is not an unlimited recording claim",
        ]
    if not reasons:
        raise ValueError("reasons required")
    return reasons


def _payload(payload: object) -> tuple[int | float, int | float, bool, str, str, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("payload keys do not match the physical qualification boundary")
    duration = _seconds(payload["durationSec"], "durationSec", allow_zero=True)
    required = _seconds(payload["requiredEnduranceSec"], "requiredEnduranceSec", allow_zero=False)
    thermal_warm = payload["thermalWarm"]
    if not isinstance(thermal_warm, bool):
        raise ValueError("thermalWarm must be a bool")
    lens_id = _text(payload["lensId"], "lensId")
    audio = _text(payload["audioSelection"], "audioSelection")
    evidence = payload["environmentalEvidence"]
    if not isinstance(evidence, bool):
        raise ValueError("environmentalEvidence must be a bool")
    advertised_size = _text(payload["advertisedSize"], "advertisedSize")
    return duration, required, thermal_warm, lens_id, audio, evidence, advertised_size


def _seconds(value: object, label: str, allow_zero: bool) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if value < 0 or (not allow_zero and value <= 0):
        raise ValueError(f"{label} must be positive" if not allow_zero else f"{label} must be non-negative")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value
