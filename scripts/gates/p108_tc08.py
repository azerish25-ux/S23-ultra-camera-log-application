"""TC-P108-08 Whole-clip acceptance.

Host fixture. A favorable mean score must not hide a small number of severe boundary failures.
Decision is recorded or rejected only.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P108-08"
NAME = 'Whole-clip acceptance'
INTERVENTION = 'Evaluate complete difficult clips at normal playback rather than selected best frames.'
EXPECTED = 'Record catastrophic artifacts separately and limit release settings where failures remain unacceptable.'
NEGATIVE = 'A favorable mean score must not hide a small number of severe boundary failures.'
REPEAT = 'Repeat blinded presentation, moderate blur, aggressive blur, and held-out scenes.'
NEGATIVE_TOKEN = 'mean-hides-severe-boundary-failures'
PAYLOAD_KEYS = ('evidenceId', 'repeat', 'depthSamples', 'threshold', 'flows', 'flow_threshold', 'smoothed', 'sampleLabels', 'outputLabels', 'frameScores', 'severeBoundaryFailures', 'releaseLimited')

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



FAVORABLE_MEAN = 0.8


def evaluate(payload: dict) -> dict:
    """A high mean must not hide severe boundary failures on the whole clip."""
    _require_keys(payload)
    gate = _gate()
    observation = gate.read_observation(payload)
    scores = payload["frameScores"]
    gate.require(isinstance(scores, list) and len(scores) >= 1, "frameScores must contain at least 1 number")
    numbers = [gate.finite_number(value, f"frameScores[{index}]") for index, value in enumerate(scores)]
    severe = payload["severeBoundaryFailures"]
    gate.require(type(severe) is int and severe >= 0, "severeBoundaryFailures must be a non-negative int")
    gate.require(type(payload["releaseLimited"]) is bool, "releaseLimited must be a bool")
    mean = sum(numbers) / len(numbers)
    rejected = list(observation["rejected"])
    extra = [f"mean_score={mean}", f"severe_boundary_failures={severe}"]
    hidden = severe > 0 and (not payload["releaseLimited"]) and mean >= FAVORABLE_MEAN
    unlimited = severe > 0 and (not payload["releaseLimited"]) and mean < FAVORABLE_MEAN
    if hidden:
        rejected.insert(0, NEGATIVE_TOKEN)
        extra.append(NEGATIVE)
        extra.append("favorable mean hid severe boundary failures")
    elif unlimited:
        rejected.insert(0, "severe-boundary-failures-not-limited")
        extra.append("severe boundary failures were not recorded as a release limit")
    elif severe > 0:
        extra.append("severe boundary failures were recorded and release was limited")
    else:
        extra.append("whole clip recorded no severe boundary failures")
    return _finish(observation, rejected, extra)
