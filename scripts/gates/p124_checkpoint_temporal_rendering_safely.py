#!/usr/bin/env python3
"""P124 Checkpoint temporal rendering safely.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P124-01 through TC-P124-08 modules.

A checkpoint carries frame_index, recipe_sha256, partial_output_sha256, and
source_sha256. Resume starts at frame_index+1. A document that calls resume
with resume_frame 0 while frame_index > 0 is rejected. The next checkpoint
frame_index must be greater than the previous one. A gap is allowed only when
missing_frames lists it. A silent gap is rejected. Recipe hashes stay stable
inside one job; a mid-job recipe change without a new job id is rejected. An
empty partial output hash is rejected. Each checkpoint source hash must match
the job source. Replacing the depth model rejects the old checkpoint unless a
distinct job is created and that resume is not called.
"""

from __future__ import annotations

import re
from typing import Any


BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P124"
TITLE = "Checkpoint temporal rendering safely"
WORKSTREAM = 16
DEPENDENCIES = ("P123",)
GOAL = "Resume expensive work without changing the visual result at the restart boundary."
METHOD = (
    "Checkpoint verified chunks and relevant temporal state with source, graph, model, "
    "profile, and algorithm hashes. Validate complete files before resuming. Recompute "
    "overlap where required and ensure final assembly contains each output frame exactly once."
)
FIXTURE = "A stopped render resumed after the depth model file has been replaced with a different version."
ORACLE = (
    "The old checkpoint is rejected or a new job is created; mixed-model output is never "
    "silently assembled."
)
MUTANT = "Validate a checkpoint only by its output filename and frame number."
DELIVERABLE = "Resume manifest and uninterrupted-equivalence tests"
RESUME_RULE = "resume starts at frame_index+1"

HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
CHECKPOINT_KEYS = {
    "frame_index",
    "recipe_sha256",
    "partial_output_sha256",
    "source_sha256",
    "missing_frames",
}
IDENTITY_FIELDS = (
    ("source", "source_sha256", "observed_source_sha256"),
    ("model", "model_sha256", "observed_model_sha256"),
    ("graph", "graph_sha256", "observed_graph_sha256"),
    ("profile", "profile_sha256", "observed_profile_sha256"),
    ("algorithm", "algorithm_sha256", "observed_algorithm_sha256"),
)
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "job_id",
    "new_job_id",
    "calls_resume",
    "source_sha256",
    "observed_source_sha256",
    "recipe_sha256",
    "model_sha256",
    "observed_model_sha256",
    "graph_sha256",
    "observed_graph_sha256",
    "profile_sha256",
    "observed_profile_sha256",
    "algorithm_sha256",
    "observed_algorithm_sha256",
    "checkpoints",
    "resume_frame",
    "assembled_frames",
    "intended_frames",
}
EVALUATE_KEYS = (DOCUMENT_KEYS - {"schemaVersion", "phase", "implementationBaseRevision"}) | {"caseId"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def resume_index(frame_index: int) -> int:
    """Next output frame after a checkpoint. Never restarts at 0 when frame_index > 0."""
    require(type(frame_index) is int and frame_index >= 0, "frame_index must be an int >= 0")
    return frame_index + 1


def distinct_new_job(job_id: str, new_job_id: str | None) -> bool:
    return isinstance(new_job_id, str) and bool(new_job_id) and new_job_id != job_id


def gap_frames(previous: int | None, frame_index: int) -> list[int]:
    """Frames omitted between checkpoints. The timeline starts at frame 0."""
    start = 0 if previous is None else previous + 1
    if frame_index < start:
        return []
    return list(range(start, frame_index))


def recipe_is_stable(recipe_sha256: str, checkpoint_recipes: list[str]) -> bool:
    return all(item == recipe_sha256 for item in checkpoint_recipes)


def mid_job_recipe_change(
    recipe_sha256: str,
    checkpoint_recipes: list[str],
    job_id: str,
    new_job_id: str | None,
) -> bool:
    """True when recipe hashes differ and no distinct new job id was opened."""
    if recipe_is_stable(recipe_sha256, checkpoint_recipes):
        return False
    return not distinct_new_job(job_id, new_job_id)


def _text(value: Any, label: str) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(), f"{label} must be a non-empty string")
    return value


def _hash(value: Any, label: str, *, allow_empty: bool = False) -> str:
    require(isinstance(value, str), f"{label} must be a string")
    if value == "" and allow_empty:
        return ""
    require(HASH_PATTERN.fullmatch(value) is not None, f"{label} must be a sha256 hex digest")
    return value


def _bool(value: Any, label: str) -> bool:
    require(type(value) is bool, f"{label} must be a bool")
    return value


