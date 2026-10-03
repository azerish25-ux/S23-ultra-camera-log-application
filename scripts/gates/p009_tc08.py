"""TC-P009-08 physical qualification boundary.

A short physical take is a measured slice only. It does not certify endurance
and it is never unlimited recording. Lens and audio identities stay attached
to the observed result.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P009-08"
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_PAYLOAD_KEYS = (
    "durationSec",
    "requiredEnduranceSec",
    "thermalWarm",
    "lensId",
    "audioSelection",
    "environmentalEvidence",
)
_EXTRAPOLATION_CLAIM = "unlimited-extrapolation"


def evaluate(payload: dict) -> dict:
    """Bound a physical take to the evidence actually supplied.

    Returns exactly caseId, decision, reasons, rejectedClaims,
    preservedResults, and openQuestions. Raises ValueError if payload is
    invalid. A shortfall in duration or environmental evidence is slice_only.
    Endurance, when observed, is still not unlimited recording.
    """
    data = _payload(payload)
    duration = data["durationSec"]
    required = data["requiredEnduranceSec"]
    thermal_warm = data["thermalWarm"]
    lens_id = data["lensId"]
    audio = data["audioSelection"]
    environmental = data["environmentalEvidence"]

    short = duration < required
    short_cold = (not thermal_warm) and short
    if short or not environmental:
        decision = "slice_only"
    else:
        decision = "endurance_observed"

    if decision in {"unlimited", "qualified"}:
        raise ValueError("a physical take must not be decided unlimited or qualified")

    reasons = [
        f"lens {lens_id} with audio {audio} observed for {duration}s"
    ]
    rejected: list[str] = []
    open_questions: list[str] = []
    if decision == "slice_only":
        reasons.append("achieved slice does not certify endurance")
        open_questions.append("endurance unqualified")
    else:
        reasons.append(f"endurance observed on lens {lens_id} with audio {audio}")
    if short_cold:
        rejected.append(_EXTRAPOLATION_CLAIM)
        reasons.append("short cold run is not an endurance certification")

    if not reasons:
        raise ValueError("reasons required")
    for reason in reasons:
        if "unlimited" in reason or "qualified" in reason:
            raise ValueError("reasons must not claim unlimited or qualified")

    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [f"duration:{duration}", lens_id, audio],
        "openQuestions": open_questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    if result["decision"] in {"unlimited", "qualified"}:
        raise ValueError("a physical take must not be decided unlimited or qualified")
    return result


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError(
            "payload keys must be durationSec, requiredEnduranceSec, thermalWarm, "
            "lensId, audioSelection, and environmentalEvidence"
        )
    duration = payload["durationSec"]
    required = payload["requiredEnduranceSec"]
    if not _number(duration) or duration < 0:
        raise ValueError("durationSec must be a non-negative finite number")
    if not _number(required) or required <= 0:
        raise ValueError("requiredEnduranceSec must be a positive finite number")
    if not isinstance(payload["thermalWarm"], bool):
        raise ValueError("thermalWarm must be a bool")
    if not isinstance(payload["environmentalEvidence"], bool):
        raise ValueError("environmentalEvidence must be a bool")
    for key in ("lensId", "audioSelection"):
        value = payload[key]
        if not isinstance(value, str) or not value:
            raise ValueError(f"{key} must be a non-empty string")
    return payload


def _number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return isinstance(value, int) or math.isfinite(value)
