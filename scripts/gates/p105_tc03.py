"""TC-P105-03 Relative-scale pumping.

Host reference. The directive negative must not come back as qualified or allowed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P105-03",
    "phase": "P105",
    "workstream": 14,
    "name": "Relative-scale pumping",
    "intervention": "Introduce a near object or scene-content change that alters raw model depth normalization.",
    "expected": "Align valid relative depth consistently or reset honestly without arbitrary global focus shifts.",
    "negative": "Independent min-max normalization per frame must fail.",
    "repeat": "Repeat stationary backgrounds with changing foreground occupancy.",
}

NEGATIVE_TOKEN = "independent-min-max-normalization-per-frame"
PAYLOAD_KEYS = ('evidenceId', 'repeat', 'nominalFramePeriodMs', 'frameTimestampsMs', 'lumaMeans', 'hideGap', 'useKeyframeAsBaseline', 'keyframeScore', 'normalization')


def _load_gate():
    path = Path(__file__).resolve().parent / "p105_establish_temporal_baselines.py"
    spec = importlib.util.spec_from_file_location("p105_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    normalization = _GATE.require_text(payload["normalization"], "normalization")
    _GATE.require(
        normalization in {"aligned-relative", "independent-minmax"},
        "normalization is not recognized",
    )
    if normalization == "independent-minmax":
        faults.append(NEGATIVE_TOKEN)
    extra = [{"normalization": normalization}]
    texts = {NEGATIVE_TOKEN: CASE["negative"]}
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
