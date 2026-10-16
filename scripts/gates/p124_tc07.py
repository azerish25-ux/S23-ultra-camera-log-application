"""TC-P124-07 Resume boundary duplication.

Host fixture. Overlapping chunks may be recomputed, but the assembled timeline
contains each intended output frame exactly once. Resume starts at frame_index+1.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P124-07"
NAME = "Resume boundary duplication"
INTERVENTION = "Assemble chunks whose temporal overlap contains repeated or omitted output frames."
EXPECTED = "Emit the exact intended timeline once and maintain declared temporal continuity."
NEGATIVE = "A playable movie with duplicated overlap frames must fail cadence integrity."
REPEAT = "Repeat fractional rates, audio-bearing clips, and scene cuts at boundaries."
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "chunks",
    "assembledFrames",
    "intendedFrames",
    "boundaryFrameIndex",
    "resumeFrame",
    "callsResume",
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
    "p124_checkpoint_temporal_rendering_safely",
    Path(__file__).resolve().parent / "p124_checkpoint_temporal_rendering_safely.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _frames(value, label: str) -> list[int]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    frames = []
    for index, item in enumerate(value):
        if type(item) is not int or item < 0:
            raise ValueError(f"{label}[{index}] must be an int >= 0")
        frames.append(item)
    return frames


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    chunks = payload["chunks"]
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("chunks must be a non-empty list")
    parsed_chunks = []
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, dict) or set(chunk) != {"start", "end"}:
            raise ValueError(f"chunks[{index}] must have start and end")
        start = chunk["start"]
        end = chunk["end"]
        if type(start) is not int or type(end) is not int or start < 0 or end < start:
            raise ValueError(f"chunks[{index}] range is invalid")
        parsed_chunks.append((start, end))
    assembled = _frames(payload["assembledFrames"], "assembledFrames")
    intended = _frames(payload["intendedFrames"], "intendedFrames")
    if len(intended) != len(set(intended)):
        raise ValueError("intendedFrames must not contain duplicates")
    boundary = payload["boundaryFrameIndex"]
    resume_frame = payload["resumeFrame"]
    if type(boundary) is not int or boundary < 0:
        raise ValueError("boundaryFrameIndex must be an int >= 0")
    if type(resume_frame) is not int or resume_frame < 0:
        raise ValueError("resumeFrame must be an int >= 0")
    calls_resume = payload["callsResume"]
    if type(calls_resume) is not bool:
        raise ValueError("callsResume must be a bool")

    required = _CORE.resume_index(boundary)
    coverage: dict[int, int] = {}
    for start, end in parsed_chunks:
        for frame in range(start, end + 1):
            coverage[frame] = coverage.get(frame, 0) + 1
    overlap = sorted(frame for frame, count in coverage.items() if count > 1)
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        INTERVENTION,
        _CORE.RESUME_RULE,
        f"resumeIndex={required}",
        "overlapFrames=" + ",".join(str(frame) for frame in overlap),
    ]
    rejected: list[str] = []
    if calls_resume and resume_frame != required:
        rejected.append("resume-not-at-frame-index-plus-one")
        reasons.append(f"resume must start at frame_index+1 ({required}), not {resume_frame}")
    if calls_resume and resume_frame == 0 and boundary > 0:
        rejected.append("resume-restarted-at-zero")
        reasons.append("resume_frame is 0 while frame_index > 0 and the document calls that resume")
    assembly_rejected, assembly_reasons = _CORE.assembly_problems(intended, assembled)
    if overlap:
        assembled_counts: dict[int, int] = {}
        for frame in assembled:
            assembled_counts[frame] = assembled_counts.get(frame, 0) + 1
        repeated = [frame for frame in overlap if assembled_counts.get(frame, 0) != 1]
        if repeated:
            reasons.append(NEGATIVE)
        else:
            reasons.append("overlap was recomputed and each overlap frame was emitted once")
    rejected.extend(assembly_rejected)
    reasons.extend(assembly_reasons)
    unique: list[str] = []
    for item in rejected:
        if item not in unique:
            unique.append(item)
    decision = "rejected" if unique else "recorded"
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": unique,
        "preservedResults": [evidence, f"resumeIndex={required}", "overlapFrames=" + ",".join(str(frame) for frame in overlap)],
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    return _CORE.seal(result)
