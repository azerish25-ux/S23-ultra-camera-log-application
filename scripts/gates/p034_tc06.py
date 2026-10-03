"""TC-P034-06 calibration identity mismatch.

Reject a profile that differs in firmware, crop, route, or CFA. An explicit
provisional path may continue only while source provenance stays unchanged.
Using current-device metadata without an identity check fails.
"""

from __future__ import annotations

CASE_ID = "TC-P034-06"
INTERVENTION = (
    "Pair a source with metadata or a profile from a different firmware, crop, route, or CFA."
)
EXPECTED = (
    "Reject incompatible development or require an explicitly provisional research "
    "path without changing provenance."
)
NEGATIVE = "Using current device metadata for an old source without checking identity must fail."

CFAS = ("RGGB", "GRBG", "GBRG", "BGGR")
_FIELDS = ("firmware", "crop", "route", "cfa")
_PAYLOAD_KEYS = (
    "sourceFirmware",
    "sourceCrop",
    "sourceRoute",
    "sourceCfa",
    "profileFirmware",
    "profileCrop",
    "profileRoute",
    "profileCfa",
    "uncheckedCurrentDevice",
    "provisional",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "provisional", "identity_checked"}
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep source provenance unless identity was checked or marked provisional."""
    source, profile, unchecked, provisional = _payload(payload)
    preserved = [f"source-{name}:{source[name]}" for name in _FIELDS]
    preserved.extend(f"profile-{name}:{profile[name]}" for name in _FIELDS)
    mismatched = [name for name in _FIELDS if source[name] != profile[name]]
    reasons = [INTERVENTION, EXPECTED]
    if unchecked:
        reasons.append(NEGATIVE)
        reasons.append("source provenance was not replaced by current device metadata")
        return _result(
            "rejected",
            reasons,
            ["unchecked-current-device"],
            preserved,
            ["identity was not checked"],
        )
    if mismatched and not provisional:
        reasons.append("incompatible identity fields: " + ", ".join(mismatched))
        reasons.append("source provenance was not overwritten")
        return _result(
            "rejected",
            reasons,
            [f"mismatch:{name}" for name in mismatched],
            preserved,
            [f"mismatch:{name}" for name in mismatched],
        )
    if mismatched:
        reasons.append("provisional research path does not change source provenance")
        return _result(
            "provisional",
            reasons,
            [],
            preserved,
            [f"provisional:{name}" for name in mismatched],
        )
    reasons.append("identity fields match; this is not physical calibration")
    return _result("identity_checked", reasons, [], preserved, ["physical calibration unverified"])


def _payload(payload: object) -> tuple[dict, dict, bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    source = {
        "firmware": _text(payload["sourceFirmware"], "sourceFirmware"),
        "crop": _text(payload["sourceCrop"], "sourceCrop"),
        "route": _text(payload["sourceRoute"], "sourceRoute"),
        "cfa": _cfa(payload["sourceCfa"], "sourceCfa"),
    }
    profile = {
        "firmware": _text(payload["profileFirmware"], "profileFirmware"),
        "crop": _text(payload["profileCrop"], "profileCrop"),
        "route": _text(payload["profileRoute"], "profileRoute"),
        "cfa": _cfa(payload["profileCfa"], "profileCfa"),
    }
    unchecked = payload["uncheckedCurrentDevice"]
    provisional = payload["provisional"]
    if type(unchecked) is not bool or type(provisional) is not bool:
        raise ValueError("uncheckedCurrentDevice and provisional must be bools")
    return source, profile, unchecked, provisional


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _cfa(value: object, label: str) -> str:
    if value not in CFAS:
        raise ValueError(f"{label} is not a supported CFA")
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
