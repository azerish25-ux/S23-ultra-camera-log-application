"""TC-P103-08 Integrated load and thermal drift.

Host fixture. Standalone model latency is not a full-camera frame-rate guarantee.
The max frame interval is kept beside the mean so an average cannot hide a stall.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P103-08"
NAME = "Integrated load and thermal drift"
INTERVENTION = "Run inference alongside actual capture, rendering, and encoding for a sustained interval."
EXPECTED = "Measure complete workload behavior and choose live or deferred operation from evidence."
NEGATIVE = "Standalone model latency must not become a full-camera frame-rate guarantee."
REPEAT = "Repeat cold start, warm operation, memory pressure, and severe thermal conditions."
NEGATIVE_TOKEN = "standalone-model-latency-become-full-camera"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "applyNegative",
    "applyMutant",
    "standaloneLatencyMs",
    "frameIntervalsMs",
    "frameBudgetMs",
    "integratedWorkloadMeasured",
    "operationChoice",
    "fullCameraFpsClaimedFromStandalone",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _positive(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{label} must be finite and > 0")
    return number


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    for name in ("applyNegative", "applyMutant", "integratedWorkloadMeasured", "fullCameraFpsClaimedFromStandalone"):
        if type(payload[name]) is not bool:
            raise ValueError(f"{name} must be a bool")
    standalone = _positive(payload["standaloneLatencyMs"], "standaloneLatencyMs")
    budget = _positive(payload["frameBudgetMs"], "frameBudgetMs")
    intervals = payload["frameIntervalsMs"]
    if not isinstance(intervals, list) or not intervals:
        raise ValueError("frameIntervalsMs must be a non-empty list")
    numbers = [_positive(item, "frameIntervalsMs item") for item in intervals]
    choice = payload["operationChoice"]
    if choice not in {"live", "deferred"}:
        raise ValueError("operationChoice must be live or deferred")
    mean_interval = sum(numbers) / len(numbers)
    max_interval = max(numbers)
    overload = max_interval > budget
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        f"standaloneLatencyMs={standalone:.6f}; meanFrameIntervalMs={mean_interval:.6f}",
        f"maxFrameIntervalMs={max_interval:.6f}; frameBudgetMs={budget:.6f}",
        f"integratedWorkloadMeasured={payload['integratedWorkloadMeasured']}; operationChoice={choice}",
    ]
    rejected: list[str] = []
    standalone_as_guarantee = payload["fullCameraFpsClaimedFromStandalone"] or (
        payload["integratedWorkloadMeasured"] is not True and choice == "live"
    )
    if payload["applyMutant"] or payload["applyNegative"] or standalone_as_guarantee:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if payload["integratedWorkloadMeasured"] is not True and "complete-workload-not-measured" not in rejected:
        rejected.append("complete-workload-not-measured")
        reasons.append("complete capture, render, and encode workload was not measured")
    if payload["integratedWorkloadMeasured"] is True and overload and choice == "live":
        rejected.append("live-choice-contradicts-integrated-evidence")
        reasons.append("live operation contradicts the integrated max frame interval")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append(
            f"operation {choice} chosen from integrated evidence; max interval kept beside the mean"
        )
        reasons.append("narrower software result retained; physical behavior stays open")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, f"maxFrameIntervalMs={max_interval:.6f}"],
        "openQuestions": ["physical S23 was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
