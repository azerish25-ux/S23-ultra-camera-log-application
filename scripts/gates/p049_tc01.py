"""TC-P049-01 negative and bright intermediate values.

Intervention: Exercise values below black and highlights above diffuse white
through the phase boundary.
Expected: Preserve valid signed and over-range information until the explicitly
declared storage or display limit.
Negative: An implicit zero-to-one clamp must be detected.
"""

from __future__ import annotations

from fractions import Fraction


CASE_ID = "TC-P049-01"
INTERVENTION = (
    "Exercise values below black and highlights above diffuse white through the phase boundary."
)
EXPECTED = (
    "Preserve valid signed and over-range information until the explicitly declared "
    "storage or display limit."
)
NEGATIVE = "An implicit zero-to-one clamp must be detected."

_LOCI = (
    "below-black",
    "zero",
    "source-white",
    "above-white",
    "encoding-boundary",
    "beyond-storage",
)
_PAYLOAD_KEYS = ("code", "black", "white", "storageLimit", "locus", "implicitClamp")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "signed_retained", "limit_held")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep signed and over-range values. Detect an implicit zero-to-one clamp."""
    code, black, white, limit, locus, implicit = _payload(payload)
    ratio = Fraction(code - black, white - black)
    norm = str(ratio)
    preserved = [
        f"code:{code}",
        f"black:{black}",
        f"white:{white}",
        f"norm:{norm}",
        f"locus:{locus}",
        f"storage-limit:{limit}",
    ]
    reasons = [EXPECTED]
    if implicit:
        decision = "rejected"
        rejected = ["implicit-zero-to-one-clamp"]
        reasons.append(NEGATIVE)
        reasons.append(f"clamp would have stored {_clamped(ratio)} and destroyed {norm}")
        questions = ["signed value retained despite the clamp attempt"]
    elif locus == "beyond-storage":
        decision = "limit_held"
        rejected = []
        reasons.append("over-range retained until the declared storage limit")
        questions = ["value exceeds the declared storage limit and is not scene white"]
    elif locus == "source-white":
        decision = "signed_retained"
        rejected = []
        reasons.append("source white reference is not a universal scene-white boundary")
        questions = ["normalized one is a source reference"]
    elif locus == "encoding-boundary":
        decision = "signed_retained"
        rejected = []
        reasons.append("held at the declared storage limit without an implicit clamp")
        questions = ["encoding boundary is not an implicit zero-to-one clamp"]
    else:
        decision = "signed_retained"
        rejected = []
        reasons.append("signed and over-range information preserved")
        questions = ["no implicit zero-to-one clamp"]
    return _result(decision, reasons, rejected, preserved, questions)


def _clamped(ratio: Fraction) -> str:
    if ratio < 0:
        return "0"
    if ratio > 1:
        return "1"
    return str(ratio)


def _payload(payload: object) -> tuple[int, int, int, int, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    code = _uint(payload["code"], "code")
    black = _uint(payload["black"], "black")
    white = _uint(payload["white"], "white")
    limit = _uint(payload["storageLimit"], "storageLimit")
    if white <= black:
        raise ValueError("white must exceed black")
    if limit <= 0:
        raise ValueError("storageLimit must be positive")
    locus = payload["locus"]
    if locus not in _LOCI:
        raise ValueError("locus is unknown")
    implicit = payload["implicitClamp"]
    if type(implicit) is not bool:
        raise ValueError("implicitClamp must be a bool")
    ratio = Fraction(code - black, white - black)
    if locus == "below-black" and not code < black:
        raise ValueError("locus does not match the code")
    if locus == "zero" and code != black:
        raise ValueError("locus does not match the code")
    if locus == "source-white" and code != white:
        raise ValueError("locus does not match the code")
    if locus == "above-white" and not (code > white and 1 < ratio < limit):
        raise ValueError("locus does not match the code")
    if locus == "encoding-boundary" and ratio != limit:
        raise ValueError("locus does not match the code")
    if locus == "beyond-storage" and not ratio > limit:
        raise ValueError("locus does not match the code")
    return code, black, white, limit, locus, implicit


def _uint(value: object, label: str) -> int:
    if not isinstance(value, str) or not value or value[0] == "-" or not value.isdigit():
        raise ValueError(label + " must be a canonical non-negative integer string")
    if value != "0" and value[0] == "0":
        raise ValueError(label + " must be canonical")
    return int(value)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("decision cannot be qualified or allowed")
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
