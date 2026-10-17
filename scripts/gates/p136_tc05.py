"""TC-P136-05 Nonvisual interaction.

Host fixture. Names, order, values, and cancellation stay available without
relying only on color or precision gestures. An unlabeled canvas as the only
control is rejected.
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
    "id": "TC-P136-05",
    "phase": "P136",
    "workstream": 17,
    "name": "Nonvisual interaction",
    "intervention": "Perform the core phase task using accessibility navigation and spoken state information.",
    "expected": "Expose usable names, order, values, and cancellation without relying only on color or precision gestures.",
    "negative": "An unlabeled custom canvas as the only control must fail.",
    "repeat": "Repeat camera operation, ROI selection, focus editing, and recovery export.",
}
NEGATIVE_TOKEN = "unlabeled-canvas-only-control"
COLOR_OR_GESTURE = "color-or-precision-gesture-only"
MISSING_SEMANTICS = "missing-name-order-value-or-cancel"
PAYLOAD_KEYS = {
    "evidenceId",
    "repeat",
    "report",
    "controlName",
    "spokenState",
    "orderExposed",
    "valueExposed",
    "cancellationExposed",
    "colorOnly",
    "precisionGestureOnly",
    "unlabeledCanvasOnly",
}


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    report = _GATE.parse_report(payload["report"])
    name = _GATE.require_text(payload["controlName"], "controlName")
    spoken = _GATE.require_text(payload["spokenState"], "spokenState")
    order = _GATE.require_bool(payload["orderExposed"], "orderExposed")
    value = _GATE.require_bool(payload["valueExposed"], "valueExposed")
    cancel = _GATE.require_bool(payload["cancellationExposed"], "cancellationExposed")
    color_only = _GATE.require_bool(payload["colorOnly"], "colorOnly")
    gesture_only = _GATE.require_bool(payload["precisionGestureOnly"], "precisionGestureOnly")
    canvas = _GATE.require_bool(payload["unlabeledCanvasOnly"], "unlabeledCanvasOnly")
    faults = []
    if canvas:
        faults.append(NEGATIVE_TOKEN)
    if color_only or gesture_only:
        faults.append(COLOR_OR_GESTURE)
    if not (order and value and cancel):
        faults.append(MISSING_SEMANTICS)
    reasons = [
        f"controlName={name} spokenState={spoken}",
        f"order={str(order).lower()} value={str(value).lower()} cancel={str(cancel).lower()}",
        f"colorOnly={str(color_only).lower()} precisionGestureOnly={str(gesture_only).lower()} unlabeledCanvasOnly={str(canvas).lower()}",
    ]
    preserved = [{
        "controlName": name,
        "spokenState": spoken,
        "orderExposed": order,
        "valueExposed": value,
        "cancellationExposed": cancel,
        "colorOnly": color_only,
        "precisionGestureOnly": gesture_only,
        "unlabeledCanvasOnly": canvas,
    }]
    return _GATE.finish_tc(
        CASE,
        evidence,
        repeat,
        report,
        faults,
        reasons,
        preserved,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            COLOR_OR_GESTURE: CASE["expected"],
            MISSING_SEMANTICS: CASE["expected"],
        },
        {
            NEGATIVE_TOKEN: "Do not use an unlabeled custom canvas as the only control.",
            COLOR_OR_GESTURE: "Do not rely only on color or precision gestures.",
            MISSING_SEMANTICS: "Expose name, order, value, and cancellation.",
        },
    )
