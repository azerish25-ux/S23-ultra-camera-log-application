#!/usr/bin/env python3
"""P121 Inspect imported media before rendering.

Host fixture only. Parse import metadata defensively and keep detected facts
apart from user interpretation. This module does not probe a device, does not
qualify a physical S23, does not fetch or invent cloud metadata, and does not
execute the TC-P121-01 through TC-P121-08 modules.

Rendering is blocked when a timestamp or the content hash is missing, and also
when any other required inspection field is missing. The caller must set
render_allowed false and list those fields exactly. A true render flag on
incomplete media is rejected. color_transfer bt709 is never rewritten to
logc3 or arri_log. An audio/video duration delta above 0.04s is a warning
kept in reasons; hide_av_delta rejects that document.
"""

from __future__ import annotations

import math
import re
from typing import Any


BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P121"
TITLE = "Inspect imported media before rendering"
WORKSTREAM = 16
DEPENDENCIES = ("P025", "P032", "P057", "P064")
GOAL = (
    "Determine source timing, geometry, color tags, rotation, and decoder support before assigning a look."
)
METHOD = (
    "Parse metadata defensively, decode representative samples, and preserve the original URI or "
    "imported copy identity. Unknown transfer or range requires an explicit interpretation rather than "
    "silent guessing. Variable-frame-rate and rotated media remain supported only through declared policies."
)
FIXTURE = "An untagged HDR-looking clip, a rotated portrait clip, and a variable-frame-rate recording."
ORACLE = (
    "The importer separates known facts from user interpretation and does not flatten every source "
    "into one assumed SDR path."
)
MUTANT = "Infer source color space solely from the filename extension."
DELIVERABLE = "Media inspection report and import normalization policy"

AV_DELTA_LIMIT_SECONDS = 0.04
AV_DELTA_EPSILON = 1e-9
SOURCE_TRANSFER = "bt709"
FORBIDDEN_RELABELS = ("logc3", "arri_log")
TRANSFERS = (
    "bt709",
    "bt601",
    "bt2020",
    "smpte2084",
    "arib-std-b67",
    "logc3",
    "arri_log",
    "linear",
)
PRIMARIES = ("bt709", "bt601", "bt2020", "p3")
RANGES = ("tv", "full")
ROTATIONS = (0, 90, 180, 270)
URI_SCHEMES = ("file", "content")
TIMEBASE_RE = re.compile(r"^[1-9][0-9]*/[1-9][0-9]*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# Inspection cannot render until every one of these is present.
# audio_timebase is skipped when audio_absent is true.
INSPECTION_FIELDS = (
    "duration_seconds",
    "fps",
    "video_timebase",
    "audio_timebase",
    "color_transfer",
    "color_primaries",
    "range",
    "frame_count",
    "content_sha256",
)
# Timestamps. audio_timebase and audio_duration_seconds apply only when audio is present.
TIMESTAMP_FIELDS = (
    "duration_seconds",
    "video_timebase",
    "audio_timebase",
    "audio_duration_seconds",
)
HASH_FIELDS = ("content_sha256",)
RENDER_BLOCKING_FIELDS = TIMESTAMP_FIELDS + HASH_FIELDS

MEDIA_KEYS = (
    "sourceUri",
    "filename",
    "duration_seconds",
    "fps",
    "video_timebase",
    "audio_timebase",
    "audio_absent",
    "audio_duration_seconds",
    "color_transfer",
    "color_primaries",
    "range",
    "frame_count",
    "content_sha256",
    "rotation_degrees",
    "rotation_policy",
    "variable_frame_rate",
    "vfr_policy",
    "rewritten_transfer",
    "transfer_interpretation",
    "range_interpretation",
    "render_allowed",
    "listed_missing_fields",
    "hide_av_delta",
    "color_from_extension",
    "cloud_metadata",
    "applyMutant",
)
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    *MEDIA_KEYS,
}
EVALUATE_KEYS = {"caseId", "evidenceId", "claim", *MEDIA_KEYS}
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


def _text(value: object, label: str) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(), f"{label} must be a non-empty string")
    return value


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _text(value, label)


def _number(value: object, label: str) -> float:
    require(type(value) is not bool and isinstance(value, (int, float)), f"{label} must be a number")
    number = float(value)
    require(math.isfinite(number), f"{label} must be finite")
    return number


