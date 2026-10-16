#!/usr/bin/env python3
"""P112 Qualify temporal lens quality at normal playback.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P112-01 through TC-P112-08 modules.

Flicker is the sample standard deviation of frame-to-frame brightness deltas.
Edge crawl is the sample standard deviation of frame-to-frame edge_energy
deltas. Focus breathing is the sample variance of focus_distance and is always
reported. A still sharpness number is never a playback qualification.
"""

from __future__ import annotations

import math
import statistics
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P112"
WORKSTREAM = 14
DEPENDENCIES = ("P111",)
TITLE = "Qualify temporal lens quality at normal playback"
SLUG = "qualify_temporal_lens_quality_at_normal_playback"
GOAL = "Require a whole-clip quality gate before promoting virtual optics from experimental status."
METHOD = (
    "Use blinded playback comparisons, perfect-depth references, artifact annotations, "
    "and per-category severity limits. Evaluate moderate settings first, then more "
    "aggressive apertures. Preserve failure clips and do not average catastrophic "
    "boundary failures into a flattering mean."
)
FIXTURE = (
    "A mixed corpus containing easy portraits and a smaller number of severe hair, "
    "reflection, and foreground-occlusion cases."
)
ORACLE = (
    "The release gate separately reports catastrophic failures and restricts settings "
    "or scenes that remain unreliable."
)
MUTANT = "Approve the renderer using selected still frames from the best clips."
DELIVERABLE = "Temporal optics acceptance report and safe default envelope"

MIN_PLAYBACK_FRAMES = 8
PLAYBACK_FPS = (24, 30)
OPEN_QUESTION = "physical S23 measurement was not run"

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "playback_fps",
    "frames",
    "flicker_limit",
    "edge_crawl_limit",
    "severity_limit",
    "still_as_playback",
    "still_sharpness",
    "measured_on_device",
    "claims_physical_lens_qualification",
    "applyMutant",
}
FRAME_KEYS = {"edge_energy", "brightness", "focus_distance", "boundary_severity"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"recorded", "rejected"}
_FORBIDDEN = {"qualified", "allowed"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def fmt(value: float | None) -> str:
    if value is None:
        return "uncomputed"
    return repr(float(value))


def _number(value: object, label: str, minimum: float | None = None, positive: bool = False) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), label + " must be a number")
    number = float(value)
    require(math.isfinite(number), label + " must be finite")
    if minimum is not None:
        require(number >= minimum, label + " must be >= " + str(minimum))
    if positive:
        require(number > 0.0, label + " must be > 0")
    return number


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def _text(value: object, label: str) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(),
            label + " must be a non-empty string")
    return value


def _delta_stdev(series: list[float]) -> float | None:
    """Sample standard deviation of consecutive deltas. Needs two or more deltas."""
    if len(series) < 3:
        return None
    deltas = [series[index] - series[index - 1] for index in range(1, len(series))]
    return float(statistics.stdev(deltas))


def _variance(series: list[float]) -> float | None:
    """Sample variance. Needs two or more observations."""
    if len(series) < 2:
        return None
    return float(statistics.variance(series))


def temporal_metrics(frames: list[dict[str, Any]]) -> dict[str, Any]:
    """Flicker, edge crawl, and focus-distance variance for one playback sequence."""
    brightness = [float(frame["brightness"]) for frame in frames]
    edge = [float(frame["edge_energy"]) for frame in frames]
    focus = [float(frame["focus_distance"]) for frame in frames]
    return {
        "frame_count": len(frames),
        "flicker": _delta_stdev(brightness),
        "edge_crawl": _delta_stdev(edge),
        "focus_distance_variance": _variance(focus),
    }


def _frames(value: object) -> list[dict[str, float]]:
    require(isinstance(value, list), "frames must be a list")
    parsed: list[dict[str, float]] = []
    for index, frame in enumerate(value):
        require(isinstance(frame, dict), f"frame {index} must be an object")
        missing = FRAME_KEYS - set(frame)
        extra = set(frame) - FRAME_KEYS
        require(not missing, f"frame {index} missing fields: " + ", ".join(sorted(missing)))
        require(not extra, f"frame {index} has unexpected fields: " + ", ".join(sorted(extra)))
        parsed.append({
            "edge_energy": _number(frame["edge_energy"], f"frame {index} edge_energy", minimum=0.0),
            "brightness": _number(frame["brightness"], f"frame {index} brightness"),
            "focus_distance": _number(frame["focus_distance"], f"frame {index} focus_distance", positive=True),
            "boundary_severity": _number(
                frame["boundary_severity"], f"frame {index} boundary_severity", minimum=0.0
            ),
        })
    return parsed


