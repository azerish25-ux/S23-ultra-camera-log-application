"""TC-P009-04 firmware cache staleness.

A changed build, codec, or probe protocol requires requalification. The cached
report stays historical evidence and a marketing model name is ignored. A
physical member that is not the logical camera id is addressed through that
owner and is not opened as an independent camera. Missing focal length stays
unknown.
"""

from __future__ import annotations

CASE_ID = "TC-P009-04"
VARIANTS = ("build_changed", "codec_changed", "protocol_changed", "unchanged")
_IDENTITY_FIELDS = ("buildFingerprint", "codecIdentity", "probeProtocol")
_CACHED_FIELDS = (
    "logicalId",
    "physicalId",
    "buildFingerprint",
    "codecIdentity",
    "probeProtocol",
    "qualified",
)
_CURRENT_FIELDS = _IDENTITY_FIELDS
_PAYLOAD_FIELDS = ("cached", "current", "variant")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Requalify when build, codec, or probe identity no longer matches the cache."""
    cached, current, _variant = _payload(payload)
    changed = [
        field for field in _IDENTITY_FIELDS if current[field] != cached[field]
    ]
    logical = cached["logicalId"]
    physical = cached["physicalId"]
    if changed:
        decision = "requalify"
        reasons = [f"{field} differs from the cached probe" for field in changed]
        reasons.append("cached probe is historical only and is not a current qualification")
        rejected = ["cache-hit"]
        preserved = [f"historical:{logical}"]
    elif cached["qualified"]:
        decision = "qualified"
        reasons = ["cached build, codec, and probe protocol match the current probe"]
        rejected = []
        preserved = [logical]
    else:
        decision = "unqualified"
        reasons = ["cached and current identities match but the cached probe is not qualified"]
        rejected = []
        preserved = []

    if physical is not None and physical != logical:
        reasons.append(f"{physical} addressed via {logical}")
    if changed and decision == "qualified":
        raise ValueError("changed identity must not be qualified from the cache")
    if decision == "allowed":
        raise ValueError("TC-P009-04 must not decide allowed")
    return _result(decision, reasons, rejected, preserved)


def _payload(payload: object) -> tuple[dict, dict, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    body = _without_model_name(payload)
    if set(body) != set(_PAYLOAD_FIELDS):
        raise ValueError("payload keys must be cached, current, and variant")
    variant = body["variant"]
    if variant not in VARIANTS:
        raise ValueError(
            "variant must be build_changed, codec_changed, protocol_changed, or unchanged"
        )
    cached = _cached(body["cached"])
    current = _current(body["current"])
    return cached, current, variant


def _cached(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("cached must be a dict")
    body = _without_model_name(value)
    if set(body) != set(_CACHED_FIELDS):
        raise ValueError("invalid cached fields")
    logical = _text(body["logicalId"], "logicalId")
    physical = _optional_text(body["physicalId"], "physicalId")
    identities = {field: _text(body[field], field) for field in _IDENTITY_FIELDS}
    qualified = _flag(body["qualified"], "qualified")
    return {
        "logicalId": logical,
        "physicalId": physical,
        **identities,
        "qualified": qualified,
    }


def _current(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("current must be a dict")
    body = _without_model_name(value)
    if set(body) != set(_CURRENT_FIELDS):
        raise ValueError("invalid current fields")
    return {field: _text(body[field], field) for field in _IDENTITY_FIELDS}


def _without_model_name(value: dict) -> dict:
    return {key: item for key, item in value.items() if key != "modelName"}


def _flag(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _text(value, label)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
) -> dict:
    if decision != "allowed" and not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["focal unknown"],
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
