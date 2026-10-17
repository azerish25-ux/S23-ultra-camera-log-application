"""TC-P135-03 Invalid control draft.

Host fixture. An incomplete or out-of-range draft stays unapplied. Partially
typed input that reaches the comparison is rejected. The committed comparison
stays in preserved results.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P135-03",
    "phase": "P135",
    "workstream": 17,
    "name": "Invalid control draft",
    "intervention": "Enter an incomplete or out-of-range numeric value and interrupt editing before Apply.",
    "expected": "Preserve committed settings and keep the draft visibly unapplied or invalid.",
    "negative": "Partially typed input reaching the camera must fail.",
    "repeat": "Repeat shutter, ISO, focus distance, ROI coordinates, and output dimensions.",
}

NEGATIVE_TOKEN = "partial-draft-reached-camera"
OUT_OF_RANGE = "out-of-range-draft-applied"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "comparison",
    "draftText",
    "draftApplied",
    "draftMinimum",
    "draftMaximum",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p135_build_side_by_side_comparison_tools.py"
    spec = importlib.util.spec_from_file_location("p135_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    value, kind = _GATE.parse_complete_number(payload["draftText"], "draftText")
    applied = _GATE.require_bool(payload["draftApplied"], "draftApplied")
    minimum = _GATE.require_number(payload["draftMinimum"], "draftMinimum")
    maximum = _GATE.require_number(payload["draftMaximum"], "draftMaximum")
    _GATE.require(minimum <= maximum, "draft range is inverted")
    if kind != "complete" and applied:
        faults.append(NEGATIVE_TOKEN)
    elif kind == "complete" and applied and (value < minimum or value > maximum):
        faults.append(OUT_OF_RANGE)
    visible_draft = not applied or kind != "complete" or value < minimum or value > maximum
    extra = [{
        "draftKind": kind,
        "draftApplied": applied,
        "draftValue": value,
        "draftMinimum": minimum,
        "draftMaximum": maximum,
        "draftVisible": visible_draft,
        "committedFrame": bundle["comparison"]["left"]["frame_index"],
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        OUT_OF_RANGE: "an out-of-range draft must not reach the camera",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
