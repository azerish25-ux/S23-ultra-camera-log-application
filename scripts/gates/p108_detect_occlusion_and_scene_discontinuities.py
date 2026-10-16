#!/usr/bin/env python3
"""P108 Detect occlusion and scene discontinuities.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P108-01 through TC-P108-08 modules.

Detection rule:
- On an ordered list of depth samples, mark a discontinuity where
  abs(d[i] - d[i-1]) > threshold.
- Mark an occlusion where the forward-backward flow residual satisfies
  abs(dx + rdx) > flow_threshold or abs(dy + rdy) > flow_threshold.
- smoothed=true on a discontinuous sequence is rejected.
- Samples marked unknown must stay unknown. Filling them and labelling
  measured is rejected.
- discontinuity_count, occlusion_count, and unknown_count are retained.
"""

from __future__ import annotations

import math
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P108"
WORKSTREAM = 14
DEPENDENCIES = ("P107",)
TITLE = "Detect occlusion and scene discontinuities"
SLUG = "detect_occlusion_and_scene_discontinuities"
GOAL = "Stop invalid temporal history from leaking across new surfaces or cuts."
METHOD = (
    "Combine flow consistency, depth disagreement, image change, and explicit edit "
    "boundaries with documented thresholds. Reset only the relevant state. Keep gradual "
    "lighting changes distinct from cuts and test partial occlusions separately from full "
    "scene replacement."
)
FIXTURE = "A hand crossing a face, a fast pan revealing a new wall, and a hard edit between unrelated clips."
ORACLE = "History is rejected in disoccluded areas and reset at the cut without smearing the previous scene."
MUTANT = "Carry temporal state across every clip boundary because timestamps are continuous."
DELIVERABLE = "Occlusion mask and scene-reset tests"
DEPTH_DISCONTINUITY_THRESHOLD = 0.5
FLOW_RESIDUAL_THRESHOLD = 0.25
DETECTION_RULE = (
    "Mark a discontinuity where abs(d[i]-d[i-1]) > threshold. "
    "Mark an occlusion where abs(dx+rdx) > flow_threshold or abs(dy+rdy) > flow_threshold. "
    "Reject smoothed=true on a discontinuous sequence. "
    "Samples marked unknown must stay unknown; filling them and labelling measured is rejected. "
    "Retain discontinuity_count, occlusion_count, and unknown_count."
)
LABELS = ("measured", "unknown")
FLOW_KEYS = ("dx", "dy", "rdx", "rdy")
COUNT_KEYS = ("discontinuity_count", "occlusion_count", "unknown_count")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "depthSamples",
    "threshold",
    "flows",
    "flow_threshold",
    "smoothed",
    "sampleLabels",
    "outputLabels",
    "editBoundary",
    "timestampsContinuous",
    "carryHistory",
    "retainOccludedHistory",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
