"""TC-P127-07 Resume boundary duplication.

Host fixture. The emitted frame list must be the intended timeline once.
Duplicated overlap frames fail cadence integrity even when the movie plays.
Omitted boundary frames fail continuity. Bundle manifest rules still apply.
"""

from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

CASE_ID = "TC-P127-07"
NAME = "Resume boundary duplication"
INTERVENTION = "Assemble chunks whose temporal overlap contains repeated or omitted output frames."
EXPECTED = "Emit the exact intended timeline once and maintain declared temporal continuity."
NEGATIVE = "A playable movie with duplicated overlap frames must fail cadence integrity."
REPEAT = "Repeat fractional rates, audio-bearing clips, and scene cuts at boundaries."
NEGATIVE_TOKEN = "duplicated-overlap-frames"
OMIT_TOKEN = "omitted-boundary-frames"
CONTINUITY_TOKEN = "declared-continuity-broken"
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
    "intendedFrames",
    "emittedFrames",
    "playable",
    "declaredContinuity",
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
    "p127_export_interoperable_result_bundles",
    Path(__file__).resolve().parent / "p127_export_interoperable_result_bundles.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _frames(value, label: str) -> list[int]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty list of ints")
    parsed: list[int] = []
    for index, item in enumerate(value):
        if type(item) is not int or item < 0:
            raise ValueError(f"{label}[{index}] must be a non-negative int")
        parsed.append(item)
    return parsed


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _CORE.require_text(payload["evidenceId"], "evidenceId", stripped=True)
    repeat = _CORE.require_text(payload["repeat"], "repeat", stripped=True)
    if type(payload["playable"]) is not bool or type(payload["declaredContinuity"]) is not bool:
        raise ValueError("timeline flags must be bools")
    intended = _frames(payload["intendedFrames"], "intendedFrames")
    emitted = _frames(payload["emittedFrames"], "emittedFrames")
    bundle = _CORE.judge_bundle(payload)
    intended_counts = Counter(intended)
    emitted_counts = Counter(emitted)
    duplicated = sorted(frame for frame, count in emitted_counts.items() if count > intended_counts.get(frame, 0))
    omitted = sorted(frame for frame, count in intended_counts.items() if emitted_counts.get(frame, 0) < count)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(bundle["reasons"])
    reasons.append(f"intendedCount={len(intended)} emittedCount={len(emitted)}")
    rejected = list(bundle["rejectedClaims"])
    if duplicated:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("duplicatedFrames=" + ",".join(str(frame) for frame in duplicated))
        if payload["playable"]:
            reasons.append("playable movie does not excuse duplicated overlap frames")
    if omitted:
        rejected.append(OMIT_TOKEN)
        reasons.append("omittedFrames=" + ",".join(str(frame) for frame in omitted))
    if emitted != intended or not payload["declaredContinuity"]:
        rejected.append(CONTINUITY_TOKEN)
        reasons.append("declared temporal continuity was not maintained")
    else:
        reasons.append("intended timeline emitted once")
    preserved = [evidence, "intendedCount=" + str(len(intended))]
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
