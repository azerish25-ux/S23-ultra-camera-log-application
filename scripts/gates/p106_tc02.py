"""TC-P106-02 Disoccluded background.

Host fixture. Newly visible pixels stay unknown instead of inheriting old depth.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CASE_ID = "TC-P106-02"
NAME = "Disoccluded background"
INTERVENTION = "Reveal new background behind a moving foreground object where historical depth is invalid."
EXPECTED = "Use current evidence and uncertainty rather than smearing previous foreground values into the new region."
NEGATIVE = "Filling all newly visible pixels with old depth must fail."
REPEAT = "Repeat thin objects, hands, hair, and large foreground occluders."
NEGATIVE_TOKEN = "filled-newly-visible-with-old-depth"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "frame_width",
    "frame_height",
    "points",
    "revealed_pixels",
    "filled_depth",
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


def _revealed(pixels, width, height, core) -> list[dict]:
    core.require(isinstance(pixels, list) and pixels, "revealed_pixels must be a non-empty list")
    parsed = []
    for index, pixel in enumerate(pixels):
        core.require(isinstance(pixel, dict) and set(pixel) == {"x", "y"},
                     f"revealed pixel {index} must have x and y")
        x = core.parse_number(pixel["x"], f"revealed pixel {index} x")
        y = core.parse_number(pixel["y"], f"revealed pixel {index} y")
        core.require(0 <= x < width and 0 <= y < height, f"revealed pixel {index} is outside the frame")
        parsed.append({"x": x, "y": y, "depth": None, "status": "unknown", "cause": "disoccluded"})
    return parsed


def evaluate(payload: dict) -> dict:
    core = _core()
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = core.parse_evidence(payload["evidenceId"])
    repeat = core.parse_repeat(payload["repeat"])
    width, height = core.parse_frame(payload["frame_width"], payload["frame_height"])
    points = core.parse_points(payload["points"])
    prev, curr, timestamps_ok = core.parse_timestamps(payload["prev_timestamp"], payload["curr_timestamp"])
    samples = core.reproject_grid(points, width, height)
    revealed = _revealed(payload["revealed_pixels"], width, height, core)
    filled = payload["filled_depth"]
    if filled is not None:
        core.parse_number(filled, "filled_depth")
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if filled is not None:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("newly visible pixels were left unknown; old foreground depth was not copied")
    else:
        reasons.append("disoccluded pixels stay invalid rather than filled with stale foreground depth")
    if not timestamps_ok:
        rejected.append("missing-source-timestamps")
        reasons.append("a result without prev_timestamp and curr_timestamp is rejected")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("narrower software result retained; physical behavior stays open")
    preserved = [
        evidence,
        {"prev_timestamp": prev, "curr_timestamp": curr, "samples": samples, "revealed": revealed},
    ]
    return core.finish(
        CASE_ID,
        decision,
        reasons,
        rejected,
        preserved,
        [core.OPEN_QUESTION, REPEAT],
    )
