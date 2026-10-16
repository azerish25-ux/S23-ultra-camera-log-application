"""TC-P121-06 Missing or revoked media access.

Host fixture. Availability follows the source grant, not a cached thumbnail.
Historical metadata is kept when the bytes are gone.
"""

from __future__ import annotations


CASE_ID = "TC-P121-06"
NAME = "Missing or revoked media access"
INTERVENTION = "Revoke the source grant or remove a file while the library still has a cached thumbnail."
EXPECTED = "Show actual availability and preserve historical metadata without treating the thumbnail as accessible media."
NEGATIVE = "Thumbnail presence must not certify a valid source or output."
REPEAT = "Repeat local files, document-provider grants, and recovered private media."
THUMB_TOKEN = "thumbnail-certifies-source"
ACCESS_TOKEN = "unavailable-source-treated-as-accessible"
REPEATS = ("local-file", "document-provider", "recovered-private")
GRANTS = ("valid", "revoked", "removed")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "sourceGrant",
    "thumbnailPresent",
    "treatedAsAccessible",
    "historicalMetadata",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Report the grant. A thumbnail is not a source and not an output."""
    fields = _payload(payload)
    available = fields["sourceGrant"] == "valid"
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}", f"grant {fields['sourceGrant']}"]
    if not available and fields["treatedAsAccessible"] and fields["thumbnailPresent"]:
        rejected.append(THUMB_TOKEN)
        reasons.append(NEGATIVE)
    elif not available and fields["treatedAsAccessible"]:
        rejected.append(ACCESS_TOKEN)
        reasons.append("revoked or removed media was treated as accessible")
    if available and not fields["treatedAsAccessible"]:
        rejected.append("valid-source-hidden")
        reasons.append("a valid grant was not shown as available")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("available" if available else "unavailable")
        reasons.append("historical metadata retained")
    preserved = [
        fields["evidenceId"],
        {
            "availability": "available" if available else fields["sourceGrant"],
            "thumbnailPresent": fields["thumbnailPresent"],
            "thumbnailCertifiesSource": False,
            "historicalMetadata": dict(fields["historicalMetadata"]),
        },
    ]
    questions = ["physical S23 capture was not run", REPEAT]
    return _result(decision, reasons, rejected, preserved, questions)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    repeat = payload["repeat"]
    grant = payload["sourceGrant"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    if grant not in GRANTS:
        raise ValueError("sourceGrant is unsupported")
    for label in ("thumbnailPresent", "treatedAsAccessible"):
        if type(payload[label]) is not bool:
            raise ValueError(f"{label} must be a bool")
    metadata = payload["historicalMetadata"]
    if not isinstance(metadata, dict) or not metadata:
        raise ValueError("historicalMetadata must be a non-empty object")
    clean = {}
    for key, value in metadata.items():
        if not isinstance(key, str) or not isinstance(value, str) or not key.strip() or not value.strip():
            raise ValueError("historicalMetadata entries must be non-empty strings")
        clean[key] = value
    return {
        "evidenceId": _text(payload["evidenceId"], "evidenceId"),
        "repeat": repeat,
        "sourceGrant": grant,
        "thumbnailPresent": payload["thumbnailPresent"],
        "treatedAsAccessible": payload["treatedAsAccessible"],
        "historicalMetadata": clean,
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
