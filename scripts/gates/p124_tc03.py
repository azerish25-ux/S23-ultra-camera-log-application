"""TC-P124-03 Checkpoint identity mismatch.

Host fixture. A retained chunk cache is not validated by filename and frame
number. A changed source, model, profile, graph, or algorithm rejects the old
resume unless a distinct job is created.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P124-03"
NAME = "Checkpoint identity mismatch"
INTERVENTION = "Replace source, model, profile, or graph while retaining a previously completed chunk cache."
EXPECTED = "Reject incompatible resume data or start a distinct job with new identities."
NEGATIVE = "Filename and frame number alone must not validate a checkpoint."
REPEAT = "Repeat one changed identity field at a time and inspect specific rejection reasons."
FILENAME_ONLY = "filename-and-frame-number-only"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "filename",
    "frameNumber",
    "validationMode",
    "changedField",
    "callsResume",
    "jobId",
    "newJobId",
    "frameIndex",
    "recipeSha256",
    "partialOutputSha256",
    "sourceSha256",
    "observedSourceSha256",
    "modelSha256",
    "observedModelSha256",
    "graphSha256",
    "observedGraphSha256",
    "profileSha256",
    "observedProfileSha256",
    "algorithmSha256",
    "observedAlgorithmSha256",
    "resumeFrame",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
FIELDS = ("none", "source", "model", "profile", "graph", "algorithm")

_SPEC = importlib.util.spec_from_file_location(
    "p124_checkpoint_temporal_rendering_safely",
    Path(__file__).resolve().parent / "p124_checkpoint_temporal_rendering_safely.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _hash(payload, key):
    return _CORE._hash(payload[key], key)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    filename = payload["filename"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("filename must be a non-empty string")
    frame_number = payload["frameNumber"]
    frame_index = payload["frameIndex"]
    if type(frame_number) is not int or frame_number < 0:
        raise ValueError("frameNumber must be an int >= 0")
    if type(frame_index) is not int or frame_index < 0:
        raise ValueError("frameIndex must be an int >= 0")
    mode = payload["validationMode"]
    changed = payload["changedField"]
    if mode not in {"hashes", "filename-and-frame"}:
        raise ValueError("validationMode must be hashes or filename-and-frame")
    if changed not in FIELDS:
        raise ValueError("changedField is invalid")
    calls_resume = payload["callsResume"]
    if type(calls_resume) is not bool:
        raise ValueError("callsResume must be a bool")
    job_id = payload["jobId"]
    new_job = payload["newJobId"]
    if not isinstance(job_id, str) or not job_id.strip():
        raise ValueError("jobId must be a non-empty string")
    if new_job is not None and (not isinstance(new_job, str) or not new_job.strip()):
        raise ValueError("newJobId must be null or a non-empty string")
    resume_frame = payload["resumeFrame"]
    if type(resume_frame) is not int or resume_frame < 0:
        raise ValueError("resumeFrame must be an int >= 0")

    document = {
        "caseId": CASE_ID,
        "evidenceId": evidence,
        "claim": NAME,
        "applyMutant": mode == "filename-and-frame",
        "job_id": job_id,
        "new_job_id": new_job,
        "calls_resume": calls_resume,
        "source_sha256": _hash(payload, "sourceSha256"),
        "observed_source_sha256": _hash(payload, "observedSourceSha256"),
        "recipe_sha256": _hash(payload, "recipeSha256"),
        "model_sha256": _hash(payload, "modelSha256"),
        "observed_model_sha256": _hash(payload, "observedModelSha256"),
        "graph_sha256": _hash(payload, "graphSha256"),
        "observed_graph_sha256": _hash(payload, "observedGraphSha256"),
        "profile_sha256": _hash(payload, "profileSha256"),
        "observed_profile_sha256": _hash(payload, "observedProfileSha256"),
        "algorithm_sha256": _hash(payload, "algorithmSha256"),
        "observed_algorithm_sha256": _hash(payload, "observedAlgorithmSha256"),
        "checkpoints": [
            {
                "frame_index": frame_index,
                "recipe_sha256": _hash(payload, "recipeSha256"),
                "partial_output_sha256": _hash(payload, "partialOutputSha256"),
                "source_sha256": _hash(payload, "sourceSha256"),
                "missing_frames": list(range(frame_index)),
            }
        ],
        "resume_frame": resume_frame,
        "assembled_frames": [],
        "intended_frames": [],
    }
    core = _CORE.evaluate(document)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION, NEGATIVE]
    reasons.extend(core["reasons"])
    rejected = list(core["rejectedClaims"])
    if mode == "filename-and-frame":
        rejected.insert(0, FILENAME_ONLY)
        reasons.append(
            "filename "
            + filename
            + " and frame "
            + str(frame_number)
            + " do not validate the checkpoint"
        )
    if changed != "none":
        reasons.append("inspected identity field " + changed)
    unique: list[str] = []
    for item in rejected:
        if item not in unique:
            unique.append(item)
    decision = "rejected" if unique else "recorded"
    preserved = [evidence, "filename=" + filename, "frameNumber=" + str(frame_number)]
    preserved.extend(item for item in core["preservedResults"] if item != evidence)
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": unique,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    return _CORE.seal(result)
