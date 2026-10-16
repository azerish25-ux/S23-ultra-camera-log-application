"""TC-P122-06 Missing or revoked media access.

Host fixture. Availability follows the source grant, not a cached thumbnail.
Historical recipe metadata stays recorded. Thumbnail presence does not certify
a source or an output. Version hashes are recomputed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P122-06"
NAME = "Missing or revoked media access"
INTERVENTION = "Revoke the source grant or remove a file while the library still has a cached thumbnail."
EXPECTED = "Show actual availability and preserve historical metadata without treating the thumbnail as accessible media."
NEGATIVE = "Thumbnail presence must not certify a valid source or output."
REPEAT = "Repeat local files, document-provider grants, and recovered private media."
NEGATIVE_TOKEN = "thumbnail-certifies-source-or-output"
METADATA_TOKEN = "historical-metadata-dropped"
UNAVAILABLE_TOKEN = "unavailable-source-treated-as-media"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "sourceAvailable",
    "thumbnailPresent",
    "historicalMetadataPreserved",
    "treatedAsAccessibleMedia",
    "outputCertified",
    "versions",
    "mutatedInPlace",
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
    "p122_create_non_destructive_recipe_versions",
    Path(__file__).resolve().parent / "p122_create_non_destructive_recipe_versions.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def valid_versions():
    return _CORE.sample_versions()


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _bool(value, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    source_available = _bool(payload["sourceAvailable"], "sourceAvailable")
    thumbnail = _bool(payload["thumbnailPresent"], "thumbnailPresent")
    historical = _bool(payload["historicalMetadataPreserved"], "historicalMetadataPreserved")
    treated = _bool(payload["treatedAsAccessibleMedia"], "treatedAsAccessibleMedia")
    certified = _bool(payload["outputCertified"], "outputCertified")
    chain = _CORE.review_versions(payload["versions"], mutated_in_place=payload["mutatedInPlace"])
    rejected = list(chain["rejectedClaims"])
    reasons = [
        f"{CASE_ID} {NAME}",
        EXPECTED,
        INTERVENTION,
        f"repeat {repeat}",
        f"sourceAvailable={source_available}",
        f"thumbnailPresent={thumbnail}",
    ]
    reasons.extend(chain["reasons"])
    if not historical and METADATA_TOKEN not in rejected:
        rejected.append(METADATA_TOKEN)
        reasons.append("historical metadata was dropped")
    if not source_available and treated and UNAVAILABLE_TOKEN not in rejected:
        rejected.append(UNAVAILABLE_TOKEN)
        reasons.append("revoked source was treated as accessible media")
    if thumbnail and not source_available and (treated or certified):
        if NEGATIVE_TOKEN not in rejected:
            rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    elif not source_available and not treated and not certified and historical:
        reasons.append("availability follows the source grant; the thumbnail is not the media")
    preserved = [
        evidence,
        f"sourceAvailable={source_available}",
        f"thumbnailPresent={thumbnail}",
        f"historicalMetadataPreserved={historical}",
    ]
    preserved.extend(chain["preservedResults"])
    result = _CORE.finish_result(
        CASE_ID,
        reasons,
        rejected,
        preserved,
        ["physical S23 measurement was not run", REPEAT],
    )
    if tuple(result) != RESULT_KEYS or evidence not in result["preservedResults"]:
        raise ValueError("result contract drifted")
    return result
