"""TC-P105-01 History without reprojection.

Host reference. The directive negative must not come back as qualified or allowed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P105-01",
    "phase": "P105",
    "workstream": 14,
    "name": "History without reprojection",
    "intervention": "Move a known object while previous depth remains in its original pixel coordinates.",
    "expected": "Reject unaligned history or warp it correctly before temporal blending.",
    "negative": "A stationary-pixel average that leaves depth trails must fail.",
    "repeat": "Repeat translation, rotation, scale change, and camera motion.",
}

NEGATIVE_TOKEN = "stationary-pixel-average-leaves-depth-trails"
PAYLOAD_KEYS = ('evidenceId', 'repeat', 'nominalFramePeriodMs', 'frameTimestampsMs', 'lumaMeans', 'hideGap', 'useKeyframeAsBaseline', 'keyframeScore', 'objectShiftPx', 'historyShiftPx')


def _load_gate():
    path = Path(__file__).resolve().parent / "p105_establish_temporal_baselines.py"
    spec = importlib.util.spec_from_file_location("p105_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    object_shift = _GATE.require_number(payload["objectShiftPx"], "objectShiftPx")
    history_shift = _GATE.require_number(payload["historyShiftPx"], "historyShiftPx")
    if history_shift == 0 and object_shift != 0:
        faults.append(NEGATIVE_TOKEN)
    elif history_shift != object_shift:
        faults.append("unaligned-history")
    extra = [{"objectShiftPx": object_shift, "historyShiftPx": history_shift}]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        "unaligned-history": "unaligned history must be rejected or warped before temporal blending",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
