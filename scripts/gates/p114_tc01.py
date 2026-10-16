"""TC-P114-01 Shutter feasibility mismatch.

Host fixture. Implied exposure is angle/360/fps. A displayed angle must match the
feasible exposure. Source cadence is not silently changed. Scope weights, estimated
frame disclosure, and the named shutter simulation still apply.
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

CASE_ID = "TC-P114-01"
NAME = "Shutter feasibility mismatch"
INTERVENTION = "Request a shutter angle whose implied exposure conflicts with actual sensor timing or exposure limits."
EXPECTED = "Show the effective feasible setting or reject it without silently changing source cadence."
NEGATIVE = "A displayed angle must not conceal a different applied exposure."
REPEAT = "Repeat integer and fractional frame rates and low-light automatic behavior."
NEGATIVE_TOKEN = "displayed-angle-conceals-different-applied-exposure"
CADENCE_TOKEN = "source-cadence-silently-changed"
ANGLE_TOLERANCE = 1e-6
EXPOSURE_TOLERANCE = 1e-9
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "shutter_angle_degrees",
    "fps",
    "contains_estimated",
    "disclosed",
    "labelled_as_longer_sensor_exposure",
    "frames",
    "displayed_angle_degrees",
    "applied_exposure_seconds",
    "sensor_max_exposure_seconds",
    "output_fps",
    "low_light_automatic",
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
    labelled = _GATE.flag(
        document["labelled_as_longer_sensor_exposure"],
        "labelled_as_longer_sensor_exposure",
    )

    displayed = _GATE.positive_number(document["displayed_angle_degrees"], "displayed_angle_degrees")
    applied = _GATE.positive_number(document["applied_exposure_seconds"], "applied_exposure_seconds")
    sensor_max = _GATE.positive_number(document["sensor_max_exposure_seconds"], "sensor_max_exposure_seconds")
    output_fps = _GATE.positive_number(document["output_fps"], "output_fps")
    low_light = _GATE.flag(document["low_light_automatic"], "low_light_automatic")

    rejected, scope_reasons = _GATE.scope_problems(
        frames,
        contains_estimated=contains_estimated,
        disclosed=disclosed,
        labelled_as_longer_sensor_exposure=labelled,
        shutter_angle_degrees=angle,
        fps=fps,
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, *scope_reasons]
    if low_light:
        reasons.append("low-light automatic behavior considered without a hidden cadence change")
    if fps is not None and abs(output_fps - fps) > EXPOSURE_TOLERANCE:
        rejected.append(CADENCE_TOKEN)
        reasons.append("source cadence changed from " + str(fps) + " to " + str(output_fps))
    if angle is not None and fps is not None:
        requested = _GATE.simulated_exposure_seconds(angle, fps)
        period = 1.0 / fps
        feasible = min(requested, sensor_max, period)
        effective_angle = feasible * 360.0 * fps
        displayed_exposure = _GATE.simulated_exposure_seconds(displayed, output_fps)
        reasons.append(
            f"requested {requested} s, feasible {feasible} s, effective angle {effective_angle}"
        )
        concealed = (
            abs(displayed - effective_angle) > ANGLE_TOLERANCE
            or abs(displayed_exposure - applied) > EXPOSURE_TOLERANCE
            or abs(applied - feasible) > EXPOSURE_TOLERANCE
        )
        if concealed:
            rejected.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
        else:
            reasons.append("displayed angle matches the feasible exposure and cadence is unchanged")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("effective feasible shutter retained; physical behavior stays open")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": _GATE.preserved_for(evidence, angle, fps),
        "openQuestions": _GATE.open_questions(REPEAT),
    }
    return _GATE.seal(result, evidence)
