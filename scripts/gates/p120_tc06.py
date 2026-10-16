"""TC-P120-06 Rolling-shutter model violation.

Host fixture. A single shear is not universal rolling-shutter removal.
Correction requires a measured readout. Unknown readout cannot justify a warp.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P120-06"
NAME = "Rolling-shutter model violation"
INTERVENTION = "Place independently moving foreground content in a scene used for global camera-motion correction."
EXPECTED = "Restrict or qualify the correction rather than applying an unjustified global warp to every object."
NEGATIVE = "One global shear must not be advertised as universal rolling-shutter removal."
REPEAT = "Repeat pans, vibrations, moving subjects, and unknown readout timing."
NEGATIVE_TOKEN = "global-shear-advertised-as-universal-rolling-shutter-removal"
WARP_TOKEN = "unjustified-global-warp"
READOUT_TOKEN = "unknown-readout-timing"
SHEAR_TOKEN = "shear-does-not-match-background-readout"
READOUT_DISAGREE = "readout-evidence-disagrees"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "combinationPassed",
    "report",
    "foregroundVelocity",
    "backgroundVelocity",
    "globalShear",
    "readoutSeconds",
    "advertisedUniversal",
    "restrictedToBackground",
)

_SPEC = importlib.util.spec_from_file_location(
    "p120_validate_combined_motion_and_optics",
    Path(__file__).resolve().parent / "p120_validate_combined_motion_and_optics.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def evaluate(payload: dict) -> dict:
    evidence, repeat = _CORE.require_payload(payload, PAYLOAD_KEYS)
    foreground = _CORE.require_number(payload["foregroundVelocity"], "foregroundVelocity")
    background = _CORE.require_number(payload["backgroundVelocity"], "backgroundVelocity")
    shear = _CORE.require_number(payload["globalShear"], "globalShear")
    readout = payload["readoutSeconds"]
    if readout is not None:
        readout = _CORE.require_number(readout, "readoutSeconds")
        _CORE.require(readout >= 0, "readoutSeconds must be non-negative")
    _CORE.require(
        type(payload["advertisedUniversal"]) is bool and type(payload["restrictedToBackground"]) is bool,
        "flags must be bools",
    )
    judgement = _CORE.judge_report(payload["report"], combination_passed=payload["combinationPassed"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(judgement["reasons"])
    rejected = list(judgement["rejectedClaims"])
    independent = not _CORE.exposures_match(foreground, background)
    if payload["advertisedUniversal"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    report_ready = _CORE.MISSING_FIELDS not in rejected
    if report_ready:
        report_readout = payload["report"]["rolling_shutter_readout"]
        applied = payload["report"]["correction_applied"]
        if report_readout == "unknown" and readout is not None:
            rejected.append(READOUT_DISAGREE)
            reasons.append("unknown readout cannot carry a numeric readout time")
        if report_readout == "measured" and readout is None:
            rejected.append(READOUT_DISAGREE)
            reasons.append("measured readout requires readoutSeconds")
        if report_readout == "unknown":
            if not _CORE.exposures_match(shear, 0.0):
                rejected.append(READOUT_TOKEN)
                reasons.append("unknown readout timing cannot justify a global shear")
        elif readout is not None and applied and _CORE.UNKNOWN_READOUT_CORRECTION not in rejected:
            expected = background * readout
            if not _CORE.exposures_match(shear, expected):
                rejected.append(SHEAR_TOKEN)
                reasons.append("expectedShear=" + _CORE.format_number(expected))
            elif independent and not payload["restrictedToBackground"]:
                rejected.append(WARP_TOKEN)
                reasons.append("independent foreground motion blocks an unrestricted global shear")
            elif not payload["advertisedUniversal"]:
                scope = "background" if payload["restrictedToBackground"] or independent else "rigid-scene"
                reasons.append("shear matches " + scope + " readout model")
        elif not applied and not _CORE.exposures_match(shear, 0.0):
            rejected.append(WARP_TOKEN)
            reasons.append("a shear was applied without correction_applied")
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
