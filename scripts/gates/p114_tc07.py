"""TC-P114-07 Guidance overrides user intent.

Host fixture. Manual exposure and focus stay under user control. Advice may warn.
It must not disable clipping warnings or change the shutter. Scope disclosure
still applies.
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

CASE_ID = "TC-P114-07"
NAME = "Guidance overrides user intent"
INTERVENTION = "Enable capture advice while the user has explicitly chosen manual exposure and focus."
EXPECTED = "Provide warnings or suggestions without hidden camera-setting changes."
NEGATIVE = "A cinematic preset that silently disables clipping warnings or changes shutter must fail."
REPEAT = "Repeat thermal advice, focus warnings, and incompatible virtual-lens framing."
NEGATIVE_TOKEN = "silent-clipping-warning-disable-or-shutter-change"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "shutter_angle_degrees",
    "fps",
    "contains_estimated",
    "disclosed",
    "labelled_as_longer_sensor_exposure",
    "frames",
    "manual_exposure",
    "manual_focus",
    "advice_enabled",
    "clipping_warnings_disabled",
    "shutter_changed",
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
    manual_exposure = _GATE.flag(document["manual_exposure"], "manual_exposure")
    manual_focus = _GATE.flag(document["manual_focus"], "manual_focus")
    advice = _GATE.flag(document["advice_enabled"], "advice_enabled")
    clipping_disabled = _GATE.flag(document["clipping_warnings_disabled"], "clipping_warnings_disabled")
    shutter_changed = _GATE.flag(document["shutter_changed"], "shutter_changed")

    rejected, scope_reasons = _GATE.scope_problems(
        frames,
        contains_estimated=contains_estimated,
        disclosed=disclosed,
        labelled_as_longer_sensor_exposure=labelled,
        shutter_angle_degrees=angle,
        fps=fps,
    )
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        *scope_reasons,
        f"manual exposure {manual_exposure}; manual focus {manual_focus}; advice {advice}",
    ]
    if clipping_disabled or shutter_changed:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    elif advice:
        reasons.append("warnings or suggestions only; shutter and clipping warnings unchanged")
    else:
        reasons.append("no capture advice changed the manual shutter or focus")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("user manual intent retained; physical behavior stays open")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": _GATE.preserved_for(evidence, angle, fps),
        "openQuestions": _GATE.open_questions(REPEAT),
    }
    return _GATE.seal(result, evidence)
