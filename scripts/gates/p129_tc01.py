"""TC-P129-01 Landscape and large-text stress.

Host fixture. Record and Stop, essential warnings, and source status stay
reachable when advanced controls open at large type in landscape. Critical
actions hidden inside scrolling content are rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P129-01"
NAME = "Landscape and large-text stress"
INTERVENTION = "Open advanced controls with increased font scale in landscape during an active take."
EXPECTED = "Keep Record or Stop, essential warnings, and selected source status reachable and readable."
NEGATIVE = "Critical actions hidden inside scrolling content must fail."
REPEAT = "Repeat small display settings, orientation changes, and simultaneous audio and storage warnings."
NEGATIVE_TOKEN = "critical-actions-hidden-in-scrolling-content"
SOURCE_UNREACHABLE = "source-status-unreachable"
WARNINGS_UNREADABLE = "warnings-unreadable"
LARGE_TEXT_SCALE = 1.3
ORIENTATIONS = frozenset({"landscape", "portrait"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "fontScale",
    "orientation",
    "advancedOpen",
    "activeTake",
    "sourceStatusReachable",
    "warningsReadable",
    "viewfinderReplaced",
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


def _number(value: object, label: str) -> float:
    if type(value) is bool or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    number = float(value)
    if number <= 0.0 or number != number or number == float("inf"):
        raise ValueError(f"{label} must be a positive finite number")
    return number


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    font_scale = _number(payload["fontScale"], "fontScale")
    orientation = _text(payload["orientation"], "orientation")
    if orientation not in ORIENTATIONS:
        raise ValueError("orientation must be landscape or portrait")
    advanced = _bool(payload["advancedOpen"], "advancedOpen")
    active = _bool(payload["activeTake"], "activeTake")
    source_reachable = _bool(payload["sourceStatusReachable"], "sourceStatusReachable")
    warnings_readable = _bool(payload["warningsReadable"], "warningsReadable")
    replaced = _bool(payload["viewfinderReplaced"], "viewfinderReplaced")
    judged = _CORE.judge_hierarchy(
        payload["capture"],
        payload["monitoring"],
        payload["processing"],
        payload["warnings"],
        payload["record_in_scroll_only"],
        payload["warnings_visible"],
        viewfinder_replaced=replaced,
    )
    rejected = list(judged["rejectedClaims"])
    reasons = [
        f"{CASE_ID} {NAME}",
        EXPECTED,
        INTERVENTION,
        f"repeat {repeat}",
        f"fontScale={font_scale}",
        f"orientation={orientation}",
        f"advancedOpen={str(advanced).lower()}",
        f"activeTake={str(active).lower()}",
    ]
    reasons.extend(judged["reasons"])
    capture_ids = set(judged["captureIds"])
    hidden = (
        payload["record_in_scroll_only"]
        or "record" not in capture_ids
        or "stop" not in capture_ids
    )
    if hidden:
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if not source_reachable:
        _add(rejected, SOURCE_UNREACHABLE)
        reasons.append("selected source status is not reachable")
    if not warnings_readable:
        _add(rejected, WARNINGS_UNREADABLE)
        reasons.append("essential warnings are not readable")
    large = font_scale >= LARGE_TEXT_SCALE
    if orientation == "landscape" and large and advanced and active and not rejected:
        reasons.append("landscape large-text stress keeps record, stop, warnings, and source status reachable")
    decision = "rejected" if rejected else "recorded"
    preserved = [evidence, f"fontScale={font_scale}", f"orientation={orientation}"]
    preserved.extend(judged["preservedResults"])
    questions = [_CORE.PHYSICAL_NOTE, REPEAT]
    return _CORE.seal_result(CASE_ID, decision, reasons, rejected, preserved, questions, evidence)