def _optional_number(value: object, label: str) -> float | None:
    if value is None:
        return None
    number = _number(value, label)
    require(number > 0.0, f"{label} must be positive")
    return number


def _token(value: object, label: str, allowed: tuple[str, ...]) -> str | None:
    if value is None:
        return None
    text = _text(value, label)
    require(text in allowed, f"{label} is not a supported token")
    return text


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, f"{label} must be a bool")
    return value


def _timebase(value: object, label: str) -> str | None:
    if value is None:
        return None
    text = _text(value, label)
    require(TIMEBASE_RE.match(text) is not None, f"{label} must be num/den")
    return text


def _sha256(value: object) -> str | None:
    if value is None:
        return None
    text = _text(value, "content_sha256")
    require(SHA256_RE.match(text) is not None, "content_sha256 must be 64 lowercase hex characters")
    return text


def _frame_count(value: object) -> int | None:
    if value is None:
        return None
    require(type(value) is int and value > 0, "frame_count must be a positive integer")
    return value


def _rotation(value: object) -> int | None:
    if value is None:
        return None
    require(type(value) is int and value in ROTATIONS, "rotation_degrees must be 0, 90, 180, or 270")
    return value


def _uri(value: object) -> str:
    text = _text(value, "sourceUri")
    require("://" in text, "sourceUri must include a scheme")
    scheme = text.split("://", 1)[0]
    require(scheme in URI_SCHEMES, "sourceUri scheme must be file or content")
    return text


def _listed(value: object) -> list[str]:
    require(isinstance(value, list), "listed_missing_fields must be a list")
    fields: list[str] = []
    for index, item in enumerate(value):
        require(isinstance(item, str) and item.strip() and item == item.strip(), f"listed field {index} is invalid")
        require(item not in fields, "listed_missing_fields contains a duplicate")
        fields.append(item)
    return fields


def _cloud(value: object) -> dict[str, Any] | None:
    if value is None:
        return None
    require(isinstance(value, dict), "cloud_metadata must be null or an object")
    return value


def blocking_fields(*, audio_absent: bool) -> tuple[str, ...]:
    """Fields whose absence blocks rendering.

    Timestamps are duration_seconds, video_timebase, and, when audio is present,
    audio_timebase plus audio_duration_seconds. The hash is content_sha256.
    fps, color_transfer, color_primaries, range, frame_count, and rotation_degrees
    are required by the inspection and block rendering the same way when missing.
    audio_timebase and audio_duration_seconds are not required when audio_absent
    is true.
    """
    fields = [
        "duration_seconds",
        "fps",
        "video_timebase",
        "color_transfer",
        "color_primaries",
        "range",
        "frame_count",
        "content_sha256",
        "rotation_degrees",
    ]
    if not audio_absent:
        fields[3:3] = ["audio_timebase", "audio_duration_seconds"]
    return tuple(fields)


