"""TC-P071-06 critical-path resource contention.

Intervention: Increase inference or preview work until it competes with
capture and encoding.
Expected: Degrade optional monitoring first while retaining the selected
source contract or stopping honestly.
Negative: Hidden source frame drops to preserve preview smoothness must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P071-06"
INTERVENTION = "Increase inference or preview work until it competes with capture and encoding."
EXPECTED = (
    "Degrade optional monitoring first while retaining the selected source contract or stopping honestly."
)
NEGATIVE = "Hidden source frame drops to preserve preview smoothness must fail."
REPEAT = "Repeat with scopes, denoising, thumbnails, and background file operations."

_WORKLOADS = ("inference", "preview", "scopes", "denoise", "thumbnails", "background-io")
_PAYLOAD_KEYS = (
    "workload",
    "contention",
    "hiddenSourceDrops",
    "previewSmooth",
    "monitoringDegraded",
    "sourceRetained",
    "stoppedHonestly",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld", "monitoring_degraded", "stopped_honestly", "source_retained"}
_TOKEN = re.compile(r"^[a-z0-9-]+$")


def evaluate(payload: dict) -> dict:
    """Degrade monitoring or stop honestly. Hidden source drops fail."""
    workload, contention, hidden, smooth, monitoring, source, stopped = _payload(payload)
    preserved = [
        f"workload:{workload}",
        f"contention:{str(contention).lower()}",
        f"preview-smooth:{str(smooth).lower()}",
        f"monitoring:{str(monitoring).lower()}",
        f"source:{str(source).lower()}",
        f"stopped:{str(stopped).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}", f"workload {workload}"]
    if hidden:
        decision = "rejected"
        rejected = ["hidden-source-drops"]
        reasons.append(NEGATIVE)
        reasons.append(f"{workload} must not drop source frames to keep preview smooth")
        questions.append("source-contract flag was retained with the rejection")
    elif stopped:
        decision = "stopped_honestly"
        rejected = []
        reasons.append(f"{workload} stopped honestly instead of hiding source drops")
    elif monitoring and source:
        decision = "monitoring_degraded"
        rejected = []
        reasons.append(f"{workload} degraded monitoring and retained the source contract")
    elif source and not contention:
        decision = "source_retained"
        rejected = []
        reasons.append(f"{workload} retained the source contract without contention")
    elif not source:
        decision = "rejected"
        rejected = ["source-contract-lost"]
        reasons.append(f"{workload} lost the source contract and did not stop honestly")
        questions.append("workload identity was retained")
    else:
        decision = "withheld"
        rejected = []
        reasons.append(f"{workload} still contends without degrading monitoring or stopping")
        questions.append("source contract was not dropped")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    workload = payload["workload"]
    if not isinstance(workload, str) or _TOKEN.fullmatch(workload) is None or workload not in _WORKLOADS:
        raise ValueError("workload is unsupported")
    flags = []
    for name in (
        "contention",
        "hiddenSourceDrops",
        "previewSmooth",
        "monitoringDegraded",
        "sourceRetained",
        "stoppedHonestly",
    ):
        value = payload[name]
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
        flags.append(value)
    return (workload, *flags)


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in {"qualified", "allowed"}:
        raise ValueError("TC-P071-06 must not yield qualified or allowed")
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
