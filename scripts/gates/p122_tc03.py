"""TC-P122-03 Checkpoint identity mismatch.

Host fixture. A chunk cache is valid only when the recomputed identity hash of
source, model, profile, and graph matches. Filename plus frame number is not
that identity. Recipe versions are checked separately and must not change source.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

CASE_ID = "TC-P122-03"
NAME = "Checkpoint identity mismatch"
INTERVENTION = "Replace source, model, profile, or graph while retaining a previously completed chunk cache."
EXPECTED = "Reject incompatible resume data or start a distinct job with new identities."
NEGATIVE = "Filename and frame number alone must not validate a checkpoint."
REPEAT = "Repeat one changed identity field at a time and inspect specific rejection reasons."
NEGATIVE_TOKEN = "filename-and-frame-number-validate-checkpoint"
RESUME_TOKEN = "incompatible-resume-accepted"
UNRESOLVED_TOKEN = "checkpoint-identity-unresolved"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "filename",
    "frameNumber",
    "sourceSha256",
    "modelId",
    "profileId",
    "graphId",
    "cachedFilename",
    "cachedFrameNumber",
    "cachedSourceSha256",
    "cachedModelId",
    "cachedProfileId",
    "cachedGraphId",
    "resumeAccepted",
    "newJobStarted",
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


def _frame(value, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def identity_preimage(source: str, model: str, profile: str, graph: str) -> str:
    return json.dumps(
        {"graph": graph, "model": model, "profile": profile, "source": source},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def identity_sha256(source: str, model: str, profile: str, graph: str) -> str:
    return hashlib.sha256(identity_preimage(source, model, profile, graph).encode("utf-8")).hexdigest()


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    filename = _text(payload["filename"], "filename")
    cached_filename = _text(payload["cachedFilename"], "cachedFilename")
    frame = _frame(payload["frameNumber"], "frameNumber")
    cached_frame = _frame(payload["cachedFrameNumber"], "cachedFrameNumber")
    source = _CORE.require_digest(payload["sourceSha256"], "sourceSha256")
    cached_source = _CORE.require_digest(payload["cachedSourceSha256"], "cachedSourceSha256")
    model = _text(payload["modelId"], "modelId")
    profile = _text(payload["profileId"], "profileId")
    graph = _text(payload["graphId"], "graphId")
    cached_model = _text(payload["cachedModelId"], "cachedModelId")
    cached_profile = _text(payload["cachedProfileId"], "cachedProfileId")
    cached_graph = _text(payload["cachedGraphId"], "cachedGraphId")
    if type(payload["resumeAccepted"]) is not bool or type(payload["newJobStarted"]) is not bool:
        raise ValueError("resume flags must be bools")
    current = identity_sha256(source, model, profile, graph)
    cached = identity_sha256(cached_source, cached_model, cached_profile, cached_graph)
    chain = _CORE.review_versions(payload["versions"], mutated_in_place=payload["mutatedInPlace"])
    rejected = list(chain["rejectedClaims"])
    reasons = [
        f"{CASE_ID} {NAME}",
        EXPECTED,
        INTERVENTION,
        f"repeat {repeat}",
        "checkpointIdentity=" + current,
        "cachedCheckpointIdentity=" + cached,
    ]
    reasons.extend(chain["reasons"])
    changed = current != cached
    filename_frame = filename == cached_filename and frame == cached_frame
    if changed and payload["resumeAccepted"]:
        if RESUME_TOKEN not in rejected:
            rejected.append(RESUME_TOKEN)
        reasons.append("incompatible resume data was accepted")
        if filename_frame and NEGATIVE_TOKEN not in rejected:
            rejected.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
    elif changed and not payload["newJobStarted"]:
        if UNRESOLVED_TOKEN not in rejected:
            rejected.append(UNRESOLVED_TOKEN)
        reasons.append("identity changed but no distinct job was started")
    elif changed:
        reasons.append("distinct job started with a new checkpoint identity")
    else:
        reasons.append("checkpoint identity matches the cached source, model, profile, and graph")
    preserved = [evidence, current, cached, identity_preimage(source, model, profile, graph)]
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
