"""TC-P106-08 Whole-clip acceptance.

Host fixture. Severe frames stay listed. A favorable mean cannot hide them.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CASE_ID = "TC-P106-08"
NAME = "Whole-clip acceptance"
INTERVENTION = "Evaluate complete difficult clips at normal playback rather than selected best frames."
EXPECTED = "Record catastrophic artifacts separately and limit release settings where failures remain unacceptable."
NEGATIVE = "A favorable mean score must not hide a small number of severe boundary failures."
REPEAT = "Repeat blinded presentation, moderate blur, aggressive blur, and held-out scenes."
NEGATIVE_TOKEN = "mean-hides-severe-boundary-failures"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "frame_scores",
    "catastrophic_threshold",
    "report",
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
    scores_in = payload["frame_scores"]
    core.require(isinstance(scores_in, list) and len(scores_in) >= 3, "frame_scores must contain at least 3 numbers")
    scores = []
    for index, score in enumerate(scores_in):
        number = core.parse_number(score, f"frame_scores[{index}]")
        core.require(0 <= number <= 1, f"frame_scores[{index}] must be in [0, 1]")
        scores.append(number)
    threshold = core.parse_number(payload["catastrophic_threshold"], "catastrophic_threshold")
    core.require(0 < threshold <= 1, "catastrophic_threshold must be in (0, 1]")
    report = payload["report"]
    core.require(report in {"mean-only", "separated-catastrophes"}, "report is invalid")
    prev, curr, timestamps_ok = core.parse_timestamps(payload["prev_timestamp"], payload["curr_timestamp"])
    severe = [index for index, score in enumerate(scores) if score < threshold]
    mean = sum(scores) / len(scores)
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        INTERVENTION,
        f"mean score {mean:.6f} over {len(scores)} frames",
    ]
    rejected: list[str] = []
    if severe and report == "mean-only":
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("severe frame indexes " + ",".join(str(index) for index in severe))
    elif report == "separated-catastrophes":
        reasons.append("catastrophic frames recorded separately: " + ",".join(str(index) for index in severe))
    else:
        reasons.append("no severe frame under the stated threshold")
    if not timestamps_ok:
        rejected.append("missing-source-timestamps")
        reasons.append("a result without prev_timestamp and curr_timestamp is rejected")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("narrower software result retained; physical behavior stays open")
    preserved = [
        evidence,
        {
            "prev_timestamp": prev,
            "curr_timestamp": curr,
            "mean": mean,
            "severeFrameIndexes": severe,
        },
    ]
    return core.finish(
        CASE_ID,
        decision,
        reasons,
        rejected,
        preserved,
        [core.OPEN_QUESTION, REPEAT],
    )
