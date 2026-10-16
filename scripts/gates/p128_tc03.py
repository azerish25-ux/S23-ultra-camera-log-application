"""TC-P128-03 Checkpoint identity mismatch.

Host fixture. A checkpoint matches only when source, model, profile, and graph
all match. Filename and frame number do not validate it. The long-form account
still has to be exact.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_INDEX = 2
NEGATIVE_TOKEN = "filename-and-frame-number-alone-validate-checkpoint"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "checkpointFilename",
    "checkpointFrame",
    "cachedSource",
    "cachedModel",
    "cachedProfile",
    "cachedGraph",
    "resumeSource",
    "resumeModel",
    "resumeProfile",
    "resumeGraph",
    "acceptedResume",
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
    filename = _text(payload["checkpointFilename"], "checkpointFilename")
    if type(payload["checkpointFrame"]) is not int:
        raise ValueError("checkpointFrame must be an int")
    if type(payload["acceptedResume"]) is not bool:
        raise ValueError("acceptedResume must be a bool")
    pairs = (
        ("source", _text(payload["cachedSource"], "cachedSource"), _text(payload["resumeSource"], "resumeSource")),
        ("model", _text(payload["cachedModel"], "cachedModel"), _text(payload["resumeModel"], "resumeModel")),
        ("profile", _text(payload["cachedProfile"], "cachedProfile"), _text(payload["resumeProfile"], "resumeProfile")),
        ("graph", _text(payload["cachedGraph"], "cachedGraph"), _text(payload["resumeGraph"], "resumeGraph")),
    )
    account = _CORE.validate_long_form(
        payload["expected_frames"],
        payload["accounted_frames"],
        payload["checkpoint_frames"],
        payload["audio_duration"],
        payload["video_duration"],
        payload["audio_absent"],
        payload["spot_check_only"],
    )
    mismatches = [name for name, cached, resume in pairs if cached != resume]
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(account["reasons"])
    reasons.append(f"checkpointFilename={filename}")
    reasons.append(f"checkpointFrame={payload['checkpointFrame']}")
    reasons.append("filename and frame number are not checkpoint validation")
    rejected = list(account["rejectedClaims"])
    if mismatches and payload["acceptedResume"]:
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("mismatched=" + ",".join(mismatches))
    elif mismatches:
        reasons.append("incompatible resume rejected for " + ",".join(mismatches))
    else:
        reasons.append("checkpoint identity matches source, model, profile, and graph")
    preserved = [evidence, "checkpointFilename=" + filename]
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
