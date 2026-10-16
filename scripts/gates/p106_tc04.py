"""TC-P106-04 Scene-cut contamination.

Host fixture. A real cut clears history even when timestamps stay continuous.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CASE_ID = "TC-P106-04"
NAME = "Scene-cut contamination"
INTERVENTION = "Join unrelated scenes or switch source clips while temporal state is populated."
EXPECTED = "Reset relevant history and prevent previous-image depth or color from leaking into the new shot."
NEGATIVE = "Continuous timestamps alone must not preserve temporal state across a real cut."
REPEAT = "Repeat hard cuts, fades, flashes, and rapid camera pans to test discrimination."
NEGATIVE_TOKEN = "continuous-timestamps-preserve-history-across-cut"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "scene_cut",
    "timestamps_continuous",
    "retain_history",
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
    for flag in ("scene_cut", "timestamps_continuous", "retain_history"):
        core.require(type(payload[flag]) is bool, flag + " must be a bool")
    prev, curr, timestamps_ok = core.parse_timestamps(payload["prev_timestamp"], payload["curr_timestamp"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if payload["scene_cut"] and payload["retain_history"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        if payload["timestamps_continuous"]:
            reasons.append("continuous timestamps did not authorize history across the cut")
    elif payload["scene_cut"]:
        reasons.append("history reset at the scene cut; previous depth did not leak")
    else:
        reasons.append("no scene cut; temporal state was not cleared by this case")
    if not timestamps_ok:
        rejected.append("missing-source-timestamps")
        reasons.append("a result without prev_timestamp and curr_timestamp is rejected")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("narrower software result retained; physical behavior stays open")
    history = "reset" if payload["scene_cut"] and not payload["retain_history"] else (
        "rejected" if payload["scene_cut"] else "eligible"
    )
    preserved = [
        evidence,
        {"prev_timestamp": prev, "curr_timestamp": curr, "history": history},
    ]
    return core.finish(
        CASE_ID,
        decision,
        reasons,
        rejected,
        preserved,
        [core.OPEN_QUESTION, REPEAT],
    )
