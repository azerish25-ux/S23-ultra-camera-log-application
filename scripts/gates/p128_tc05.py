"""TC-P128-05 Temporary storage exhaustion.

Host fixture. The budget must cover intermediate bytes and duplicate
publication storage, not only the final output. An insufficient budget pauses
or fails before source loss. The long-form account still has to be exact.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_INDEX = 4
NEGATIVE_TOKEN = "budget-only-final-output-bytes"
PROCEEDED_TOKEN = "proceeded-without-intermediate-budget"
SOURCE_TOKEN = "source-lost"
ARTIFACT_TOKEN = "artifacts-not-recoverable"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "remainingBytes",
    "intermediateBytes",
    "duplicatePublicationBytes",
    "finalOutputBytes",
    "proceeded",
    "sourcePreserved",
    "recoverableArtifacts",
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


def _bytes(value, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be an int >= 0")
    return value


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    remaining = _bytes(payload["remainingBytes"], "remainingBytes")
    intermediate = _bytes(payload["intermediateBytes"], "intermediateBytes")
    duplicate = _bytes(payload["duplicatePublicationBytes"], "duplicatePublicationBytes")
    final_output = _bytes(payload["finalOutputBytes"], "finalOutputBytes")
    for flag in ("proceeded", "sourcePreserved", "recoverableArtifacts"):
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
    required = intermediate + duplicate + final_output
    insufficient = remaining < required
    only_final = remaining >= final_output and insufficient
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(account["reasons"])
    reasons.append(f"requiredBytes={required}")
    reasons.append(f"finalOutputBytes={final_output}")
    reasons.append(f"remainingBytes={remaining}")
    rejected = list(account["rejectedClaims"])
    if only_final and payload["proceeded"]:
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    elif insufficient and payload["proceeded"]:
        _add(rejected, PROCEEDED_TOKEN)
        reasons.append("work proceeded without a budget for intermediate and publication bytes")
    elif insufficient:
        if not payload["sourcePreserved"]:
            _add(rejected, SOURCE_TOKEN)
            reasons.append("source was lost while storage was exhausted")
        elif not payload["recoverableArtifacts"]:
            _add(rejected, ARTIFACT_TOKEN)
            reasons.append("recoverable artifacts were not preserved")
        else:
            reasons.append("paused or failed safely before source loss")
    elif not payload["sourcePreserved"]:
        _add(rejected, SOURCE_TOKEN)
        reasons.append("source was lost")
    else:
        reasons.append("budget covers intermediate, duplicate publication, and final output")
    preserved = [evidence, f"requiredBytes={required}"]
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
