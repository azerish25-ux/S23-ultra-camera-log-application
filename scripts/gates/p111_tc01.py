"""TC-P111-01 History without reprojection.

Host fixture. Unaligned history is rejected by computing the warp, not by a flag.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P111-01"
NAME = "History without reprojection"
INTERVENTION = "Move a known object while previous depth remains in its original pixel coordinates."
EXPECTED = "Reject unaligned history or warp it correctly before temporal blending."
NEGATIVE = "A stationary-pixel average that leaves depth trails must fail."
REPEAT = "Repeat translation, rotation, scale change, and camera motion."
NEGATIVE_TOKEN = "stationary-pixel-average-depth-trails"
PAYLOAD_KEYS = ("evidenceId", "repeat", "history", "motion", "blend")
MOTION_KEYS = {"dx", "dy", "scale", "rotation_deg"}
POINT_KEYS = {"x", "y", "depth"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _number(value, label: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label} must be a number")
    number = float(value)
    _require(math.isfinite(number), f"{label} must be finite")
    return number


def _text(value, label: str) -> str:
    _require(isinstance(value, str) and value.strip() and value == value.strip(), f"{label} must be a non-empty string")
    return value


def reproject(point: dict, motion: dict) -> dict:
    """Warp a history sample by the known object motion before blending."""
    rotation = math.radians(motion["rotation_deg"])
    cosine = math.cos(rotation)
    sine = math.sin(rotation)
    scale = motion["scale"]
    x = point["x"]
    y = point["y"]
    return {
        "x": scale * (cosine * x - sine * y) + motion["dx"],
        "y": scale * (sine * x + cosine * y) + motion["dy"],
        "depth": point["depth"],
    }


def _identity(motion: dict) -> bool:
    return (
        motion["dx"] == 0.0
        and motion["dy"] == 0.0
        and motion["scale"] == 1.0
        and motion["rotation_deg"] == 0.0
    )


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    _require(payload["blend"] in {"stationary-pixel", "reprojected"}, "blend is invalid")
    motion_in = payload["motion"]
    _require(isinstance(motion_in, dict) and set(motion_in) == MOTION_KEYS, "motion keys are invalid")
    motion = {
        "dx": _number(motion_in["dx"], "dx"),
        "dy": _number(motion_in["dy"], "dy"),
        "scale": _number(motion_in["scale"], "scale"),
        "rotation_deg": _number(motion_in["rotation_deg"], "rotation_deg"),
    }
    _require(motion["scale"] > 0.0, "scale must be > 0")
    history = payload["history"]
    _require(isinstance(history, list) and history, "history must be a non-empty list")
    points = []
    for index, item in enumerate(history):
        _require(isinstance(item, dict) and set(item) == POINT_KEYS, f"history {index} keys are invalid")
        points.append(
            {
                "x": _number(item["x"], f"history {index} x"),
                "y": _number(item["y"], f"history {index} y"),
                "depth": _number(item["depth"], f"history {index} depth"),
            }
        )
        _require(points[-1]["depth"] > 0.0, "depth must be > 0")
    warped = [reproject(point, motion) for point in points]
    moved = not _identity(motion)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED]
    rejected: list[str] = []
    if payload["blend"] == "stationary-pixel" and moved:
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("stationary-pixel history was not warped before temporal blending")
    else:
        decision = "recorded"
        reasons.append("history warped before blending" if payload["blend"] == "reprojected" else "history already aligned")
    reasons.append(
        "warped:"
        + ",".join(f"{item['x']:.6g}:{item['y']:.6g}:{item['depth']:.6g}" for item in warped)
    )
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, "warped-count:" + str(len(warped))],
        "openQuestions": ["physical S23 capture was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
