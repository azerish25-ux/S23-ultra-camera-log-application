"""TC-P105-04 Scene-cut contamination.

Host reference. The directive negative must not come back as qualified or allowed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P105-04",
    "phase": "P105",
    "workstream": 14,
    "name": "Scene-cut contamination",
    "intervention": "Join unrelated scenes or switch source clips while temporal state is populated.",
    "expected": "Reset relevant history and prevent previous-image depth or color from leaking into the new shot.",
    "negative": "Continuous timestamps alone must not preserve temporal state across a real cut.",
    "repeat": "Repeat hard cuts, fades, flashes, and rapid camera pans to test discrimination.",
}

NEGATIVE_TOKEN = "continuous-timestamps-preserve-state-across-cut"
PAYLOAD_KEYS = ('evidenceId', 'repeat', 'nominalFramePeriodMs', 'frameTimestampsMs', 'lumaMeans', 'hideGap', 'useKeyframeAsBaseline', 'keyframeScore', 'sceneCut', 'historyReset')


def _load_gate():
    path = Path(__file__).resolve().parent / "p105_establish_temporal_baselines.py"
    spec = importlib.util.spec_from_file_location("p105_gate_for_tc04", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    scene_cut = _GATE.require_bool(payload["sceneCut"], "sceneCut")
    history_reset = _GATE.require_bool(payload["historyReset"], "historyReset")
    if scene_cut and not history_reset:
        faults.append(NEGATIVE_TOKEN)
    extra = [{"sceneCut": scene_cut, "historyReset": history_reset}]
    texts = {NEGATIVE_TOKEN: CASE["negative"]}
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
