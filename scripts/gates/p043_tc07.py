"""TC-P043-07 unrecorded measurement conditions.

Intervention: Remove illuminant, exposure, target identity, or source revision
from calibration evidence.
Expected: Downgrade or reject the measurement claim while retaining the data
for exploratory research.
Negative: An attractive color result without experimental context must not
become the default measured profile.
"""

from __future__ import annotations

CASE_ID = "TC-P043-07"
INTERVENTION = (
    "Remove illuminant, exposure, target identity, or source revision from "
    "calibration evidence."
)
EXPECTED = (
    "Downgrade or reject the measurement claim while retaining the data for "
    "exploratory research."
)
NEGATIVE = (
    "An attractive color result without experimental context must not become "
    "the default measured profile."
)

_MISSING = ("none", "illuminant", "exposure", "target", "revision")
_ORIGINS = ("measured-attempt", "author-assertion", "manufacturer-metadata")
_PAYLOAD_KEYS = (
    "datasetId",
    "missing",
    "origin",
    "attractiveColor",
    "samplesRetained",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "downgraded", "context_recorded")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep exploratory samples. Do not promote context-free color to a profile."""
    dataset, missing, origin, attractive, samples = _payload(payload)
    preserved = [
        f"dataset:{dataset}",
        f"samples:{samples}",
        f"origin:{origin}",
        f"missing:{missing}",
    ]
    contextual = missing == "none" and origin == "measured-attempt"
    rejected: list[str] = []
    questions = ["retained samples stay available for exploratory research"]
    if attractive and not contextual:
        decision = "rejected"
        rejected.append("attractive-without-context")
        if missing != "none":
            rejected.append(f"missing:{missing}")
        if origin != "measured-attempt":
            rejected.append(origin)
        reasons = [NEGATIVE, EXPECTED, "samples retained without a default measured profile"]
    elif not contextual:
        decision = "downgraded"
        if missing != "none":
            rejected.append(f"missing:{missing}")
        if origin != "measured-attempt":
            rejected.append(origin)
        reasons = [EXPECTED, "measurement claim downgraded", "samples retained"]
    else:
        decision = "context_recorded"
        reasons = [
            "experimental context recorded",
            "attractive color is not itself a measured profile",
            "this record is not the default measured profile",
        ]
        questions.append("recorded context is not physical qualification")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    dataset = payload["datasetId"]
    samples = payload["samplesRetained"]
    for label, value in (("datasetId", dataset), ("samplesRetained", samples)):
        if not isinstance(value, str) or not value or value != value.strip():
            raise ValueError(f"{label} must be a non-empty string")
    missing = payload["missing"]
    if missing not in _MISSING:
        raise ValueError("missing is not a known evidence field")
    origin = payload["origin"]
    if origin not in _ORIGINS:
        raise ValueError("origin is not a known profile origin")
    attractive = payload["attractiveColor"]
    if type(attractive) is not bool:
        raise ValueError("attractiveColor must be a bool")
    return dataset, missing, origin, attractive, samples


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("context decision cannot be qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
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