def _missing(media: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for name in INSPECTION_FIELDS:
        if name == "audio_timebase" and media["audio_absent"]:
            continue
        if media[name] is None:
            missing.append(name)
    if not media["audio_absent"] and media["audio_duration_seconds"] is None:
        missing.append("audio_duration_seconds")
    if media["rotation_degrees"] is None:
        missing.append("rotation_degrees")
    return missing


def _parse_media(payload: dict[str, Any]) -> dict[str, Any]:
    audio_absent = _bool(payload["audio_absent"], "audio_absent")
    audio_timebase = _timebase(payload["audio_timebase"], "audio_timebase")
    audio_duration = _optional_number(payload["audio_duration_seconds"], "audio_duration_seconds")
    if audio_absent:
        require(audio_timebase is None, "audio_timebase must be null when audio_absent")
        require(audio_duration is None, "audio_duration_seconds must be null when audio_absent")
    rotation = _rotation(payload["rotation_degrees"])
    variable = _bool(payload["variable_frame_rate"], "variable_frame_rate")
    return {
        "sourceUri": _uri(payload["sourceUri"]),
        "filename": _text(payload["filename"], "filename"),
        "duration_seconds": _optional_number(payload["duration_seconds"], "duration_seconds"),
        "fps": _optional_number(payload["fps"], "fps"),
        "video_timebase": _timebase(payload["video_timebase"], "video_timebase"),
        "audio_timebase": audio_timebase,
        "audio_absent": audio_absent,
        "audio_duration_seconds": audio_duration,
        "color_transfer": _token(payload["color_transfer"], "color_transfer", TRANSFERS),
        "color_primaries": _token(payload["color_primaries"], "color_primaries", PRIMARIES),
        "range": _token(payload["range"], "range", RANGES),
        "frame_count": _frame_count(payload["frame_count"]),
        "content_sha256": _sha256(payload["content_sha256"]),
        "rotation_degrees": rotation,
        "rotation_policy": _optional_text(payload["rotation_policy"], "rotation_policy"),
        "variable_frame_rate": variable,
        "vfr_policy": _optional_text(payload["vfr_policy"], "vfr_policy"),
        "rewritten_transfer": _token(payload["rewritten_transfer"], "rewritten_transfer", TRANSFERS),
        "transfer_interpretation": _optional_text(payload["transfer_interpretation"], "transfer_interpretation"),
        "range_interpretation": _optional_text(payload["range_interpretation"], "range_interpretation"),
        "render_allowed": _bool(payload["render_allowed"], "render_allowed"),
        "listed_missing_fields": _listed(payload["listed_missing_fields"]),
        "hide_av_delta": _bool(payload["hide_av_delta"], "hide_av_delta"),
        "color_from_extension": _bool(payload["color_from_extension"], "color_from_extension"),
        "cloud_metadata": _cloud(payload["cloud_metadata"]),
        "applyMutant": _bool(payload["applyMutant"], "applyMutant"),
    }


def _delta(media: dict[str, Any]) -> float | None:
    if media["audio_absent"]:
        return None
    video = media["duration_seconds"]
    audio = media["audio_duration_seconds"]
    if video is None or audio is None:
        return None
    return abs(video - audio)


def _exceeds(delta: float) -> bool:
    return delta > AV_DELTA_LIMIT_SECONDS + AV_DELTA_EPSILON


def _relabel_target(media: dict[str, Any]) -> str | None:
    if media["color_transfer"] != SOURCE_TRANSFER:
        return None
    for candidate in (media["rewritten_transfer"], media["transfer_interpretation"]):
        if candidate in FORBIDDEN_RELABELS:
            return candidate
    return None


def _seal(result: dict[str, Any]) -> dict[str, Any]:
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(result["decision"] in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(isinstance(result["reasons"], list) and result["reasons"], "reasons must be non-empty")
    require(all(isinstance(item, str) and item for item in result["reasons"]), "reasons must be strings")
    require(isinstance(result["rejectedClaims"], list), "rejectedClaims must be a list")
    require(isinstance(result["preservedResults"], list) and result["preservedResults"], "evidence wiped")
    require(isinstance(result["openQuestions"], list) and result["openQuestions"], "openQuestions must be non-empty")
    evidence = result["preservedResults"][0]
    require(isinstance(evidence, str) and evidence in result["preservedResults"], "evidence must be preserved")
    require(any("physical S23" in item for item in result["openQuestions"]), "physical S23 note missing")
    return result


def decide_inspection(
    *,
    case_id: str,
    evidence_id: str,
    claim: str,
    media: dict[str, Any],
) -> dict[str, Any]:
    """Inspect one import. Do not guess timestamps, hashes, or cloud tags."""
    missing = _missing(media)
    delta = _delta(media)
    warning = delta is not None and _exceeds(delta)
    relabel = _relabel_target(media)
    timestamp_missing = [name for name in missing if name in TIMESTAMP_FIELDS]
    hash_missing = [name for name in missing if name in HASH_FIELDS]
    other_missing = [name for name in missing if name not in timestamp_missing and name not in hash_missing]
    listed = media["listed_missing_fields"]

    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
    ]
    rejected: list[str] = []

    if media["applyMutant"] or media["color_from_extension"]:
        rejected.append(MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    if relabel is not None:
        rejected.append("bt709-rewritten-to-" + relabel)
        reasons.append("color_transfer bt709 must not be rewritten to " + relabel)
    if timestamp_missing:
        reasons.append("missing timestamps block rendering: " + ", ".join(timestamp_missing))
    if hash_missing:
        reasons.append("missing hash blocks rendering: " + ", ".join(hash_missing))
    if other_missing:
        reasons.append("missing inspection fields block rendering: " + ", ".join(other_missing))
    if sorted(listed) != sorted(missing):
        rejected.append("missing-fields-not-listed")
        reasons.append("missing fields were not listed exactly: " + ", ".join(missing))
    if missing and media["render_allowed"]:
        rejected.append("render-allowed-while-blocked")
        reasons.append("render_allowed true while required inspection fields are missing")
    if warning:
        reasons.append(f"av-duration-delta-above-0.04s: {delta:.6f}")
        if media["hide_av_delta"]:
            rejected.append("hidden-av-duration-delta")
            reasons.append("audio/video duration delta was hidden")
    if media["cloud_metadata"] is not None:
        rejected.append("invented-cloud-metadata")
        reasons.append("cloud metadata was not invented and was not fetched")
    if media["rotation_degrees"] not in (None, 0) and not media["rotation_policy"]:
        rejected.append("undeclared-rotation-policy")
        reasons.append("rotated media requires a declared rotation policy")
    if media["variable_frame_rate"] and not media["vfr_policy"]:
        rejected.append("undeclared-variable-frame-rate-policy")
        reasons.append("variable-frame-rate media requires a declared policy")
    duration = media["duration_seconds"]
    fps = media["fps"]
    frames = media["frame_count"]
    if duration is not None and fps is not None and frames is not None and not media["variable_frame_rate"]:
        if abs(frames - (duration * fps)) > 1.0:
            rejected.append("timing-frame-count-contradiction")
            reasons.append("frame_count disagrees with duration_seconds and fps")
    if media["color_transfer"] is None and media["transfer_interpretation"] is None and "color_transfer" in missing:
        reasons.append("unknown transfer was not guessed")
    if media["range"] is None and media["range_interpretation"] is None and "range" in missing:
        reasons.append("unknown range was not guessed")

    if not rejected and missing and not media["render_allowed"]:
        reasons.append("honest incomplete media recorded")
        reasons.append("missing fields: " + ", ".join(missing))
    if rejected:
        decision = "rejected"
    else:
        decision = "recorded"
        if not missing and media["render_allowed"]:
            reasons.append("inspection complete; render permitted from detected facts")
        elif not missing:
            reasons.append("inspection complete; render not requested")
        reasons.append("method: " + METHOD)

    facts = {
        "sourceUri": media["sourceUri"],
        "filename": media["filename"],
        "duration_seconds": media["duration_seconds"],
        "fps": media["fps"],
        "video_timebase": media["video_timebase"],
        "audio_timebase": media["audio_timebase"],
        "audio_absent": media["audio_absent"],
        "audio_duration_seconds": media["audio_duration_seconds"],
        "color_transfer": media["color_transfer"],
        "color_primaries": media["color_primaries"],
        "range": media["range"],
        "frame_count": media["frame_count"],
        "content_sha256": media["content_sha256"],
        "rotation_degrees": media["rotation_degrees"],
        "rotation_policy": media["rotation_policy"],
        "variable_frame_rate": media["variable_frame_rate"],
        "vfr_policy": media["vfr_policy"],
        "missing_fields": missing,
        "av_delta_seconds": delta,
        "render_allowed": False if missing else media["render_allowed"],
        "transfer_interpretation": media["transfer_interpretation"],
        "range_interpretation": media["range_interpretation"],
        "rewritten_transfer": media["rewritten_transfer"],
    }
    questions = [
        "physical S23 capture was not run",
        "cloud metadata was not invented",
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence_id, claim, facts],
        "openQuestions": questions,
    }
    return _seal(result)


def _identity(payload: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    evidence = _text(payload["evidenceId"], "evidenceId")
    claim = _text(payload["claim"], "claim")
    return evidence, claim, _parse_media(payload)


def _keys(payload: dict[str, Any], expected: set[str], label: str) -> None:
    require(isinstance(payload, dict), f"{label} must be an object")
    missing = expected - set(payload)
    extra = set(payload) - expected
    require(not missing, label + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, label + " has unexpected fields: " + ", ".join(sorted(extra)))


def assess(document: dict) -> dict[str, Any]:
    """Apply the import-inspection oracle to one fixture document."""
    _keys(document, DOCUMENT_KEYS, "document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence, claim, media = _identity(document)
    return decide_inspection(case_id=PHASE, evidence_id=evidence, claim=claim, media=media)


def evaluate(payload: dict) -> dict[str, Any]:
    """Inspect one declared import. Invalid shapes raise ValueError."""
    _keys(payload, EVALUATE_KEYS, "payload")
    case_id = _text(payload["caseId"], "caseId")
    evidence, claim, media = _identity(payload)
    return decide_inspection(case_id=case_id, evidence_id=evidence, claim=claim, media=media)
