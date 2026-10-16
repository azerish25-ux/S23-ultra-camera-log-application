"""TC-P105-02 Disoccluded background.

Host reference. The directive negative must not come back as qualified or allowed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P105-02",
    "phase": "P105",
    "workstream": 14,
    "name": "Disoccluded background",
    "intervention": "Reveal new background behind a moving foreground object where historical depth is invalid.",
    "expected": "Use current evidence and uncertainty rather than smearing previous foreground values into the new region.",
    "negative": "Filling all newly visible pixels with old depth must fail.",
    "repeat": "Repeat thin objects, hands, hair, and large foreground occluders.",
}

NEGATIVE_TOKEN = "filling-newly-visible-pixels-with-old-depth"
PAYLOAD_KEYS = ('evidenceId', 'repeat', 'nominalFramePeriodMs', 'frameTimestampsMs', 'lumaMeans', 'hideGap', 'useKeyframeAsBaseline', 'keyframeScore', 'newlyVisiblePixels', 'filledFromOldDepth')


def _load_gate():
    path = Path(__file__).resolve().parent / "p105_establish_temporal_baselines.py"
    spec = importlib.util.spec_from_file_location("p105_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    newly = _GATE.require_count(payload["newlyVisiblePixels"], "newlyVisiblePixels")
    filled = _GATE.require_count(payload["filledFromOldDepth"], "filledFromOldDepth")
    _GATE.require(filled <= newly, "filledFromOldDepth cannot exceed newlyVisiblePixels")
    if filled > 0:
        faults.append(NEGATIVE_TOKEN)
    extra = [{"newlyVisiblePixels": newly, "filledFromOldDepth": filled}]
    texts = {NEGATIVE_TOKEN: CASE["negative"]}
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
