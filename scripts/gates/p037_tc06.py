"""TC-P037-06 calibration identity mismatch.

Reject a profile whose firmware, crop, route, or CFA does not match the
source, unless the caller marks an explicit provisional research path.
Provisional results keep the source provenance. Using current device metadata
without an identity check is rejected.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P037-06"
INTERVENTION = "Pair a source with metadata or a profile from a different firmware, crop, route, or CFA."
EXPECTED = (
    "Reject incompatible development or require an explicitly provisional research path "
    "without changing provenance."
)
NEGATIVE = "Using current device metadata for an old source without checking identity must fail."

_FIELDS = ("firmware", "crop", "route", "cfa")
_MISMATCH = _FIELDS + ("none",)
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_PAYLOAD_KEYS = (
    "sourceFirmware",
    "sourceCrop",
    "sourceRoute",
    "sourceCfa",
    "profileFirmware",
    "profileCrop",
    "profileRoute",
    "profileCfa",
    "mismatchField",
    "useCurrentDevice",
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
_FORBIDDEN = {"qualified", "allowed"}
_SOURCE_KEY = {
    "firmware": "sourceFirmware",
    "crop": "sourceCrop",
    "route": "sourceRoute",
    "cfa": "sourceCfa",
}
_PROFILE_KEY = {
    "firmware": "profileFirmware",
    "crop": "profileCrop",
    "route": "profileRoute",
    "cfa": "profileCfa",
}


def evaluate(payload: dict) -> dict:
    """Reject an identity mismatch or keep a provisional path on the source."""
    fields = _payload(payload)
    preserved = [
        f"sourceFirmware:{fields['sourceFirmware']}",
        f"sourceCrop:{fields['sourceCrop']}",
        f"sourceRoute:{fields['sourceRoute']}",
        f"sourceCfa:{fields['sourceCfa']}",
    ]
    reasons = [EXPECTED, INTERVENTION, f"mismatch {fields['mismatchField']}"]
    if fields["useCurrentDevice"]:
        reasons.append(NEGATIVE)
        reasons.append("source provenance was not replaced")
        return _result(
            "rejected",
            reasons,
            ["unchecked-current-device-metadata"],
            preserved,
            ["current device metadata was not applied"],
        )
    field = fields["mismatchField"]
    if field == "none":
        reasons.append("identity fields matched")
        return _result("identity_checked", reasons, [], preserved, [])
    claim = f"identity-mismatch:{field}"
    if fields["provisional"]:
        reasons.append("provisional research path left source provenance unchanged")
        reasons.append(f"profile {field} was not copied onto the source")
        return _result(
            "provisional_research",
            reasons,
            [],
            preserved,
            [f"provisional {field} mismatch"],
        )
    reasons.append(f"rejected on {field}")
    return _result("rejected", reasons, [claim], preserved, [f"{field} mismatch"])


def _token(value: object, label: str) -> str:
    if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
        raise ValueError(label + " must be a token")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    fields = {key: _token(payload[key], key) for key in _PAYLOAD_KEYS if key.startswith("source") or key.startswith("profile")}
    mismatch = payload["mismatchField"]
    if mismatch not in _MISMATCH:
        raise ValueError("mismatchField is unknown")
    use_current = payload["useCurrentDevice"]
    provisional = payload["provisional"]
    if type(use_current) is not bool or type(provisional) is not bool:
        raise ValueError("useCurrentDevice and provisional must be bools")
    differed = [name for name in _FIELDS if fields[_SOURCE_KEY[name]] != fields[_PROFILE_KEY[name]]]
    if mismatch == "none":
        if differed:
            raise ValueError("mismatchField none requires identical identity fields")
        if provisional:
            raise ValueError("provisional does not apply when identity matches")
    else:
        if differed != [mismatch]:
            raise ValueError("mismatchField must be the only differing identity field")
    fields["mismatchField"] = mismatch
    fields["useCurrentDevice"] = use_current
    fields["provisional"] = provisional
    return fields


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in _FORBIDDEN:
        raise ValueError("TC-P037-06 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
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
