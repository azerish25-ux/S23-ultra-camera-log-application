"""TC-P108-06 Subject identity crossing.

Host fixture. Choosing the nearest face independently in every frame must fail.
Decision is recorded or rejected only.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P108-06"
NAME = 'Subject identity crossing'
INTERVENTION = 'Let two similar subjects cross while one remains the user-selected focus target.'
EXPECTED = 'Follow the documented identity and target-loss policy without unexplained focus jumps.'
NEGATIVE = 'Choosing the nearest face independently in every frame must fail.'
REPEAT = 'Repeat brief occlusion, leaving frame, re-entry, and low-confidence tracking.'
NEGATIVE_TOKEN = 'nearest-face-independently-every-frame'
PAYLOAD_KEYS = ('evidenceId', 'repeat', 'depthSamples', 'threshold', 'flows', 'flow_threshold', 'smoothed', 'sampleLabels', 'outputLabels', 'selectedTarget', 'nearestFaceByFrame', 'chosenFaceByFrame')

_GATE = None


def _gate():
    global _GATE
    if _GATE is None:
        path = Path(__file__).resolve().parent / "p108_detect_occlusion_and_scene_discontinuities.py"
        spec = importlib.util.spec_from_file_location("p108_detect_occlusion_and_scene_discontinuities", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _GATE = module
    return _GATE


def _require_keys(payload: dict) -> None:
    gate = _gate()
    gate.require(isinstance(payload, dict), "payload must be an object")
    missing = set(PAYLOAD_KEYS) - set(payload)
    extra = set(payload) - set(PAYLOAD_KEYS)
    gate.require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    gate.require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))


def _finish(observation: dict, rejected: list[str], extra_reasons: list[str]) -> dict:
    gate = _gate()
    reasons = gate.case_reasons(
        CASE_ID,
        NAME,
        observation["repeat"],
        EXPECTED,
        INTERVENTION,
        observation["counts"],
        extra_reasons,
    )
    return gate.finish(
        case_id=CASE_ID,
        evidence=observation["evidence"],
        claim=CASE_ID,
        counts=observation["counts"],
        rejected=rejected,
        reasons=reasons,
        open_questions=[gate.OPEN_QUESTION, REPEAT],
    )



def _faces(value, label):
    gate = _gate()
    gate.require(isinstance(value, list) and len(value) >= 1, label + " must contain at least 1 id")
    parsed = []
    for index, item in enumerate(value):
        gate.require(isinstance(item, str) and item.strip() and item == item.strip(),
                     f"{label}[{index}] must be a non-empty string")
        parsed.append(item)
    return parsed


def evaluate(payload: dict) -> dict:
    """Keep the selected target. Do not retarget to whichever face is nearest."""
    _require_keys(payload)
    gate = _gate()
    observation = gate.read_observation(payload)
    selected = gate.non_empty_string(payload["selectedTarget"], "selectedTarget")
    nearest = _faces(payload["nearestFaceByFrame"], "nearestFaceByFrame")
    chosen = _faces(payload["chosenFaceByFrame"], "chosenFaceByFrame")
    gate.require(len(nearest) == len(chosen), "nearest and chosen face sequences must match")
    follows_nearest = all(choice == near for choice, near in zip(chosen, nearest))
    nearest_leaves = any(near != selected for near in nearest)
    rejected = list(observation["rejected"])
    extra = []
    if follows_nearest and nearest_leaves:
        rejected.insert(0, NEGATIVE_TOKEN)
        extra.append(NEGATIVE)
        extra.append("chosen face matched the nearest face after it left the selected target")
    elif any(choice != selected for choice in chosen):
        rejected.insert(0, "unexplained-focus-jump")
        extra.append("chosen face left the documented target")
    else:
        extra.append("chosen face stayed on the documented target")
    return _finish(observation, rejected, extra)