def _frame_list(value: Any, label: str) -> list[int]:
    require(isinstance(value, list), f"{label} must be a list")
    frames: list[int] = []
    for index, item in enumerate(value):
        require(type(item) is int and item >= 0, f"{label}[{index}] must be an int >= 0")
        frames.append(item)
    return frames


def parse_checkpoint(value: Any, index: int) -> dict[str, Any]:
    require(isinstance(value, dict), f"checkpoints[{index}] must be an object")
    require(set(value) == CHECKPOINT_KEYS, f"checkpoints[{index}] keys are invalid")
    frame_index = value["frame_index"]
    require(type(frame_index) is int and frame_index >= 0, "frame_index must be an int >= 0")
    missing = _frame_list(value["missing_frames"], f"checkpoints[{index}].missing_frames")
    require(len(missing) == len(set(missing)), "missing_frames must not contain duplicates")
    return {
        "frame_index": frame_index,
        "recipe_sha256": _hash(value["recipe_sha256"], f"checkpoints[{index}].recipe_sha256"),
        "partial_output_sha256": _hash(
            value["partial_output_sha256"],
            f"checkpoints[{index}].partial_output_sha256",
            allow_empty=True,
        ),
        "source_sha256": _hash(value["source_sha256"], f"checkpoints[{index}].source_sha256"),
        "missing_frames": missing,
    }


def parse_checkpoints(value: Any) -> list[dict[str, Any]]:
    require(isinstance(value, list) and value, "checkpoints must be a non-empty list")
    return [parse_checkpoint(item, index) for index, item in enumerate(value)]


def _unique(items: list[str]) -> list[str]:
    unique: list[str] = []
    for item in items:
        if item not in unique:
            unique.append(item)
    return unique


def assembly_problems(intended_frames: list[int], assembled_frames: list[int]) -> tuple[list[str], list[str]]:
    """Each intended output frame must appear exactly once, in order."""
    rejected: list[str] = []
    reasons: list[str] = []
    assembled_counts: dict[int, int] = {}
    for frame in assembled_frames:
        assembled_counts[frame] = assembled_counts.get(frame, 0) + 1
    duplicated = [frame for frame, count in assembled_counts.items() if count > 1]
    if duplicated:
        rejected.append("duplicated-overlap-frame")
        rejected.append("cadence-integrity")
        reasons.append(
            "duplicated overlap frames fail cadence integrity at "
            + ",".join(str(frame) for frame in duplicated)
        )
    intended_set = set(intended_frames)
    omitted = [frame for frame in intended_frames if frame not in assembled_counts]
    if omitted:
        rejected.append("omitted-output-frame")
        rejected.append("cadence-integrity")
        reasons.append("omitted output frames " + ",".join(str(frame) for frame in omitted))
    unexpected = [frame for frame in assembled_frames if frame not in intended_set]
    if unexpected and "duplicated-overlap-frame" not in rejected:
        rejected.append("unexpected-assembled-frame")
        reasons.append("assembled frames outside the intended timeline")
    if not rejected and assembled_frames != intended_frames:
        rejected.append("cadence-integrity")
        reasons.append("final assembly is not the intended timeline once")
    if not rejected:
        reasons.append("final assembly contains each output frame exactly once")
    return _unique(rejected), reasons


def chain_problems(
    checkpoints: list[dict[str, Any]],
    *,
    job_source_sha256: str,
    recipe_sha256: str,
    job_id: str,
    new_job_id: str | None,
) -> tuple[list[str], list[str]]:
    """Increasing frame_index, declared gaps, stable recipe, complete partials, source match."""
    rejected: list[str] = []
    reasons: list[str] = []
    previous: int | None = None
    for checkpoint in checkpoints:
        frame_index = checkpoint["frame_index"]
        expected = gap_frames(previous, frame_index)
        if previous is not None and frame_index <= previous:
            rejected.append("checkpoint-frame-not-increasing")
            reasons.append(
                f"checkpoint frame_index {frame_index} is not greater than {previous}"
            )
            expected = []
        listed = checkpoint["missing_frames"]
        silent = [frame for frame in expected if frame not in listed]
        extra = [frame for frame in listed if frame not in expected]
        if silent:
            rejected.append("silent-gap")
            reasons.append("silent gap at frames " + ",".join(str(frame) for frame in silent))
        if extra:
            rejected.append("missing-frames-not-in-gap")
            reasons.append(
                "missing_frames lists frames that are not a gap: "
                + ",".join(str(frame) for frame in extra)
            )
        if checkpoint["partial_output_sha256"] == "":
            rejected.append("empty-partial-output-hash")
            reasons.append(f"partial output hash is empty at frame_index {frame_index}")
        if checkpoint["source_sha256"] != job_source_sha256:
            rejected.append("source-hash-mismatch")
            reasons.append(f"source hash does not match the job source at frame_index {frame_index}")
        if previous is None or frame_index > previous:
            previous = frame_index
    recipes = [checkpoint["recipe_sha256"] for checkpoint in checkpoints]
    if mid_job_recipe_change(recipe_sha256, recipes, job_id, new_job_id):
        rejected.append("mid-job-recipe-change")
        reasons.append("recipe hash changed without a new job id")
    elif not recipe_is_stable(recipe_sha256, recipes):
        reasons.append(f"recipe change created a new job {new_job_id}")
    else:
        reasons.append("recipe hash is stable across checkpoints of this job")
    return _unique(rejected), reasons


