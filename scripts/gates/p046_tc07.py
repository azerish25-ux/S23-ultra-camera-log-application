"""TC-P046-07 unrecorded measurement conditions.

Intervention: Remove illuminant, exposure, target identity, or source revision
from calibration evidence.
Expected: Downgrade or reject the measurement claim while retaining the data
for exploratory research.
Negative: An attractive color result without experimental context must not
become the default measured profile.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P046-07"
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

_ORIGINS = ("measurement", "author-assertion", "manufacturer-metadata")
_FIELDS = (
    ("illuminant", "illuminant"),
    ("exposure", "exposure"),
    ("targetIdentity", "target-identity"),
    ("sourceRevision", "source-revision"),
)
_PAYLOAD_KEYS = (
    "recordId",
    "illuminant",
    "exposure",
    "targetIdentity",
    "sourceRevision",
    "attractiveColor",
    "origin",
    "requestDefault",
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
_DECISIONS = ("rejected", "downgraded", "context_recorded")
_FORBIDDEN = {"qualified", "allowed"}
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")


def evaluate(payload: dict) -> dict:
    """Downgrade a context-free color result. Keep the exploratory samples."""
    record_id, fields, attractive, origin, request_default, samples = _payload(payload)
    missing = [label for key, label in _FIELDS if fields[key] == ""]
    preserved = [f"record:{record_id}"]
    for key, label in _FIELDS:
        preserved.append(f"{label}:{fields[key] or 'missing'}")
    preserved.append(f"origin:{origin}")
    preserved.append(f"attractive:{str(attractive).lower()}")
    preserved.extend(f"sample:{item}" for item in samples)
    context_gap = bool(missing) or origin != "measurement"
    reasons = [EXPECTED]
    if request_default and context_gap:
        decision = "rejected"
        rejected = ["default-measured-profile"]
        if attractive:
            rejected.append("attractive-without-context")
        if origin != "measurement":
            rejected.append(origin)
        rejected.extend(f"missing:{name}" for name in missing)
        reasons.append(NEGATIVE)
        questions = ["default measured profile refused"]
    elif context_gap:
        decision = "downgraded"
        rejected = ["measurement-claim"]
        if attractive:
            rejected.append("attractive-without-context")
        if origin != "measurement":
            rejected.append(origin)
        rejected.extend(f"missing:{name}" for name in missing)
        reasons.append("measurement claim downgraded; exploratory data retained")
        questions = ["retained for exploratory research"]
    else:
        decision = "context_recorded"
        rejected = []
        reasons.append("experimental context is recorded; this is not a default measured profile")
        questions = []
    return _result(decision, reasons, rejected, preserved, questions)


def _field(value: object, label: str) -> str:
    if not isinstance(value, str) or (value != "" and _TOKEN.fullmatch(value) is None):
        raise ValueError(label + " must be empty or a token")
    return value


def _payload(payload: object) -> tuple[str, dict[str, str], bool, str, bool, list[str]]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    record_id = payload["recordId"]
    if not isinstance(record_id, str) or _TOKEN.fullmatch(record_id) is None:
        raise ValueError("recordId must be a token")
    fields = {key: _field(payload[key], key) for key, _label in _FIELDS}
    attractive = payload["attractiveColor"]
    request_default = payload["requestDefault"]
    if type(attractive) is not bool or type(request_default) is not bool:
        raise ValueError("attractiveColor and requestDefault must be bools")
    origin = payload["origin"]
    if origin not in _ORIGINS:
        raise ValueError("origin is unknown")
    samples = payload["samples"]
    if (
        not isinstance(samples, list)
        or not samples
        or any(not isinstance(item, str) or _TOKEN.fullmatch(item) is None for item in samples)
    ):
        raise ValueError("samples must be a non-empty token list")
    return record_id, fields, attractive, origin, request_default, list(samples)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("measurement-context decision cannot be qualified or allowed")
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