OPEN_QUESTION = "physical S23 measurement was not run"
SMOOTHING_CLAIM = "smoothing-across-discontinuity"
UNKNOWN_FILL_CLAIM = "filled-unknown-labelled-measured"
OCCLUDED_HISTORY_CLAIM = "occluded-history-retained"
CUT_HISTORY_CLAIM = "history-carried-across-edit-boundary"
CASES = (
    {
        "id": "TC-P108-01",
        "phase": "P108",
        "workstream": 14,
        "name": "History without reprojection",
        "intervention": "Move a known object while previous depth remains in its original pixel coordinates.",
        "expected": "Reject unaligned history or warp it correctly before temporal blending.",
        "negative": "A stationary-pixel average that leaves depth trails must fail.",
        "repeat": "Repeat translation, rotation, scale change, and camera motion.",
    },
    {
        "id": "TC-P108-02",
        "phase": "P108",
        "workstream": 14,
        "name": "Disoccluded background",
        "intervention": "Reveal new background behind a moving foreground object where historical depth is invalid.",
        "expected": "Use current evidence and uncertainty rather than smearing previous foreground values into the new region.",
        "negative": "Filling all newly visible pixels with old depth must fail.",
        "repeat": "Repeat thin objects, hands, hair, and large foreground occluders.",
    },
    {
        "id": "TC-P108-03",
        "phase": "P108",
        "workstream": 14,
        "name": "Relative-scale pumping",
        "intervention": "Introduce a near object or scene-content change that alters raw model depth normalization.",
        "expected": "Align valid relative depth consistently or reset honestly without arbitrary global focus shifts.",
        "negative": "Independent min-max normalization per frame must fail.",
        "repeat": "Repeat stationary backgrounds with changing foreground occupancy.",
    },
    {
        "id": "TC-P108-04",
        "phase": "P108",
        "workstream": 14,
        "name": "Scene-cut contamination",
        "intervention": "Join unrelated scenes or switch source clips while temporal state is populated.",
        "expected": "Reset relevant history and prevent previous-image depth or color from leaking into the new shot.",
        "negative": "Continuous timestamps alone must not preserve temporal state across a real cut.",
        "repeat": "Repeat hard cuts, fades, flashes, and rapid camera pans to test discrimination.",
    },
    {
        "id": "TC-P108-05",
        "phase": "P108",
        "workstream": 14,
        "name": "Mixed-pixel boundaries",
        "intervention": "Use moving hair, glasses, smoke, or motion-blurred edges against detailed backgrounds.",
        "expected": "Preserve plausible partial coverage and bound temporal halos under the selected safe settings.",
        "negative": "A dilated binary person mask must not pass demanding boundary quality by itself.",
        "repeat": "Repeat backlighting, crossing subjects, and different foreground-background contrast.",
    },
    {
        "id": "TC-P108-06",
        "phase": "P108",
        "workstream": 14,
        "name": "Subject identity crossing",
        "intervention": "Let two similar subjects cross while one remains the user-selected focus target.",
        "expected": "Follow the documented identity and target-loss policy without unexplained focus jumps.",
        "negative": "Choosing the nearest face independently in every frame must fail.",
        "repeat": "Repeat brief occlusion, leaving frame, re-entry, and low-confidence tracking.",
    },
    {
        "id": "TC-P108-07",
        "phase": "P108",
        "workstream": 14,
        "name": "Bokeh ordering and leakage",
        "intervention": "Render strong foreground defocus with bright lights behind an in-focus opaque subject.",
        "expected": "Respect layering and normalized energy while declaring unavoidable missing-background approximations.",
        "negative": "Uniform background blur with no foreground coverage model must fail.",
        "repeat": "Repeat perfect-depth and estimated-depth inputs to isolate the faulty subsystem.",
    },
    {
        "id": "TC-P108-08",
        "phase": "P108",
        "workstream": 14,
        "name": "Whole-clip acceptance",
        "intervention": "Evaluate complete difficult clips at normal playback rather than selected best frames.",
        "expected": "Record catastrophic artifacts separately and limit release settings where failures remain unacceptable.",
        "negative": "A favorable mean score must not hide a small number of severe boundary failures.",
        "repeat": "Repeat blinded presentation, moderate blur, aggressive blur, and held-out scenes.",
    },
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def finite_number(value: object, label: str) -> float:
    require(type(value) in (int, float), label + " must be a number")
    number = float(value)
    require(math.isfinite(number), label + " must be finite")
    return number


def non_empty_string(value: object, label: str) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(),
            label + " must be a non-empty string")
    return value


def discontinuity_indexes(depth_samples: list[float], threshold: float) -> list[int]:
    """Indexes i where abs(d[i] - d[i-1]) > threshold. Equality is not a mark."""
    require(threshold >= 0.0, "threshold must be >= 0")
    indexes: list[int] = []
    for index in range(1, len(depth_samples)):
        if abs(depth_samples[index] - depth_samples[index - 1]) > threshold:
            indexes.append(index)
    return indexes


def flow_is_occlusion(dx: float, dy: float, rdx: float, rdy: float, flow_threshold: float) -> bool:
    """Forward-backward residual. Consistent flow has rdx ≈ -dx and rdy ≈ -dy."""
    require(flow_threshold >= 0.0, "flow_threshold must be >= 0")
    return abs(dx + rdx) > flow_threshold or abs(dy + rdy) > flow_threshold


def occlusion_indexes(flows: list[dict[str, float]], flow_threshold: float) -> list[int]:
    indexes: list[int] = []
    for index, flow in enumerate(flows):
        if flow_is_occlusion(flow["dx"], flow["dy"], flow["rdx"], flow["rdy"], flow_threshold):
            indexes.append(index)
    return indexes


