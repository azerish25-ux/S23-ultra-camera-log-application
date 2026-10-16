"""TC-P106-01 History without reprojection.

Host fixture. Unaligned history is rejected; a real backward flow is warped.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CASE_ID = "TC-P106-01"
NAME = "History without reprojection"
INTERVENTION = "Move a known object while previous depth remains in its original pixel coordinates."
EXPECTED = "Reject unaligned history or warp it correctly before temporal blending."
NEGATIVE = "A stationary-pixel average that leaves depth trails must fail."
REPEAT = "Repeat translation, rotation, scale change, and camera motion."
NEGATIVE_TOKEN = "stationary-pixel-average-depth-trails"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "frame_width",
    "frame_height",
    "motion_px",
    "points",
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
    motion = core.parse_motion(payload["motion_px"])
    points = core.parse_points(payload["points"])
    prev, curr, timestamps_ok = core.parse_timestamps(payload["prev_timestamp"], payload["curr_timestamp"])
    samples = core.reproject_grid(points, width, height)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if motion > 0 and all(point["dx"] == 0 and point["dy"] == 0 for point in points):
        rejected.append(NEGATIVE_TOKEN)
        rejected.append(core.MUTANT)
        reasons.append(NEGATIVE)
        reasons.append("history stayed on the original pixel indices while motion_px > 0")
    else:
        reasons.append("backward flow moved previous depth before blending")
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
