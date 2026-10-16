"""TC-P128-06 Missing or revoked media access.

Host fixture. Availability follows the source grant and the file, not a cached
thumbnail. Historical metadata stays. The long-form account still has to be exact.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_INDEX = 5
NEGATIVE_TOKEN = "thumbnail-certifies-source-or-output"
METADATA_TOKEN = "historical-metadata-dropped"
AVAILABILITY_TOKEN = "availability-disagrees-with-grant"
GRANTS = {"granted", "revoked", "absent"}
AVAILABILITY = {"available", "unavailable"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "thumbnailPresent",
    "sourceGrant",
    "sourceFilePresent",
    "historicalMetadataPreserved",
    "availability",
    "expected_frames",
    "accounted_frames",
    "checkpoint_frames",
    "audio_duration",
    "video_duration",
    "audio_absent",
    "spot_check_only",
)

_SPEC = importlib.util.spec_from_file_location(
    "p128_validate_long_form_development_end_to_end",
    Path(__file__).resolve().parent / "p128_validate_long_form_development_end_to_end.py",
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


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    grant = _text(payload["sourceGrant"], "sourceGrant")
    availability = _text(payload["availability"], "availability")
    if grant not in GRANTS:
        raise ValueError("sourceGrant is not granted, revoked, or absent")
    if availability not in AVAILABILITY:
        raise ValueError("availability is not available or unavailable")
    for flag in ("thumbnailPresent", "sourceFilePresent", "historicalMetadataPreserved"):
        if type(payload[flag]) is not bool:
            raise ValueError(flag + " must be a bool")
    account = _CORE.validate_long_form(
        payload["expected_frames"],
        payload["accounted_frames"],
        payload["checkpoint_frames"],
        payload["audio_duration"],
        payload["video_duration"],
        payload["audio_absent"],
        payload["spot_check_only"],
    )
    thumbnail = payload["thumbnailPresent"]
    actually = grant == "granted" and payload["sourceFilePresent"]
    shown = availability == "available"
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(account["reasons"])
    reasons.append("actualAvailability=" + ("available" if actually else "unavailable"))
    reasons.append("thumbnailPresent=" + ("true" if thumbnail else "false"))
    rejected = list(account["rejectedClaims"])
    if shown and not actually:
        if thumbnail:
            _add(rejected, NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
        else:
            _add(rejected, AVAILABILITY_TOKEN)
            reasons.append("availability does not follow the source grant and file")
    elif (not shown) and actually:
        _add(rejected, AVAILABILITY_TOKEN)
        reasons.append("available media was hidden")
    elif thumbnail and not actually:
        reasons.append("thumbnail retained; not treated as accessible media")
    if not payload["historicalMetadataPreserved"]:
        _add(rejected, METADATA_TOKEN)
        reasons.append("historical metadata was dropped")
    elif not rejected:
        reasons.append("historical metadata preserved")
    preserved = [evidence, "actualAvailability=" + ("available" if actually else "unavailable")]
    preserved.extend(account["preservedResults"])
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
    return result