def unknown_indexes(sample_labels: list[str]) -> list[int]:
    return [index for index, label in enumerate(sample_labels) if label == "unknown"]


def filled_unknown_indexes(sample_labels: list[str], output_labels: list[str]) -> list[int]:
    filled: list[int] = []
    for index, label in enumerate(sample_labels):
        if label == "unknown" and output_labels[index] == "measured":
            filled.append(index)
    return filled


def count_report(
    depth_samples: list[float],
    threshold: float,
    flows: list[dict[str, float]],
    flow_threshold: float,
    sample_labels: list[str],
) -> dict[str, int]:
    report = {
        "discontinuity_count": len(discontinuity_indexes(depth_samples, threshold)),
        "occlusion_count": len(occlusion_indexes(flows, flow_threshold)),
        "unknown_count": len(unknown_indexes(sample_labels)),
    }
    require(tuple(report) == COUNT_KEYS, "count keys drifted")
    return report


def parse_depth_samples(value: object) -> list[float]:
    require(isinstance(value, list) and len(value) >= 1, "depthSamples must contain at least 1 number")
    return [finite_number(item, f"depthSamples[{index}]") for index, item in enumerate(value)]


def parse_labels(value: object, length: int, label: str) -> list[str]:
    require(isinstance(value, list) and len(value) == length, label + " length must match depthSamples")
    parsed: list[str] = []
    for index, item in enumerate(value):
        require(item in LABELS, f"{label}[{index}] must be measured or unknown")
        parsed.append(item)
    return parsed


def parse_flows(value: object) -> list[dict[str, float]]:
    require(isinstance(value, list), "flows must be a list")
    flows: list[dict[str, float]] = []
    for index, item in enumerate(value):
        require(isinstance(item, dict), f"flows[{index}] must be an object")
        require(set(item) == set(FLOW_KEYS), f"flows[{index}] keys must be dx, dy, rdx, rdy")
        flows.append({key: finite_number(item[key], f"flows[{index}].{key}") for key in FLOW_KEYS})
    return flows


def core_rejections(
    *,
    smoothed: bool,
    counts: dict[str, int],
    sample_labels: list[str],
    output_labels: list[str],
) -> list[str]:
    rejected: list[str] = []
    if smoothed and counts["discontinuity_count"] > 0:
        rejected.append(SMOOTHING_CLAIM)
    if filled_unknown_indexes(sample_labels, output_labels):
        rejected.append(UNKNOWN_FILL_CLAIM)
    return rejected


def read_observation(payload: dict) -> dict[str, Any]:
    """Parse shared depth, flow, and label fields. Counts are computed, not copied from the caller."""
    require(isinstance(payload, dict), "payload must be an object")
    evidence = non_empty_string(payload["evidenceId"], "evidenceId")
    repeat = non_empty_string(payload["repeat"], "repeat")
    depth_samples = parse_depth_samples(payload["depthSamples"])
    threshold = finite_number(payload["threshold"], "threshold")
    flows = parse_flows(payload["flows"])
    flow_threshold = finite_number(payload["flow_threshold"], "flow_threshold")
    require(type(payload["smoothed"]) is bool, "smoothed must be a bool")
    sample_labels = parse_labels(payload["sampleLabels"], len(depth_samples), "sampleLabels")
    output_labels = parse_labels(payload["outputLabels"], len(depth_samples), "outputLabels")
    counts = count_report(depth_samples, threshold, flows, flow_threshold, sample_labels)
    rejected = core_rejections(
        smoothed=payload["smoothed"],
        counts=counts,
        sample_labels=sample_labels,
        output_labels=output_labels,
    )
    return {
        "evidence": evidence,
        "repeat": repeat,
        "depth_samples": depth_samples,
        "sample_labels": sample_labels,
        "output_labels": output_labels,
        "counts": counts,
        "rejected": rejected,
    }


