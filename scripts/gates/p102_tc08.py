"""TC-P102-08 Integrated load and thermal drift.

Host reference. Frame intervals measured while capture, rendering, and
encoding are all active are the workload. Standalone latency is not a
full-camera frame-rate guarantee.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P102-08"
NAME = "Integrated load and thermal drift"
INTERVENTION = "Run inference alongside actual capture, rendering, and encoding for a sustained interval."
EXPECTED = "Measure complete workload behavior and choose live or deferred operation from evidence."
NEGATIVE = "Standalone model latency must not become a full-camera frame-rate guarantee."
REPEAT = "Repeat cold start, warm operation, memory pressure, and severe thermal conditions."
NEGATIVE_TOKEN = "standalone-model-latency-become-full-camera"
PAYLOAD_KEYS = {
    "evidenceId",
    "repeat",
    "standaloneLatencyMs",
    "captureActive",
    "renderingActive",
    "encodingActive",
    "sustainedIntervalS",
    "integratedSamples",
    "chosenOperation",
    "claimedFrameRateGuarantee",
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


def _positive_number(value: object, label: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), label + " must be a number")
    number = float(value)
    _require(math.isfinite(number) and number > 0, label + " must be a positive finite number")
    return number


def evaluate(payload: dict) -> dict:
    _require(isinstance(payload, dict) and set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    standalone = _positive_number(payload["standaloneLatencyMs"], "standaloneLatencyMs")
    for flag in ("captureActive", "renderingActive", "encodingActive", "claimedFrameRateGuarantee"):
        _require(type(payload[flag]) is bool, flag + " must be a bool")
    interval = payload["sustainedIntervalS"]
    _require(type(interval) is int and interval >= 1, "sustainedIntervalS must be a positive int")
    samples = payload["integratedSamples"]
    _require(isinstance(samples, list) and 3 <= len(samples) <= 64, "integratedSamples must contain 3 to 64 numbers")
    parsed = [_positive_number(item, "integrated sample") for item in samples]
    operation = payload["chosenOperation"]
    _require(operation in {"live", "deferred"}, "chosenOperation must be live or deferred")

    mean = sum(parsed) / len(parsed)
    integrated = payload["captureActive"] and payload["renderingActive"] and payload["encodingActive"]
    rejected: list[str] = []
    reasons = [
        f"{CASE_ID} {NAME}",
        EXPECTED,
        f"repeat {repeat}",
        f"integrated-mean-ms={mean:.3f}",
        f"standalone-latency-ms={standalone:.3f}",
        f"sustained-interval-s={interval}",
    ]
    if not integrated:
        rejected.append("integrated-workload-not-measured")
        reasons.append("capture, rendering, and encoding were not all active")
    if payload["claimedFrameRateGuarantee"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("standalone latency was promoted to a frame-rate guarantee")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append(f"operation {operation} chosen from integrated samples, not standalone latency")
    return _finish(decision, reasons, rejected, evidence, [f"integrated-mean-ms:{mean:.3f}", "operation:" + operation])


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
