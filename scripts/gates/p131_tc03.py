"""TC-P131-03 Invalid control draft.

Host reference. An incomplete draft such as "1." or "" does not change the
applied value. Partially typed input that reaches the camera is rejected.
An explicit out-of-range submit is rejected and the previous applied value stays.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P131-03",
    "phase": "P131",
    "workstream": 17,
    "name": "Invalid control draft",
    "intervention": "Enter an incomplete or out-of-range numeric value and interrupt editing before Apply.",
    "expected": "Preserve committed settings and keep the draft visibly unapplied or invalid.",
    "negative": "Partially typed input reaching the camera must fail.",
    "repeat": "Repeat shutter, ISO, focus distance, ROI coordinates, and output dimensions.",
}

NEGATIVE_TOKEN = "partial-draft-reached-camera"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "committed",
    "proposed",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p131_design_manual_controls_for_deliberate_operation.py"
    spec = importlib.util.spec_from_file_location("p131_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    info = bundle["info"]
    incomplete = info["draftKind"] != "complete"
    reached = incomplete and (
        info["proposed"]["apply_partial"]
        or not _GATE.same_number(info["proposed"]["applied"], info["previous"])
    )
    if reached:
        faults.append(NEGATIVE_TOKEN)
    extra = [{
        "draft": info["proposed"]["draft"],
        "draftKind": info["draftKind"],
        "draftStatus": info["status"],
        "applied": info["surviving"],
        "previousApplied": info["previous"],
        "candidateApplied": info["candidate"],
    }]
    return _GATE.finish_case(CASE, bundle, faults, extra, {NEGATIVE_TOKEN: CASE["negative"]})
