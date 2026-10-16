"""TC-P129-05 Nonvisual interaction.

Host fixture. Controls expose usable names, order, values, and cancellation.
An unlabeled custom canvas as the only control is rejected, as is a control
that relies only on color or a precision gesture.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P129-05"
NAME = "Nonvisual interaction"
INTERVENTION = "Perform the core phase task using accessibility navigation and spoken state information."
EXPECTED = (
    "Expose usable names, order, values, and cancellation without relying only on color or precision gestures."
)
NEGATIVE = "An unlabeled custom canvas as the only control must fail."
REPEAT = "Repeat camera operation, ROI selection, focus editing, and recovery export."
NEGATIVE_TOKEN = "unlabeled-canvas-only-control"
COLOR_OR_GESTURE = "color-or-precision-only"
MISSING_NAME = "missing-accessible-name"
CONTROL_KEYS = {"id", "accessibleName", "value", "order"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "controls",
    "cancellation",
    "colorOnly",
    "precisionGestureOnly",
    "unlabeledCanvasOnly",
    "capture",
    "monitoring",
    "processing",
    "warnings",
    "record_in_scroll_only",
    "warnings_visible",
)

_SPEC = importlib.util.spec_from_file_location(
    "p129_define_the_camera_screen_information_hierarchy",
    Path(__file__).resolve().parent / "p129_define_the_camera_screen_information_hierarchy.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _controls(items: object) -> list[dict]:
    if not isinstance(items, list) or not items:
        raise ValueError("controls must be a non-empty list")
    parsed = []
    seen = set()
    orders = set()
    for index, item in enumerate(items):
        label = f"controls[{index}]"
        if not isinstance(item, dict) or set(item) != CONTROL_KEYS:
            raise ValueError(f"{label} keys must be id, accessibleName, value, order")
        ident = item["id"]
        name = item["accessibleName"]
        value = item["value"]
        order = item["order"]
        if not isinstance(ident, str) or not ident.strip() or ident != ident.strip():
            raise ValueError(f"{label}.id must be a non-empty string")
        if not isinstance(name, str) or name != name.strip():
            raise ValueError(f"{label}.accessibleName must be a string")
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError(f"{label}.value must be a non-empty string")
        if type(order) is not int or order < 0:
            raise ValueError(f"{label}.order must be a non-negative int")
        if ident in seen:
            raise ValueError("duplicate control id")
        if order in orders:
            raise ValueError("duplicate control order")
        seen.add(ident)
        orders.add(order)
        parsed.append({"id": ident, "accessibleName": name, "value": value, "order": order})
    return parsed


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    controls = _controls(payload["controls"])
    cancellation = payload["cancellation"]
    if not isinstance(cancellation, str) or cancellation != cancellation.strip():
        raise ValueError("cancellation must be a string")
    color_only = _bool(payload["colorOnly"], "colorOnly")
    gesture_only = _bool(payload["precisionGestureOnly"], "precisionGestureOnly")
    unlabeled = _bool(payload["unlabeledCanvasOnly"], "unlabeledCanvasOnly")
    judged = _CORE.judge_hierarchy(
        payload["capture"],
        payload["monitoring"],
        payload["processing"],
        payload["warnings"],
        payload["record_in_scroll_only"],
        payload["warnings_visible"],
    )
    rejected = list(judged["rejectedClaims"])
    spoken = [item["id"] for item in sorted(controls, key=lambda item: item["order"])]
    reasons = [
        f"{CASE_ID} {NAME}",
        EXPECTED,
        INTERVENTION,
        f"repeat {repeat}",
        "spokenOrder=" + ",".join(spoken),
        "cancellation=" + (cancellation if cancellation else "missing"),
    ]
    reasons.extend(judged["reasons"])
    blank = [item["id"] for item in controls if not item["accessibleName"].strip()]
    only_canvas = unlabeled or (len(controls) == 1 and bool(blank)) or (blank and len(blank) == len(controls))
    if only_canvas:
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    elif blank:
        _add(rejected, MISSING_NAME)
        reasons.append("accessible name missing for " + ",".join(blank))
    if not cancellation:
        _add(rejected, "missing-cancellation")
        reasons.append("cancellation is not exposed")
    if color_only or gesture_only:
        _add(rejected, COLOR_OR_GESTURE)
        reasons.append("control relies only on color or a precision gesture")
    if not rejected:
        reasons.append("names, order, values, and cancellation are exposed")
    decision = "rejected" if rejected else "recorded"
    preserved = [evidence, "spokenOrder=" + ",".join(spoken), "cancellation=" + (cancellation or "missing")]
    preserved.extend(judged["preservedResults"])
    questions = [_CORE.PHYSICAL_NOTE, REPEAT]
    return _CORE.seal_result(CASE_ID, decision, reasons, rejected, preserved, questions, evidence)
