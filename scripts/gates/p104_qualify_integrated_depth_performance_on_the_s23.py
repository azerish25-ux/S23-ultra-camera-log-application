#!/usr/bin/env python3
"""P104 integrated depth performance on the S23.

Host fixture only. For each sample:

    total_ms = capture_ms + inference_ms + render_ms + encode_ms

The frame interval is 1000/fps. The over-budget fraction is the share of
samples whose total_ms is greater than that interval. Standalone inference_ms
is not a camera frame rate. Dropped frames stay in the result.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P104-01 through TC-P104-08.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any


BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P104"
WORKSTREAM = 13
DEPENDENCIES = ("P103",)
TITLE = "Qualify integrated depth performance on the S23"
SLUG = "qualify_integrated_depth_performance_on_the_s23"
GOAL = "Decide what can run live and what belongs in deferred development."
METHOD = (
    "Measure latency, memory, energy, thermal state, and boundary quality while capture "
    "and preview are active. Test sustained operation, not just a single inference. "
    "Record input resolution and inference cadence separately from output video resolution."
)
FIXTURE = "A model that runs quickly when isolated but reduces recording stability during a sustained take."
ORACLE = (
    "The scheduler chooses a lower-cost preview or deferred-only policy rather than "
    "hiding dropped source frames."
)
MUTANT = "Advertise model inference rate as full-resolution rendered recording rate."
DELIVERABLE = "Physical inference qualification and live-versus-deferred decision"
OPEN_QUESTION = "physical S23 measurement was not run"

COMPONENT_KEYS = ("capture_ms", "inference_ms", "render_ms", "encode_ms")
DEVICES = ("s23", "host")
QUALIFICATIONS = ("unavailable", "claimed", "qualified")
THERMALS = ("nominal", "warm", "severe")
MEMORIES = ("nominal", "pressure", "severe")
LIVE_DEPTHS = ("live", "deferred_only", "lower_cost_preview")
FRAME_RATE_SOURCES = ("integrated", "inference")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "device",
    "measured_on_device",
    "physical_qualification",
    "measurement_id",
    "fps",
    "input_resolution",
    "inference_cadence_hz",
    "output_resolution",
    "thermal",
    "memory",
    "live_depth",
    "dropped_frames",
    "hide_dropped_frames",
    "frame_rate_source",
    "samples",
}
SAMPLE_KEYS = set(COMPONENT_KEYS)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = {"recorded", "rejected"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _as_decimal(value: object, label: str) -> Decimal:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), label + " must be a number")
    if isinstance(value, float):
        require(math.isfinite(value), label + " must be finite")
        return Decimal(str(value))
    return Decimal(value)


def _non_negative(value: object, label: str) -> Decimal:
    number = _as_decimal(value, label)
    require(number >= 0, label + " must be >= 0")
    return number


def _positive(value: object, label: str) -> Decimal:
    number = _as_decimal(value, label)
    require(number > 0, label + " must be > 0")
    return number


def _resolution(value: object, label: str) -> str:
    require(isinstance(value, str) and "x" in value, label + " must look like WxH")
    width, _, height = value.partition("x")
    require(width.isdigit() and height.isdigit() and int(width) > 0 and int(height) > 0, label + " must look like WxH")
    require(str(int(width)) == width and str(int(height)) == height, label + " must look like WxH")
    return value


def _evidence(value: object) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(), "evidenceId must be a non-empty string")
    return value


def _choice(value: object, allowed: tuple[str, ...], label: str) -> str:
    require(isinstance(value, str) and value in allowed, label + " is unsupported")
    return value


def canonical(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def sample_total_ms(sample: dict) -> float:
    """capture_ms + inference_ms + render_ms + encode_ms."""
    require(isinstance(sample, dict), "sample must be an object")
    missing = SAMPLE_KEYS - set(sample)
    extra = set(sample) - SAMPLE_KEYS
    require(not missing, "sample missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "sample has unexpected fields: " + ", ".join(sorted(extra)))
    total = sum((_non_negative(sample[key], key) for key in COMPONENT_KEYS), Decimal("0"))
    return float(total)


def frame_interval_ms(fps: object) -> float:
    """Frame interval in milliseconds: 1000/fps."""
    return float(Decimal(1000) / _positive(fps, "fps"))


def over_budget_fraction(samples: list, fps: object) -> float:
    """Share of samples whose integrated total_ms exceeds 1000/fps."""
    require(isinstance(samples, list) and samples, "samples must be a non-empty list")
    report = budget_report(samples, fps)
    return report["over_count"] / report["count"]


def budget_report(samples: list, fps: object) -> dict[str, Any]:
    """Integrated totals, interval, and the strict greater-than over-budget share."""
    require(isinstance(samples, list) and samples, "samples must be a non-empty list")
    interval = Decimal(1000) / _positive(fps, "fps")
    totals: list[Decimal] = []
    inferences: list[Decimal] = []
    over: list[bool] = []
    for index, sample in enumerate(samples):
        require(isinstance(sample, dict), f"sample {index} must be an object")
        missing = SAMPLE_KEYS - set(sample)
        extra = set(sample) - SAMPLE_KEYS
        require(not missing, f"sample {index} missing fields: " + ", ".join(sorted(missing)))
        require(not extra, f"sample {index} has unexpected fields: " + ", ".join(sorted(extra)))
        parts = [_non_negative(sample[key], f"sample {index} {key}") for key in COMPONENT_KEYS]
        total = sum(parts, Decimal("0"))
        totals.append(total)
        inferences.append(parts[1])
        over.append(total > interval)
    count = len(totals)
    over_count = sum(over)
    return {
        "interval": interval,
        "totals": totals,
        "inferences": inferences,
        "over": over,
        "over_count": over_count,
        "count": count,
        "fraction": Decimal(over_count) / Decimal(count),
    }


def _exact_document(document: dict) -> None:
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P104")
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    _evidence(document["evidenceId"])
    _choice(document["device"], DEVICES, "device")
    require(type(document["measured_on_device"]) is bool, "measured_on_device must be a bool")
    _choice(document["physical_qualification"], QUALIFICATIONS, "physical_qualification")
    measurement = document["measurement_id"]
    require(
        measurement is None or (isinstance(measurement, str) and measurement.strip() and measurement == measurement.strip()),
        "measurement_id must be null or a non-empty string",
    )
    _positive(document["fps"], "fps")
    _resolution(document["input_resolution"], "input_resolution")
    _positive(document["inference_cadence_hz"], "inference_cadence_hz")
    _resolution(document["output_resolution"], "output_resolution")
    _choice(document["thermal"], THERMALS, "thermal")
    _choice(document["memory"], MEMORIES, "memory")
    _choice(document["live_depth"], LIVE_DEPTHS, "live_depth")
    dropped = document["dropped_frames"]
    require(type(dropped) is int and dropped >= 0, "dropped_frames must be a non-negative int")
    require(type(document["hide_dropped_frames"]) is bool, "hide_dropped_frames must be a bool")
    _choice(document["frame_rate_source"], FRAME_RATE_SOURCES, "frame_rate_source")
    require(isinstance(document["samples"], list) and document["samples"], "samples must be a non-empty list")


def _faults(document: dict, report: dict[str, Any]) -> list[str]:
    rejected: list[str] = []
    if document["frame_rate_source"] == "inference":
        rejected.append(MUTANT)
        rejected.append("standalone-inference-as-camera-fps")
    qualification = document["physical_qualification"]
    measured = document["measured_on_device"]
    measurement_id = document["measurement_id"]
    if qualification == "unavailable":
        if measured:
            rejected.append("measured-on-device-contradicts-unavailable")
    else:
        if measurement_id is None:
            rejected.append("unmeasured-physical-qualification")
        if not measured:
            rejected.append("physical-qualification-not-measured-on-device")
        if measured:
            rejected.append("physical-s23-measurement-was-not-run")
    severe = document["thermal"] == "severe" or document["memory"] == "severe"
    live = document["live_depth"]
    if severe and live == "live":
        rejected.append("live-under-severe")
    elif severe and live != "deferred_only":
        rejected.append("severe-requires-deferred-only")
    if live == "live" and report["fraction"] > 0:
        rejected.append("live-despite-integrated-over-budget")
    if live == "live" and document["dropped_frames"] > 0:
        rejected.append("live-while-dropping-source-frames")
    if document["hide_dropped_frames"]:
        rejected.append("hidden-dropped-frames")
    return rejected


def _preserved(document: dict, report: dict[str, Any]) -> list[str]:
    fps = canonical(_positive(document["fps"], "fps"))
    cadence = canonical(_positive(document["inference_cadence_hz"], "inference_cadence_hz"))
    preserved = [
        document["evidenceId"],
        f"device:{document['device']}",
        f"measured-on-device:{str(document['measured_on_device']).lower()}",
        f"physical-qualification:{document['physical_qualification']}",
        "measurement-id:" + (document["measurement_id"] if document["measurement_id"] is not None else "none"),
        f"input-resolution:{document['input_resolution']}",
        f"inference-cadence-hz:{cadence}",
        f"output-resolution:{document['output_resolution']}",
        f"output-fps:{fps}",
        f"frame-interval:1000/{fps}",
        f"over-budget:{report['over_count']}/{report['count']}",
        f"over-budget-fraction:{canonical(report['fraction'])}",
        f"dropped-frames:{document['dropped_frames']}",
        f"hide-dropped-frames:{str(document['hide_dropped_frames']).lower()}",
        f"live-depth:{document['live_depth']}",
        f"thermal:{document['thermal']}",
        f"memory:{document['memory']}",
        f"frame-rate-source:{document['frame_rate_source']}",
    ]
    for index, (total, inference, flag) in enumerate(zip(report["totals"], report["inferences"], report["over"])):
        preserved.append(
            f"sample:{index}:total-ms:{canonical(total)}:inference-ms:{canonical(inference)}:"
            f"over-budget:{str(flag).lower()}"
        )
    return preserved


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    require(decision in DECISIONS, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "P104 must not decide qualified or allowed")
    require(reasons and all(isinstance(item, str) and item for item in reasons), "reasons must be non-empty strings")
    require(all(isinstance(item, str) and item for item in rejected), "rejectedClaims must be strings")
    require(preserved and evidence in preserved, "evidence must be preserved")
    require(questions and questions[0] == OPEN_QUESTION, "openQuestions must say the physical S23 measurement was not run")
    result = {
        "caseId": PHASE,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    return result


def assess(document: dict) -> dict[str, Any]:
    """Record an honest host budget, or reject a false camera-rate or qualification claim.

    Decision is only ``recorded`` or ``rejected``. A physical S23 qualification
    is never ``qualified``. Dropped-frame count is always retained.
    """
    _exact_document(document)
    report = budget_report(document["samples"], document["fps"])
    rejected = _faults(document, report)
    evidence = document["evidenceId"]
    fraction = canonical(report["fraction"])
    reasons = [
        ORACLE,
        "host fixture only; not a physical S23 measurement",
        (
            "integrated frame budget total_ms = capture_ms + inference_ms + render_ms + encode_ms; "
            f"interval = 1000/{canonical(_positive(document['fps'], 'fps'))} ms; "
            f"over-budget fraction = {report['over_count']}/{report['count']} = {fraction}"
        ),
        (
            f"dropped-frames {document['dropped_frames']} retained; "
            "standalone inference_ms is not a camera frame rate"
        ),
        (
            f"input {document['input_resolution']} at inference cadence "
            f"{canonical(_positive(document['inference_cadence_hz'], 'inference_cadence_hz'))} Hz "
            f"is separate from output {document['output_resolution']} at "
            f"{canonical(_positive(document['fps'], 'fps'))} fps"
        ),
    ]
    if document["thermal"] == "severe" or document["memory"] == "severe":
        reasons.append("severe thermal or memory forces live_depth to deferred_only")
    if document["frame_rate_source"] == "inference":
        reasons.append("mutant rejected: " + MUTANT)
    if document["physical_qualification"] == "unavailable" and not document["measured_on_device"]:
        reasons.append("physical qualification is unavailable because the S23 measurement was not run")
    elif document["physical_qualification"] != "unavailable":
        reasons.append("a physical qualification claim is not a measured S23 result")
    if document["hide_dropped_frames"]:
        reasons.append("dropped source frames were claimed hidden and the count was kept anyway")
    questions = [
        OPEN_QUESTION,
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("scheduler policy " + document["live_depth"] + " kept with the integrated budget")
    return _result(decision, reasons, rejected, _preserved(document, report), questions, evidence)


def evaluate(document: dict) -> dict[str, Any]:
    """Same contract as assess."""
    return assess(document)
