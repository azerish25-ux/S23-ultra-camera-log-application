"""TC-P013-04 firmware and codec cache staleness for codec routes.

A cached probe is historical only after build, codec, or probe-protocol
identity changes. A marketing model name must not bypass that change.
"""

from __future__ import annotations

CASE_ID = "TC-P013-04"
INTERVENTION = (
    "Change device build or codec identity while retaining a previously "
    "successful cached probe."
)
EXPECTED = (
    "Require requalification for affected tuples and preserve the old report "
    "only as historical evidence."
)
NEGATIVE = "A marketing-model-name cache hit must not bypass the changed environment."
VARIANTS = ("build_changed", "codec_changed", "protocol_changed", "unchanged")
_CACHED_FIELDS = (
    "tupleId",
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
_PAYLOAD_KEYS = ("cached", "current", "modelName", "variant")
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
    cached, current, model_name, _variant = _payload(payload)
    changes = [label for key, label in _IDENTITY if cached[key] != current[key]]
    tuple_id = cached["tupleId"]
    historical = f"historical:{tuple_id}"
    if changes:
        decision = "requalify"
        reasons = [
            "cached probe is historical only after " + ", ".join(changes) + " identity change",
            NEGATIVE,
            f"marketing model name {model_name} is not a cache key",
        ]
        rejected = ["cache-hit", "model-name-bypass"]
        preserved = [historical]
        open_questions = ["requalify affected tuples before reuse"]
    elif cached["previouslySuccessful"]:
        decision = "current"
        reasons = [
            "build, codec, and probe-protocol identities match the cached probe",
            "current status is not a new physical qualification",
        ]
        rejected = []
        preserved = [tuple_id, historical]
        open_questions = []
    else:
        decision = "unqualified"
        reasons = [
            "build, codec, and probe-protocol identities match the unsuccessful cached probe",
        ]
        rejected = []
        preserved = [historical]
        open_questions = ["cached probe was not previously successful"]

    if changes and decision != "requalify":
        raise ValueError("identity change requires requalification")
    if changes and decision in {"qualified", "allowed", "current"}:
        raise ValueError("model-name cache hit must not bypass a changed environment")
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P013-04 must not decide qualified or allowed")
    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object) -> tuple[dict, dict, str, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("payload keys must be cached, current, modelName, and variant")
    variant = payload["variant"]
    if variant not in VARIANTS:
        raise ValueError(
            "variant must be build_changed, codec_changed, protocol_changed, or unchanged"
        )
    model_name = payload["modelName"]
    if not isinstance(model_name, str) or model_name == "" or model_name != model_name.strip():
        raise ValueError("modelName must be a non-empty string")
    cached = _mapping(payload["cached"], _CACHED_FIELDS, "cached")
    current = _mapping(payload["current"], _CURRENT_FIELDS, "current")
    _text(cached["tupleId"], "tupleId")
    for key, _label in _IDENTITY:
        _text(cached[key], key)
        _text(current[key], key)
    if type(cached["previouslySuccessful"]) is not bool:
        raise ValueError("previouslySuccessful must be a bool")
    return cached, current, model_name, variant


def _mapping(value: object, fields: tuple[str, ...], label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a dict")
    if set(value) != set(fields):
        raise ValueError(f"invalid {label} fields")
    return value


def _text(value: object, field: str) -> None:
    if not isinstance(value, str) or value == "" or value != value.strip():
        raise ValueError(f"{field} must be a non-empty string")


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision not in {"requalify", "current", "unqualified"}:
        raise ValueError("unexpected TC-P013-04 decision")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": open_questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
