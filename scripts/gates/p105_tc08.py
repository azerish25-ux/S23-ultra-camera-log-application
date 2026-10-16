"""TC-P105-08 Whole-clip acceptance.

Host reference. The directive negative must not come back as qualified or allowed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import statistics

CASE = {
    "id": "TC-P105-08",
    "phase": "P105",
    "workstream": 14,
    "name": "Whole-clip acceptance",
    "intervention": "Evaluate complete difficult clips at normal playback rather than selected best frames.",
    "expected": "Record catastrophic artifacts separately and limit release settings where failures remain unacceptable.",
    "negative": "A favorable mean score must not hide a small number of severe boundary failures.",
    "repeat": "Repeat blinded presentation, moderate blur, aggressive blur, and held-out scenes.",
}

NEGATIVE_TOKEN = "favorable-mean-hides-severe-boundary-failures"
PAYLOAD_KEYS = ('evidenceId', 'repeat', 'nominalFramePeriodMs', 'frameTimestampsMs', 'lumaMeans', 'hideGap', 'useKeyframeAsBaseline', 'keyframeScore', 'frameScores', 'severeBoundaryFailures', 'scoreReduction')


def _load_gate():
    path = Path(__file__).resolve().parent / "p105_establish_temporal_baselines.py"
    spec = importlib.util.spec_from_file_location("p105_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    scores = payload["frameScores"]
    _GATE.require(
        isinstance(scores, list) and len(scores) == bundle["metrics"]["frameCount"],
        "frameScores must match the frame count",
    )
    numbers = [
        _GATE.require_number(item, f"frameScores[{index}]") for index, item in enumerate(scores)
    ]
    severe = _GATE.require_count(payload["severeBoundaryFailures"], "severeBoundaryFailures")
    reduction = _GATE.require_text(payload["scoreReduction"], "scoreReduction")
    _GATE.require(reduction in {"separate-severe", "mean-only"}, "scoreReduction is not recognized")
    if len(numbers) == 1 and "pretty-keyframe-score-as-sequence-baseline" not in faults:
        faults.append("pretty-keyframe-score-as-sequence-baseline")
    if severe > 0 and reduction == "mean-only":
        faults.append(NEGATIVE_TOKEN)
    mean_score = statistics.mean(numbers)
    extra = [{
        "meanFrameScore": mean_score,
        "severeBoundaryFailures": severe,
        "scoreReduction": reduction,
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        "pretty-keyframe-score-as-sequence-baseline": _GATE.FAULT_TEXT[
            "pretty-keyframe-score-as-sequence-baseline"
        ],
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
