"""TC-P105-05 Mixed-pixel boundaries.

Host reference. The directive negative must not come back as qualified or allowed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P105-05",
    "phase": "P105",
    "workstream": 14,
    "name": "Mixed-pixel boundaries",
    "intervention": "Use moving hair, glasses, smoke, or motion-blurred edges against detailed backgrounds.",
    "expected": "Preserve plausible partial coverage and bound temporal halos under the selected safe settings.",
    "negative": "A dilated binary person mask must not pass demanding boundary quality by itself.",
    "repeat": "Repeat backlighting, crossing subjects, and different foreground-background contrast.",
}

NEGATIVE_TOKEN = "dilated-binary-person-mask-passes-boundary-quality"
PAYLOAD_KEYS = ('evidenceId', 'repeat', 'nominalFramePeriodMs', 'frameTimestampsMs', 'lumaMeans', 'hideGap', 'useKeyframeAsBaseline', 'keyframeScore', 'boundaryModel')


def _load_gate():
    path = Path(__file__).resolve().parent / "p105_establish_temporal_baselines.py"
    spec = importlib.util.spec_from_file_location("p105_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    boundary = _GATE.require_text(payload["boundaryModel"], "boundaryModel")
    _GATE.require(
        boundary in {"partial-coverage", "dilated-binary-mask"},
        "boundaryModel is not recognized",
    )
    if boundary == "dilated-binary-mask":
        faults.append(NEGATIVE_TOKEN)
    extra = [{"boundaryModel": boundary}]
    texts = {NEGATIVE_TOKEN: CASE["negative"]}
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
