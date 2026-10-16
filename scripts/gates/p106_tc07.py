"""TC-P106-07 Bokeh ordering and leakage.

Host fixture. Layered coverage is recorded. Uniform background blur is not.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CASE_ID = "TC-P106-07"
NAME = "Bokeh ordering and leakage"
INTERVENTION = "Render strong foreground defocus with bright lights behind an in-focus opaque subject."
EXPECTED = "Respect layering and normalized energy while declaring unavoidable missing-background approximations."
NEGATIVE = "Uniform background blur with no foreground coverage model must fail."
REPEAT = "Repeat perfect-depth and estimated-depth inputs to isolate the faulty subsystem."
NEGATIVE_TOKEN = "uniform-background-blur-without-foreground-coverage"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "foreground_depth",
    "background_depth",
    "foreground_coverage",
    "model",
    "prev_timestamp",
    "curr_timestamp",
)


def _core():
    name = "p106_implement_flow_based_history_reprojection"
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def evaluate(payload: dict) -> dict:
    core = _core()
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = core.parse_evidence(payload["evidenceId"])
    repeat = core.parse_repeat(payload["repeat"])
    foreground = core.parse_number(payload["foreground_depth"], "foreground_depth")
    background = core.parse_number(payload["background_depth"], "background_depth")
    coverage = core.parse_number(payload["foreground_coverage"], "foreground_coverage")
    core.require(0 <= coverage <= 1, "foreground_coverage must be in [0, 1]")
    core.require(foreground < background, "foreground must be nearer than background")
    model = payload["model"]
    core.require(model in {"layered-coverage", "uniform-background-blur"}, "model is invalid")
    prev, curr, timestamps_ok = core.parse_timestamps(payload["prev_timestamp"], payload["curr_timestamp"])
    background_weight = 1.0 - coverage
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    layers = {
        "foreground_depth": foreground,
        "background_depth": background,
        "foreground_coverage": coverage,
        "background_weight": background_weight,
        "energy": coverage + background_weight,
    }
    if model == "uniform-background-blur":
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    else:
        reasons.append("layered coverage energy is normalized")
        if coverage == 1:
            layers["background_status"] = "unknown"
            reasons.append("occluded background is an approximation, not a measured sample")
        else:
            layers["background_status"] = "partial"
            reasons.append("uncovered background keeps weight 1 - coverage and is not a uniform blur")
    if not timestamps_ok:
        rejected.append("missing-source-timestamps")
        reasons.append("a result without prev_timestamp and curr_timestamp is rejected")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("narrower software result retained; physical behavior stays open")
    preserved = [evidence, {"prev_timestamp": prev, "curr_timestamp": curr, "layers": layers}]
    return core.finish(
        CASE_ID,
        decision,
        reasons,
        rejected,
        preserved,
        [core.OPEN_QUESTION, REPEAT],
    )
