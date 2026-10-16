"""TC-P123-06 Missing or revoked media access.

Host fixture. Displayed availability follows the source grant and file, not a
cached thumbnail. Historical metadata stays even when the media is gone.
"""

from __future__ import annotations


CASE_ID = "TC-P123-06"
NAME = "Missing or revoked media access"
INTERVENTION = "Revoke the source grant or remove a file while the library still has a cached thumbnail."
EXPECTED = "Show actual availability and preserve historical metadata without treating the thumbnail as accessible media."
NEGATIVE = "Thumbnail presence must not certify a valid source or output."
REPEAT = "Repeat local files, document-provider grants, and recovered private media."
GRANTS = ("present", "revoked")
AVAILABILITY = ("available", "unavailable")
REPEATS = ("local-file", "document-provider", "recovered-private")
PAYLOAD_KEYS = (
    "evidenceId",
    "sourceGrant",
    "filePresent",
    "thumbnailPresent",
    "thumbnailCertifiesAccess",
    "displayedAvailability",
    "historicalMetadata",
    "repeat",
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
    """Reject a thumbnail that stands in for a missing source."""
    fields = _payload(payload)
    actual = fields["sourceGrant"] == "present" and fields["filePresent"]
    expected = "available" if actual else "unavailable"
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}"]
    if fields["displayedAvailability"] != expected:
        rejected.append("availability-does-not-match-source")
        reasons.append(f"displayed {fields['displayedAvailability']} but actual availability is {expected}")
    if fields["thumbnailCertifiesAccess"]:
        rejected.append("thumbnail-certifies-source-or-output")
        reasons.append(NEGATIVE)
    if fields["thumbnailPresent"] and not actual and fields["displayedAvailability"] == "available":
        if "thumbnail-certifies-source-or-output" not in rejected:
            rejected.append("thumbnail-certifies-source-or-output")
        reasons.append("cached thumbnail was treated as accessible media")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("availability follows the source and historical metadata remains")
    preserved = [
        fields["evidenceId"],
        fields["historicalMetadata"],
        {
            "sourceGrant": fields["sourceGrant"],
            "filePresent": fields["filePresent"],
            "thumbnailPresent": fields["thumbnailPresent"],
            "actualAvailable": actual,
            "displayedAvailability": fields["displayedAvailability"],
        },
    ]
    return _result(decision, reasons, rejected, preserved, ["physical S23 capture was not run", REPEAT])


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    grant = payload["sourceGrant"]
    if grant not in GRANTS:
        raise ValueError("sourceGrant is unsupported")
    displayed = payload["displayedAvailability"]
    if displayed not in AVAILABILITY:
        raise ValueError("displayedAvailability is unsupported")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    metadata = payload["historicalMetadata"]
    if not isinstance(metadata, str) or not metadata.strip() or metadata != metadata.strip():
        raise ValueError("historicalMetadata must be a non-empty string")
    return {
        "evidenceId": evidence,
        "sourceGrant": grant,
        "filePresent": _bool(payload["filePresent"], "filePresent"),
        "thumbnailPresent": _bool(payload["thumbnailPresent"], "thumbnailPresent"),
        "thumbnailCertifiesAccess": _bool(payload["thumbnailCertifiesAccess"], "thumbnailCertifiesAccess"),
        "displayedAvailability": displayed,
        "historicalMetadata": metadata,
        "repeat": repeat,
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
