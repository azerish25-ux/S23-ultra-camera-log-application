"""TC-P121-08 Shared bundle privacy and interpretation.

Host fixture. Private paths are redacted. A Log master keeps its interpretation
record and is not presented as universally self-describing. Technical signal
and recipe metadata stay with the bundle.
"""

from __future__ import annotations


CASE_ID = "TC-P121-08"
NAME = "Shared bundle privacy and interpretation"
INTERVENTION = "Export a result with private paths or without necessary signal and recipe metadata."
EXPECTED = "Redact personal information while retaining the technical interpretation needed for correct use."
NEGATIVE = "A Log master without its required interpretation record must not be silently presented as universally self-describing."
REPEAT = "Repeat clean Log, rendered SDR, HDR-derived looks, and unverified partial exports."
LOG_TOKEN = "log-master-without-interpretation"
SELF_TOKEN = "log-master-presented-as-self-describing"
PARTIAL_TOKEN = "unverified-partial-presented-as-complete"
METADATA_TOKEN = "missing-signal-or-recipe-metadata"
REPEATS = ("clean-log", "rendered-sdr", "hdr-derived", "unverified-partial")
KINDS = {"clean-log": "log", "rendered-sdr": "sdr", "hdr-derived": "hdr", "unverified-partial": "partial"}
PRIVATE_MARKERS = ("/sdcard/", "/home/", "/storage/emulated/", "/storage/", "/Users/", "DCIM")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "paths",
    "masterKind",
    "interpretationRecord",
    "recipeMetadataPresent",
    "signalMetadataPresent",
    "presentedAsSelfDescribing",
    "verified",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _redact(path: str) -> str:
    for marker in PRIVATE_MARKERS:
        if marker in path:
            return "redacted://media"
    return path


def evaluate(payload: dict) -> dict:
    """Redact private paths and refuse a Log master that pretends to be self-describing."""
    fields = _payload(payload)
    redacted = [_redact(path) for path in fields["paths"]]
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}", f"kind {fields['masterKind']}"]
    record = fields["interpretationRecord"]
    kind = fields["masterKind"]
    if redacted != fields["paths"]:
        reasons.append("private paths redacted")
    if kind == "log" and (record is None or "transfer" not in record):
        rejected.append(LOG_TOKEN)
        reasons.append(NEGATIVE)
    if kind == "log" and fields["presentedAsSelfDescribing"]:
        rejected.append(SELF_TOKEN)
        reasons.append("a Log master was presented as universally self-describing")
    if kind == "hdr" and (record is None or "transfer" not in record):
        rejected.append("hdr-derived-without-interpretation")
        reasons.append("an HDR-derived look needs its interpretation record")
    if kind != "partial" and (not fields["recipeMetadataPresent"] or not fields["signalMetadataPresent"]):
        rejected.append(METADATA_TOKEN)
        reasons.append("signal and recipe metadata are required for correct use")
    if kind == "partial":
        if fields["presentedAsSelfDescribing"] or fields["verified"]:
            rejected.append(PARTIAL_TOKEN)
            reasons.append("an unverified partial export was presented as complete")
        if not fields["verified"]:
            reasons.append("partial export remains unverified")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("technical interpretation retained and personal paths redacted")
    preserved = [
        fields["evidenceId"],
        {
            "redactedPaths": redacted,
            "masterKind": kind,
            "interpretationRecord": None if record is None else dict(record),
            "recipeMetadataPresent": fields["recipeMetadataPresent"],
            "signalMetadataPresent": fields["signalMetadataPresent"],
            "presentedAsSelfDescribing": False if kind == "log" else fields["presentedAsSelfDescribing"],
            "verified": False if kind == "partial" else fields["verified"],
        },
    ]
    questions = ["physical S23 capture was not run", REPEAT]
    return _result(decision, reasons, rejected, preserved, questions)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _record(value: object) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or not value:
        raise ValueError("interpretationRecord must be null or a non-empty object")
    clean = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str) or not key.strip() or not item.strip():
            raise ValueError("interpretationRecord entries must be non-empty strings")
        clean[key] = item
    return clean


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    kind = payload["masterKind"]
    if kind != KINDS[repeat]:
        raise ValueError("masterKind does not match repeat")
    paths = payload["paths"]
    if not isinstance(paths, list) or not paths:
        raise ValueError("paths must be a non-empty list")
    clean_paths = []
    for index, path in enumerate(paths):
        if not isinstance(path, str) or not path.strip() or path != path.strip():
            raise ValueError(f"path {index} must be a non-empty string")
        clean_paths.append(path)
    for label in ("recipeMetadataPresent", "signalMetadataPresent", "presentedAsSelfDescribing", "verified"):
        if type(payload[label]) is not bool:
            raise ValueError(f"{label} must be a bool")
    return {
        "evidenceId": _text(payload["evidenceId"], "evidenceId"),
        "repeat": repeat,
        "paths": clean_paths,
        "masterKind": kind,
        "interpretationRecord": _record(payload["interpretationRecord"]),
        "recipeMetadataPresent": payload["recipeMetadataPresent"],
        "signalMetadataPresent": payload["signalMetadataPresent"],
        "presentedAsSelfDescribing": payload["presentedAsSelfDescribing"],
        "verified": payload["verified"],
    }


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if not reasons or not preserved or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    return result
