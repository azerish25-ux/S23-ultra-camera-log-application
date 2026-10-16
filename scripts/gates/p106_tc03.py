"""TC-P106-03 Relative-scale pumping.

Host fixture. Source depths ride through the warp. Independent min-max fails.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

CASE_ID = "TC-P106-03"
NAME = "Relative-scale pumping"
INTERVENTION = "Introduce a near object or scene-content change that alters raw model depth normalization."
EXPECTED = "Align valid relative depth consistently or reset honestly without arbitrary global focus shifts."
NEGATIVE = "Independent min-max normalization per frame must fail."
REPEAT = "Repeat stationary backgrounds with changing foreground occupancy."
NEGATIVE_TOKEN = "independent-minmax-per-frame"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "source_depths",
    "reported_depths",
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


def _depths(value, label, core) -> list[float]:
    core.require(isinstance(value, list) and len(value) >= 2, label + " must contain at least 2 numbers")
    return [core.parse_number(item, f"{label}[{index}]") for index, item in enumerate(value)]


def _matches(left: list[float], right: list[float]) -> bool:
    return len(left) == len(right) and all(math.isclose(a, b, rel_tol=0, abs_tol=1e-9) for a, b in zip(left, right))


def _minmax(values: list[float], core) -> list[float]:
    lo = min(values)
    hi = max(values)
    core.require(hi > lo, "minmax span is zero")
    span = hi - lo
    return [(value - lo) / span for value in values]


def evaluate(payload: dict) -> dict:
    core = _core()
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = core.parse_evidence(payload["evidenceId"])
    repeat = core.parse_repeat(payload["repeat"])
    source = _depths(payload["source_depths"], "source_depths", core)
    reported = _depths(payload["reported_depths"], "reported_depths", core)
    core.require(len(source) == len(reported), "reported_depths length must match source_depths")
    prev, curr, timestamps_ok = core.parse_timestamps(payload["prev_timestamp"], payload["curr_timestamp"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if not _matches(source, reported):
        if _matches(reported, _minmax(source, core)):
            rejected.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
        else:
            rejected.append("relative-depth-changed")
            reasons.append("reprojected depth must keep source values; arbitrary rescaling is not alignment")
    else:
        reasons.append("source relative depth kept; no independent min-max was applied")
    if not timestamps_ok:
        rejected.append("missing-source-timestamps")
        reasons.append("a result without prev_timestamp and curr_timestamp is rejected")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("narrower software result retained; physical behavior stays open")
    preserved = [
        evidence,
        {"prev_timestamp": prev, "curr_timestamp": curr, "source_depths": source, "kept_depths": source},
    ]
    return core.finish(
        CASE_ID,
        decision,
        reasons,
        rejected,
        preserved,
        [core.OPEN_QUESTION, REPEAT],
    )
