"""TC-P051-01 negative and bright intermediate values.

Intervention: Exercise values below black and highlights above diffuse white
through the phase boundary.
Expected: Preserve valid signed and over-range information until the explicitly
declared storage or display limit.
Negative: An implicit zero-to-one clamp must be detected.
"""

from __future__ import annotations

CASE_ID = "TC-P051-01"
INTERVENTION = (
    "Exercise values below black and highlights above diffuse white through the phase boundary."
)
EXPECTED = (
    "Preserve valid signed and over-range information until the explicitly declared "
    "storage or display limit."
)
NEGATIVE = "An implicit zero-to-one clamp must be detected."

_CLAMPS = ("none", "declared-limit", "implicit-zero-one")
_PAYLOAD_KEYS = (
    "samples",
    "blackLevel",
    "whiteLevel",
    "encodingMin",
    "encodingMax",
    "clamp",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "retained", "limited")
_FORBIDDEN = {"qualified", "allowed"}
_LIMIT = 1_000_000


def evaluate(payload: dict) -> dict:
    """Keep signed and over-range samples unless a declared limit says otherwise."""
    samples, black, white, encoding_min, encoding_max, clamp = _payload(payload)
    preserved = [f"sample:{value}" for value in samples]
    preserved.append(f"black:{black}")
    preserved.append(f"white:{white}")
    preserved.append(f"encoding:{encoding_min}:{encoding_max}")
    if clamp == "implicit-zero-one":
        return _result(
            "rejected",
            [EXPECTED, NEGATIVE, "implicit zero-to-one clamp detected"],
            ["implicit-zero-to-one-clamp"],
            preserved,
            ["signed and over-range samples remain in the inventory"],
        )
    if clamp == "declared-limit":
        notes: list[str] = []
        for value in samples:
            if value < encoding_min or value > encoding_max:
                clipped = min(max(value, encoding_min), encoding_max)
                notes.append(f"limited:{value}->{clipped}")
            else:
                notes.append(f"kept:{value}")
        return _result(
            "limited",
            [EXPECTED, "only the declared storage or display limit was applied"],
            [],
            preserved + notes,
            [],
        )
    return _result(
        "retained",
        [EXPECTED, "signed and over-range values were not clamped"],
        [],
        preserved,
        [],
    )


def _payload(payload: object) -> tuple[list[int], int, int, int, int, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    samples = payload["samples"]
    if type(samples) is not list or not samples:
        raise ValueError("samples must be a non-empty list")
    parsed: list[int] = []
    for value in samples:
        if type(value) is not int or not -_LIMIT <= value <= _LIMIT:
            raise ValueError("sample out of range")
        parsed.append(value)
    black = _level(payload["blackLevel"], "blackLevel")
    white = _level(payload["whiteLevel"], "whiteLevel")
    if white <= black:
        raise ValueError("whiteLevel must exceed blackLevel")
    encoding_min = _level(payload["encodingMin"], "encodingMin")
    encoding_max = _level(payload["encodingMax"], "encodingMax")
    if encoding_max <= encoding_min:
        raise ValueError("encodingMax must exceed encodingMin")
    clamp = payload["clamp"]
    if clamp not in _CLAMPS:
        raise ValueError("clamp must be none, declared-limit, or implicit-zero-one")
    return parsed, black, white, encoding_min, encoding_max, clamp


def _level(value: object, label: str) -> int:
    if type(value) is not int or not -_LIMIT <= value <= _LIMIT:
        raise ValueError(label + " must be an in-range int")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("value decision cannot be qualified or allowed")
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
