"""TC-P114-08 Combined temporal effects.

Host fixture. Stabilization, virtual focus, motion integration, and film finishing
must be checked together. Separate passes do not replace that regression. Shared
geometry and cadence stay intact. Scope disclosure still applies.
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

CASE_ID = "TC-P114-08"
NAME = "Combined temporal effects"
INTERVENTION = "Enable stabilization, virtual focus, motion integration, and film finishing on the same difficult clip."
EXPECTED = "Preserve shared geometry and timing without doubled edges, unstable masks, or unexplained cadence changes."
NEGATIVE = "Independent success of each effect cannot replace the combined regression."
REPEAT = "Repeat scene cuts, chunk resumes, and low-confidence motion estimates."
NEGATIVE_TOKEN = "independent-success-cannot-replace-combined-regression"
EDGE_TOKEN = "doubled-edges"
MASK_TOKEN = "unstable-masks"
CADENCE_TOKEN = "unexplained-cadence-change"
GEOMETRY_TOKEN = "shared-geometry-not-preserved"
REQUIRED_EFFECTS = frozenset({
    "stabilization",
    "virtual_focus",
    "motion_integration",
    "film_finishing",
})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "shutter_angle_degrees",
    "fps",
    "contains_estimated",
    "disclosed",
    "labelled_as_longer_sensor_exposure",
    "frames",
    "effects",
    "individual_passes",
    "combined_checked",
    "doubled_edges",
    "unstable_masks",
    "cadence_changed",
    "shared_geometry",
)


def _effects(value: object) -> list[str]:
    _GATE.require(isinstance(value, list) and value, "effects must be a non-empty list")
    _GATE.require(all(isinstance(item, str) and item.strip() for item in value), "effects must be non-empty strings")
    return list(value)


def _passes(value: object) -> dict[str, bool]:
    _GATE.require(isinstance(value, dict), "individual_passes must be an object")
    _GATE.require(set(value) == REQUIRED_EFFECTS, "individual_passes must name the four combined effects")
    return {key: _GATE.flag(value[key], "individual_passes." + key) for key in sorted(REQUIRED_EFFECTS)}


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
    effects = _effects(document["effects"])
    passes = _passes(document["individual_passes"])
    combined = _GATE.flag(document["combined_checked"], "combined_checked")
    doubled = _GATE.flag(document["doubled_edges"], "doubled_edges")
    unstable = _GATE.flag(document["unstable_masks"], "unstable_masks")
    cadence_changed = _GATE.flag(document["cadence_changed"], "cadence_changed")
    shared = _GATE.flag(document["shared_geometry"], "shared_geometry")

    rejected, scope_reasons = _GATE.scope_problems(
        frames,
        contains_estimated=contains_estimated,
        disclosed=disclosed,
        labelled_as_longer_sensor_exposure=labelled,
        shutter_angle_degrees=angle,
        fps=fps,
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, *scope_reasons]
    if set(effects) != REQUIRED_EFFECTS or not combined:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        if all(passes.values()):
            reasons.append("individual passes were true and were not accepted in place of the combination")
    if doubled:
        rejected.append(EDGE_TOKEN)
        reasons.append("combined pass showed doubled edges")
    if unstable:
        rejected.append(MASK_TOKEN)
        reasons.append("combined pass showed unstable masks")
    if cadence_changed:
        rejected.append(CADENCE_TOKEN)
        reasons.append("combined pass changed cadence without explanation")
    if not shared:
        rejected.append(GEOMETRY_TOKEN)
        reasons.append("shared geometry was not preserved")
    if not rejected:
        reasons.append("combined temporal regression preserved geometry and cadence")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("combined result retained; physical behavior stays open")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": _GATE.preserved_for(evidence, angle, fps),
        "openQuestions": _GATE.open_questions(REPEAT),
    }
    return _GATE.seal(result, evidence)