def validate_document(document: dict) -> list[dict[str, float]]:
    """Raise ValueError unless document is a P112 playback fixture."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    _text(document["evidenceId"], "evidenceId")
    _text(document["claim"], "claim")
    fps = document["playback_fps"]
    require(type(fps) is int and fps in PLAYBACK_FPS, "playback_fps must be 24 or 30")
    _number(document["flicker_limit"], "flicker_limit", minimum=0.0)
    _number(document["edge_crawl_limit"], "edge_crawl_limit", minimum=0.0)
    _number(document["severity_limit"], "severity_limit", minimum=0.0)
    _bool(document["still_as_playback"], "still_as_playback")
    _number(document["still_sharpness"], "still_sharpness", minimum=0.0)
    _bool(document["measured_on_device"], "measured_on_device")
    _bool(document["claims_physical_lens_qualification"], "claims_physical_lens_qualification")
    _bool(document["applyMutant"], "applyMutant")
    return _frames(document["frames"])


def _boundary(frames: list[dict[str, float]], limit: float) -> dict[str, Any]:
    if not frames:
        return {
            "mean": None,
            "peak": None,
            "catastrophic": [],
        }
    severities = [frame["boundary_severity"] for frame in frames]
    return {
        "mean": float(math.fsum(severities) / len(severities)),
        "peak": float(max(severities)),
        "catastrophic": [index for index, value in enumerate(severities) if value > limit],
    }


def assess(document: dict) -> dict[str, Any]:
    """Record honest playback metrics or reject the sequence.

    The decision is only ``recorded`` or ``rejected``. It is never ``qualified``
    or ``allowed``. Over-limit flicker, edge crawl, or a severe boundary frame
    rejects the sequence. Those failures are not averaged into a pass.
    """
    frames = validate_document(document)
    metrics = temporal_metrics(frames)
    boundary = _boundary(frames, float(document["severity_limit"]))
    evidence = document["evidenceId"]
    claim = document["claim"]
    flicker = metrics["flicker"]
    edge_crawl = metrics["edge_crawl"]
    breathing = metrics["focus_distance_variance"]
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        f"playback_fps={document['playback_fps']}",
        f"frame_count={metrics['frame_count']}",
        "flicker is the sample standard deviation of brightness deltas",
        f"flicker={fmt(flicker)}",
        "edge_crawl is the sample standard deviation of edge_energy deltas",
        f"edge_crawl={fmt(edge_crawl)}",
        "focus_distance_variance is the sample variance of focus_distance",
        f"focus_distance_variance={fmt(breathing)}",
        "breathing reported; focus_distance variance is not hidden",
        f"mean_boundary_severity={fmt(boundary['mean'])}",
        f"peak_boundary_severity={fmt(boundary['peak'])}",
        f"still_sharpness={fmt(float(document['still_sharpness']))}",
        "still_sharpness is not a playback qualification",
    ]
    rejected: list[str] = []
    if document["applyMutant"]:
        rejected.append(MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    if document["still_as_playback"]:
        rejected.append("still-frame-sharpness-cannot-qualify-playback")
        reasons.append("a single still-frame sharpness number cannot qualify playback")
    if metrics["frame_count"] < MIN_PLAYBACK_FRAMES:
        rejected.append("frame-count-below-playback-minimum")
        reasons.append("frame count below 8 cannot qualify playback")
    if document["claims_physical_lens_qualification"] and not document["measured_on_device"]:
        rejected.append("physical-lens-qualification-without-measured-on-device")
        reasons.append("physical lens qualification claimed without measured_on_device")
    if flicker is not None and flicker > float(document["flicker_limit"]):
        rejected.append("flicker-exceeds-declared-limit")
        reasons.append("flicker exceeds declared limit; sequence rejected rather than averaged into a pass")
    if edge_crawl is not None and edge_crawl > float(document["edge_crawl_limit"]):
        rejected.append("edge-crawl-exceeds-declared-limit")
        reasons.append("edge_crawl exceeds declared limit; sequence rejected rather than averaged into a pass")
    if boundary["catastrophic"]:
        rejected.append("severe-boundary-failure-not-averaged-into-a-pass")
        indexes = ",".join(str(index) for index in boundary["catastrophic"])
        reasons.append(
            "peak boundary severity exceeds the declared limit at frames "
            + indexes
            + "; mean_boundary_severity was not averaged into a pass"
        )
    if rejected:
        decision = "rejected"
    else:
        decision = "recorded"
        reasons.append("honest playback metrics recorded for " + evidence)
        reasons.append("method: " + METHOD)
    require(decision in _DECISIONS and decision not in _FORBIDDEN,
            "this phase must not qualify or allow the fixture")
    catastrophic = "none" if not boundary["catastrophic"] else ",".join(
        str(index) for index in boundary["catastrophic"]
    )
    preserved = [
        evidence,
        claim,
        f"playback_fps={document['playback_fps']}",
        f"frame_count={metrics['frame_count']}",
        f"flicker={fmt(flicker)}",
        f"edge_crawl={fmt(edge_crawl)}",
        f"focus_distance_variance={fmt(breathing)}",
        f"mean_boundary_severity={fmt(boundary['mean'])}",
        f"peak_boundary_severity={fmt(boundary['peak'])}",
        f"catastrophic_frames={catastrophic}",
        f"still_sharpness={fmt(float(document['still_sharpness']))}",
        f"still_as_playback={'true' if document['still_as_playback'] else 'false'}",
        f"measured_on_device={'true' if document['measured_on_device'] else 'false'}",
    ]
    result = {
        "caseId": PHASE,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": [
            OPEN_QUESTION,
            "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
        ],
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(result["decision"] in _DECISIONS, "decision must be recorded or rejected")
    return result
