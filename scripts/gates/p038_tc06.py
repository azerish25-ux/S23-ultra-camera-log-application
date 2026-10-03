"""TC-P038-06 calibration identity mismatch.

Intervention: Pair a source with metadata or a profile from a different
firmware, crop, route, or CFA.
Expected: Reject incompatible development or require an explicitly provisional
research path without changing provenance.
Negative: Using current device metadata for an old source without checking
identity must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P038-06"
INTERVENTION = (
    "Pair a source with metadata or a profile from a different firmware, crop, route, or CFA."
)
EXPECTED = (
    "Reject incompatible development or require an explicitly provisional research "
    "path without changing provenance."
)
NEGATIVE = "Using current device metadata for an old source without checking identity must fail."

_ORIGINS = ("capture-snapshot", "current-device")
_FIELDS = ("firmware", "crop", "route", "cfa")
_PAYLOAD_KEYS = (
    "sourceFirmware",
    "sourceCrop",
    "sourceRoute",
    "sourceCfa",
    "sourceHandset",
    "sourceProvenance",
    "profileFirmware",
    "profileCrop",
    "profileRoute",
    "profileCfa",
    "profileHandset",
    "profileOrigin",
    "provisional",
    "checkIdentity",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "provisional", "identity_matched", "withheld")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Match firmware, crop, route, and CFA. Do not rewrite provenance."""
    source, profile, origin, provisional, check = _payload(payload)
    preserved = [f"provenance:{source['provenance']}"]
    for field in ("firmware", "crop", "route", "cfa", "handset"):
        preserved.append(f"source.{field}:{source[field]}")
    mismatches = [f"{field}-mismatch" for field in _FIELDS if source[field] != profile[field]]
    if origin == "current-device" and not check:
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "provenance was not changed"],
            ["current-metadata-as-capture-truth", *mismatches],
            preserved,
            ["identity was not checked"],
        )
    if not check:
        return _result(
            "withheld",
            [EXPECTED, "identity was not checked", "provenance was not changed"],
            [],
            preserved,
            ["identity check required"],
        )
    if mismatches and provisional:
        return _result(
            "provisional",
            [
                EXPECTED,
                "provisional research path does not change provenance",
                "provisional is not a measured profile",
            ],
            mismatches,
            preserved,
            ["provisional research only"],
        )
    if mismatches:
        return _result(
            "rejected",
            [EXPECTED, "incompatible development rejected", "provenance was not changed"],
            mismatches,
            preserved,
            ["identity mismatch"],
        )
    return _result(
        "identity_matched",
        [EXPECTED, "identity fields matched the capture-time source", "provenance unchanged"],
        [],
        preserved,
        ["identity match is not a measured colour profile"],
    )


def _payload(payload: object) -> tuple[dict, dict, str, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    source = {
        "firmware": _text(payload["sourceFirmware"], "sourceFirmware"),
        "crop": _text(payload["sourceCrop"], "sourceCrop"),
        "route": _text(payload["sourceRoute"], "sourceRoute"),
        "cfa": _text(payload["sourceCfa"], "sourceCfa"),
        "handset": _text(payload["sourceHandset"], "sourceHandset"),
        "provenance": _text(payload["sourceProvenance"], "sourceProvenance"),
    }
    profile = {
        "firmware": _text(payload["profileFirmware"], "profileFirmware"),
        "crop": _text(payload["profileCrop"], "profileCrop"),
        "route": _text(payload["profileRoute"], "profileRoute"),
        "cfa": _text(payload["profileCfa"], "profileCfa"),
        "handset": _text(payload["profileHandset"], "profileHandset"),
    }
    origin = payload["profileOrigin"]
    if origin not in _ORIGINS:
        raise ValueError("profileOrigin must be capture-snapshot or current-device")
    provisional = payload["provisional"]
    check = payload["checkIdentity"]
    if type(provisional) is not bool or type(check) is not bool:
        raise ValueError("provisional and checkIdentity must be bools")
    return source, profile, origin, provisional, check


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(label + " must be a non-empty string")
    return value


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
