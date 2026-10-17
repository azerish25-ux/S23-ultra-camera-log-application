"""TC-P132-03 Invalid control draft.

Host reference. An incomplete or out-of-range threshold draft stays unapplied.
Clipping counts keep using the declared threshold already on the scope.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P132-03",
    "phase": "P132",
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
    "scopes",
    "source",
    "applyMutant",
    "draftText",
    "draftApplied",
    "draftMinimum",
    "draftMaximum",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p132_build_scopes_with_declared_signal_domains.py"
    spec = importlib.util.spec_from_file_location("p132_gate_for_tc03", path)
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
    clipping = _GATE.scope_by_kind(bundle["info"], "clipping")
    extra = [{
        "draftKind": kind,
        "draftApplied": applied,
        "draftValue": value,
        "draftMinimum": minimum,
        "draftMaximum": maximum,
        "declaredThreshold": clipping["threshold"],
        "clippingCount": clipping["clippingCount"],
        "draftVisible": not applied or kind != "complete" or value < minimum or value > maximum,
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        OUT_OF_RANGE: "an out-of-range draft must not reach the camera",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
