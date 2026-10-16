"""TC-P128-04 Cancellation at acceptance boundary.

Host fixture. Cancellation is acknowledged only after ownership is controlled.
A cancelled job is not published as accepted, and a late worker callback cannot
reverse the cancellation. The long-form account still has to be exact.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_INDEX = 3
NEGATIVE_TOKEN = "late-callback-reverses-cancellation"
PUBLISH_TOKEN = "cancelled-job-published-as-accepted"
OWNERSHIP_TOKEN = "cancel-acknowledged-before-ownership"
STAGES = {"rendering", "verification", "publication", "cleanup"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "stage",
    "cancelRequested",
    "ownershipControlled",
    "cancelAcknowledged",
    "callbackAccepts",
    "published",
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
    stage = _text(payload["stage"], "stage")
    if stage not in STAGES:
        raise ValueError("stage is not a cancellation boundary")
    flags = ("cancelRequested", "ownershipControlled", "cancelAcknowledged", "callbackAccepts", "published")
    for flag in flags:
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
    cancel = payload["cancelRequested"]
    owned = payload["ownershipControlled"]
    acknowledged = payload["cancelAcknowledged"]
    callback = payload["callbackAccepts"]
    published = payload["published"]
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(account["reasons"])
    reasons.append(f"stage={stage}")
    rejected = list(account["rejectedClaims"])
    if cancel and callback:
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if cancel and published:
        _add(rejected, PUBLISH_TOKEN)
        reasons.append("a cancelled job was published as accepted")
    if cancel and acknowledged and not owned:
        _add(rejected, OWNERSHIP_TOKEN)
        reasons.append("cancellation was acknowledged before ownership was controlled")
    if not rejected:
        if cancel and owned and acknowledged and not callback and not published:
            reasons.append("cancellation acknowledged after ownership was controlled")
        elif not cancel and owned and published and not callback:
            reasons.append("publication kept; no cancellation to reverse")
        elif cancel and not owned and not acknowledged and not published:
            reasons.append("cancellation is not acknowledged until ownership is controlled")
        else:
            reasons.append(f"stage {stage} left cancellation and publication consistent")
    preserved = [evidence, f"stage={stage}"]
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
