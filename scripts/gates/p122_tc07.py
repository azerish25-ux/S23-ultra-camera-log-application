"""TC-P122-07 Resume boundary duplication.

Host fixture. Assembled frames must equal the intended timeline once.
Duplicated overlap frames fail cadence integrity even when the movie plays.
Omitted boundary frames are rejected. The recipe chain is hashed again.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P122-07"
NAME = "Resume boundary duplication"
INTERVENTION = "Assemble chunks whose temporal overlap contains repeated or omitted output frames."
EXPECTED = "Emit the exact intended timeline once and maintain declared temporal continuity."
NEGATIVE = "A playable movie with duplicated overlap frames must fail cadence integrity."
REPEAT = "Repeat fractional rates, audio-bearing clips, and scene cuts at boundaries."
NEGATIVE_TOKEN = "duplicated-overlap-frames"
OMITTED_TOKEN = "omitted-boundary-frames"
ORDER_TOKEN = "timeline-order-mismatch"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "intendedFrames",
    "assembledFrames",
    "playable",
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


def _frames(value, label: str) -> list[int]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty list")
    frames = []
    for index, item in enumerate(value):
        if type(item) is not int or item < 0:
            raise ValueError(f"{label}[{index}] must be a non-negative integer")
        frames.append(item)
    return frames


def _counts(frames: list[int]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for frame in frames:
        counts[frame] = counts.get(frame, 0) + 1
    return counts


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    intended = _frames(payload["intendedFrames"], "intendedFrames")
    assembled = _frames(payload["assembledFrames"], "assembledFrames")
    if type(payload["playable"]) is not bool:
        raise ValueError("playable must be a bool")
    chain = _CORE.review_versions(payload["versions"], mutated_in_place=payload["mutatedInPlace"])
    rejected = list(chain["rejectedClaims"])
    intended_counts = _counts(intended)
    assembled_counts = _counts(assembled)
    duplicated = any(assembled_counts.get(frame, 0) > count for frame, count in intended_counts.items()) or any(
        frame not in intended_counts for frame in assembled_counts
    )
    # A brand-new frame number is not an overlap duplicate of an intended frame.
    overlap_duplicated = any(assembled_counts.get(frame, 0) > count for frame, count in intended_counts.items())
    omitted = any(assembled_counts.get(frame, 0) < count for frame, count in intended_counts.items())
    reasons = [
        f"{CASE_ID} {NAME}",
        EXPECTED,
        INTERVENTION,
        f"repeat {repeat}",
        f"intendedCount={len(intended)}",
        f"assembledCount={len(assembled)}",
        f"playable={payload['playable']}",
    ]
    reasons.extend(chain["reasons"])
    if overlap_duplicated:
        if NEGATIVE_TOKEN not in rejected:
            rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if omitted and OMITTED_TOKEN not in rejected:
        rejected.append(OMITTED_TOKEN)
        reasons.append("intended frames were omitted at a resume boundary")
    if intended != assembled and not overlap_duplicated and not omitted and ORDER_TOKEN not in rejected:
        rejected.append(ORDER_TOKEN)
        reasons.append("assembled order does not match the intended timeline")
    if intended == assembled:
        reasons.append("timeline emitted once")
    preserved = [
        evidence,
        f"intendedCount={len(intended)}",
        f"assembledCount={len(assembled)}",
        "duplicated=" + str(duplicated),
    ]
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
