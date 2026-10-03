"""TC-P036-06 calibration identity mismatch.

Intervention: Pair a source with metadata or a profile from a different
firmware, crop, route, or CFA.
Expected: Reject incompatible development or require an explicitly provisional
research path without changing provenance.
Negative: Using current device metadata for an old source without checking
identity must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P036-06"
INTERVENTION = (
    "Pair a source with metadata or a profile from a different firmware, crop, route, or CFA."
)
EXPECTED = (
    "Reject incompatible development or require an explicitly provisional research path "
    "without changing provenance."
)
NEGATIVE = "Using current device metadata for an old source without checking identity must fail."

_FIELDS = ("firmware", "crop", "route", "cfa")
_CFA = ("RGGB", "BGGR", "GRBG", "GBRG")
_PATHS = ("reject", "provisional", "unchecked")
_PAYLOAD_KEYS = (
    "sourceFirmware",
    "profileFirmware",
    "sourceCrop",
    "profileCrop",
    "sourceRoute",
    "profileRoute",
    "sourceCfa",
    "profileCfa",
    "path",
    "provenance",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "provisional", "checked")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Reject or mark provisional identity mismatches. Keep provenance."""
    fields = _payload(payload)
    pairs = {
        "firmware": (fields["sourceFirmware"], fields["profileFirmware"]),
        "crop": (fields["sourceCrop"], fields["profileCrop"]),
        "route": (fields["sourceRoute"], fields["profileRoute"]),
        "cfa": (fields["sourceCfa"], fields["profileCfa"]),
    }
    mismatched = [name for name in _FIELDS if pairs[name][0] != pairs[name][1]]
    preserved = [fields["provenance"]]
    for name in _FIELDS:
        preserved.append(f"source.{name}:{pairs[name][0]}")
        preserved.append(f"profile.{name}:{pairs[name][1]}")
    rejected = [f"identity-mismatch:{name}" for name in mismatched]
    questions: list[str] = []
    if fields["path"] == "unchecked":
        decision = "rejected"
        rejected = ["unchecked-current-device-metadata", *rejected]
        reasons = [NEGATIVE, EXPECTED, "provenance was not changed"]
        questions.append("identity was not checked")
    elif mismatched and fields["path"] == "reject":
        decision = "rejected"
        reasons = [EXPECTED, "incompatible development rejected", "provenance was not changed"]
        reasons.extend(f"mismatch {name}" for name in mismatched)
    elif mismatched and fields["path"] == "provisional":
        decision = "provisional"
        reasons = [
            EXPECTED,
            "explicit provisional research path",
            "provenance was not changed",
        ]
        reasons.extend(f"mismatch {name}" for name in mismatched)
        questions.append("provisional research path is not production development")
    else:
        decision = "checked"
        rejected = []
        reasons = [EXPECTED, "identity fields matched", "provenance was not changed"]
    return _result(decision, reasons, rejected, preserved, questions)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(label + " must be a non-empty string")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    source_cfa = _text(payload["sourceCfa"], "sourceCfa")
    profile_cfa = _text(payload["profileCfa"], "profileCfa")
    if source_cfa not in _CFA or profile_cfa not in _CFA:
        raise ValueError("cfa must be a supported pattern")
    path = payload["path"]
    if path not in _PATHS:
        raise ValueError("path must be reject, provisional, or unchecked")
    return {
        "sourceFirmware": _text(payload["sourceFirmware"], "sourceFirmware"),
        "profileFirmware": _text(payload["profileFirmware"], "profileFirmware"),
        "sourceCrop": _text(payload["sourceCrop"], "sourceCrop"),
        "profileCrop": _text(payload["profileCrop"], "profileCrop"),
        "sourceRoute": _text(payload["sourceRoute"], "sourceRoute"),
        "profileRoute": _text(payload["profileRoute"], "profileRoute"),
        "sourceCfa": source_cfa,
        "profileCfa": profile_cfa,
        "path": path,
        "provenance": _text(payload["provenance"], "provenance"),
    }


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
