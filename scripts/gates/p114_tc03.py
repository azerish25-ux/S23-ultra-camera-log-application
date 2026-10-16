"""TC-P114-03 Temporal integration energy.

Host fixture. Linear-domain energy is the weight-sum of radiance. Trail extent is
the span of positive-weight positions. Display-encoded averages and unnormalized
weights fail. Estimated-frame disclosure still applies.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p114_define_synthetic_shutter_scope",
    Path(__file__).resolve().parent / "p114_define_synthetic_shutter_scope.py",
)
_GATE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_GATE)

CASE_ID = "TC-P114-03"
NAME = "Temporal integration energy"
INTERVENTION = "Integrate known synthetic motion over an explicitly defined exposure window."
EXPECTED = "Match independent linear-domain energy and trail extent within the numerical tolerance."
NEGATIVE = "Averaging display-encoded frames or unnormalized temporal weights must fail."
REPEAT = "Repeat constant velocity, acceleration, and partial exposure at clip boundaries."
DISPLAY_TOKEN = "display-encoded-frame-average"
ENERGY_TOKEN = "linear-energy-mismatch"
TRAIL_TOKEN = "trail-extent-mismatch"
DOMAINS = frozenset({"linear", "display"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "shutter_angle_degrees",
    "fps",
    "contains_estimated",
    "disclosed",
    "labelled_as_longer_sensor_exposure",
    "frames",
    "domain",
    "reference_energy",
    "reference_trail",
)


def _radiance(value: object, name: str) -> float:
    number = _GATE.finite_number(value, name)
    _GATE.require(number >= 0.0, name + " must be >= 0")
    return number


def integrate(frames: list[dict]) -> tuple[float, float]:
    energy = math.fsum(frame["weight"] * frame["radiance"] for frame in frames)
    positions = [frame["position"] for frame in frames if frame["weight"] > 0.0]
    trail = (max(positions) - min(positions)) if positions else 0.0
    return energy, trail


def evaluate(payload: dict) -> dict:
    document = _GATE.exact_keys(payload, set(PAYLOAD_KEYS), "payload")
    evidence = _GATE.evidence_id(document["evidenceId"])
    repeat = _GATE.repeat_text(document["repeat"])
    frames = _GATE.check_extra(
        _GATE.parse_frames(document["frames"], ("position", "radiance")),
        {"position": _GATE.finite_number, "radiance": _radiance},
    )
    angle = _GATE.optional_positive(document["shutter_angle_degrees"], "shutter_angle_degrees")
    fps = _GATE.optional_positive(document["fps"], "fps")
    contains_estimated = _GATE.flag(document["contains_estimated"], "contains_estimated")
    disclosed = _GATE.flag(document["disclosed"], "disclosed")
    labelled = _GATE.flag(document["labelled_as_longer_sensor_exposure"], "labelled_as_longer_sensor_exposure")
    domain = document["domain"]
    _GATE.require(domain in DOMAINS, "domain must be linear or display")
    reference_energy = _GATE.finite_number(document["reference_energy"], "reference_energy")
    reference_trail = _GATE.finite_number(document["reference_trail"], "reference_trail")

    rejected, scope_reasons = _GATE.scope_problems(
        frames,
        contains_estimated=contains_estimated,
        disclosed=disclosed,
        labelled_as_longer_sensor_exposure=labelled,
        shutter_angle_degrees=angle,
        fps=fps,
    )
    energy, trail = integrate(frames)
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        *scope_reasons,
        f"integrated linear energy {energy}",
        f"trail extent {trail}",
    ]
    if domain == "display":
        rejected.append(DISPLAY_TOKEN)
        reasons.append(NEGATIVE)
    else:
        if abs(energy - reference_energy) > _GATE.WEIGHT_TOLERANCE:
            rejected.append(ENERGY_TOKEN)
            reasons.append("linear-domain energy missed the independent reference")
        if abs(trail - reference_trail) > _GATE.WEIGHT_TOLERANCE:
            rejected.append(TRAIL_TOKEN)
            reasons.append("trail extent missed the independent reference")
        if ENERGY_TOKEN not in rejected and TRAIL_TOKEN not in rejected:
            reasons.append("linear energy and trail match within 1e-6")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("linear integration retained; physical behavior stays open")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": _GATE.preserved_for(evidence, angle, fps, [f"energy:{energy}"]),
        "openQuestions": _GATE.open_questions(REPEAT),
    }
    return _GATE.seal(result, evidence)
