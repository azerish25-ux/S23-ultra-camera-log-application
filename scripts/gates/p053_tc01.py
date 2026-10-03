"""TC-P053-01 negative and bright intermediate values.

Intervention: Exercise values below black and highlights above diffuse white
through the phase boundary.
Expected: Preserve valid signed and over-range information until the explicitly
declared storage or display limit.
Negative: An implicit zero-to-one clamp must be detected.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P053-01"
INTERVENTION = (
    "Exercise values below black and highlights above diffuse white through the phase boundary."
)
EXPECTED = (
    "Preserve valid signed and over-range information until the explicitly declared "
    "storage or display limit."
)
NEGATIVE = "An implicit zero-to-one clamp must be detected."

_LOCI = ("around-zero", "source-white", "encoding-boundary")
_LIMIT_KINDS = ("none", "storage", "display")
_PAYLOAD_KEYS = ("sampleId", "locus", "value", "limitKind", "limit", "implicitClamp")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "preserved", "bounded")
_FORBIDDEN = {"qualified", "allowed"}
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")
_SIGNED = re.compile(r"0|-?[1-9][0-9]*")
_UINT = re.compile(r"0|[1-9][0-9]*")


def evaluate(payload: dict) -> dict:
    """Keep signed and over-range values. Reject an implicit zero-to-one clamp."""
    sample_id, locus, value, kind, limit, implicit = _payload(payload)
    preserved = [
        sample_id,
        f"locus:{locus}",
        f"value:{value}",
        f"limit-kind:{kind}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    if implicit:
        return _result(
            "rejected",
            reasons + [NEGATIVE],
            ["implicit-zero-to-one-clamp"],
            preserved,
            ["implicit clamp would erase signed or over-range information"],
        )
    if kind == "none":
        reasons.append(f"{locus} value {value} stays unmodified")
        return _result(
            "preserved",
            reasons,
            [],
            preserved,
            ["no storage or display limit was declared"],
        )
    preserved.append(f"limit:{kind}:{limit}")
    if int(value) > int(limit):
        reasons.append(f"explicit {kind} limit {limit} is recorded without a zero-to-one clamp")
        return _result(
            "bounded",
            reasons,
            [],
            preserved,
            [f"value exceeds the declared {kind} limit"],
        )
    reasons.append(f"{locus} value {value} is inside the declared {kind} limit")
    return _result("preserved", reasons, [], preserved, [f"{locus} retained"])


def _payload(payload: object) -> tuple[str, str, str, str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    sample_id = payload["sampleId"]
    if not isinstance(sample_id, str) or _TOKEN.fullmatch(sample_id) is None:
        raise ValueError("sampleId must be a token")
    locus = payload["locus"]
    if locus not in _LOCI:
        raise ValueError("locus is unknown")
    value = payload["value"]
    if not isinstance(value, str) or _SIGNED.fullmatch(value) is None:
        raise ValueError("value must be a canonical integer string")
    kind = payload["limitKind"]
    if kind not in _LIMIT_KINDS:
        raise ValueError("limitKind is unknown")
    limit = payload["limit"]
    if kind == "none":
        if limit != "none":
            raise ValueError("limit must be none when no limit is declared")
    elif not isinstance(limit, str) or _UINT.fullmatch(limit) is None:
        raise ValueError("limit must be a canonical non-negative integer string")
    implicit = payload["implicitClamp"]
    if type(implicit) is not bool:
        raise ValueError("implicitClamp must be a bool")
    return sample_id, locus, value, kind, limit, implicit


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("range decision cannot be qualified or allowed")
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
