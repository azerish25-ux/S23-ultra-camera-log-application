"""TC-P114-06 Rolling-shutter model violation.

Host fixture. Independent foreground motion cannot inherit one global shear
advertised as universal rolling-shutter removal. Unknown readout blocks that warp.
Scope disclosure still applies. Decision is recorded or rejected, never qualified.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p114_define_synthetic_shutter_scope",
    Path(__file__).resolve().parent / "p114_define_synthetic_shutter_scope.py",
)
_GATE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_GATE)

CASE_ID = "TC-P114-06"
NAME = "Rolling-shutter model violation"
INTERVENTION = "Place independently moving foreground content in a scene used for global camera-motion correction."
EXPECTED = "Restrict or qualify the correction rather than applying an unjustified global warp to every object."
NEGATIVE = "One global shear must not be advertised as universal rolling-shutter removal."
REPEAT = "Repeat pans, vibrations, moving subjects, and unknown readout timing."
NEGATIVE_TOKEN = "global-shear-advertised-as-universal-rolling-shutter-removal"
WARP_TOKEN = "unjustified-global-warp"
READOUT_TOKEN = "unknown-readout-timing"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "shutter_angle_degrees",
    "fps",
    "contains_estimated",
    "disclosed",
    "labelled_as_longer_sensor_exposure",
    "frames",
    "independent_foreground_motion",
    "applied_global_shear",
    "advertised_as_universal_removal",
    "correction_restricted",
    "readout_known",
)


def evaluate(payload: dict) -> dict:
    document = _GATE.exact_keys(payload, set(PAYLOAD_KEYS), "payload")
    evidence = _GATE.evidence_id(document["evidenceId"])
    repeat = _GATE.repeat_text(document["repeat"])
    frames = _GATE.parse_frames(document["frames"])
    angle = _GATE.optional_positive(document["shutter_angle_degrees"], "shutter_angle_degrees")
    fps = _GATE.optional_positive(document["fps"], "fps")
    contains_estimated = _GATE.flag(document["contains_estimated"], "contains_estimated")
    disclosed = _GATE.flag(document["disclosed"], "disclosed")
    labelled = _GATE.flag(document["labelled_as_longer_sensor_exposure"], "labelled_as_longer_sensor_exposure")
    independent = _GATE.flag(document["independent_foreground_motion"], "independent_foreground_motion")
    shear = _GATE.flag(document["applied_global_shear"], "applied_global_shear")
    advertised = _GATE.flag(document["advertised_as_universal_removal"], "advertised_as_universal_removal")
    restricted = _GATE.flag(document["correction_restricted"], "correction_restricted")
    readout_known = _GATE.flag(document["readout_known"], "readout_known")

    rejected, scope_reasons = _GATE.scope_problems(
        frames,
        contains_estimated=contains_estimated,
        disclosed=disclosed,
        labelled_as_longer_sensor_exposure=labelled,
        shutter_angle_degrees=angle,
        fps=fps,
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, *scope_reasons]
    if advertised:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if independent and shear and not restricted:
        rejected.append(WARP_TOKEN)
        reasons.append("independent foreground received an unrestricted global warp")
    if shear and not readout_known:
        rejected.append(READOUT_TOKEN)
        reasons.append("global shear was applied without known readout timing")
    if not rejected:
        if independent and restricted:
            reasons.append("correction restricted; not advertised as universal rolling-shutter removal")
        else:
            reasons.append("no universal rolling-shutter claim was recorded")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("rolling-shutter limit retained; physical behavior stays open")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": _GATE.preserved_for(evidence, angle, fps),
        "openQuestions": _GATE.open_questions(REPEAT),
    }
    return _GATE.seal(result, evidence)
