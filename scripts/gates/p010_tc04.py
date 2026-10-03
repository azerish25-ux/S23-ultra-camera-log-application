"""TC-P010-04 ordinary stream map: firmware and codec cache staleness.

A cached probe is historical only after build, codec, or probe-protocol
identity changes. A marketing model name must not bypass that.
"""

from __future__ import annotations

CASE_ID = "TC-P010-04"
VARIANTS = ("build_changed", "codec_changed", "protocol_changed", "unchanged")
_CACHED_FIELDS = (
    "streamId",
    "buildFingerprint",
    "codecIdentity",
    "probeProtocol",
    "qualified",
)
_CURRENT_FIELDS = ("buildFingerprint", "codecIdentity", "probeProtocol")
_IDENTITY = (
    ("buildFingerprint", "build"),
    ("codecIdentity", "codec"),
    ("probeProtocol", "probe-protocol"),
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Requalify when cache identity drifts. Ignore the marketing model name."""
    cached, current, _model_name, _variant = _payload(payload)
    changes = [
        label for key, label in _IDENTITY if cached[key] != current[key]
    ]
    stream_id = cached["streamId"]
    if changes:
        decision = "requalify"
        reasons = [
            "cached probe is historical only after "
            + ", ".join(changes)
            + " identity change"
        ]
        rejected = ["cache-hit"]
        preserved = [f"historical:{stream_id}"]
    elif cached["qualified"]:
        decision = "qualified"
        reasons = [
            "build, codec, and probe-protocol identities match the qualified cached probe"
        ]
        rejected = []
        preserved = [stream_id]
    else:
        decision = "unqualified"
        reasons = [
            "build, codec, and probe-protocol identities match the unqualified cached probe"
        ]
        rejected = []
        preserved = [stream_id]

    if changes and decision != "requalify":
        raise ValueError("identity change requires requalification")
    if changes and cached["qualified"] and decision == "qualified":
        raise ValueError("qualified cache must not win after identity change")
    if not reasons:
        raise ValueError("reasons required")

    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": [],
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result


def _payload(payload: object) -> tuple[dict, dict, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != {"cached", "current", "modelName", "variant"}:
        raise ValueError("payload keys must be cached, current, modelName, and variant")
    variant = payload["variant"]
    if variant not in VARIANTS:
        raise ValueError(
            "variant must be build_changed, codec_changed, protocol_changed, or unchanged"
        )
    model_name = payload["modelName"]
    if not isinstance(model_name, str) or model_name == "":
        raise ValueError("modelName must be a non-empty string")
    cached = _mapping(payload["cached"], _CACHED_FIELDS, "cached")
    current = _mapping(payload["current"], _CURRENT_FIELDS, "current")
    _text(cached["streamId"], "streamId")
    for key, _label in _IDENTITY:
        _text(cached[key], key)
        _text(current[key], key)
    if not isinstance(cached["qualified"], bool):
        raise ValueError("qualified must be a bool")
    return cached, current, model_name, variant


def _mapping(value: object, fields: tuple[str, ...], label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a dict")
    if set(value) != set(fields):
        raise ValueError(f"invalid {label} fields")
    return value


def _text(value: object, field: str) -> None:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{field} must be a non-empty string")
