"""TC-P127-06 Missing or revoked media access.

Host fixture. Availability follows the grant and the file, not the thumbnail.
Historical metadata stays even when the media is gone. A cached thumbnail
must not certify accessible media. Bundle manifest rules still apply.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P127-06"
NAME = "Missing or revoked media access"
INTERVENTION = "Revoke the source grant or remove a file while the library still has a cached thumbnail."
EXPECTED = "Show actual availability and preserve historical metadata without treating the thumbnail as accessible media."
NEGATIVE = "Thumbnail presence must not certify a valid source or output."
REPEAT = "Repeat local files, document-provider grants, and recovered private media."
NEGATIVE_TOKEN = "thumbnail-certified-accessible-media"
AVAIL_TOKEN = "availability-misreported"
HISTORY_TOKEN = "historical-metadata-dropped"
GRANTS = frozenset({"valid", "revoked", "missing"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "filename",
    "labels",
    "manifest",
    "export_allowed",
    "grade_applied",
    "metadataTexts",
    "interpretation",
    "selfDescribing",
    "publishPrivatePaths",
    "personalIdentifiers",
    "grant",
    "filePresent",
    "thumbnailCached",
    "reportedAvailability",
    "thumbnailUsedAsAccessProof",
    "historicalMetadataPreserved",
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
    "p127_export_interoperable_result_bundles",
    Path(__file__).resolve().parent / "p127_export_interoperable_result_bundles.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _CORE.require_text(payload["evidenceId"], "evidenceId", stripped=True)
    repeat = _CORE.require_text(payload["repeat"], "repeat", stripped=True)
    grant = payload["grant"]
    if grant not in GRANTS:
        raise ValueError("grant must be valid, revoked, or missing")
    report = payload["reportedAvailability"]
    if report not in {"available", "unavailable"}:
        raise ValueError("reportedAvailability must be available or unavailable")
    flags = ("filePresent", "thumbnailCached", "thumbnailUsedAsAccessProof", "historicalMetadataPreserved")
    if any(type(payload[name]) is not bool for name in flags):
        raise ValueError("media flags must be bools")
    bundle = _CORE.judge_bundle(payload)
    actual = "available" if grant == "valid" and payload["filePresent"] else "unavailable"
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(bundle["reasons"])
    reasons.append("actualAvailability=" + actual)
    reasons.append("thumbnailCached=" + ("true" if payload["thumbnailCached"] else "false"))
    rejected = list(bundle["rejectedClaims"])
    if report != actual:
        rejected.append(AVAIL_TOKEN)
        reasons.append("reported availability does not match the grant and file")
    if payload["thumbnailUsedAsAccessProof"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    elif payload["thumbnailCached"] and actual == "unavailable":
        reasons.append("cached thumbnail kept as a preview, not as accessible media")
    if not payload["historicalMetadataPreserved"]:
        rejected.append(HISTORY_TOKEN)
        reasons.append("historical metadata must be preserved")
    else:
        reasons.append("historical metadata preserved")
    preserved = [evidence, "actualAvailability=" + actual]
    preserved.extend(bundle["preservedResults"])
    result = _CORE.seal(
        CASE_ID,
        evidence,
        reasons,
        rejected,
        preserved,
        ["physical S23 measurement was not run", REPEAT],
    )
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    return result
