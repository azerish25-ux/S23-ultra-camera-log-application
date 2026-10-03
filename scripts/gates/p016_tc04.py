"""TC-P016-04 firmware and codec cache staleness on the first slice.

A cached probe is historical after build, codec, or probe-protocol identity
changes. A marketing model name is ignored. A cache match is not a physical
S23 qualification.
"""

from __future__ import annotations

CASE_ID = "TC-P016-04"
INTERVENTION = (
    "Change device build or codec identity while retaining a previously successful cached probe."
)
EXPECTED = (
    "Require requalification for affected tuples and preserve the old report "
    "only as historical evidence."
)
NEGATIVE = "A marketing-model-name cache hit must not bypass the changed environment."
VARIANTS = ("build_changed", "codec_changed", "protocol_changed", "unchanged")
_VARIANT_DIFFS = {
    "unchanged": frozenset(),
    "build_changed": frozenset({"build"}),
    "codec_changed": frozenset({"codec"}),
    "protocol_changed": frozenset({"probe-protocol"}),
}
_CACHED_FIELDS = (
    "streamId",
    "buildFingerprint",
    "codecIdentity",
    "probeProtocol",
    "previouslySuccessful",
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
_ORACLE_PRESERVED = ("file-retained", "playback:separate", "cadence:separate")
_NOT_ENDURANCE = "not-endurance-certified"


def evaluate(payload: dict) -> dict:
    """Requalify when cache identity drifts. Ignore the marketing model name."""
    cached, current, _model_name, _variant = _payload(payload)
    changes = [label for key, label in _IDENTITY if cached[key] != current[key]]
    stream_id = cached["streamId"]
    if changes:
        decision = "requalify"
        reasons = [
            "cached probe is historical only after " + ", ".join(changes) + " identity change"
        ]
        rejected = ["cache-hit"]
        preserved = [f"historical:{stream_id}"]
        if decision in {"qualified", "allowed"} or stream_id in preserved:
            raise ValueError("a changed environment must not keep a live cache hit")
    elif cached["previouslySuccessful"]:
        decision = "cache_current"
        reasons = [
            "build, codec, and probe-protocol identities match the cached probe",
            "a cache match is not a physical S23 qualification",
        ]
        rejected = []
        preserved = [stream_id]
    else:
        decision = "cache_unsuccessful"
        reasons = [
            "build, codec, and probe-protocol identities match the unsuccessful cached probe"
        ]
        rejected = []
        preserved = [stream_id]

    if changes and decision != "requalify":
        raise ValueError("identity change requires requalification")
    if _model_name and changes and decision != "requalify":
        raise ValueError(NEGATIVE)
    return _finish(decision, reasons, rejected, preserved, [])


def _finish(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError(f"{CASE_ID} must not decide qualified or allowed")
    kept = list(preserved)
    for token in _ORACLE_PRESERVED:
        if token not in kept:
            kept.append(token)
    questions = list(open_questions)
    if _NOT_ENDURANCE not in questions:
        questions.append(_NOT_ENDURANCE)
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": kept,
        "openQuestions": questions,
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
    if type(cached["previouslySuccessful"]) is not bool:
        raise ValueError("previouslySuccessful must be a bool")
    changes = {label for key, label in _IDENTITY if cached[key] != current[key]}
    if changes != _VARIANT_DIFFS[variant]:
        raise ValueError("variant does not match the identity diff")
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
