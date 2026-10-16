"""TC-P124-06 Missing or revoked media access.

Host fixture. Availability follows the source grant, not a cached thumbnail.
Historical metadata stays even when the media itself is gone.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P124-06"
NAME = "Missing or revoked media access"
INTERVENTION = "Revoke the source grant or remove a file while the library still has a cached thumbnail."
EXPECTED = "Show actual availability and preserve historical metadata without treating the thumbnail as accessible media."
NEGATIVE = "Thumbnail presence must not certify a valid source or output."
REPEAT = "Repeat local files, document-provider grants, and recovered private media."
THUMBNAIL = "thumbnail-certifies-source"
AVAILABILITY = "availability-hides-revocation"
METADATA = "historical-metadata-dropped"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "sourceGrant",
    "filePresent",
    "thumbnailPresent",
    "availability",
    "historicalMetadataPreserved",
    "thumbnailTreatedAsMedia",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_SPEC = importlib.util.spec_from_file_location(
    "p124_checkpoint_temporal_rendering_safely",
    Path(__file__).resolve().parent / "p124_checkpoint_temporal_rendering_safely.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _bool(value, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    grant = payload["sourceGrant"]
    if grant not in {"valid", "revoked", "missing"}:
        raise ValueError("sourceGrant must be valid, revoked, or missing")
    file_present = _bool(payload["filePresent"], "filePresent")
    thumbnail = _bool(payload["thumbnailPresent"], "thumbnailPresent")
    availability = payload["availability"]
    if availability not in {"available", "unavailable"}:
        raise ValueError("availability must be available or unavailable")
    metadata = _bool(payload["historicalMetadataPreserved"], "historicalMetadataPreserved")
    treated = _bool(payload["thumbnailTreatedAsMedia"], "thumbnailTreatedAsMedia")

    accessible = grant == "valid" and file_present
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        INTERVENTION,
        "availability=" + availability,
        "sourceGrant=" + grant,
    ]
    rejected: list[str] = []
    if not accessible and availability != "unavailable":
        rejected.append(AVAILABILITY)
        reasons.append("availability does not match the revoked or missing source")
    if accessible and availability != "available":
        rejected.append(AVAILABILITY)
        reasons.append("a present granted source was reported unavailable")
    if treated:
        rejected.append(THUMBNAIL)
        reasons.append(NEGATIVE)
    if not metadata:
        rejected.append(METADATA)
        reasons.append("historical metadata was dropped with the media")
    if thumbnail and not accessible:
        reasons.append("thumbnail remains cached and is not the source")
    if not rejected:
        reasons.append("actual availability was shown")
    decision = "rejected" if rejected else "recorded"
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [
            evidence,
            "sourceGrant=" + grant,
            "thumbnailPresent=" + str(thumbnail).lower(),
            "availability=" + availability,
        ],
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    return _CORE.seal(result)
