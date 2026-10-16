"""TC-P107-08 Whole-clip acceptance.

Host reference. A favorable mean must not hide severe boundary failures.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P107-08"
NAME = "Whole-clip acceptance"
INTERVENTION = "Evaluate complete difficult clips at normal playback rather than selected best frames."
EXPECTED = "Record catastrophic artifacts separately and limit release settings where failures remain unacceptable."
NEGATIVE = "A favorable mean score must not hide a small number of severe boundary failures."
REPEAT = "Repeat blinded presentation, moderate blur, aggressive blur, and held-out scenes."
NEGATIVE_TOKEN = "mean-hides-severe-failures"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "frame_scores",
    "severe_boundary_failures",
    "severe_recorded_separately",
    "release_limited",
    "selected_best_frames_only",
)
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


def evaluate(payload: dict) -> dict:
    _require(isinstance(payload, dict) and set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(), "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    scores = payload["frame_scores"]
    _require(isinstance(scores, list) and scores, "frame_scores must be a non-empty list")
    values: list[float] = []
    for index, item in enumerate(scores):
        _require(isinstance(item, (int, float)) and not isinstance(item, bool), f"frame_scores[{index}] must be a number")
        value = float(item)
        _require(math.isfinite(value) and 0.0 <= value <= 1.0, f"frame_scores[{index}] must lie in [0, 1]")
        values.append(value)
    severe = payload["severe_boundary_failures"]
    _require(isinstance(severe, int) and not isinstance(severe, bool) and severe >= 0, "severe_boundary_failures must be a non-negative int")
    for name in ("severe_recorded_separately", "release_limited", "selected_best_frames_only"):
        _require(type(payload[name]) is bool, f"{name} must be a bool")
    mean = sum(values) / float(len(values))
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        INTERVENTION,
        f"mean={format(mean, '.12g')}",
        f"severe={severe}",
    ]
    rejected: list[str] = []
    if payload["selected_best_frames_only"]:
        rejected.append("best-frames-only")
        reasons.append("selected best frames are not a whole-clip result")
    if severe > 0 and not payload["severe_recorded_separately"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("favorable mean %s does not hide %d severe boundary failures" % (format(mean, ".12g"), severe))
    if severe > 0 and not payload["release_limited"]:
        rejected.append("release-not-limited")
        reasons.append("release settings stay unlimited while severe failures remain")
    if not rejected:
        reasons.append("catastrophic artifacts stayed visible in the host record" if severe else "no severe boundary failures in this clip")
    decision = "rejected" if rejected else "recorded"
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, f"mean={format(mean, '.12g')}", f"severe={severe}"],
        "openQuestions": ["physical S23 was not run", REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result