def decide_resume(
    *,
    case_id: str,
    evidence_id: str,
    claim: str,
    apply_mutant: bool,
    job_id: str,
    new_job_id: str | None,
    calls_resume: bool,
    source_sha256: str,
    observed_source_sha256: str,
    recipe_sha256: str,
    model_sha256: str,
    observed_model_sha256: str,
    graph_sha256: str,
    observed_graph_sha256: str,
    profile_sha256: str,
    observed_profile_sha256: str,
    algorithm_sha256: str,
    observed_algorithm_sha256: str,
    checkpoints: list[dict[str, Any]],
    resume_frame: int,
    assembled_frames: list[int],
    intended_frames: list[int],
) -> dict[str, Any]:
    boundary = checkpoints[-1]["frame_index"]
    required = resume_index(boundary)
    rejected: list[str] = []
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        RESUME_RULE,
        f"resumeIndex={required}",
        f"boundaryFrame={boundary}",
    ]
    if calls_resume and resume_frame != required:
        rejected.append("resume-not-at-frame-index-plus-one")
        reasons.append(f"resume must start at frame_index+1 ({required}), not {resume_frame}")
    if calls_resume and resume_frame == 0 and boundary > 0:
        rejected.append("resume-restarted-at-zero")
        reasons.append("resume_frame is 0 while frame_index > 0 and the document calls that resume")
    if not calls_resume:
        reasons.append("document does not call resume; resumeIndex was not reused")

    chain_rejected, chain_reasons = chain_problems(
        checkpoints,
        job_source_sha256=source_sha256,
        recipe_sha256=recipe_sha256,
        job_id=job_id,
        new_job_id=new_job_id,
    )
    rejected.extend(chain_rejected)
    reasons.extend(chain_reasons)
    recipes = [checkpoint["recipe_sha256"] for checkpoint in checkpoints]
    if calls_resume and not recipe_is_stable(recipe_sha256, recipes):
        rejected.append("resume-binds-changed-recipe")
        reasons.append("resume would bind a changed recipe to the old checkpoint")

    observed = {
        "source_sha256": source_sha256,
        "observed_source_sha256": observed_source_sha256,
        "model_sha256": model_sha256,
        "observed_model_sha256": observed_model_sha256,
        "graph_sha256": graph_sha256,
        "observed_graph_sha256": observed_graph_sha256,
        "profile_sha256": profile_sha256,
        "observed_profile_sha256": observed_profile_sha256,
        "algorithm_sha256": algorithm_sha256,
        "observed_algorithm_sha256": observed_algorithm_sha256,
    }
    opened_new_job = distinct_new_job(job_id, new_job_id)
    for name, recorded_key, observed_key in IDENTITY_FIELDS:
        if observed[recorded_key] == observed[observed_key]:
            continue
        if opened_new_job and not calls_resume:
            reasons.append(f"{name} replacement created new job {new_job_id}; old checkpoint not assembled")
            continue
        rejected.append(f"identity-mismatch-{name}")
        reasons.append(f"{name} hash changed and the old checkpoint was not left behind")
    if observed_model_sha256 != model_sha256 and opened_new_job and not calls_resume:
        reasons.append("mixed-model output was not silently assembled")

    assembly_rejected, assembly_reasons = assembly_problems(intended_frames, assembled_frames)
    rejected.extend(assembly_rejected)
    reasons.extend(assembly_reasons)

    if apply_mutant:
        rejected.append(MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
        reasons.append("filename and frame number alone do not validate a checkpoint")

    rejected = _unique(rejected)
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("method: " + METHOD)
        reasons.append("deliverable: " + DELIVERABLE)
    preserved = [
        evidence_id,
        claim,
        f"resumeIndex={required}",
        f"boundaryFrame={boundary}",
        f"jobId={job_id}",
        f"recipeSha256={recipe_sha256}",
        f"callsResume={str(calls_resume).lower()}",
    ]
    if opened_new_job:
        preserved.append(f"newJobId={new_job_id}")
    for checkpoint in checkpoints:
        preserved.append(
            "checkpoint frame_index="
            + str(checkpoint["frame_index"])
            + " partial="
            + (checkpoint["partial_output_sha256"] or "empty")
        )
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": [
            "physical S23 measurement was not run",
            "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
        ],
    }
    return seal(result)


