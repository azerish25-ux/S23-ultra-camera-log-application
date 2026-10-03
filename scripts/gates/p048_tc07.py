"""TC-P048-07 unrecorded measurement conditions.

Intervention: Remove illuminant, exposure, target identity, or source revision
from calibration evidence.
Expected: Downgrade or reject the measurement claim while retaining the data
for exploratory research.
Negative: An attractive color result without experimental context must not
become the default measured profile.
"""

from __future__ import annotations


CASE_ID = "TC-P048-07"
INTERVENTION = (
    "Remove illuminant, exposure, target identity, or source revision from calibration evidence."
)
EXPECTED = (
    "Downgrade or reject the measurement claim while retaining the data for exploratory research."
)
NEGATIVE = (
    "An attractive color result without experimental context must not become the default "
    "measured profile."
)

_ORIGINS = ("measured", "author_assertion", "manufacturer_metadata")
_CONTEXT = ("illuminant", "exposure", "targetIdentity", "sourceRevision")
_PAYLOAD_KEYS = (
    "illuminant",
    "exposure",
    "targetIdentity",
    "sourceRevision",
    "colorResult",
    "claimMeasured",
    "origin",
    "samples",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "downgraded", "withheld", "exploratory")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Downgrade a context-free color result and keep the exploratory samples."""
    fields, color, claim, origin, samples = _payload(payload)
    preserved = [f"sample:{item}" for item in samples]
    preserved.append(f"color:{color}")
    preserved.append(f"origin:{origin}")
    for name in _CONTEXT:
        preserved.append(f"{_label(name)}:{fields[name] or 'removed'}")
    rejected: list[str] = []
    for name in _CONTEXT:
        if fields[name] == "":
            rejected.append(f"removed:{_label(name)}")
    if origin == "author_assertion":
        rejected.append("author-assertion")
    elif origin == "manufacturer_metadata":
        rejected.append("manufacturer-metadata")
    reasons = [EXPECTED, "exploratory samples retained"]
    if claim and rejected:
        decision = "rejected"
        reasons.append(NEGATIVE)
        questions = ["context-free color result was not installed as the measured profile"]
    elif rejected:
        decision = "downgraded"
        reasons.append("measurement claim downgraded; data retained for exploratory research")
        questions = ["retained for exploratory research"]
    elif claim:
        decision = "withheld"
        rejected = ["not-default-measured-profile"]
        reasons.append("full context still does not make this the default measured profile")
        questions = ["recorded context is not a default measured profile"]
    else:
        decision = "exploratory"
        reasons.append("context retained without a default measured profile")
        questions = ["context retained; not a default measured profile"]
    return _result(decision, reasons, rejected, preserved, questions)


def _label(name: str) -> str:
    return {
        "illuminant": "illuminant",
        "exposure": "exposure",
        "targetIdentity": "target",
        "sourceRevision": "revision",
    }[name]


def _context_string(value: object, label: str) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise ValueError(label + " must be a string without surrounding space")
    return value


def _payload(payload: object) -> tuple[dict[str, str], str, bool, str, list[str]]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    fields = {name: _context_string(payload[name], name) for name in _CONTEXT}
    color = payload["colorResult"]
    if not isinstance(color, str) or not color or color != color.strip():
        raise ValueError("colorResult must be a non-empty string")
    claim = payload["claimMeasured"]
    if type(claim) is not bool:
        raise ValueError("claimMeasured must be a bool")
    origin = payload["origin"]
    if origin not in _ORIGINS:
        raise ValueError("origin is unknown")
    samples = payload["samples"]
    if (
        not isinstance(samples, list)
        or not samples
        or any(not isinstance(item, str) or not item or item != item.strip() for item in samples)
    ):
        raise ValueError("samples must be a non-empty list of strings")
    return fields, color, claim, origin, list(samples)


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
