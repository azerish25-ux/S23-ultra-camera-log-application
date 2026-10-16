"""TC-P126-03 Checkpoint identity mismatch.

Host fixture. Resume compares source, model, profile, graph, and content hash.
A matching filename and frame number do not validate a checkpoint. Clip rows
still follow the P126 playable rule.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_INDEX = 2
NEGATIVE_TOKEN = "filename-frame-validate-checkpoint"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "checkpointFilename",
    "checkpointFrame",
    "checkpointSourceId",
    "checkpointModelId",
    "checkpointProfileId",
    "checkpointGraphId",
    "checkpointSha256",
    "currentFilename",
    "currentFrame",
    "currentSourceId",
    "currentModelId",
    "currentProfileId",
    "currentGraphId",
    "currentSha256",
    "resume",
    "clips",
    "omitted_ids",
)
IDENTITY = (
    ("source", "checkpointSourceId", "currentSourceId"),
    ("model", "checkpointModelId", "currentModelId"),
    ("profile", "checkpointProfileId", "currentProfileId"),
    ("graph", "checkpointGraphId", "currentGraphId"),
    ("sha256", "checkpointSha256", "currentSha256"),
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


def _sha(value, label: str) -> str:
    text = _text(value, label)
    if _CORE.SHA256_HEX.fullmatch(text) is None:
        raise ValueError(f"{label} must be 64 lowercase hex chars")
    return text


def _frame(value, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative int")
    return value


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    checkpoint_filename = _text(payload["checkpointFilename"], "checkpointFilename")
    current_filename = _text(payload["currentFilename"], "currentFilename")
    checkpoint_frame = _frame(payload["checkpointFrame"], "checkpointFrame")
    current_frame = _frame(payload["currentFrame"], "currentFrame")
    for name, left, right in IDENTITY:
        if name == "sha256":
            _sha(payload[left], left)
            _sha(payload[right], right)
        else:
            _text(payload[left], left)
            _text(payload[right], right)
    if type(payload["resume"]) is not bool:
        raise ValueError("resume must be a bool")
    library = _CORE.evaluate_library(payload["clips"], payload["omitted_ids"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(library["reasons"])
    rejected = list(library["rejectedClaims"])
    mismatched = [name for name, left, right in IDENTITY if payload[left] != payload[right]]
    filename_match = checkpoint_filename == current_filename and checkpoint_frame == current_frame
    if payload["resume"]:
        for name in mismatched:
            _add(rejected, "checkpoint-identity-mismatch:" + name)
            reasons.append("checkpoint identity mismatch: " + name)
        if mismatched and filename_match:
            _add(rejected, NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
        if not mismatched:
            reasons.append("checkpoint-identities-match")
    elif mismatched:
        reasons.append("distinct-job:" + ",".join(mismatched))
    else:
        reasons.append("resume-not-requested")
    preserved = [evidence]
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
    return result