def seal(result: dict[str, Any]) -> dict[str, Any]:
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(result["decision"] in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(isinstance(result["reasons"], list) and result["reasons"], "reasons must be non-empty")
    require(all(isinstance(item, str) and item for item in result["reasons"]), "reasons must be non-empty strings")
    require(isinstance(result["rejectedClaims"], list), "rejectedClaims must be a list")
    require(all(isinstance(item, str) for item in result["rejectedClaims"]), "rejectedClaims must be strings")
    if result["decision"] == "recorded":
        require(result["rejectedClaims"] == [], "recorded result cannot reject claims")
    else:
        require(result["rejectedClaims"], "rejected result needs a claim")
    require(isinstance(result["preservedResults"], list) and result["preservedResults"], "evidence wiped")
    require(isinstance(result["openQuestions"], list) and result["openQuestions"], "openQuestions must be non-empty")
    require(
        any("physical S23 measurement was not run" in item for item in result["openQuestions"]),
        "openQuestions must say physical S23 measurement was not run",
    )
    evidence = result["preservedResults"][0]
    require(isinstance(evidence, str) and evidence in result["preservedResults"], "evidence must be preserved")
    return result


def _job_fields(payload: dict[str, Any]) -> dict[str, Any]:
    job_id = _text(payload["job_id"], "job_id")
    new_job_id = payload["new_job_id"]
    require(new_job_id is None or (isinstance(new_job_id, str) and new_job_id.strip() and new_job_id == new_job_id.strip()),
            "new_job_id must be null or a non-empty string")
    resume_frame = payload["resume_frame"]
    require(type(resume_frame) is int and resume_frame >= 0, "resume_frame must be an int >= 0")
    intended = _frame_list(payload["intended_frames"], "intended_frames")
    require(len(intended) == len(set(intended)), "intended_frames must not contain duplicates")
    return {
        "evidence_id": _text(payload["evidenceId"], "evidenceId"),
        "claim": _text(payload["claim"], "claim"),
        "apply_mutant": _bool(payload["applyMutant"], "applyMutant"),
        "job_id": job_id,
        "new_job_id": new_job_id,
        "calls_resume": _bool(payload["calls_resume"], "calls_resume"),
        "source_sha256": _hash(payload["source_sha256"], "source_sha256"),
        "observed_source_sha256": _hash(payload["observed_source_sha256"], "observed_source_sha256"),
        "recipe_sha256": _hash(payload["recipe_sha256"], "recipe_sha256"),
        "model_sha256": _hash(payload["model_sha256"], "model_sha256"),
        "observed_model_sha256": _hash(payload["observed_model_sha256"], "observed_model_sha256"),
        "graph_sha256": _hash(payload["graph_sha256"], "graph_sha256"),
        "observed_graph_sha256": _hash(payload["observed_graph_sha256"], "observed_graph_sha256"),
        "profile_sha256": _hash(payload["profile_sha256"], "profile_sha256"),
        "observed_profile_sha256": _hash(payload["observed_profile_sha256"], "observed_profile_sha256"),
        "algorithm_sha256": _hash(payload["algorithm_sha256"], "algorithm_sha256"),
        "observed_algorithm_sha256": _hash(payload["observed_algorithm_sha256"], "observed_algorithm_sha256"),
        "checkpoints": parse_checkpoints(payload["checkpoints"]),
        "resume_frame": resume_frame,
        "assembled_frames": _frame_list(payload["assembled_frames"], "assembled_frames"),
        "intended_frames": intended,
    }


def _require_keys(payload: dict[str, Any], expected: set[str], label: str) -> None:
    require(isinstance(payload, dict), f"{label} must be an object")
    missing = expected - set(payload)
    extra = set(payload) - expected
    require(not missing, f"{label} missing fields: " + ", ".join(sorted(missing)))
    require(not extra, f"{label} has unexpected fields: " + ", ".join(sorted(extra)))


def assess(document: dict[str, Any]) -> dict[str, Any]:
    """Apply the resume oracle to one checkpoint fixture."""
    _require_keys(document, DOCUMENT_KEYS, "document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    fields = _job_fields(document)
    return decide_resume(case_id=PHASE, **fields)


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate one resume manifest. Invalid shapes raise ValueError."""
    _require_keys(payload, EVALUATE_KEYS, "payload")
    case_id = _text(payload["caseId"], "caseId")
    fields = _job_fields(payload)
    return decide_resume(case_id=case_id, **fields)
