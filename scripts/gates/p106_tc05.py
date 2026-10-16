"""TC-P106-05 Mixed-pixel boundaries.

Host fixture. Partial coverage stays partial. Inconsistent flow stays unknown.
A dilated binary mask, or neighbour-filled unknowns called measured, fails.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CASE_ID = "TC-P106-05"
NAME = "Mixed-pixel boundaries"
INTERVENTION = "Use moving hair, glasses, smoke, or motion-blurred edges against detailed backgrounds."
EXPECTED = "Preserve plausible partial coverage and bound temporal halos under the selected safe settings."
NEGATIVE = "A dilated binary person mask must not pass demanding boundary quality by itself."
REPEAT = "Repeat backlighting, crossing subjects, and different foreground-background contrast."
NEGATIVE_TOKEN = "dilated-binary-person-mask-not-boundary-quality"
FILL_TOKEN = "unknowns-filled-from-neighbours-called-measured"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "frame_width",
    "frame_height",
    "points",
    "fill_unknowns_as_measured",
    "dilated_binary_mask_only",
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
    width, height = core.parse_frame(payload["frame_width"], payload["frame_height"])
    core.require(type(payload["fill_unknowns_as_measured"]) is bool, "fill_unknowns_as_measured must be a bool")
    core.require(type(payload["dilated_binary_mask_only"]) is bool, "dilated_binary_mask_only must be a bool")
    points = core.parse_points(payload["points"])
    core.require(all("coverage" in point for point in points), "each boundary point must declare coverage")
    prev, curr, timestamps_ok = core.parse_timestamps(payload["prev_timestamp"], payload["curr_timestamp"])
    samples = core.reproject_grid(points, width, height)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if payload["dilated_binary_mask_only"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if payload["fill_unknowns_as_measured"] and any(sample["status"] == "unknown" for sample in samples):
        rejected.append(FILL_TOKEN)
        reasons.append("inconsistent or empty samples stay unknown; neighbour depth was not called measured")
    if not rejected:
        reasons.append("partial coverage kept; forward-backward failures were not promoted to measured depth")
    if not timestamps_ok:
        rejected.append("missing-source-timestamps")
        reasons.append("a result without prev_timestamp and curr_timestamp is rejected")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("narrower software result retained; physical behavior stays open")
    preserved = [evidence, {"prev_timestamp": prev, "curr_timestamp": curr, "samples": samples}]
    return core.finish(
        CASE_ID,
        decision,
        reasons,
        rejected,
        preserved,
        [core.OPEN_QUESTION, REPEAT],
    )
