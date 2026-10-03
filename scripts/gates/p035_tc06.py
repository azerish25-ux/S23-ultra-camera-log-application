"""TC-P035-06 calibration identity mismatch.

Intervention: Pair a source with metadata or a profile from a different
firmware, crop, route, or CFA.
Expected: Reject incompatible development or require an explicitly provisional
research path without changing provenance.
Negative: Using current device metadata for an old source without checking
identity must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P035-06"
INTERVENTION = (
    "Pair a source with metadata or a profile from a different firmware, crop, route, or CFA."
)
EXPECTED = (
    "Reject incompatible development or require an explicitly provisional research path "
    "without changing provenance."
)
NEGATIVE = "Using current device metadata for an old source without checking identity must fail."

FIELDS = ("firmware", "crop", "route", "cfa", "none")
PATHS = ("check", "provisional", "current_device")
_PAYLOAD_KEYS = ("field", "sourceValue", "profileValue", "path", "provenance")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "provisional", "identity_checked")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep provenance. Mismatched identity is not current-device metadata."""
    field, source, profile, path, provenance = _payload(payload)
    label = "identity" if field == "none" else field
    preserved = [
        f"provenance:{provenance}",
        f"source:{label}={source}",
        f"profile:{label}={profile}",
    ]
    if path == "current_device":
        claims = ["current-device-metadata"]
        if field != "none":
            claims.append("mismatch-" + field)
        return _result(
            "rejected",
            [EXPECTED, NEGATIVE, "provenance was not replaced"],
            claims,
            preserved,
            ["identity unchecked"],
        )
    if field == "none":
        return _result(
            "identity_checked",
            [EXPECTED, "identity fields match and provenance is unchanged"],
            [],
            preserved,
            ["identity match is not physical S23 qualification"],
        )
    if path == "provisional":
        return _result(
            "provisional",
            [EXPECTED, "provisional research path does not change provenance"],
            ["mismatch-" + field],
            preserved,
            ["provisional path is not a measured profile"],
        )
    return _result(
        "rejected",
        [EXPECTED, f"{field} identity mismatch rejects development"],
        ["mismatch-" + field],
        preserved,
        ["provenance unchanged"],
    )


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload")
    field = payload["field"]
    path = payload["path"]
    source = payload["sourceValue"]
    profile = payload["profileValue"]
    provenance = payload["provenance"]
    if field not in FIELDS or path not in PATHS:
        raise ValueError("field or path")
    for label, value in (("sourceValue", source), ("profileValue", profile), ("provenance", provenance)):
        if not isinstance(value, str) or not value or value != value.strip():
            raise ValueError(label)
    if field == "none" and source != profile:
        raise ValueError("none requires equal identity values")
    if field != "none" and source == profile:
        raise ValueError("a named field must differ")
    if path == "provisional" and field == "none":
        raise ValueError("provisional path requires a mismatch")
    return field, source, profile, path, provenance


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("identity decision cannot be qualified or allowed")
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
