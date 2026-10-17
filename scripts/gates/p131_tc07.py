"""TC-P131-07 Unfair comparison view.

Host reference. Scale, time, and transfer mismatches are disclosed before a
preference. Automatically enhancing one side is rejected. The comparison does
not rewrite the applied manual target.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

CASE = {
    "id": "TC-P131-07",
    "phase": "P131",
    "workstream": 17,
    "name": "Unfair comparison view",
    "intervention": "Compare outputs at different times, scales, or display transforms without making those differences visible.",
    "expected": "Align comparable content or clearly disclose the mismatch before presenting a preference judgment.",
    "negative": "Automatically enhancing one side of a comparison must fail.",
    "repeat": "Repeat source-versus-result, recipe revisions, and different output aspect ratios.",
}

NEGATIVE_TOKEN = "auto-enhanced-comparison-side"
UNDISCLOSED = "undisclosed-comparison-mismatch"
SIDE_KEYS = {"scale", "transfer", "enhanced", "time"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "committed",
    "proposed",
    "left",
    "right",
    "mismatchDisclosed",
    "preferenceJudgment",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p131_design_manual_controls_for_deliberate_operation.py"
    spec = importlib.util.spec_from_file_location("p131_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _norm(value: str) -> str:
    return "".join(ch for ch in value.casefold() if ch.isalnum())


def _side(value: object, label: str) -> dict:
    _GATE.require(isinstance(value, dict) and set(value) == SIDE_KEYS, label + " keys are invalid")
    scale = _GATE.require_number(value["scale"], label + ".scale")
    _GATE.require(scale > 0, label + ".scale must be positive")
    return {
        "scale": scale,
        "transfer": _GATE.require_text(value["transfer"], label + ".transfer"),
        "enhanced": _GATE.require_bool(value["enhanced"], label + ".enhanced"),
        "time": _GATE.require_number(value["time"], label + ".time"),
    }


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    left = _side(payload["left"], "left")
    right = _side(payload["right"], "right")
    disclosed = _GATE.require_bool(payload["mismatchDisclosed"], "mismatchDisclosed")
    preference = _GATE.require_bool(payload["preferenceJudgment"], "preferenceJudgment")
    if left["enhanced"] or right["enhanced"]:
        faults.append(NEGATIVE_TOKEN)
    mismatch = (
        not _close(left["scale"], right["scale"])
        or _norm(left["transfer"]) != _norm(right["transfer"])
        or not _close(left["time"], right["time"])
    )
    if mismatch and preference and not disclosed:
        faults.append(UNDISCLOSED)
    extra = [{
        "mismatch": mismatch,
        "mismatchDisclosed": disclosed,
        "preferenceJudgment": preference,
        "leftEnhanced": left["enhanced"],
        "rightEnhanced": right["enhanced"],
        "applied": bundle["info"]["surviving"],
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        UNDISCLOSED: "a preference requires aligned content or a disclosed mismatch",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
