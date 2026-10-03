"""TC-P042-07 unrecorded measurement conditions.

Missing illuminant, exposure, target identity, or source revision downgrades
the claim. Author assertions and manufacturer metadata are not measurements.
An attractive color result does not become the default profile.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P042-07"
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

_ORIGINS = ("measured", "author_assertion", "manufacturer_metadata")
_FIELDS = ("illuminant", "exposure", "targetId", "sourceRevision")
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")
_PAYLOAD_KEYS = (
    "illuminant",
    "exposure",
    "targetId",
    "sourceRevision",
    "origin",
    "colorAppeal",
    "profileRequested",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "downgraded", "withheld")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep partial evidence. Do not install it as the measured profile."""
    fields, origin, appeal, requested = _payload(payload)
    preserved = [f"{name}:{value}" for name, value in fields if value is not None]
    preserved.extend(f"missing:{name}" for name, value in fields if value is None)
    preserved.append(f"origin:{origin}")
    preserved.append(f"color:{appeal}")
    missing = [name for name, value in fields if value is None]
    incomplete = bool(missing) or origin != "measured"
    if requested and incomplete:
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "attractive color was not installed as the default profile"],
            ["unrecorded-conditions", "default-profile"],
            preserved,
            ["exploratory data remains available"],
        )
    if incomplete:
        return _result(
            "downgraded",
            [EXPECTED, INTERVENTION, "measurement claim downgraded; exploratory data retained"],
            ["unrecorded-conditions"],
            preserved,
            ["exploratory research is not the default measured profile"],
        )
    return _result(
        "withheld",
        ["context is complete and was not installed as the default profile"],
        [],
        preserved,
        ["a complete host record is still not a physical measurement"],
    )


def _payload(payload: object) -> tuple[list[tuple[str, str | None]], str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    fields: list[tuple[str, str | None]] = []
    for name in _FIELDS:
        value = payload[name]
        if value is None:
            fields.append((name, None))
            continue
        if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
            raise ValueError(f"{name} must be a token or null")
        fields.append((name, value))
    origin = payload["origin"]
    if origin not in _ORIGINS:
        raise ValueError("origin is not an allowed value")
    appeal = payload["colorAppeal"]
    if not isinstance(appeal, str) or _TOKEN.fullmatch(appeal) is None:
        raise ValueError("colorAppeal must be a token")
    requested = payload["profileRequested"]
    if type(requested) is not bool:
        raise ValueError("profileRequested must be a bool")
    return fields, origin, appeal, requested


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P042-07 must not yield qualified or allowed")
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
