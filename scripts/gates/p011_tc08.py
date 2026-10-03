"""TC-P011-08 physical qualification boundary.

A short take does not certify endurance. Duration below the requirement, or
missing environmental evidence, is only a slice. A short cold run must not
extrapolate to unlimited recording. This host result does not qualify a
physical S23.
"""

from __future__ import annotations

import math


CASE_ID = "TC-P011-08"
INTERVENTION = (
    "Supply a short successful physical take but omit the longer duration and "
    "environmental evidence required by the gate."
)
EXPECTED = (
    "Report the achieved slice accurately and leave endurance or higher-resolution claims unqualified."
)
NEGATIVE = "Extrapolating a short cold run into unlimited recording must fail."
_PAYLOAD_KEYS = (
    "durationSec",
    "requiredEnduranceSec",
    "thermalWarm",
    "lensId",
    "audioSelection",
    "environmentalEvidence",
    "advertisedSize",
    "aeMin",
    "aeMax",
    "requestedFps",
    "containerTimestampsAssigned",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_UNLIMITED_CLAIM = "unlimited-extrapolation"
_ENDURANCE_QUESTION = "endurance unqualified"
_FORBIDDEN = {"qualified", "allowed", "native_fixed_24", "unlimited"}


def evaluate(payload: dict) -> dict:
    """Bound a physical take so a short slice cannot certify endurance."""
    (
        duration,
        required,
        thermal_warm,
        lens_id,
        audio,
        evidence,
        advertised_size,
        ae_min,
        ae_max,
        requested,
        timestamps,
    ) = _payload(payload)
    short = duration < required
    if short or not evidence:
        decision = "slice_only"
    else:
        decision = "endurance_observed"
    rejected: list[str] = []
    if short and not thermal_warm:
        rejected.append(_UNLIMITED_CLAIM)
    if timestamps:
        rejected.append("native-fixed-24")
    preserved = [
        f"{duration}s",
        lens_id,
        audio,
        advertised_size,
        f"ae:{_text(ae_min)}-{_text(ae_max)}",
        f"requested:{_text(requested)}",
    ]
    reasons = _reasons(decision, duration, required, thermal_warm, evidence, short, timestamps)
    open_questions = [_ENDURANCE_QUESTION] if decision == "slice_only" else []
    if decision == "slice_only" and _ENDURANCE_QUESTION not in open_questions:
        raise ValueError("slice must leave endurance unqualified")
    if short and not thermal_warm and decision in _FORBIDDEN:
        raise ValueError(NEGATIVE)
    if short and not thermal_warm and _UNLIMITED_CLAIM not in rejected:
        raise ValueError(NEGATIVE)
    return _result(decision, reasons, rejected, preserved, open_questions)


def _reasons(decision, duration, required, thermal_warm, evidence, short, timestamps) -> list[str]:
    if decision == "slice_only":
        reasons: list[str] = []
        if short:
            reasons.append(f"duration {duration}s is below required endurance {required}s")
        if not evidence:
            reasons.append("environmental evidence is missing")
        reasons.append("achieved slice does not certify endurance or a physical S23")
        if short and not thermal_warm:
            reasons.append("short cold run does not extrapolate to unlimited recording")
    else:
        reasons = [
            "required endurance was met with environmental evidence",
            "observed endurance is not an unlimited recording claim",
            "observed endurance does not qualify a physical S23",
        ]
    if timestamps:
        reasons.append("container timestamps do not certify native fixed 24")
    if not reasons:
        raise ValueError("reasons required")
    return reasons


def _payload(payload: object):
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    duration = _seconds(payload["durationSec"], "durationSec", allow_zero=True)
    required = _seconds(payload["requiredEnduranceSec"], "requiredEnduranceSec", allow_zero=False)
    thermal_warm = payload["thermalWarm"]
    evidence = payload["environmentalEvidence"]
    timestamps = payload["containerTimestampsAssigned"]
    if type(thermal_warm) is not bool or type(evidence) is not bool or type(timestamps) is not bool:
        raise ValueError("thermalWarm, environmentalEvidence, and containerTimestampsAssigned must be bools")
    lens_id = _text_field(payload["lensId"], "lensId")
    audio = _text_field(payload["audioSelection"], "audioSelection")
    advertised_size = _size(payload["advertisedSize"])
    ae_min = _rate(payload["aeMin"], "aeMin")
    ae_max = _rate(payload["aeMax"], "aeMax")
    if _cmp(ae_min, ae_max) > 0:
        raise ValueError("aeMin must not exceed aeMax")
    requested = _rate(payload["requestedFps"], "requestedFps")
    return (
        duration,
        required,
        thermal_warm,
        lens_id,
        audio,
        evidence,
        advertised_size,
        ae_min,
        ae_max,
        requested,
        timestamps,
    )


def _seconds(value: object, label: str, allow_zero: bool) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if value < 0 or (not allow_zero and value <= 0):
        raise ValueError(f"{label} must be positive" if not allow_zero else f"{label} must be non-negative")
    return value


def _text_field(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _size(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("advertisedSize must be a string")
    width, sep, height = value.partition("x")
    if sep != "x" or not width.isdigit() or width[0] == "0" or not height.isdigit() or height[0] == "0":
        raise ValueError("advertisedSize must look like 3840x2160")
    return value


def _rate(value: object, context: str) -> tuple[int, int]:
    if not isinstance(value, dict) or set(value) != {"numerator", "denominator"}:
        raise ValueError(context + " must be a numerator/denominator object")
    numerator = value["numerator"]
    denominator = value["denominator"]
    if type(numerator) is not int or type(denominator) is not int:
        raise ValueError(context + " must use ints")
    if numerator <= 0 or denominator <= 0:
        raise ValueError(context + " must be positive")
    if math.gcd(numerator, denominator) != 1:
        raise ValueError(context + " must be reduced")
    return numerator, denominator


def _text(rate: tuple[int, int]) -> str:
    return f"{rate[0]}/{rate[1]}"


def _cmp(left: tuple[int, int], right: tuple[int, int]) -> int:
    gap = left[0] * right[1] - right[0] * left[1]
    return (gap > 0) - (gap < 0)


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in _FORBIDDEN:
        raise ValueError("TC-P011-08 must not yield qualified, allowed, unlimited, or native_fixed_24")
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