def case_reasons(
    case_id: str,
    name: str,
    repeat: str,
    expected: str,
    intervention: str,
    counts: dict[str, int],
    extra: list[str],
) -> list[str]:
    reasons = [
        f"{case_id} {name} repeat {repeat}",
        expected,
        intervention,
        f"discontinuity_count={counts['discontinuity_count']}",
        f"occlusion_count={counts['occlusion_count']}",
        f"unknown_count={counts['unknown_count']}",
    ]
    reasons.extend(extra)
    return reasons


def finish(
    *,
    case_id: str,
    evidence: str,
    claim: str,
    counts: dict[str, int],
    rejected: list[str],
    reasons: list[str],
    open_questions: list[str],
) -> dict[str, Any]:
    require(all(isinstance(item, str) and item for item in rejected), "rejected claims must be non-empty strings")
    require(len(rejected) == len(set(rejected)), "rejected claims must be unique")
    decision = "rejected" if rejected else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(OPEN_QUESTION in open_questions, "physical measurement must stay open")
    for key in COUNT_KEYS:
        require(type(counts[key]) is int and counts[key] >= 0, key + " must be a non-negative int")
        require(f"{key}={counts[key]}" in reasons, key + " must be retained in reasons")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, claim, dict(counts)],
        "openQuestions": open_questions,
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    retained = result["preservedResults"][2]
    require(isinstance(retained, dict) and tuple(retained) == COUNT_KEYS, "counts must be retained")
    require(retained == counts, "retained counts drifted")
    return result


def assess(document: dict) -> dict[str, Any]:
    """Detect discontinuities and occlusions. Reject smearing, filled unknowns, and the cut mutant."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = non_empty_string(document["evidenceId"], "evidenceId")
    claim = non_empty_string(document["claim"], "claim")
    depth_samples = parse_depth_samples(document["depthSamples"])
    threshold = finite_number(document["threshold"], "threshold")
    flows = parse_flows(document["flows"])
    flow_threshold = finite_number(document["flow_threshold"], "flow_threshold")
    require(type(document["smoothed"]) is bool, "smoothed must be a bool")
    sample_labels = parse_labels(document["sampleLabels"], len(depth_samples), "sampleLabels")
    output_labels = parse_labels(document["outputLabels"], len(depth_samples), "outputLabels")
    for flag in ("editBoundary", "timestampsContinuous", "carryHistory", "retainOccludedHistory"):
        require(type(document[flag]) is bool, flag + " must be a bool")
    counts = count_report(depth_samples, threshold, flows, flow_threshold, sample_labels)
    rejected = core_rejections(
        smoothed=document["smoothed"],
        counts=counts,
        sample_labels=sample_labels,
        output_labels=output_labels,
    )
    if counts["occlusion_count"] > 0 and document["retainOccludedHistory"]:
        rejected.append(OCCLUDED_HISTORY_CLAIM)
    if document["editBoundary"] and document["carryHistory"]:
        if document["timestampsContinuous"]:
            rejected.append(MUTANT)
        rejected.append(CUT_HISTORY_CLAIM)
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "detection: " + DETECTION_RULE,
        f"discontinuity_count={counts['discontinuity_count']}",
        f"occlusion_count={counts['occlusion_count']}",
        f"unknown_count={counts['unknown_count']}",
    ]
    if counts["discontinuity_count"] == 0 and not document["editBoundary"]:
        reasons.append("depth steps within threshold are not a scene cut")
    if document["smoothed"] and counts["discontinuity_count"] > 0:
        reasons.append("smoothed=true on a discontinuous sequence")
    if UNKNOWN_FILL_CLAIM in rejected:
        reasons.append("unknown samples were filled and labelled measured")
    if OCCLUDED_HISTORY_CLAIM in rejected:
        reasons.append("history was retained in an occluded region")
    if document["editBoundary"] and document["carryHistory"] and document["timestampsContinuous"]:
        reasons.append("mutant rejected: " + MUTANT)
    elif document["editBoundary"] and not document["carryHistory"]:
        reasons.append("edit boundary reset history despite timestamp continuity")
    if not rejected:
        reasons.append("method: " + METHOD)
        reasons.append("finite host observation retained for " + evidence)
    questions = [
        OPEN_QUESTION,
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]
    return finish(
        case_id=PHASE,
        evidence=evidence,
        claim=claim,
        counts=counts,
        rejected=rejected,
        reasons=reasons,
        open_questions=questions,
    )
