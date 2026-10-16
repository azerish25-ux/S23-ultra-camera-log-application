"""TC-P120-02 Existing blur ambiguity.

Host fixture. Additional synthetic shutter blur is the only qualified step.
Existing blur cannot be removed. Exact arbitrary conversion is rejected.
The target exposure must match the combined report.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P120-02"
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
TARGET_TOKEN = "target-exposure-disagrees-with-combined-report"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "combinationPassed",
    "report",
    "sourceBlurSeconds",
    "targetExposureSeconds",
    "claimsExactArbitraryConversion",
    "thinMotionUndersampled",
)

_SPEC = importlib.util.spec_from_file_location(
    "p120_validate_combined_motion_and_optics",
    Path(__file__).resolve().parent / "p120_validate_combined_motion_and_optics.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def evaluate(payload: dict) -> dict:
    evidence, repeat = _CORE.require_payload(payload, PAYLOAD_KEYS)
    source_blur = _CORE.require_number(payload["sourceBlurSeconds"], "sourceBlurSeconds")
    target = _CORE.require_number(payload["targetExposureSeconds"], "targetExposureSeconds")
    _CORE.require(source_blur >= 0 and target >= 0, "blur and exposure must be non-negative")
    _CORE.require(type(payload["claimsExactArbitraryConversion"]) is bool, "claimsExactArbitraryConversion must be a bool")
    _CORE.require(type(payload["thinMotionUndersampled"]) is bool, "thinMotionUndersampled must be a bool")
    judgement = _CORE.judge_report(payload["report"], combination_passed=payload["combinationPassed"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(judgement["reasons"])
    rejected = list(judgement["rejectedClaims"])
    if payload["claimsExactArbitraryConversion"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    report_ready = _CORE.MISSING_FIELDS not in rejected and _CORE.EXPOSURE_MISMATCH not in rejected
    if report_ready:
        exposure = _CORE.require_number(payload["report"]["exposure_seconds"], "exposure_seconds")
        if not _CORE.exposures_match(target, exposure):
            rejected.append(TARGET_TOKEN)
            reasons.append("target exposure must match the combined report")
    if source_blur > target + _CORE.EXPOSURE_TOLERANCE:
        rejected.append(CANNOT_RECONSTRUCT)
        reasons.append("existing blur exceeds the requested exposure and cannot be removed")
        reasons.append("defectOrigin=source_blur")
    elif payload["thinMotionUndersampled"]:
        rejected.append(UNDERSAMPLED)
        reasons.append("undersampled thin motion cannot be faithfully reconstructed")
        reasons.append("defectOrigin=source_blur")
    elif NEGATIVE_TOKEN not in rejected and TARGET_TOKEN not in rejected and report_ready:
        additional = target - source_blur
        reasons.append("additionalBlurSeconds=" + _CORE.format_number(additional))
        reasons.append("qualified additional blur only; exact arbitrary conversion is not claimed")
    preserved = [evidence]
    preserved.extend(judgement["preservedResults"])
    return _CORE.assemble_result(
        case_id=CASE_ID,
        evidence=evidence,
        reasons=reasons,
        rejected=rejected,
        preserved=preserved,
        repeat_note=REPEAT,
    )
