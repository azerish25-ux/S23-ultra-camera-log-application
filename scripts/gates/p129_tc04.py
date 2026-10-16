"""TC-P129-04 Stale or wrong-domain scope.

Host fixture. Monitoring aids report freshness and measurement domain.
An RGB8 preview histogram must not certify source bit depth or sensor clipping.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path


CASE_ID = "TC-P129-04"
NAME = "Stale or wrong-domain scope"
INTERVENTION = (
    "Feed a monitoring aid delayed preview samples or a display-clipped image from an unclipped source."
)
EXPECTED = "Identify freshness and measurement domain instead of falsely reporting sensor conditions."
NEGATIVE = "An RGB8 preview histogram must not certify source bit depth or sensor clipping."
REPEAT = "Repeat waveform, false color, focus peaking, and color histogram."
NEGATIVE_TOKEN = "rgb8-preview-certifies-source"
WRONG_DOMAIN_CLIP = "display-clip-reported-as-sensor-clip"
AIDS = frozenset({"waveform", "false-color", "focus-peaking", "histogram", "microphone-meters"})
DOMAINS = frozenset({"preview-rgb8", "source", "display"})
STALE_AFTER_SECONDS = 0.25
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "aid",
    "freshnessSeconds",
    "domain",
    "claimedSourceBitDepth",
    "reportsSensorClipping",
    "sourceClipped",
    "displayClipped",
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
    if not math.isfinite(number) or number < 0.0:
        raise ValueError(f"{label} must be a non-negative finite number")
    return number


def _bit_depth(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is bool or type(value) is not int:
        raise ValueError("claimedSourceBitDepth must be an int or null")
    if value < 1 or value > 32:
        raise ValueError("claimedSourceBitDepth is outside 1..32")
    return value


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    aid = _text(payload["aid"], "aid")
    if aid not in AIDS:
        raise ValueError("aid is unsupported")
    freshness = _number(payload["freshnessSeconds"], "freshnessSeconds")
    domain = _text(payload["domain"], "domain")
    if domain not in DOMAINS:
        raise ValueError("domain is unsupported")
    bit_depth = _bit_depth(payload["claimedSourceBitDepth"])
    reports_clip = _bool(payload["reportsSensorClipping"], "reportsSensorClipping")
    source_clipped = _bool(payload["sourceClipped"], "sourceClipped")
    display_clipped = _bool(payload["displayClipped"], "displayClipped")
    judged = _CORE.judge_hierarchy(
        payload["capture"],
        payload["monitoring"],
        payload["processing"],
        payload["warnings"],
        payload["record_in_scroll_only"],
        payload["warnings_visible"],
    )
    rejected = list(judged["rejectedClaims"])
    freshness_label = "stale" if freshness > STALE_AFTER_SECONDS else "fresh"
    reasons = [
        f"{CASE_ID} {NAME}",
        EXPECTED,
        INTERVENTION,
        f"repeat {repeat}",
        f"aid={aid}",
        f"freshness={freshness_label}",
        f"freshnessSeconds={format(freshness, '.12g')}",
        f"domain={domain}",
    ]
    reasons.extend(judged["reasons"])
    if domain == "preview-rgb8" and (bit_depth is not None or reports_clip):
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    elif domain == "display" and display_clipped and not source_clipped and reports_clip:
        _add(rejected, WRONG_DOMAIN_CLIP)
        reasons.append("display clipping was reported as sensor clipping")
    else:
        reasons.append("freshness and measurement domain are identified")
        reasons.append("aid does not certify source bit depth or sensor clipping from the wrong domain")
    decision = "rejected" if rejected else "recorded"
    bit_token = "none" if bit_depth is None else str(bit_depth)
    preserved = [
        evidence,
        f"aid={aid}",
        f"domain={domain}",
        f"freshness={freshness_label}",
        f"claimedSourceBitDepth={bit_token}",
    ]
    preserved.extend(judged["preservedResults"])
    questions = [_CORE.PHYSICAL_NOTE, REPEAT]
    return _CORE.seal_result(CASE_ID, decision, reasons, rejected, preserved, questions, evidence)
