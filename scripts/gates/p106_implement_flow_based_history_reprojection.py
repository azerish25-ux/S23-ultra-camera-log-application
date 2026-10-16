#!/usr/bin/env python3
"""P106 Implement flow-based history reprojection.

Host fixture only. This module does not probe a device and does not qualify a
physical S23. Previous depth is moved by an explicit backward flow before any
temporal blend. Samples that leave the frame, or that fail the forward-backward
check, stay unknown. Their depth is never invented, extrapolated, or copied
from a neighbour and then called measured.
"""

from __future__ import annotations

import math
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P106"
TITLE = "Implement flow-based history reprojection"
GOAL = "Align previous depth into current image coordinates before blending temporal information."
METHOD = (
    "Use explicit flow direction, coordinate scale, valid regions, and source timestamps. "
    "Test translation and rotation with synthetic known geometry. Reject invalid reprojections "
    "and preserve current-frame evidence where history is unavailable."
)
FIXTURE = "A square translating by a known pixel offset with newly revealed background on one side."
ORACLE = (
    "The warped history aligns the square while leaving disoccluded pixels invalid rather than "
    "filled with stale foreground depth."
)
MUTANT = "Blend previous and current depth at identical pixel indices without warping."
DELIVERABLE = "History reprojection module and synthetic flow tests"

# Flow components are already in the same pixel units as x and y.
COORDINATE_SCALE_PX = 1.0
# |flow + reverse_flow| above this Euclidean threshold is not a stable correspondence.
FORWARD_BACKWARD_INCONSISTENCY_PX = 1.0

OPEN_QUESTION = "physical S23 measurement was not run"

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "frame_width",
    "frame_height",
    "motion_px",
    "prev_timestamp",
    "curr_timestamp",
    "points",
    "fill_unknowns_as_measured",
}
POINT_REQUIRED = {"x", "y", "depth", "dx", "dy"}
POINT_OPTIONAL = {"rdx", "rdy", "coverage"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
REPROJECTION_RULE = (
    "Reproject each previous depth sample by its backward flow: (x, y, depth, dx, dy) "
    "lands at (x + dx * COORDINATE_SCALE_PX, y + dy * COORDINATE_SCALE_PX) with "
    "COORDINATE_SCALE_PX = 1, so the new position is (x + dx, y + dy). "
    "A landing outside the half-open frame [0, frame_width) x [0, frame_height) is unknown; "
    "its depth is not extrapolated. |flow + reverse_flow| = hypot(dx + rdx, dy + rdy) "
    "above FORWARD_BACKWARD_INCONSISTENCY_PX (1 pixel) is unknown. "
    "Unknowns are not filled from neighbouring depth and called measured. "
    "All-zero flow while motion_px > 0 is history pasted without warping and is rejected. "
    "prev_timestamp and curr_timestamp are kept with the result; without both, the result is rejected."
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def parse_number(value: Any, label: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), label + " must be a number")
    number = float(value)
    require(math.isfinite(number), label + " must be finite")
    return number


def parse_evidence(value: Any) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(),
            "evidenceId must be a non-empty string")
    return value


def parse_repeat(value: Any) -> str:
    require(isinstance(value, str) and value.strip(), "repeat must be a non-empty string")
    return value


def parse_frame(width: Any, height: Any) -> tuple[int, int]:
    require(type(width) is int and width > 0, "frame_width must be a positive int")
    require(type(height) is int and height > 0, "frame_height must be a positive int")
    return width, height


def parse_motion(value: Any) -> float:
    motion = parse_number(value, "motion_px")
    require(motion >= 0, "motion_px must be >= 0")
    return motion


def parse_timestamps(prev: Any, curr: Any) -> tuple[str | None, str | None, bool]:
    """Return kept timestamp strings and whether both identities are present.

    None or a blank string is a missing identity (the result is rejected).
    Any other non-string is invalid input.
    """
    kept: list[str | None] = []
    ok = True
    for label, value in (("prev_timestamp", prev), ("curr_timestamp", curr)):
        if value is None or value == "":
            kept.append(None)
            ok = False
            continue
        require(isinstance(value, str) and value == value.strip() and value.strip(),
                label + " must be a timestamp string")
        kept.append(value)
    return kept[0], kept[1], ok


def parse_points(points: Any, *, min_count: int = 1) -> list[dict[str, Any]]:
    require(isinstance(points, list) and len(points) >= min_count, "points must be a non-empty list")
    parsed: list[dict[str, Any]] = []
    for index, point in enumerate(points):
        require(isinstance(point, dict), f"point {index} must be an object")
        missing = POINT_REQUIRED - set(point)
        extra = set(point) - POINT_REQUIRED - POINT_OPTIONAL
        require(not missing, f"point {index} missing fields: " + ", ".join(sorted(missing)))
        require(not extra, f"point {index} has unexpected fields: " + ", ".join(sorted(extra)))
        has_rdx = "rdx" in point
        has_rdy = "rdy" in point
        require(has_rdx == has_rdy, f"point {index} reverse flow must include both rdx and rdy")
        item = {
            "x": parse_number(point["x"], f"point {index} x"),
            "y": parse_number(point["y"], f"point {index} y"),
            "depth": parse_number(point["depth"], f"point {index} depth"),
            "dx": parse_number(point["dx"], f"point {index} dx"),
            "dy": parse_number(point["dy"], f"point {index} dy"),
        }
        if has_rdx:
            item["rdx"] = parse_number(point["rdx"], f"point {index} rdx")
            item["rdy"] = parse_number(point["rdy"], f"point {index} rdy")
        if "coverage" in point:
            coverage = parse_number(point["coverage"], f"point {index} coverage")
            require(0 <= coverage <= 1, f"point {index} coverage must be in [0, 1]")
            item["coverage"] = coverage
        parsed.append(item)
    return parsed


