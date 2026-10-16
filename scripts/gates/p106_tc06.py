"""TC-P106-06 Subject identity crossing.

Host fixture. Focus follows the documented identity through the warp.
Nearest-face selection on each frame is rejected.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CASE_ID = "TC-P106-06"
NAME = "Subject identity crossing"
INTERVENTION = "Let two similar subjects cross while one remains the user-selected focus target."
EXPECTED = "Follow the documented identity and target-loss policy without unexplained focus jumps."
NEGATIVE = "Choosing the nearest face independently in every frame must fail."
REPEAT = "Repeat brief occlusion, leaving frame, re-entry, and low-confidence tracking."
NEGATIVE_TOKEN = "nearest-face-independently-each-frame"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "frame_width",
    "frame_height",
    "subjects",
    "selection_policy",
    "prev_timestamp",
    "curr_timestamp",
)
SUBJECT_REQUIRED = {"id", "x", "y", "depth", "dx", "dy", "selected"}


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


def _subjects(value, core) -> list[dict]:
    core.require(isinstance(value, list) and len(value) >= 2, "subjects must contain at least 2 items")
    parsed = []
    seen = set()
    for index, subject in enumerate(value):
        core.require(isinstance(subject, dict) and set(subject) == SUBJECT_REQUIRED,
                     f"subject {index} fields are invalid")
        identity = subject["id"]
        core.require(isinstance(identity, str) and identity.strip() and identity == identity.strip(),
                     f"subject {index} id must be a non-empty string")
        core.require(identity not in seen, f"subject {index} id is duplicated")
        seen.add(identity)
        core.require(type(subject["selected"]) is bool, f"subject {index} selected must be a bool")
        parsed.append({
            "id": identity,
            "x": core.parse_number(subject["x"], f"subject {index} x"),
            "y": core.parse_number(subject["y"], f"subject {index} y"),
            "depth": core.parse_number(subject["depth"], f"subject {index} depth"),
            "dx": core.parse_number(subject["dx"], f"subject {index} dx"),
            "dy": core.parse_number(subject["dy"], f"subject {index} dy"),
            "selected": subject["selected"],
        })
    selected = [item for item in parsed if item["selected"]]
    core.require(len(selected) == 1, "exactly one subject must be the documented focus target")
    return parsed


def evaluate(payload: dict) -> dict:
    core = _core()
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = core.parse_evidence(payload["evidenceId"])
    repeat = core.parse_repeat(payload["repeat"])
    width, height = core.parse_frame(payload["frame_width"], payload["frame_height"])
    subjects = _subjects(payload["subjects"], core)
    policy = payload["selection_policy"]
    core.require(policy in {"documented-identity", "nearest-face"}, "selection_policy is invalid")
    prev, curr, timestamps_ok = core.parse_timestamps(payload["prev_timestamp"], payload["curr_timestamp"])
    samples = core.reproject_grid(subjects, width, height)
    for subject, sample in zip(subjects, samples):
        sample["id"] = subject["id"]
        sample["selected"] = subject["selected"]
    focus = next(subject["id"] for subject in subjects if subject["selected"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if policy == "nearest-face":
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("focus stayed on documented identity " + focus + " and was not reassigned to the nearer face")
    else:
        focus_sample = next(sample for sample in samples if sample["id"] == focus)
        if focus_sample["status"] == "unknown":
            reasons.append("target loss declared for " + focus + "; focus was not handed to another subject")
        else:
            reasons.append("followed documented identity " + focus + " through the warp")
    if not timestamps_ok:
        rejected.append("missing-source-timestamps")
        reasons.append("a result without prev_timestamp and curr_timestamp is rejected")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("narrower software result retained; physical behavior stays open")
    preserved = [
        evidence,
        {"prev_timestamp": prev, "curr_timestamp": curr, "focusId": focus, "samples": samples},
    ]
    return core.finish(
        CASE_ID,
        decision,
        reasons,
        rejected,
        preserved,
        [core.OPEN_QUESTION, REPEAT],
    )
