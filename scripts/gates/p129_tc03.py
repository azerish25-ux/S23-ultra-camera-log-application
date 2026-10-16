"""TC-P129-03 Invalid control draft.

Host fixture. An interrupted draft stays unapplied. Partially typed or
out-of-range input that reaches the camera is rejected, and the committed
value is preserved.
"""

from __future__ import annotations

import importlib.util
import math
import re
from pathlib import Path


CASE_ID = "TC-P129-03"
NAME = "Invalid control draft"
INTERVENTION = "Enter an incomplete or out-of-range numeric value and interrupt editing before Apply."
EXPECTED = "Preserve committed settings and keep the draft visibly unapplied or invalid."
NEGATIVE = "Partially typed input reaching the camera must fail."
REPEAT = "Repeat shutter, ISO, focus distance, ROI coordinates, and output dimensions."
NEGATIVE_TOKEN = "partial-draft-reached-camera"
COMPLETE_DRAFT = re.compile(r"^[+-]?(?:\d+\.\d+|\d+|\.\d+)(?:[eE][+-]?\d+)?$")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "control",
    "committed",
    "draft",
    "minimum",
    "maximum",
    "applied",
    "cameraValue",
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


def _draft_state(draft: object, minimum: float, maximum: float) -> tuple[bool, bool, float | None]:
    if isinstance(draft, str):
        if not COMPLETE_DRAFT.fullmatch(draft):
            return False, False, None
        value = float(draft)
        if not math.isfinite(value):
            raise ValueError("draft must be finite")
    else:
        value = _number(draft, "draft")
    return True, minimum <= value <= maximum, value


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    control = _text(payload["control"], "control")
    minimum = _number(payload["minimum"], "minimum")
    maximum = _number(payload["maximum"], "maximum")
    if minimum > maximum:
        raise ValueError("minimum must not exceed maximum")
    committed = _number(payload["committed"], "committed")
    if not minimum <= committed <= maximum:
        raise ValueError("committed value must lie inside the control range")
    camera = _number(payload["cameraValue"], "cameraValue")
    applied = _bool(payload["applied"], "applied")
    complete, in_range, draft_value = _draft_state(payload["draft"], minimum, maximum)
    judged = _CORE.judge_hierarchy(
        payload["capture"],
        payload["monitoring"],
        payload["processing"],
        payload["warnings"],
        payload["record_in_scroll_only"],
        payload["warnings_visible"],
    )
    rejected = list(judged["rejectedClaims"])
    draft_text = payload["draft"] if isinstance(payload["draft"], str) else format(draft_value, ".12g")
    reasons = [
        f"{CASE_ID} {NAME}",
        EXPECTED,
        INTERVENTION,
        f"repeat {repeat}",
        f"control={control}",
        f"committed={format(committed, '.12g')}",
        f"draft={draft_text}",
        f"draftComplete={str(complete).lower()}",
        f"draftInRange={str(in_range).lower()}",
        f"applied={str(applied).lower()}",
    ]
    reasons.extend(judged["reasons"])
    invalid = (not complete) or (not in_range)
    reached = (not applied and not _close(camera, committed)) or (applied and invalid)
    if applied and complete and in_range and draft_value is not None and not _close(camera, draft_value):
        reached = True
    if reached:
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("committed value remains " + format(committed, ".12g"))
    elif not applied:
        reasons.append("draft stays unapplied; committed value remains " + format(committed, ".12g"))
        if invalid:
            reasons.append("draft is visibly invalid")
    else:
        reasons.append("applied draft matches the camera value")
    decision = "rejected" if rejected else "recorded"
    preserved = [
        evidence,
        f"control={control}",
        f"committed={format(committed, '.12g')}",
        f"draft={draft_text}",
        f"cameraValue={format(camera, '.12g')}",
    ]
    preserved.extend(judged["preservedResults"])
    questions = [_CORE.PHYSICAL_NOTE, REPEAT]
    return _CORE.seal_result(CASE_ID, decision, reasons, rejected, preserved, questions, evidence)
