"""TC-P105-06 Subject identity crossing.

Host reference. The directive negative must not come back as qualified or allowed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P105-06",
    "phase": "P105",
    "workstream": 14,
    "name": "Subject identity crossing",
    "intervention": "Let two similar subjects cross while one remains the user-selected focus target.",
    "expected": "Follow the documented identity and target-loss policy without unexplained focus jumps.",
    "negative": "Choosing the nearest face independently in every frame must fail.",
    "repeat": "Repeat brief occlusion, leaving frame, re-entry, and low-confidence tracking.",
}

NEGATIVE_TOKEN = "nearest-face-independently-every-frame"
PAYLOAD_KEYS = ('evidenceId', 'repeat', 'nominalFramePeriodMs', 'frameTimestampsMs', 'lumaMeans', 'hideGap', 'useKeyframeAsBaseline', 'keyframeScore', 'focusPolicy')


def _load_gate():
    path = Path(__file__).resolve().parent / "p105_establish_temporal_baselines.py"
    spec = importlib.util.spec_from_file_location("p105_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    policy = _GATE.require_text(payload["focusPolicy"], "focusPolicy")
    _GATE.require(
        policy in {"documented-identity", "nearest-face-per-frame"},
        "focusPolicy is not recognized",
    )
    if policy == "nearest-face-per-frame":
        faults.append(NEGATIVE_TOKEN)
    extra = [{"focusPolicy": policy}]
    texts = {NEGATIVE_TOKEN: CASE["negative"]}
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
