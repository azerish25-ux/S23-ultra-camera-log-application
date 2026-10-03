"""TC-P073-01 stock identity without measurements.

Intervention: Attach a famous stock name to an unmeasured generic response model.
Expected: Keep the model labelled reconstructed or synthetic and separate the name
from any calibrated fidelity claim.
Negative: A marketing label alone must not establish measured material behavior.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P073-01"
INTERVENTION = "Attach a famous stock name to an unmeasured generic response model."
EXPECTED = (
    "Keep the model labelled reconstructed or synthetic and separate the name "
    "from any calibrated fidelity claim."
)
NEGATIVE = "A marketing label alone must not establish measured material behavior."
REPEAT = "Repeat for daylight, tungsten, monochrome, and historical-stock interpretations."

_INTERPRETATIONS = ("daylight", "tungsten", "monochrome", "historical-stock")
_LABELS = ("reconstructed", "synthetic", "measured")
_MODELS = ("generic", "density")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .'-]*$")
_PAYLOAD_KEYS = ("stockName", "modelKind", "measuredSamples", "label", "interpretation")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld", "reconstructed", "synthetic", "measured_record"}


def evaluate(payload: dict) -> dict:
    """Keep an unmeasured model reconstructed or synthetic, apart from its marketing name."""
    stock_name, model_kind, measured_samples, label, interpretation = _payload(payload)
    preserved = [
        stock_name,
        f"model:{model_kind}",
        f"label:{label}",
        f"interpretation:{interpretation}",
        f"samples:{str(measured_samples).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}", f"repeat site {interpretation}"]
    rejected: list[str] = []
    if not measured_samples and label == "measured":
        decision = "rejected"
        rejected.append("marketing-label")
        reasons.append(NEGATIVE)
        reasons.append(f"{stock_name} remains a display name and does not establish measured material behavior")
    elif not measured_samples and label in {"reconstructed", "synthetic"}:
        decision = label
        reasons.append(f"{stock_name} is a display name and is not a calibrated fidelity claim")
        reasons.append(f"model stays {label} for the {interpretation} interpretation")
    elif measured_samples and label == "measured":
        decision = "measured_record"
        reasons.append(f"measured samples are recorded separately from the marketing name {stock_name}")
        questions.append("a measured record is not a qualified stock or an allowed fidelity claim")
    else:
        decision = "rejected"
        rejected.append("label-sample-mismatch")
        reasons.append("the evidence label disagrees with whether samples were measured")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    stock_name = payload["stockName"]
    if not isinstance(stock_name, str) or stock_name != stock_name.strip() or _NAME.fullmatch(stock_name) is None:
        raise ValueError("stockName must be a display name")
    model_kind = payload["modelKind"]
    if model_kind not in _MODELS:
        raise ValueError("modelKind is unsupported")
    label = payload["label"]
    if label not in _LABELS:
        raise ValueError("label is unsupported")
    interpretation = payload["interpretation"]
    if interpretation not in _INTERPRETATIONS:
        raise ValueError("interpretation is unsupported")
    measured_samples = payload["measuredSamples"]
    if type(measured_samples) is not bool:
        raise ValueError("measuredSamples must be a bool")
    return stock_name, model_kind, measured_samples, label, interpretation


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in {"qualified", "allowed"}:
        raise ValueError("TC-P073-01 must not yield qualified or allowed")
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
