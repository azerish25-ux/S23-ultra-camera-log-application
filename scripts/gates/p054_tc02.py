"""TC-P054-02 CFA and crop parity.

Intervention: Use every supported mosaic pattern with odd and even crop
origins and distinct channel values.
Expected: Maintain correct channel identity and interpolation coordinates
across the transformed image.
Negative: Resetting mosaic parity after a crop must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal

CASE_ID = "TC-P054-02"
INTERVENTION = (
    "Use every supported mosaic pattern with odd and even crop origins and distinct channel values."
)
EXPECTED = (
    "Maintain correct channel identity and interpolation coordinates across the transformed image."
)
NEGATIVE = "Resetting mosaic parity after a crop must fail."

_PATTERNS = ("RGGB", "GRBG", "GBRG", "BGGR")
_SITES = ("interior", "border", "padded-row", "rotated")
_MOSAIC = {
    "RGGB": {(0, 0): "R", (1, 0): "G", (0, 1): "G", (1, 1): "B"},
    "GRBG": {(0, 0): "G", (1, 0): "R", (0, 1): "B", (1, 1): "G"},
    "GBRG": {(0, 0): "G", (1, 0): "B", (0, 1): "R", (1, 1): "G"},
    "BGGR": {(0, 0): "B", (1, 0): "G", (0, 1): "G", (1, 1): "R"},
}
_PAYLOAD_KEYS = ("pattern", "originX", "originY", "site", "red", "green", "blue", "parityReset")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_UINT = re.compile(r"0|[1-9][0-9]*")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def channel_at(pattern: str, origin_x: int, origin_y: int) -> str:
    """Return the mosaic channel at a crop origin. Parity follows the origin."""
    return _MOSAIC[pattern][(origin_x % 2, origin_y % 2)]


def evaluate(payload: dict) -> dict:
    """Keep CFA phase after a crop. Resetting parity is rejected."""
    pattern, origin_x, origin_y, site, red, green, blue, reset = _payload(payload)
    phase = channel_at(pattern, origin_x, origin_y)
    sample = {"R": red, "G": green, "B": blue}[phase]
    preserved = [
        pattern,
        f"origin:{origin_x},{origin_y}",
        f"site:{site}",
        f"phase:{phase}",
        f"R:{red}",
        f"G:{green}",
        f"B:{blue}",
        f"sample:{sample}",
    ]
    if site == "rotated":
        preserved.append(f"rotated-coordinate:{origin_y},{origin_x}")
    reasons = [EXPECTED, INTERVENTION, f"{pattern} origin {origin_x},{origin_y} phase {phase}"]
    rejected: list[str] = []
    questions = [f"{site} keeps channel {phase} at the crop origin"]
    if reset:
        decision = "rejected"
        rejected.append("mosaic-parity-reset")
        reasons.append(NEGATIVE)
        questions.append("crop parity was reset and the correct phase was kept in the inventory")
    else:
        decision = "parity-kept"
        reasons.append("channel identity follows the crop origin rather than a reset phase")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, int, int, str, str, str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    pattern = payload["pattern"]
    if pattern not in _PATTERNS:
        raise ValueError("pattern is unsupported")
    origin_x = _uint(payload["originX"], "originX")
    origin_y = _uint(payload["originY"], "originY")
    site = payload["site"]
    if site not in _SITES:
        raise ValueError("site is unsupported")
    red = _decimal(payload["red"], "red")
    green = _decimal(payload["green"], "green")
    blue = _decimal(payload["blue"], "blue")
    if len({Decimal(red), Decimal(green), Decimal(blue)}) != 3:
        raise ValueError("channel values must be distinct")
    reset = payload["parityReset"]
    if type(reset) is not bool:
        raise ValueError("parityReset must be a bool")
    return pattern, origin_x, origin_y, site, red, green, blue, reset


def _uint(value: object, label: str) -> int:
    if not isinstance(value, str) or _UINT.fullmatch(value) is None:
        raise ValueError(f"{label} must be a canonical non-negative integer string")
    return int(value)


def _decimal(value: object, label: str) -> str:
    if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
        raise ValueError(f"{label} must be a canonical decimal string")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P054-02 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
