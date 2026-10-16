"""TC-P116-02 Existing blur ambiguity.

Host fixture. Additional synthetic shutter blur is the only qualified step.
Existing blur cannot be removed, and exact arbitrary conversion is rejected.
Estimated frames stay origin=estimated.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

CASE_ID = "TC-P116-02"
NAME = "Existing blur ambiguity"
INTERVENTION = (
    "Supply sources with different amounts of already-recorded motion blur to the same synthetic-shutter request."
)
EXPECTED = "Apply only qualified additional processing and identify cases that cannot be faithfully reconstructed."
NEGATIVE = "Claiming exact arbitrary shutter conversion from any source must fail."
REPEAT = "Repeat short exposure, long exposure, and undersampled thin motion."
NEGATIVE_TOKEN = "exact-arbitrary-shutter-conversion"
CANNOT_RECONSTRUCT = "existing-blur-cannot-be-faithfully-reconstructed"
UNDERSAMPLED = "undersampled-thin-motion-cannot-be-reconstructed"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "sourceBlurSeconds",
    "targetExposureSeconds",
    "claimsExactArbitraryConversion",
    "thinMotionUndersampled",
    "captured",
    "estimated",
    "withheldMidpoint",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_SPEC = importlib.util.spec_from_file_location(
    "p116_evaluate_interpolation_without_hidden_hallucination",
    Path(__file__).resolve().parent / "p116_evaluate_interpolation_without_hidden_hallucination.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _number(value, label: str) -> float:
    if type(value) is bool or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    source_blur = _number(payload["sourceBlurSeconds"], "sourceBlurSeconds")
    target = _number(payload["targetExposureSeconds"], "targetExposureSeconds")
    if source_blur < 0 or target < 0:
        raise ValueError("blur and exposure must be non-negative")
    if type(payload["claimsExactArbitraryConversion"]) is not bool:
        raise ValueError("claimsExactArbitraryConversion must be a bool")
    if type(payload["thinMotionUndersampled"]) is not bool:
        raise ValueError("thinMotionUndersampled must be a bool")
    timeline = _CORE.evaluate_timeline(
        payload["captured"], payload["estimated"], payload["withheldMidpoint"]
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(timeline["reasons"])
    rejected = list(timeline["rejectedClaims"])
    additional = target - source_blur
    if payload["claimsExactArbitraryConversion"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if source_blur > target + _CORE.ABSOLUTE_TOLERANCE:
        rejected.append(CANNOT_RECONSTRUCT)
        reasons.append("existing blur exceeds the requested exposure and cannot be removed")
    elif payload["thinMotionUndersampled"]:
        rejected.append(UNDERSAMPLED)
        reasons.append("undersampled thin motion cannot be faithfully reconstructed")
    elif not payload["claimsExactArbitraryConversion"]:
        reasons.append("additionalBlurSeconds=" + format(additional, ".12g"))
        reasons.append("qualified additional blur only; exact arbitrary conversion is not claimed")
    preserved = [evidence]
    preserved.extend(timeline["preservedResults"])
    decision = "rejected" if rejected else "recorded"
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
