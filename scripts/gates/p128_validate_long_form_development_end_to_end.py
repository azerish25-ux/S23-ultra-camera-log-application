#!/usr/bin/env python3
"""P128 Validate long-form development end to end.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P128-01 through TC-P128-08 modules.

Long-form validation takes expected_frames, accounted_frames (indexes),
checkpoint_frames (strictly increasing), audio_duration, and video_duration.

Every index from 0 inclusive to expected_frames exclusive must appear exactly
once in accounted_frames. Missing or duplicate indexes reject. An index outside
that span rejects. The checkpoint chain must be strictly increasing and the
last checkpoint must be <= expected_frames-1. A break rejects.
abs(audio_duration-video_duration) > 0.04 rejects unless audio_absent is true.
spot_check_only true rejects even when the lists look complete. A complete
honest account is recorded. This does not certify physical playback. The
decision is never qualified or allowed.
"""

from __future__ import annotations

import math
from typing import Any


BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P128"
WORKSTREAM = 16
TITLE = "Validate long-form development end to end"
GOAL = "Prove that the deferred workflow survives realistic interruptions and large media."
METHOD = (
    "Run complete import, recipe edit, render, cancel, resume, verify, publish, and re-open workflows. "
    "Use rotated, variable-rate, audio-bearing, high-resolution, and corrupt-edge fixtures. "
    "Record limitations separately for software and physical-device execution."
)
FIXTURE = (
    "A multi-minute clip with audio, orientation metadata, temporal effects, "
    "and one process termination during rendering."
)
ORACLE = (
    "The final accepted result has correct timing, orientation, audio, provenance, "
    "and no duplicated checkpoint boundary frames."
)
MUTANT = "Validate only short silent landscape clips."
DELIVERABLE = "End-to-end deferred-development acceptance report"
DEPENDENCIES = ("P127",)
AUDIO_VIDEO_LIMIT = 0.04
ACCOUNTING_RULE = "exact-once-strict-checkpoint-audio-limit-0.04"
MISSING_FRAME = "missing-frame-index"
DUPLICATE_FRAME = "duplicate-frame-index"
OUT_OF_RANGE_FRAME = "out-of-range-frame-index"
CHECKPOINT_BREAK = "checkpoint-chain-break"
AUDIO_MISMATCH = "audio-video-duration-mismatch"
SPOT_CHECK = "spot-check-only"

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "expected_frames",
    "accounted_frames",
    "checkpoint_frames",
    "audio_duration",
    "video_duration",
    "audio_absent",
    "spot_check_only",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
