"""TC-P134-01 Landscape and large-text stress.

Host reference. Record or Stop, essential warnings, and the selected source stay
reachable. Critical actions hidden in scrolling content are rejected. Progress
still follows the phase rule and is not a fabricated completion.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P134-01",
    "phase": "P134",
    "workstream": 17,
    "name": "Landscape and large-text stress",
    "intervention": "Open advanced controls with increased font scale in landscape during an active take.",
    "expected": "Keep Record or Stop, essential warnings, and selected source status reachable and readable.",
    "negative": "Critical actions hidden inside scrolling content must fail.",
    "repeat": "Repeat small display settings, orientation changes, and simultaneous audio and storage warnings.",
}

NEGATIVE_TOKEN = "critical-actions-hidden-in-scrolling-content"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "progress",
    "fontScale",
    "orientation",
    "activeTake",
    "recordReachable",
    "stopReachable",
    "warningsReadable",
    "sourceStatusReadable",
    "actionsHiddenInScroll",
    "sourceId",
    "sourceStatusText",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p134_design_transparent_progress_and_failure_states.py"
    spec = importlib.util.spec_from_file_location("p134_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    font_scale = _GATE.require_number(payload["fontScale"], "fontScale")
    _GATE.require(font_scale > 0, "fontScale must be positive")
    orientation = _GATE.require_text(payload["orientation"], "orientation")
    _GATE.require(orientation in {"landscape", "portrait"}, "orientation is not recognized")
    active_take = _GATE.require_bool(payload["activeTake"], "activeTake")
    record_reachable = _GATE.require_bool(payload["recordReachable"], "recordReachable")
    stop_reachable = _GATE.require_bool(payload["stopReachable"], "stopReachable")
    warnings_readable = _GATE.require_bool(payload["warningsReadable"], "warningsReadable")
    source_status_readable = _GATE.require_bool(payload["sourceStatusReadable"], "sourceStatusReadable")
    hidden = _GATE.require_bool(payload["actionsHiddenInScroll"], "actionsHiddenInScroll")
    source_id = _GATE.require_text(payload["sourceId"], "sourceId")
    status_text = _GATE.require_text(payload["sourceStatusText"], "sourceStatusText")
    shows_source = status_text == source_id
    if hidden or not (
        record_reachable
        and stop_reachable
        and warnings_readable
        and source_status_readable
        and shows_source
    ):
        faults.append(NEGATIVE_TOKEN)
    if active_take and bundle["progress"]["success"] is True:
        faults.append(_GATE.PREMATURE_COMPLETE)
    extra = [{
        "fontScale": font_scale,
        "orientation": orientation,
        "activeTake": active_take,
        "recordReachable": record_reachable,
        "stopReachable": stop_reachable,
        "warningsReadable": warnings_readable,
        "sourceStatusReadable": source_status_readable and shows_source,
        "actionsHiddenInScroll": hidden,
        "sourceId": source_id,
    }]
    return _GATE.finish_case(CASE, bundle, faults, extra, {NEGATIVE_TOKEN: CASE["negative"]})
