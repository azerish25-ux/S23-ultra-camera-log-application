"""TC-P135-01 Landscape and large-text stress.

Host fixture. Record or Stop, warnings, and the matched source stay reachable.
Critical actions hidden in scrolling content are rejected. The comparison match
rule still applies.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P135-01",
    "phase": "P135",
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
    "comparison",
    "fontScale",
    "orientation",
    "activeTake",
    "recordReachable",
    "stopReachable",
    "warningsReadable",
    "sourceStatusReadable",
    "actionsHiddenInScroll",
    "sourceStatusText",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p135_build_side_by_side_comparison_tools.py"
    spec = importlib.util.spec_from_file_location("p135_gate_for_tc01", path)
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
    status_text = payload["sourceStatusText"]
    _GATE.require(isinstance(status_text, str), "sourceStatusText must be a string")
    shows_source = status_text == bundle["comparison"]["left"]["source_sha256"]
    if hidden or not (
        record_reachable and stop_reachable and warnings_readable and source_status_readable and shows_source
    ):
        faults.append(NEGATIVE_TOKEN)
    extra = [{
        "fontScale": font_scale,
        "orientation": orientation,
        "activeTake": active_take,
        "recordReachable": record_reachable,
        "stopReachable": stop_reachable,
        "warningsReadable": warnings_readable,
        "sourceStatusReadable": source_status_readable and shows_source,
        "actionsHiddenInScroll": hidden,
        "statusLabel": _GATE.status_label(bundle["info"]),
    }]
    return _GATE.finish_case(CASE, bundle, faults, extra, {NEGATIVE_TOKEN: CASE["negative"]})
