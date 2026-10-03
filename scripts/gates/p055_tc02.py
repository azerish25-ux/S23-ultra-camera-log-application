"""TC-P055-02 CFA and crop parity.

Intervention: Use every supported mosaic pattern with odd and even crop
origins and distinct channel values.
Expected: Maintain correct channel identity and interpolation coordinates
across the transformed image.
Negative: Resetting mosaic parity after a crop must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P055-02"
INTERVENTION = (
    "Use every supported mosaic pattern with odd and even crop origins and distinct channel values."
)
EXPECTED = (
    "Maintain correct channel identity and interpolation coordinates across the transformed image."
)
NEGATIVE = "Resetting mosaic parity after a crop must fail."
REPEAT = "Repeat with border pixels, padded rows, and rotated developed output."

_MOSAIC = {
    "RGGB": ("R", "G", "G", "B"),
    "BGGR": ("B", "G", "G", "R"),
    "GRBG": ("G", "R", "B", "G"),
    "GBRG": ("G", "B", "R", "G"),
}
_SITES = ("interior", "border", "padded-row", "rotated")
_PAYLOAD_KEYS = (
    "pattern",
    "cropX",
    "cropY",
    "sampleX",
    "sampleY",
    "red",
    "green",
    "blue",
    "resetParity",
    "site",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_VALUE = re.compile(r"0|[1-9][0-9]*")


def evaluate(payload: dict) -> dict:
    """Keep mosaic channel identity unless parity is reset after the crop."""
    pattern, crop_x, crop_y, sample_x, sample_y, red, green, blue, reset, site = _payload(payload)
    phase_x = (crop_x + sample_x) & 1
    phase_y = (crop_y + sample_y) & 1
    channel = _MOSAIC[pattern][phase_y * 2 + phase_x]
    values = {"R": red, "G": green, "B": blue}
    preserved = [
        f"pattern:{pattern}",
        f"origin:{crop_x},{crop_y}",
        f"sample:{sample_x},{sample_y}",
        f"coord:{crop_x + sample_x},{crop_y + sample_y}",
        f"channel:{channel}",
        f"value:{channel}={values[channel]}",
        f"site:{site}",
        f"distinct:{red},{green},{blue}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}"]
    if reset:
        decision = "rejected"
        rejected = ["mosaic-parity-reset"]
        reasons.append(NEGATIVE)
        reasons.append(f"crop origin {crop_x},{crop_y} must not be forced back to phase 0,0")
        questions.append(f"correct channel {channel} was retained after the rejected reset")
    else:
        decision = "parity_kept"
        rejected = []
        reasons.append(f"{pattern} sample maps to {channel} at phase {phase_x},{phase_y}")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    pattern = payload["pattern"]
    if pattern not in _MOSAIC:
        raise ValueError("pattern is unsupported")
    crop_x = _uint(payload["cropX"], "cropX")
    crop_y = _uint(payload["cropY"], "cropY")
    sample_x = _uint(payload["sampleX"], "sampleX")
    sample_y = _uint(payload["sampleY"], "sampleY")
    red = _code(payload["red"], "red")
    green = _code(payload["green"], "green")
    blue = _code(payload["blue"], "blue")
    if len({red, green, blue}) != 3:
        raise ValueError("channel values must be distinct")
    reset = payload["resetParity"]
    if type(reset) is not bool:
        raise ValueError("resetParity must be a bool")
    site = payload["site"]
    if site not in _SITES:
        raise ValueError("site is unsupported")
    return pattern, crop_x, crop_y, sample_x, sample_y, red, green, blue, reset, site


def _uint(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(label + " must be a non-negative int")
    return value


def _code(value: object, label: str) -> str:
    if not isinstance(value, str) or _VALUE.fullmatch(value) is None:
        raise ValueError(label + " must be a canonical non-negative integer string")
    return value


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P055-02 must not yield qualified or allowed")
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
