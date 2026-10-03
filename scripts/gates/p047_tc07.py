"""TC-P047-07 unrecorded measurement conditions.

Intervention: Remove illuminant, exposure, target identity, or source revision
from calibration evidence.
Expected: Downgrade or reject the measurement claim while retaining the data
for exploratory research.
Negative: An attractive color result without experimental context must not
become the default measured profile.
"""

from __future__ import annotations

CASE_ID = "TC-P047-07"
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

_KINDS = ("measured", "author-assertion", "manufacturer-metadata")
_FIELDS = ("illuminant", "exposure", "targetIdentity", "sourceRevision")
_TOKEN = "abcdefghijklmnopqrstuvwxyz0123456789-:+."
_PAYLOAD_KEYS = (
    "sampleId",
    "illuminant",
    "exposure",
    "targetIdentity",
    "sourceRevision",
    "attractiveColor",
    "evidenceKind",
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
    """Downgrade a claim that lacks context. Attractive color is not a default."""
    sample, fields, attractive, kind = _payload(payload)
    preserved = ["sample:" + sample, "evidence:" + kind, "attractive:" + str(attractive).lower()]
    missing: list[str] = []
    for name in _FIELDS:
        value = fields[name]
        if value is None:
            missing.append(name)
            preserved.append("missing:" + name)
        else:
            preserved.append(name + ":" + value)
    exploratory = ["exploratory-data-retained:" + sample]
    if kind != "measured" or missing or (attractive and missing):
        rejected = ["not-default-measured-profile"]
        if kind != "measured":
            rejected.append(kind)
        for name in missing:
            rejected.append("missing:" + name)
        reasons = [EXPECTED, "measurement claim is not the default measured profile"]
        reasons.append("data retained for exploratory research")
        if attractive and (missing or kind != "measured"):
            reasons.append(NEGATIVE)
        decision = "rejected" if attractive and missing else "downgraded"
        if attractive and missing:
            reasons.append("attractive color without context was rejected")
        return _result(decision, reasons, rejected, preserved, exploratory)
    reasons = [
        EXPECTED,
        "experimental context recorded",
        "attractive color was not promoted to the default measured profile",
    ]
    return _result(
        "context_recorded",
        reasons,
        [],
        preserved,
        ["recorded context is not physical S23 qualification"],
    )


def _payload(payload: object) -> tuple[str, dict, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    kind = payload["evidenceKind"]
    if kind not in _KINDS:
        raise ValueError("evidenceKind is unsupported")
    attractive = payload["attractiveColor"]
    if type(attractive) is not bool:
        raise ValueError("attractiveColor must be a bool")
    sample = _token(payload["sampleId"], "sampleId")
    fields = {name: _optional(payload[name], name) for name in _FIELDS}
    return sample, fields, attractive, kind


def _optional(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _token(value, label)


def _token(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or any(char not in _TOKEN for char in value):
        raise ValueError(label + " must be a canonical token or null")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("context decision cannot be qualified or allowed")
    if not reasons or any(type(item) is not str or not item for item in reasons):
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
