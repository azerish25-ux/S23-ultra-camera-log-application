"""TC-P033-06 calibration identity mismatch.

A source and a profile must agree on firmware, crop, route, and CFA before
development. A mismatch is rejected, or held to an explicit provisional
research path that does not change provenance. Current device metadata used
without an identity check is the negative control.
"""

from __future__ import annotations

CASE_ID = "TC-P033-06"
INTERVENTION = "Pair a source with metadata or a profile from a different firmware, crop, route, or CFA."
EXPECTED = (
    "Reject incompatible development or require an explicitly provisional research path without "
    "changing provenance."
)
NEGATIVE = "Using current device metadata for an old source without checking identity must fail."
REPEATS = ("firmware", "crop", "route", "cfa")
_FIELDS = REPEATS
_CFAS = ("RGGB", "GRBG", "GBRG", "BGGR")
_PAYLOAD_KEYS = (
    "sourceFirmware",
    "sourceCrop",
    "sourceRoute",
    "sourceCfa",
    "profileFirmware",
    "profileCrop",
    "profileRoute",
    "profileCfa",
    "provisional",
    "useCurrentDeviceMetadata",
    "identityChecked",
    "provenanceChanged",
    "evidenceId",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Reject a mismatched identity unless the path is explicitly provisional."""
    data = _payload(payload)
    mismatches = [field for field in _FIELDS if data["source"][field] != data["profile"][field]]
    reasons = ["compared " + ",".join(_FIELDS)]
    rejected: list[str] = []
    if data["useCurrentDeviceMetadata"] and not data["identityChecked"]:
        rejected.append("unchecked-current-metadata")
        reasons.append(NEGATIVE)
    elif not data["identityChecked"]:
        rejected.append("identity-not-checked")
        reasons.append("identity was not checked")
    if data["provenanceChanged"]:
        rejected.append("provenance-changed")
        reasons.append("provenance must not change")
    if mismatches and data["identityChecked"]:
        rejected.extend("mismatch-" + field for field in mismatches)
        reasons.append("mismatched " + ",".join(mismatches))
    if rejected and not (
        mismatches
        and data["provisional"]
        and data["identityChecked"]
        and not data["provenanceChanged"]
        and not (data["useCurrentDeviceMetadata"] and not data["identityChecked"])
    ):
        decision = "rejected"
        reasons.append(EXPECTED)
    elif mismatches and data["provisional"]:
        decision = "provisional_research"
        rejected = ["mismatch-" + field for field in mismatches]
        reasons.append(EXPECTED)
        reasons.append("provisional research does not change provenance and is not qualification")
    elif not mismatches and data["identityChecked"] and not data["provenanceChanged"]:
        decision = "identity_checked"
        reasons.append("firmware, crop, route, and CFA match")
        reasons.append("identity_checked is not a measured calibration")
    else:
        decision = "rejected"
        reasons.append(EXPECTED)
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P033-06 must not yield qualified or allowed")
    questions = ["no physical calibration is claimed"]
    return _result(decision, reasons, rejected, _preserved(data), questions)


def _payload(payload: object) -> dict:
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
    evidence = _text(payload["evidenceId"], "evidenceId")
    return {
        "source": source,
        "profile": profile,
        "provisional": _bool(payload["provisional"], "provisional"),
        "useCurrentDeviceMetadata": _bool(payload["useCurrentDeviceMetadata"], "useCurrentDeviceMetadata"),
        "identityChecked": _bool(payload["identityChecked"], "identityChecked"),
        "provenanceChanged": _bool(payload["provenanceChanged"], "provenanceChanged"),
        "evidenceId": evidence,
    }


def _preserved(data: dict) -> list[str]:
    preserved = ["evidence:" + data["evidenceId"]]
    for label, side in (("source", data["source"]), ("profile", data["profile"])):
        for field in _FIELDS:
            preserved.append(label + "-" + field + ":" + side[field])
    preserved.append("provenance:" + ("changed" if data["provenanceChanged"] else "unchanged"))
    return preserved


def _cfa(value: object, name: str) -> str:
    text = _text(value, name)
    if text not in _CFAS:
        raise ValueError(f"{name} must be a supported CFA")
    return text


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P033-06 must not yield qualified or allowed")
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
