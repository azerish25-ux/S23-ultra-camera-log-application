"""TC-P136-01 Landscape and large-text stress.

Host fixture. Record or Stop, essential warnings, and source status stay
reachable during a large-text landscape take. Critical actions hidden in
scrolling content are rejected. A desktop screenshot cannot approve the UI.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p136_run_usability_acceptance_on_the_physical_phone",
    Path(__file__).resolve().parent / "p136_run_usability_acceptance_on_the_physical_phone.py",
)
_GATE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_GATE)

CASE = {
    "id": "TC-P136-01",
    "phase": "P136",
    "workstream": 17,
    "name": "Landscape and large-text stress",
    "intervention": "Open advanced controls with increased font scale in landscape during an active take.",
    "expected": "Keep Record or Stop, essential warnings, and selected source status reachable and readable.",
    "negative": "Critical actions hidden inside scrolling content must fail.",
    "repeat": "Repeat small display settings, orientation changes, and simultaneous audio and storage warnings.",
}
NEGATIVE_TOKEN = "critical-actions-hidden-in-scrolling-content"
LARGE_TEXT_SCALE = 1.3
ORIENTATIONS = frozenset({"landscape", "portrait"})
PAYLOAD_KEYS = {
    "evidenceId",
    "repeat",
    "report",
    "fontScale",
    "orientation",
    "activeTake",
    "advancedOpen",
    "recordReachable",
    "stopReachable",
    "warningsReadable",
    "sourceStatusReadable",
    "actionsHiddenInScroll",
}


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    report = _GATE.parse_report(payload["report"])
    font_scale = _GATE.require_number(payload["fontScale"], "fontScale")
    _GATE.require(font_scale > 0, "fontScale must be positive")
    orientation = _GATE.require_text(payload["orientation"], "orientation")
    _GATE.require(orientation in ORIENTATIONS, "orientation is not recognized")
    active = _GATE.require_bool(payload["activeTake"], "activeTake")
    advanced = _GATE.require_bool(payload["advancedOpen"], "advancedOpen")
    record = _GATE.require_bool(payload["recordReachable"], "recordReachable")
    stop = _GATE.require_bool(payload["stopReachable"], "stopReachable")
    warnings = _GATE.require_bool(payload["warningsReadable"], "warningsReadable")
    source = _GATE.require_bool(payload["sourceStatusReadable"], "sourceStatusReadable")
    hidden = _GATE.require_bool(payload["actionsHiddenInScroll"], "actionsHiddenInScroll")
    large_landscape = font_scale >= LARGE_TEXT_SCALE and orientation == "landscape" and active and advanced
    reachable = record and stop and warnings and source
    faults = []
    if hidden or not reachable:
        faults.append(NEGATIVE_TOKEN)
    reasons = [
        f"fontScale={font_scale} orientation={orientation} largeTextLandscape={str(large_landscape).lower()}",
        f"record={str(record).lower()} stop={str(stop).lower()} warnings={str(warnings).lower()} source={str(source).lower()}",
    ]
    preserved = [{
        "fontScale": font_scale,
        "orientation": orientation,
        "activeTake": active,
        "advancedOpen": advanced,
        "largeTextLandscape": large_landscape,
        "recordReachable": record,
        "stopReachable": stop,
        "warningsReadable": warnings,
        "sourceStatusReadable": source,
        "actionsHiddenInScroll": hidden,
        "measuredOnDevice": False,
    }]
    return _GATE.finish_tc(
        CASE,
        evidence,
        repeat,
        report,
        faults,
        reasons,
        preserved,
        {NEGATIVE_TOKEN: CASE["negative"]},
        {NEGATIVE_TOKEN: "Keep Record, Stop, warnings, and source status out of scrolling-only content."},
    )
