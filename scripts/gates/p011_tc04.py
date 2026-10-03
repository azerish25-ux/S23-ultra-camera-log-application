"""TC-P011-04 firmware and codec cache staleness.

A cached timing probe is historical after build, codec, or probe-protocol
identity changes. A marketing model name must not bypass that change.
"""

from __future__ import annotations

import math


CASE_ID = "TC-P011-04"
INTERVENTION = (
    "Change device build or codec identity while retaining a previously successful cached probe."
)
EXPECTED = (
    "Require requalification for affected tuples and preserve the old report only as historical evidence."
)
NEGATIVE = "A marketing-model-name cache hit must not bypass the changed environment."
VARIANTS = ("build_changed", "codec_changed", "protocol_changed", "unchanged")
_CACHED_KEYS = ("tupleId", "buildFingerprint", "codecIdentity", "probeProtocol")
_CURRENT_KEYS = ("buildFingerprint", "codecIdentity", "probeProtocol")
_IDENTITY = (
    ("buildFingerprint", "build"),
    ("codecIdentity", "codec"),
    ("probeProtocol", "probe-protocol"),
)
_PAYLOAD_KEYS = (
    "cached",
    "current",
    "marketingModel",
    "variant",
    "aeMin",
    "aeMax",
    "requestedFps",
    "containerTimestampsAssigned",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed", "native_fixed_24"}


def evaluate(payload: dict) -> dict:
    """Requalify when cache identity drifts. Ignore the marketing model name."""
    cached, current, model, variant, ae_min, ae_max, requested, timestamps = _payload(payload)
    changes = [label for key, label in _IDENTITY if cached[key] != current[key]]
    inventory = [f"ae:{_text(ae_min)}-{_text(ae_max)}", f"requested:{_text(requested)}"]
    tuple_id = cached["tupleId"]
    if changes:
        decision = "requalify"
        reasons = [
            "cached probe is historical only after " + ", ".join(changes) + " identity change",
            f"marketing model {model} does not bypass the changed environment",
            f"variant {variant}",
        ]
        rejected = ["cache-hit"]
        preserved = [f"historical:{tuple_id}", *inventory]
        if decision in _FORBIDDEN:
            raise ValueError(NEGATIVE)
    else:
        decision = "cache_matches"
        reasons = [
            "build, codec, and probe-protocol identities match",
            "a marketing model name was not used as the cache key",
            f"variant {variant}",
        ]
        rejected = []
        preserved = [tuple_id, *inventory]
    if timestamps:
        rejected.append("native-fixed-24")
        reasons.append("container timestamps do not certify native fixed 24")
    if changes and decision != "requalify":
        raise ValueError(NEGATIVE)
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object):
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    variant = payload["variant"]
    if variant not in VARIANTS:
        raise ValueError("variant must be build_changed, codec_changed, protocol_changed, or unchanged")
    cached = _record(payload["cached"], set(_CACHED_KEYS), "cached")
    current = _record(payload["current"], set(_CURRENT_KEYS), "current")
    model = payload["marketingModel"]
    if not isinstance(model, str) or not model or model != model.strip():
        raise ValueError("marketingModel must be a non-empty string")
    timestamps = payload["containerTimestampsAssigned"]
    if type(timestamps) is not bool:
        raise ValueError("containerTimestampsAssigned must be a bool")
    ae_min = _rate(payload["aeMin"], "aeMin")
    ae_max = _rate(payload["aeMax"], "aeMax")
    if _cmp(ae_min, ae_max) > 0:
        raise ValueError("aeMin must not exceed aeMax")
    requested = _rate(payload["requestedFps"], "requestedFps")
    return cached, current, model, variant, ae_min, ae_max, requested, timestamps


def _record(value: object, keys: set[str], context: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(context + " fields are invalid")
    for key in keys:
        item = value[key]
        if not isinstance(item, str) or not item or item != item.strip():
            raise ValueError(context + "." + key + " must be a non-empty string")
    return value


def _rate(value: object, context: str) -> tuple[int, int]:
    if not isinstance(value, dict) or set(value) != {"numerator", "denominator"}:
        raise ValueError(context + " must be a numerator/denominator object")
    numerator = value["numerator"]
    denominator = value["denominator"]
    if type(numerator) is not int or type(denominator) is not int:
        raise ValueError(context + " must use ints")
    if numerator <= 0 or denominator <= 0:
        raise ValueError(context + " must be positive")
    if math.gcd(numerator, denominator) != 1:
        raise ValueError(context + " must be reduced")
    return numerator, denominator


def _text(rate: tuple[int, int]) -> str:
    return f"{rate[0]}/{rate[1]}"


def _cmp(left: tuple[int, int], right: tuple[int, int]) -> int:
    gap = left[0] * right[1] - right[0] * left[1]
    return (gap > 0) - (gap < 0)


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in _FORBIDDEN:
        raise ValueError("TC-P011-04 must not yield qualified, allowed, or native_fixed_24")
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
