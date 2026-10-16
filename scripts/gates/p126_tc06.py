"""TC-P126-06 Missing or revoked media access.

Host fixture. A revoked grant stays unavailable even when a thumbnail is cached.
Historical metadata is preserved. Thumbnail presence does not certify media.
Clip rows still follow the P126 playable rule.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_INDEX = 5
NEGATIVE_TOKEN = "thumbnail-certifies-valid-source"
REVOKED_TOKEN = "revoked-grant-still-available"
ACCESS_TOKEN = "availability-contradicts-access"
CACHE_TOKEN = "thumbnail-cache-not-recorded"
ACCESS_KINDS = ("local", "document-provider", "recovered")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "access",
    "grantRevoked",
    "sourceClipId",
    "thumbnailCached",
    "treatsThumbnailAsMedia",
    "historicalMetadata",
    "clips",
    "omitted_ids",
)

_SPEC = importlib.util.spec_from_file_location(
    "p126_build_a_trustworthy_clip_library",
    Path(__file__).resolve().parent / "p126_build_a_trustworthy_clip_library.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)
CASE = _CORE.CASES[CASE_INDEX]
CASE_ID = CASE["id"]
NAME = CASE["name"]
INTERVENTION = CASE["intervention"]
EXPECTED = CASE["expected"]
NEGATIVE = CASE["negative"]
REPEAT = CASE["repeat"]
RESULT_KEYS = _CORE.RESULT_KEYS


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _flag(value, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    access = _text(payload["access"], "access")
    if access not in ACCESS_KINDS:
        raise ValueError("access is invalid")
    revoked = _flag(payload["grantRevoked"], "grantRevoked")
    source_id = _text(payload["sourceClipId"], "sourceClipId")
    thumbnail_cached = _flag(payload["thumbnailCached"], "thumbnailCached")
    treats = _flag(payload["treatsThumbnailAsMedia"], "treatsThumbnailAsMedia")
    historical = _text(payload["historicalMetadata"], "historicalMetadata")
    library = _CORE.evaluate_library(payload["clips"], payload["omitted_ids"])
    if not isinstance(payload["clips"], list):
        raise ValueError("clips must be a list")
    rows = [clip for clip in payload["clips"] if isinstance(clip, dict) and clip.get("clip_id") == source_id]
    if len(rows) != 1:
        raise ValueError("source clip must appear once")
    source = rows[0]
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(library["reasons"])
    reasons.append("access=" + access)
    rejected = list(library["rejectedClaims"])
    unavailable = (
        source.get("present") is False
        and source.get("playable") is False
        and source.get("verification") == "missing"
    )
    if revoked and not unavailable:
        _add(rejected, REVOKED_TOKEN)
        reasons.append("revoked grant is still marked available")
    if not revoked and source.get("present") is not True:
        _add(rejected, ACCESS_TOKEN)
        reasons.append("accessible media was marked unavailable")
    if revoked and thumbnail_cached and source.get("thumbnail_cached") is not True:
        _add(rejected, CACHE_TOKEN)
        reasons.append("cached thumbnail was not recorded on the missing source")
    if treats:
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    elif revoked and thumbnail_cached:
        reasons.append("thumbnail-cached-not-media:" + source_id)
    preserved = [evidence, historical]
    preserved.extend(library["preservedResults"])
    decision = "rejected" if rejected else "recorded"
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    if historical not in result["preservedResults"]:
        raise ValueError("historical metadata wiped")
    return result
