"""TC-P125-06 Missing or revoked media access.

Host fixture. Availability follows the source grant. A cached thumbnail does
not certify the source or the output, and historical metadata stays.
"""

from __future__ import annotations


CASE_ID = "TC-P125-06"
NAME = "Missing or revoked media access"
INTERVENTION = "Revoke the source grant or remove a file while the library still has a cached thumbnail."
EXPECTED = "Show actual availability and preserve historical metadata without treating the thumbnail as accessible media."
NEGATIVE = "Thumbnail presence must not certify a valid source or output."
REPEAT = "Repeat local files, document-provider grants, and recovered private media."
THUMBNAIL_TOKEN = "thumbnail-certifies-source-or-output"
AVAILABILITY_TOKEN = "availability-not-actual"
METADATA_TOKEN = "historical-metadata-dropped"
REPEATS = ("local-file", "document-provider", "recovered-private")
GRANTS = ("valid", "revoked", "removed")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "accessKind",
    "grantState",
    "thumbnailCached",
    "availability",
    "historicalMetadataPreserved",
    "thumbnailCertifiesMedia",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    access = payload["accessKind"]
    grant = payload["grantState"]
    if repeat not in REPEATS or access != repeat:
        raise ValueError("repeat is unsupported")
    if grant not in GRANTS:
        raise ValueError("grantState is unsupported")
    availability = payload["availability"]
    if availability not in ("available", "unavailable"):
        raise ValueError("availability is unsupported")
    cached = _bool(payload["thumbnailCached"], "thumbnailCached")
    metadata = _bool(payload["historicalMetadataPreserved"], "historicalMetadataPreserved")
    certifies = _bool(payload["thumbnailCertifiesMedia"], "thumbnailCertifiesMedia")
    expected = "available" if grant == "valid" else "unavailable"
    rejected: list[str] = []
    if availability != expected:
        rejected.append(AVAILABILITY_TOKEN)
    if certifies:
        rejected.append(THUMBNAIL_TOKEN)
    if not metadata:
        rejected.append(METADATA_TOKEN)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    if THUMBNAIL_TOKEN in rejected:
        reasons.append(NEGATIVE)
    if AVAILABILITY_TOKEN in rejected:
        reasons.append(f"actual availability is {expected}")
    if METADATA_TOKEN in rejected:
        reasons.append("historical metadata remains after the grant changes")
    if not rejected:
        reasons.append(f"availability shown as {expected}")
        reasons.append("thumbnail was not treated as accessible media")
    preserved = [
        evidence,
        {
            "accessKind": access,
            "grantState": grant,
            "thumbnailCached": cached,
            "availability": availability,
            "expectedAvailability": expected,
            "historicalMetadataPreserved": metadata,
            "thumbnailCertifiesMedia": False if not certifies else True,
        },
    ]
    return _result("rejected" if rejected else "recorded", reasons, rejected, preserved)


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 capture was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if not reasons or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    return result
