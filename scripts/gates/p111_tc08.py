"""TC-P111-08 Whole-clip acceptance.

Host fixture. A favorable mean cannot hide a catastrophic frame when release is requested.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P111-08"
NAME = "Whole-clip acceptance"
INTERVENTION = "Evaluate complete difficult clips at normal playback rather than selected best frames."
EXPECTED = "Record catastrophic artifacts separately and limit release settings where failures remain unacceptable."
NEGATIVE = "A favorable mean score must not hide a small number of severe boundary failures."
REPEAT = "Repeat blinded presentation, moderate blur, aggressive blur, and held-out scenes."
NEGATIVE_TOKEN = "mean-score-hides-severe-boundary-failures"
PAYLOAD_KEYS = ("evidenceId", "repeat", "releaseRequested", "frames")
FRAME_KEYS = {"id", "score", "catastrophic"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _text(value, label: str) -> str:
    _require(isinstance(value, str) and value.strip() and value == value.strip(), f"{label} must be a non-empty string")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    _require(type(payload["releaseRequested"]) is bool, "releaseRequested must be a bool")
    frames = payload["frames"]
    _require(isinstance(frames, list) and len(frames) >= 2, "frames must contain at least 2 samples")
    parsed = []
    seen = set()
    for index, frame in enumerate(frames):
        _require(isinstance(frame, dict) and set(frame) == FRAME_KEYS, f"frame {index} keys are invalid")
        frame_id = _text(frame["id"], f"frame {index} id")
        _require(frame_id not in seen, "frame ids must be unique")
        seen.add(frame_id)
        _require(isinstance(frame["score"], (int, float)) and not isinstance(frame["score"], bool), "score must be a number")
        score = float(frame["score"])
        _require(math.isfinite(score) and 0.0 <= score <= 1.0, "score must be finite and inside [0, 1]")
        _require(type(frame["catastrophic"]) is bool, "catastrophic must be a bool")
        parsed.append({"id": frame_id, "score": score, "catastrophic": frame["catastrophic"]})
    mean = sum(item["score"] for item in parsed) / len(parsed)
    catastrophic = [item["id"] for item in parsed if item["catastrophic"]]
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        f"mean_score={format(mean, '.12g')} catastrophic={','.join(catastrophic) if catastrophic else 'none'}",
        f"release_requested={payload['releaseRequested']}",
    ]
    rejected: list[str] = []
    if catastrophic and payload["releaseRequested"]:
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("release refused because catastrophic frames remain")
    else:
        decision = "recorded"
        if catastrophic:
            reasons.append("catastrophic frames recorded separately; release stays limited")
        else:
            reasons.append("no catastrophic frame in the whole clip")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [
            evidence,
            f"mean_score:{format(mean, '.12g')}",
            "catastrophic:" + (",".join(catastrophic) if catastrophic else "none"),
        ],
        "openQuestions": ["physical S23 capture was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    if not any(str(item).startswith("catastrophic:") for item in result["preservedResults"]):
        raise ValueError("catastrophic frames were not recorded separately")
    return result
