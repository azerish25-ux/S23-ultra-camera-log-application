"""TC-P129-07 Unfair comparison view.

Host fixture. A preference judgment requires aligned content or a disclosed
mismatch. Automatically enhancing one side is rejected.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path


CASE_ID = "TC-P129-07"
NAME = "Unfair comparison view"
INTERVENTION = (
    "Compare outputs at different times, scales, or display transforms without making those differences visible."
)
EXPECTED = "Align comparable content or clearly disclose the mismatch before presenting a preference judgment."
NEGATIVE = "Automatically enhancing one side of a comparison must fail."
REPEAT = "Repeat source-versus-result, recipe revisions, and different output aspect ratios."
NEGATIVE_TOKEN = "automatic-one-side-enhancement"
UNDISCLOSED = "undisclosed-comparison-mismatch"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "leftTime",
    "rightTime",
    "leftScale",
    "rightScale",
    "leftTransform",
    "rightTransform",
    "leftEnhanced",
    "rightEnhanced",
    "mismatchDisclosed",
    "preferencePresented",
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
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-12)


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    left_time = _number(payload["leftTime"], "leftTime")
    right_time = _number(payload["rightTime"], "rightTime")
    left_scale = _number(payload["leftScale"], "leftScale")
    right_scale = _number(payload["rightScale"], "rightScale")
    if left_scale <= 0.0 or right_scale <= 0.0:
        raise ValueError("scale must be positive")
    left_transform = _text(payload["leftTransform"], "leftTransform")
    right_transform = _text(payload["rightTransform"], "rightTransform")
    left_enhanced = _bool(payload["leftEnhanced"], "leftEnhanced")
    right_enhanced = _bool(payload["rightEnhanced"], "rightEnhanced")
    disclosed = _bool(payload["mismatchDisclosed"], "mismatchDisclosed")
    preference = _bool(payload["preferencePresented"], "preferencePresented")
    judged = _CORE.judge_hierarchy(
        payload["capture"],
        payload["monitoring"],
        payload["processing"],
        payload["warnings"],
        payload["record_in_scroll_only"],
        payload["warnings_visible"],
    )
    rejected = list(judged["rejectedClaims"])
    aligned = (
        _close(left_time, right_time)
        and _close(left_scale, right_scale)
        and left_transform == right_transform
    )
    reasons = [
        f"{CASE_ID} {NAME}",
        EXPECTED,
        INTERVENTION,
        f"repeat {repeat}",
        f"aligned={str(aligned).lower()}",
        f"mismatchDisclosed={str(disclosed).lower()}",
        f"preferencePresented={str(preference).lower()}",
    ]
    reasons.extend(judged["reasons"])
    if left_enhanced or right_enhanced:
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if (not aligned) and preference and (not disclosed):
        _add(rejected, UNDISCLOSED)
        reasons.append("preference judgment hides a time, scale, or display-transform mismatch")
    if not rejected:
        if aligned:
            reasons.append("comparison sides are aligned")
        else:
            reasons.append("mismatch is disclosed before any preference judgment")
    decision = "rejected" if rejected else "recorded"
    preserved = [
        evidence,
        f"leftTime={format(left_time, '.12g')}",
        f"rightTime={format(right_time, '.12g')}",
        f"leftScale={format(left_scale, '.12g')}",
        f"rightScale={format(right_scale, '.12g')}",
        f"leftTransform={left_transform}",
        f"rightTransform={right_transform}",
        f"aligned={str(aligned).lower()}",
    ]
    preserved.extend(judged["preservedResults"])
    questions = [_CORE.PHYSICAL_NOTE, REPEAT]
    return _CORE.seal_result(CASE_ID, decision, reasons, rejected, preserved, questions, evidence)
