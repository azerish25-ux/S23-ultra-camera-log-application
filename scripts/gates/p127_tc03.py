"""TC-P127-03 Checkpoint identity mismatch.

Host fixture. Resume is valid only when source, model, profile, and graph
identities match. Filename and frame number are not an identity. A changed
identity is either rejected or started as a distinct job. Bundle rules apply.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P127-03"
NAME = "Checkpoint identity mismatch"
INTERVENTION = "Replace source, model, profile, or graph while retaining a previously completed chunk cache."
EXPECTED = "Reject incompatible resume data or start a distinct job with new identities."
NEGATIVE = "Filename and frame number alone must not validate a checkpoint."
REPEAT = "Repeat one changed identity field at a time and inspect specific rejection reasons."
NEGATIVE_TOKEN = "filename-and-frame-validated-checkpoint"
MISMATCH_TOKEN = "checkpoint-identity-mismatch"
STUCK_TOKEN = "incompatible-checkpoint-not-split"
FALSE_SPLIT_TOKEN = "distinct-job-without-identity-change"
IDENTITY_FIELDS = ("sourceSha256", "modelId", "profileId", "graphId")
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
    "checkpoint",
    "current",
    "resumeAccepted",
    "distinctJob",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_OBJECT_KEYS = {"sourceSha256", "modelId", "profileId", "graphId", "filename", "frameNumber"}

_SPEC = importlib.util.spec_from_file_location(
    "p127_export_interoperable_result_bundles",
    Path(__file__).resolve().parent / "p127_export_interoperable_result_bundles.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _identity(value, label: str) -> dict:
    if not isinstance(value, dict) or set(value) != _OBJECT_KEYS:
        raise ValueError(f"{label} keys are invalid")
    parsed = {
        "sourceSha256": _CORE.require_hash(value["sourceSha256"], f"{label}.sourceSha256"),
        "modelId": _CORE.require_text(value["modelId"], f"{label}.modelId", stripped=True),
        "profileId": _CORE.require_text(value["profileId"], f"{label}.profileId", stripped=True),
        "graphId": _CORE.require_text(value["graphId"], f"{label}.graphId", stripped=True),
        "filename": _CORE.require_text(value["filename"], f"{label}.filename", stripped=True),
    }
    frame = value["frameNumber"]
    if type(frame) is not int or frame < 0:
        raise ValueError(f"{label}.frameNumber must be a non-negative int")
    parsed["frameNumber"] = frame
    return parsed


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _CORE.require_text(payload["evidenceId"], "evidenceId", stripped=True)
    repeat = _CORE.require_text(payload["repeat"], "repeat", stripped=True)
    if type(payload["resumeAccepted"]) is not bool or type(payload["distinctJob"]) is not bool:
        raise ValueError("resume flags must be bools")
    checkpoint = _identity(payload["checkpoint"], "checkpoint")
    current = _identity(payload["current"], "current")
    bundle = _CORE.judge_bundle(payload)
    changed = [field for field in IDENTITY_FIELDS if checkpoint[field] != current[field]]
    filename_frame = (
        checkpoint["filename"] == current["filename"] and checkpoint["frameNumber"] == current["frameNumber"]
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(bundle["reasons"])
    rejected = list(bundle["rejectedClaims"])
    if changed:
        reasons.append("identity changed: " + ",".join(changed))
        if payload["resumeAccepted"]:
            rejected.append(MISMATCH_TOKEN)
            reasons.append("incompatible resume rejected for " + ",".join(changed))
            if filename_frame:
                rejected.append(NEGATIVE_TOKEN)
                reasons.append(NEGATIVE)
        elif not payload["distinctJob"]:
            rejected.append(STUCK_TOKEN)
            reasons.append("changed identity must start a distinct job when resume is refused")
        else:
            reasons.append("distinct job started with new identities")
    else:
        if payload["distinctJob"]:
            rejected.append(FALSE_SPLIT_TOKEN)
            reasons.append("distinct job requires a changed identity")
        else:
            reasons.append("checkpoint identity matched; filename and frame number were not the identity")
    preserved = [evidence, "checkpointSource=" + checkpoint["sourceSha256"]]
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
