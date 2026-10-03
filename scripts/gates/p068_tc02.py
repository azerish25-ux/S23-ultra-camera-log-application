"""TC-P068-02 accumulated floating-point error.

Intervention: Run signed, high-range, and cancellation-sensitive values
through repeated or wide-support operations.
Expected: Remain inside the declared error budget or promote the affected
stage to sufficient precision.
Negative: Using FP16 everywhere without differential validation must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P068-02"
INTERVENTION = (
    "Run signed, high-range, and cancellation-sensitive values through repeated or wide-support operations."
)
EXPECTED = "Remain inside the declared error budget or promote the affected stage to sufficient precision."
NEGATIVE = "Using FP16 everywhere without differential validation must fail."
REPEAT = "Repeat with long blur accumulations, matrices, and highlight reconstruction attempts."

_OPERATIONS = ("wide-support", "long-blur", "matrix", "highlight")
_PRECISIONS = ("fp16", "fp32", "fp64")
_SUFFICIENT = ("fp32", "fp64")
_PAYLOAD_KEYS = (
    "stageId",
    "operation",
    "precision",
    "observedError",
    "errorBudget",
    "differentialValidation",
    "promoted",
    "signedValue",
    "highRange",
    "cancellation",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "within_budget", "precision_promoted"}
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")
_SIGNED = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")
_UNSIGNED = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Keep the error budget, or reject undifferentiated FP16."""
    (
        stage,
        operation,
        precision,
        observed,
        budget,
        differential,
        promoted,
        signed_value,
        high_range,
        cancellation,
    ) = _payload(payload)
    preserved = [
        stage,
        f"operation:{operation}",
        f"precision:{precision}",
        f"observed:{observed}",
        f"budget:{budget}",
        f"signed:{signed_value}",
        f"high-range:{high_range}",
        f"cancellation:{cancellation}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}", f"operation {operation}"]
    rejected: list[str] = []
    if precision == "fp16" and not differential:
        decision = "rejected"
        rejected.append("fp16-without-differential")
        reasons.append(NEGATIVE)
        reasons.append(f"{stage} stayed at FP16 without a differential check")
        questions.append("signed, high-range, and cancellation samples were retained")
    elif Decimal(observed) <= Decimal(budget):
        decision = "within_budget"
        reasons.append(f"observed error {observed} is inside budget {budget}")
    elif promoted and precision in _SUFFICIENT:
        decision = "precision_promoted"
        reasons.append(f"{stage} promoted to {precision} after exceeding budget {budget}")
        questions.append("promotion is not a qualified measurement")
    else:
        decision = "rejected"
        rejected.append("error-budget-exceeded")
        reasons.append(f"observed error {observed} exceeds budget {budget} without sufficient precision")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    stage = payload["stageId"]
    if not isinstance(stage, str) or _TOKEN.fullmatch(stage) is None:
        raise ValueError("stageId must be a token")
    operation = payload["operation"]
    if operation not in _OPERATIONS:
        raise ValueError("operation is unsupported")
    precision = payload["precision"]
    if precision not in _PRECISIONS:
        raise ValueError("precision is unsupported")
    observed = _unsigned(payload["observedError"], "observedError")
    budget = _unsigned(payload["errorBudget"], "errorBudget")
    if Decimal(budget) <= 0:
        raise ValueError("errorBudget must be positive")
    differential = payload["differentialValidation"]
    promoted = payload["promoted"]
    if type(differential) is not bool or type(promoted) is not bool:
        raise ValueError("differentialValidation and promoted must be bools")
    signed_value = _signed(payload["signedValue"], "signedValue")
    high_range = _signed(payload["highRange"], "highRange")
    cancellation = _signed(payload["cancellation"], "cancellation")
    return (
        stage,
        operation,
        precision,
        observed,
        budget,
        differential,
        promoted,
        signed_value,
        high_range,
        cancellation,
    )


def _signed(value: object, label: str) -> str:
    if not isinstance(value, str) or _SIGNED.fullmatch(value) is None or value == "-0":
        raise ValueError(f"{label} must be a canonical signed decimal")
    return value


def _unsigned(value: object, label: str) -> str:
    if not isinstance(value, str) or _UNSIGNED.fullmatch(value) is None:
        raise ValueError(f"{label} must be a canonical non-negative decimal")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in {"qualified", "allowed"}:
        raise ValueError("TC-P068-02 must not yield qualified or allowed")
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
