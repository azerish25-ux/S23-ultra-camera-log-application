"""TC-P016-08 physical qualification boundary on the first slice.

A short take does not certify endurance or a higher-resolution mode. A short
cold run must not extrapolate to unlimited recording. Observed duration with
environmental evidence is still not a physical S23 endurance certificate.
"""

from __future__ import annotations

CASE_ID = "TC-P016-08"
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
    "higherResolutionClaimed",
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
_HIGHER_RES = "higher-resolution"
_ENDURANCE_QUESTION = "endurance unqualified"
_ORACLE_PRESERVED = ("file-retained", "playback:separate", "cadence:separate")
_NOT_ENDURANCE = "not-endurance-certified"


def evaluate(payload: dict) -> dict:
    """Bound a take so a short slice cannot certify endurance or unlimited recording."""
    (
        duration,
        required,
        thermal_warm,
        lens_id,
        audio,
        evidence,
        advertised_size,
        higher_resolution,
    ) = _payload(payload)
    short = duration < required
    if short or not evidence or higher_resolution:
        decision = "slice_only"
    else:
        decision = "endurance_observed"

    rejected: list[str] = []
    if short and not thermal_warm:
        rejected.append(_UNLIMITED_CLAIM)
    if higher_resolution:
        rejected.append(_HIGHER_RES)
        if decision == "endurance_observed":
            decision = "slice_only"

    preserved = [f"{duration}s", lens_id, audio, advertised_size]
    reasons = _reasons(
        decision, duration, required, thermal_warm, evidence, short, higher_resolution
    )
    open_questions = [_ENDURANCE_QUESTION] if decision == "slice_only" else ["not an endurance certificate"]
    if higher_resolution and "higher-resolution unqualified" not in open_questions:
        open_questions.append("higher-resolution unqualified")

    if decision not in _DECISIONS or decision in {"unlimited", "qualified", "allowed"}:
        raise ValueError("endurance decision cannot be unlimited, qualified, or allowed")
    if decision == "slice_only" and _ENDURANCE_QUESTION not in open_questions:
        raise ValueError("slice must leave endurance unqualified")
    if short and not thermal_warm and _UNLIMITED_CLAIM not in rejected:
        raise ValueError(NEGATIVE)
    return _finish(decision, reasons, rejected, preserved, open_questions)


def _reasons(
    decision: str,
    duration: int,
    required: int,
    thermal_warm: bool,
    evidence: bool,
    short: bool,
    higher_resolution: bool,
) -> list[str]:
    if decision == "slice_only":
        reasons: list[str] = []
        if short:
            reasons.append(f"duration {duration}s is below required endurance {required}s")
        if not evidence:
            reasons.append("environmental evidence is missing")
        if higher_resolution:
            reasons.append("higher-resolution claim left unqualified")
        reasons.append("achieved slice does not certify endurance")
        if short and not thermal_warm:
            reasons.append("short cold run does not extrapolate to unlimited recording")
    else:
        reasons = [
            "required endurance duration was met with environmental evidence",
            "observed endurance is not an unlimited recording claim",
            "observed endurance is not a physical S23 endurance certificate",
        ]
    if not reasons:
        raise ValueError("reasons required")
    return reasons


def _finish(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError(f"{CASE_ID} must not decide qualified or allowed")
    kept = list(preserved)
    for token in _ORACLE_PRESERVED:
        if token not in kept:
            kept.append(token)
    questions = list(open_questions)
    if decision == "slice_only" and "endurance unqualified" not in questions:
        questions.append("endurance unqualified")
    if _NOT_ENDURANCE not in questions and "endurance unqualified" not in questions:
        questions.append(_NOT_ENDURANCE)
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": kept,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result


def _payload(
    payload: object,
) -> tuple[int, int, bool, str, str, bool, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("payload keys do not match the physical qualification boundary")
    duration = _seconds(payload["durationSec"], "durationSec", allow_zero=True)
    required = _seconds(payload["requiredEnduranceSec"], "requiredEnduranceSec", allow_zero=False)
    thermal_warm = payload["thermalWarm"]
    if type(thermal_warm) is not bool:
        raise ValueError("thermalWarm must be a bool")
    lens_id = _text(payload["lensId"], "lensId")
    audio = _text(payload["audioSelection"], "audioSelection")
    evidence = payload["environmentalEvidence"]
    if type(evidence) is not bool:
        raise ValueError("environmentalEvidence must be a bool")
    advertised_size = _text(payload["advertisedSize"], "advertisedSize")
    higher = payload["higherResolutionClaimed"]
    if type(higher) is not bool:
        raise ValueError("higherResolutionClaimed must be a bool")
    return duration, required, thermal_warm, lens_id, audio, evidence, advertised_size, higher


def _seconds(value: object, label: str, allow_zero: bool) -> int:
    if type(value) is not int:
        raise ValueError(f"{label} must be an int")
    if value < 0 or (not allow_zero and value <= 0):
        raise ValueError(
            f"{label} must be positive" if not allow_zero else f"{label} must be non-negative"
        )
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value