CASES = (
    {
        "id": "TC-P128-01",
        "name": "Ambiguous imported signal",
        "intervention": "Import media with absent or contradictory color tags, rotation, or timing metadata.",
        "expected": (
            "Separate detected facts from user interpretation and avoid silent normalization "
            "to an assumed source type."
        ),
        "negative": "Filename extension alone must not determine transfer or dynamic range.",
        "repeat": "Repeat HDR-looking untagged clips, variable rates, and portrait rotation.",
    },
    {
        "id": "TC-P128-02",
        "name": "Mutable recipe during export",
        "intervention": "Change UI parameters after a render has begun but before it finishes.",
        "expected": "Keep the running job bound to its frozen recipe and create a new version for subsequent edits.",
        "negative": "Reading live slider values for successive output frames must fail.",
        "repeat": "Repeat stock, focus, grain seed, output range, and source interpretation changes.",
    },
    {
        "id": "TC-P128-03",
        "name": "Checkpoint identity mismatch",
        "intervention": "Replace source, model, profile, or graph while retaining a previously completed chunk cache.",
        "expected": "Reject incompatible resume data or start a distinct job with new identities.",
        "negative": "Filename and frame number alone must not validate a checkpoint.",
        "repeat": "Repeat one changed identity field at a time and inspect specific rejection reasons.",
    },
    {
        "id": "TC-P128-04",
        "name": "Cancellation at acceptance boundary",
        "intervention": "Cancel during rendering, verification, publication, or final cleanup.",
        "expected": (
            "Acknowledge cancellation only after ownership is controlled and never publish a "
            "cancelled job as accepted."
        ),
        "negative": "A late worker callback that reverses cancellation must fail.",
        "repeat": "Repeat with process restart and an already retained partial output.",
    },
    {
        "id": "TC-P128-05",
        "name": "Temporary storage exhaustion",
        "intervention": "Make remaining space insufficient for intermediate work or duplicate publication storage.",
        "expected": (
            "Pause or fail safely before source loss, preserving recoverable artifacts and "
            "clear cleanup choices."
        ),
        "negative": "Budgeting only final output bytes must fail.",
        "repeat": "Repeat before rendering, during chunk assembly, and during gallery publication.",
    },
    {
        "id": "TC-P128-06",
        "name": "Missing or revoked media access",
        "intervention": "Revoke the source grant or remove a file while the library still has a cached thumbnail.",
        "expected": (
            "Show actual availability and preserve historical metadata without treating the "
            "thumbnail as accessible media."
        ),
        "negative": "Thumbnail presence must not certify a valid source or output.",
        "repeat": "Repeat local files, document-provider grants, and recovered private media.",
    },
    {
        "id": "TC-P128-07",
        "name": "Resume boundary duplication",
        "intervention": "Assemble chunks whose temporal overlap contains repeated or omitted output frames.",
        "expected": "Emit the exact intended timeline once and maintain declared temporal continuity.",
        "negative": "A playable movie with duplicated overlap frames must fail cadence integrity.",
        "repeat": "Repeat fractional rates, audio-bearing clips, and scene cuts at boundaries.",
    },
    {
        "id": "TC-P128-08",
        "name": "Shared bundle privacy and interpretation",
        "intervention": "Export a result with private paths or without necessary signal and recipe metadata.",
        "expected": "Redact personal information while retaining the technical interpretation needed for correct use.",
        "negative": (
            "A Log master without its required interpretation record must not be silently "
            "presented as universally self-describing."
        ),
        "repeat": "Repeat clean Log, rendered SDR, HDR-derived looks, and unverified partial exports.",
    },
)
OPEN_QUESTIONS = (
    "physical S23 measurement was not run",
    "a complete frame account does not certify physical playback",
    "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _text(value: Any, label: str) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(), f"{label} must be a non-empty string")
    return value


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def format_number(value: float) -> str:
    return format(value, ".12g")


def _require_int(value: Any, label: str) -> int:
    require(type(value) is int, f"{label} must be an int")
    return value


def _require_index_list(value: Any, label: str) -> list[int]:
    require(isinstance(value, list), f"{label} must be a list")
    return [_require_int(item, f"{label}[{index}]") for index, item in enumerate(value)]


def _require_duration(value: Any, label: str) -> float:
    require(type(value) is not bool and isinstance(value, (int, float)), f"{label} must be a number")
    number = float(value)
    require(math.isfinite(number), f"{label} must be finite")
    require(number >= 0, f"{label} must be >= 0")
    return number


def _require_bool(value: Any, label: str) -> bool:
    require(type(value) is bool, f"{label} must be a bool")
    return value


def validate_long_form(
    expected_frames: Any,
    accounted_frames: Any,
    checkpoint_frames: Any,
    audio_duration: Any,
    video_duration: Any,
    audio_absent: Any,
    spot_check_only: Any,
) -> dict[str, Any]:
    """Account every output index once and keep the checkpoint and duration chain honest.

    A recorded result is a complete honest account. It does not certify physical playback.
    """
    expected = _require_int(expected_frames, "expected_frames")
    require(expected >= 1, "expected_frames must be >= 1")
    accounted = _require_index_list(accounted_frames, "accounted_frames")
    checkpoints = _require_index_list(checkpoint_frames, "checkpoint_frames")
    audio = _require_duration(audio_duration, "audio_duration")
    video = _require_duration(video_duration, "video_duration")
    absent = _require_bool(audio_absent, "audio_absent")
    spot = _require_bool(spot_check_only, "spot_check_only")

    counts: dict[int, int] = {}
    for index in accounted:
        counts[index] = counts.get(index, 0) + 1
    missing = [index for index in range(expected) if counts.get(index, 0) == 0]
    duplicates = sorted(index for index, count in counts.items() if count > 1)
    out_of_range = sorted(index for index in counts if index < 0 or index >= expected)
    exact = sum(1 for index in range(expected) if counts.get(index, 0) == 1)
    delta = abs(audio - video)
    chain = "checkpointChain=" + (
        "<".join(str(item) for item in checkpoints) if checkpoints else "empty"
    )
    account_token = f"frameAccount={exact}/{expected}"
    delta_token = "audioVideoDelta=" + format_number(delta)
    rejected: list[str] = []
    reasons = [
        account_token,
        "accountedIndexes=" + ",".join(str(index) for index in accounted),
        f"requiredSpan=0..{expected - 1}",
        chain,
        delta_token,
        "audioAbsent=" + ("true" if absent else "false"),
        "spotCheckOnly=" + ("true" if spot else "false"),
        "accountingRule=" + ACCOUNTING_RULE,
        "this does not certify physical playback",
    ]
    if missing:
        _add(rejected, MISSING_FRAME)
        reasons.append("missing indexes: " + ",".join(str(index) for index in missing))
    if duplicates:
        _add(rejected, DUPLICATE_FRAME)
        reasons.append("duplicate indexes: " + ",".join(str(index) for index in duplicates))
    if out_of_range:
        _add(rejected, OUT_OF_RANGE_FRAME)
        reasons.append("out-of-range indexes: " + ",".join(str(index) for index in out_of_range))

    break_notes: list[str] = []
    if not checkpoints:
        break_notes.append("checkpoint chain is empty")
    else:
        for index in range(1, len(checkpoints)):
            if checkpoints[index] <= checkpoints[index - 1]:
                break_notes.append("checkpoint chain is not strictly increasing")
                break
        if checkpoints[-1] > expected - 1:
            break_notes.append("last checkpoint is greater than expected_frames-1")
        if any(item < 0 for item in checkpoints):
            break_notes.append("checkpoint index is negative")
    if break_notes:
        _add(rejected, CHECKPOINT_BREAK)
        reasons.extend(break_notes)

    if absent:
        reasons.append("audio duration check skipped because audio_absent is true")
    elif delta > AUDIO_VIDEO_LIMIT:
        _add(rejected, AUDIO_MISMATCH)
        reasons.append(
            "abs(audio_duration-video_duration)=" + format_number(delta) + " > 0.04"
        )
    else:
        reasons.append("audio and video durations agree within 0.04")

    if spot:
        _add(rejected, SPOT_CHECK)
        reasons.append("spot_check_only is rejected even if the accounted lists look complete")
        reasons.append(MUTANT)
    elif not rejected:
        reasons.append("complete honest account recorded")

    preserved = [
        account_token,
        chain,
        delta_token,
        "accountingRule=" + ACCOUNTING_RULE,
        "physical-playback-not-certified",
    ]
    decision = "rejected" if rejected else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    return {
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
    }


def assess(document: dict) -> dict[str, Any]:
    """Record a complete honest long-form account, or reject a broken one.

    The decision is never qualified or allowed. Evidence stays in preservedResults.
    A recorded account does not certify physical playback.
    """
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = _text(document["evidenceId"], "evidenceId")
    claim = _text(document["claim"], "claim")
    require(type(document["applyMutant"]) is bool, "applyMutant must be a bool")
    account = validate_long_form(
        document["expected_frames"],
        document["accounted_frames"],
        document["checkpoint_frames"],
        document["audio_duration"],
        document["video_duration"],
        document["audio_absent"],
        document["spot_check_only"],
    )
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "goal: " + GOAL,
        "fixture: " + FIXTURE,
    ]
    reasons.extend(account["reasons"])
    rejected = list(account["rejectedClaims"])
    if document["applyMutant"]:
        rejected.insert(0, MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("method: " + METHOD)
        reasons.append("deliverable: " + DELIVERABLE)
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    preserved = [evidence, claim]
    preserved.extend(account["preservedResults"])
    result = {
        "caseId": PHASE,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": list(OPEN_QUESTIONS),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(
        "accountingRule=" + ACCOUNTING_RULE in result["reasons"] + result["preservedResults"],
        "accounting rule missing",
    )
    require("physical S23 measurement was not run" in result["openQuestions"], "open question missing")
    return result
