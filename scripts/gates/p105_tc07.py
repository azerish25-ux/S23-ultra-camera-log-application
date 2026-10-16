"""TC-P105-07 Bokeh ordering and leakage.

Host reference. The directive negative must not come back as qualified or allowed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P105-07",
    "phase": "P105",
    "workstream": 14,
    "name": "Bokeh ordering and leakage",
    "intervention": "Render strong foreground defocus with bright lights behind an in-focus opaque subject.",
    "expected": "Respect layering and normalized energy while declaring unavoidable missing-background approximations.",
    "negative": "Uniform background blur with no foreground coverage model must fail.",
    "repeat": "Repeat perfect-depth and estimated-depth inputs to isolate the faulty subsystem.",
}

NEGATIVE_TOKEN = "uniform-background-blur-without-foreground-coverage"
PAYLOAD_KEYS = ('evidenceId', 'repeat', 'nominalFramePeriodMs', 'frameTimestampsMs', 'lumaMeans', 'hideGap', 'useKeyframeAsBaseline', 'keyframeScore', 'blurMode', 'foregroundCoverageModel')


def _load_gate():
    path = Path(__file__).resolve().parent / "p105_establish_temporal_baselines.py"
    spec = importlib.util.spec_from_file_location("p105_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    blur_mode = _GATE.require_text(payload["blurMode"], "blurMode")
    coverage = _GATE.require_bool(payload["foregroundCoverageModel"], "foregroundCoverageModel")
    _GATE.require(blur_mode in {"layered", "uniform-background"}, "blurMode is not recognized")
    if blur_mode == "uniform-background" and coverage is False:
        faults.append(NEGATIVE_TOKEN)
    extra = [{"blurMode": blur_mode, "foregroundCoverageModel": coverage}]
    texts = {NEGATIVE_TOKEN: CASE["negative"]}
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
