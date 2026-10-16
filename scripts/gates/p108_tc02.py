"""TC-P108-02 Disoccluded background.

Host fixture. Filling all newly visible pixels with old depth must fail.
Decision is recorded or rejected only.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P108-02"
NAME = 'Disoccluded background'
INTERVENTION = 'Reveal new background behind a moving foreground object where historical depth is invalid.'
EXPECTED = 'Use current evidence and uncertainty rather than smearing previous foreground values into the new region.'
NEGATIVE = 'Filling all newly visible pixels with old depth must fail.'
REPEAT = 'Repeat thin objects, hands, hair, and large foreground occluders.'
NEGATIVE_TOKEN = 'filled-unknown-labelled-measured'
PAYLOAD_KEYS = ('evidenceId', 'repeat', 'depthSamples', 'threshold', 'flows', 'flow_threshold', 'smoothed', 'sampleLabels', 'outputLabels', 'newlyVisibleIndex', 'oldDepth', 'filledDepth')

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



def evaluate(payload: dict) -> dict:
    """Newly visible unknown samples must stay unknown. Old depth labelled measured is rejected."""
    _require_keys(payload)
    gate = _gate()
    observation = gate.read_observation(payload)
    index = payload["newlyVisibleIndex"]
    gate.require(type(index) is int and 0 <= index < len(observation["sample_labels"]),
                 "newlyVisibleIndex must address a sample")
    gate.require(observation["sample_labels"][index] == "unknown",
                 "newly visible sample must be marked unknown")
    old_depth = gate.finite_number(payload["oldDepth"], "oldDepth")
    filled_depth = gate.finite_number(payload["filledDepth"], "filledDepth")
    filled_with_old = (
        observation["output_labels"][index] == "measured" and filled_depth == old_depth
    )
    rejected = list(observation["rejected"])
    extra = []
    if filled_with_old:
        if NEGATIVE_TOKEN not in rejected:
            rejected.insert(0, NEGATIVE_TOKEN)
        extra.append(NEGATIVE)
        extra.append("newly visible pixel was filled with the previous foreground depth and labelled measured")
    else:
        extra.append("newly visible pixel stayed unknown")
    return _finish(observation, rejected, extra)