def reproject_grid(points: list[dict[str, Any]], frame_width: int, frame_height: int) -> list[dict[str, Any]]:
    """Warp previous depth samples into the current frame.

    New position is (x + dx, y + dy) at COORDINATE_SCALE_PX = 1. Outside samples
    and forward-backward failures become unknown with depth None. Neighbour
    depth is never copied into those holes.
    """
    require(type(frame_width) is int and frame_width > 0, "frame_width must be a positive int")
    require(type(frame_height) is int and frame_height > 0, "frame_height must be a positive int")
    warped: list[dict[str, Any]] = []
    for point in points:
        dx = point["dx"]
        dy = point["dy"]
        nx = point["x"] + dx * COORDINATE_SCALE_PX
        ny = point["y"] + dy * COORDINATE_SCALE_PX
        rdx = point["rdx"] if "rdx" in point else -dx
        rdy = point["rdy"] if "rdy" in point else -dy
        inconsistency = math.hypot(dx + rdx, dy + rdy)
        coverage = point["coverage"] if "coverage" in point else 1.0
        status = "measured"
        cause = "aligned"
        depth: float | None = point["depth"]
        if nx < 0 or ny < 0 or nx >= frame_width or ny >= frame_height:
            status = "unknown"
            cause = "outside-frame"
            depth = None
        elif inconsistency > FORWARD_BACKWARD_INCONSISTENCY_PX:
            status = "unknown"
            cause = "forward-backward-inconsistent"
            depth = None
        elif coverage == 0:
            status = "unknown"
            cause = "no-coverage"
            depth = None
        elif coverage < 1:
            status = "partial"
            cause = "partial-coverage"
        warped.append({
            "x": nx,
            "y": ny,
            "depth": depth,
            "status": status,
            "cause": cause,
            "source_x": point["x"],
            "source_y": point["y"],
        })
    return warped


def finish(
    case_id: str,
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[Any],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(bool(reasons), "reasons must be non-empty")
    require(bool(preserved) and isinstance(preserved[0], str) and preserved[0].strip(),
            "evidence must be preserved")
    require(any(OPEN_QUESTION in item for item in questions), "open question missing")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    return result


def _timestamp_record(prev: str | None, curr: str | None, samples: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "prev_timestamp": prev,
        "curr_timestamp": curr,
        "samples": samples,
    }


def assess(document: dict) -> dict[str, Any]:
    """Reproject history and reject pasted, filled, or untimestamped results."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = parse_evidence(document["evidenceId"])
    claim = document["claim"]
    require(isinstance(claim, str) and claim.strip(), "claim must be a non-empty string")
    require(type(document["fill_unknowns_as_measured"]) is bool, "fill_unknowns_as_measured must be a bool")
    width, height = parse_frame(document["frame_width"], document["frame_height"])
    motion = parse_motion(document["motion_px"])
    prev, curr, timestamps_ok = parse_timestamps(document["prev_timestamp"], document["curr_timestamp"])
    points = parse_points(document["points"])
    samples = reproject_grid(points, width, height)
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        REPROJECTION_RULE,
    ]
    rejected: list[str] = []
    flows_all_zero = all(point["dx"] == 0 and point["dy"] == 0 for point in points)
    if motion > 0 and flows_all_zero:
        rejected.append(MUTANT)
        rejected.append("history-pasted-without-flow")
        reasons.append("mutant rejected: " + MUTANT)
        reasons.append("motion_px > 0 but every backward flow is zero; history was pasted at the same pixels")
    inconsistent = [sample for sample in samples if sample["cause"] == "forward-backward-inconsistent"]
    outside = [sample for sample in samples if sample["cause"] == "outside-frame"]
    if document["fill_unknowns_as_measured"] and inconsistent:
        rejected.append("unknowns-filled-from-neighbours-called-measured")
        reasons.append(
            "forward-backward failures stay unknown; neighbouring depth was not written back as measured"
        )
    if document["fill_unknowns_as_measured"] and outside:
        rejected.append("outside-frame-extrapolated-with-invented-depth")
        reasons.append("samples outside the frame stay unknown; depth was not extrapolated")
    if not timestamps_ok:
        rejected.append("missing-source-timestamps")
        reasons.append("a result without prev_timestamp and curr_timestamp is rejected")
    if not rejected:
        reasons.append("warped history retained for " + evidence)
        reasons.append("method: " + METHOD)
        reasons.append("pixels with no landed history sample stay invalid")
    questions = [
        OPEN_QUESTION,
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]
    preserved = [evidence, claim, _timestamp_record(prev, curr, samples)]
    return finish(PHASE, "rejected" if rejected else "recorded", reasons, rejected, preserved, questions)


def evaluate(document: dict) -> dict[str, Any]:
    """Same contract as assess."""
    return assess(document)
