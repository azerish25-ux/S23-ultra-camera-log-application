"""TC-P069-08 misleading microbenchmark.

Intervention: Provide excellent isolated kernel timing but poor integrated
performance under real data movement.
Expected: Report end-to-end latency and bottlenecks rather than extrapolating
from the fastest kernel.
Negative: A standalone model benchmark must not become a recording frame-rate claim.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P069-08"
INTERVENTION = "Provide excellent isolated kernel timing but poor integrated performance under real data movement."
EXPECTED = "Report end-to-end latency and bottlenecks rather than extrapolating from the fastest kernel."
NEGATIVE = "A standalone model benchmark must not become a recording frame-rate claim."
REPEAT = "Repeat cold, warm, sustained, and thermally constrained runs."

_RUNS = ("cold", "warm", "sustained", "thermal")
_BOTTLENECKS = ("kernel", "upload", "readback", "encode", "none")
_PAYLOAD_KEYS = (
    "run",
    "kernelMs",
    "endToEndMs",
    "bottleneck",
    "reportedEndToEnd",
    "recordingClaim",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "end_to_end_reported"}
_UNSIGNED = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Report end-to-end latency. A kernel time is not a recording frame rate."""
    run, kernel, end_to_end, bottleneck, reported, recording = _payload(payload)
    preserved = [
        f"run:{run}",
        f"kernel-ms:{kernel}",
        f"end-to-end-ms:{end_to_end}",
        f"bottleneck:{bottleneck}",
        f"reported:{str(reported).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}", f"run {run}"]
    rejected: list[str] = []
    if recording:
        rejected.append("recording-frame-rate-claim")
        reasons.append(NEGATIVE)
        reasons.append(f"{run} kernel {kernel} ms was not promoted to a recording frame rate")
    if not reported:
        rejected.append("kernel-extrapolation")
        reasons.append(f"{run} did not report end-to-end latency {end_to_end} ms")
    if reported and not recording:
        if Decimal(end_to_end) < Decimal(kernel):
            rejected.append("inverted-latency")
            reasons.append(f"end-to-end {end_to_end} ms is below kernel {kernel} ms")
        elif bottleneck == "none":
            rejected.append("missing-bottleneck")
            reasons.append(f"{run} reported latency without a bottleneck")
    if rejected:
        decision = "rejected"
        questions.append("kernel and end-to-end timings were retained")
    else:
        decision = "end_to_end_reported"
        reasons.append(f"{run} end-to-end {end_to_end} ms bottleneck {bottleneck}")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    run = payload["run"]
    if run not in _RUNS:
        raise ValueError("run is unsupported")
    kernel = _unsigned(payload["kernelMs"], "kernelMs")
    end_to_end = _unsigned(payload["endToEndMs"], "endToEndMs")
    if Decimal(kernel) <= 0 or Decimal(end_to_end) <= 0:
        raise ValueError("timings must be positive")
    bottleneck = payload["bottleneck"]
    if bottleneck not in _BOTTLENECKS:
        raise ValueError("bottleneck is unsupported")
    reported = payload["reportedEndToEnd"]
    recording = payload["recordingClaim"]
    if type(reported) is not bool or type(recording) is not bool:
        raise ValueError("reportedEndToEnd and recordingClaim must be bools")
    return run, kernel, end_to_end, bottleneck, reported, recording


def _unsigned(value: object, label: str) -> str:
    if not isinstance(value, str) or _UNSIGNED.fullmatch(value) is None:
        raise ValueError(f"{label} must be a canonical non-negative decimal")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in {"qualified", "allowed"}:
        raise ValueError("TC-P069-08 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
