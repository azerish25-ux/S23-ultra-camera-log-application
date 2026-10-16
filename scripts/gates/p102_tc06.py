"""TC-P102-06 Stale depth result.

Host reference. Temporal identity is timestamp equality. Geometric identity is
crop equality. A float array that matches neither may be rejected or
reprojected under a validated policy, not applied.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P102-06"
NAME = "Stale depth result"
INTERVENTION = "Delay inference until its result no longer matches the current source timestamp or crop."
EXPECTED = "Reject or explicitly reproject the result under a validated policy rather than applying it blindly."
NEGATIVE = "A float array without temporal and geometric identity must not be accepted."
REPEAT = "Repeat rapid camera movement, rotation, source switches, and scene cuts."
NEGATIVE_TOKEN = "float-array-without-temporal-geometric-identity"
PAYLOAD_KEYS = {
    "evidenceId",
    "repeat",
    "sourceTimestamp",
    "resultTimestamp",
    "sourceCrop",
    "resultCrop",
    "policy",
    "reprojectValidated",
    "depthValues",
}
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


def _stamp(value: object, label: str) -> int:
    _require(type(value) is int and value >= 0, label + " must be a non-negative int")
    return value


def _crop(value: object, label: str) -> tuple[int, int, int, int]:
    _require(isinstance(value, list) and len(value) == 4, label + " must be [x, y, w, h]")
    x, y, width, height = value
    _require(type(x) is int and type(y) is int and x >= 0 and y >= 0, label + " origin must be a non-negative int")
    _require(type(width) is int and type(height) is int and width >= 1 and height >= 1,
             label + " size must be a positive int")
    return (x, y, width, height)


def evaluate(payload: dict) -> dict:
    _require(isinstance(payload, dict) and set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    source_stamp = _stamp(payload["sourceTimestamp"], "sourceTimestamp")
    result_stamp = _stamp(payload["resultTimestamp"], "resultTimestamp")
    source_crop = _crop(payload["sourceCrop"], "sourceCrop")
    result_crop = _crop(payload["resultCrop"], "resultCrop")
    policy = payload["policy"]
    _require(policy in {"reject", "reproject", "apply"}, "policy must be reject, reproject, or apply")
    _require(type(payload["reprojectValidated"]) is bool, "reprojectValidated must be a bool")
    values = payload["depthValues"]
    _require(isinstance(values, list) and 1 <= len(values) <= 64, "depthValues must be a non-empty float array")
    for index, item in enumerate(values):
        _require(isinstance(item, (int, float)) and not isinstance(item, bool), f"depthValues[{index}] must be a number")
        _require(math.isfinite(float(item)), f"depthValues[{index}] must be finite")

    temporal = source_stamp == result_stamp
    geometric = source_crop == result_crop
    identified = temporal and geometric
    rejected: list[str] = []
    reasons = [
        f"{CASE_ID} {NAME}",
        EXPECTED,
        f"repeat {repeat}",
        "temporal-identity:" + ("match" if temporal else "stale"),
        "geometric-identity:" + ("match" if geometric else "stale"),
    ]
    if not identified and not (policy == "reject" or (policy == "reproject" and payload["reprojectValidated"])):
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("float array lacks temporal and geometric identity")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        if identified:
            reasons.append("depth array matches source timestamp and crop")
        elif policy == "reject":
            reasons.append("stale depth rejected")
        else:
            reasons.append("stale depth reprojected under a validated policy")
    return _finish(
        decision,
        reasons,
        rejected,
        evidence,
        [f"samples:{len(values)}", "identity:match" if identified else "identity:stale"],
    )


def _finish(decision: str, reasons: list[str], rejected: list[str], evidence: str, extra: list[str]) -> dict:
    _require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, *extra],
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result
