"""TC-P053-02 CFA and crop parity.

Intervention: Use every supported mosaic pattern with odd and even crop origins
and distinct channel values.
Expected: Maintain correct channel identity and interpolation coordinates across
the transformed image.
Negative: Resetting mosaic parity after a crop must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P053-02"
INTERVENTION = (
    "Use every supported mosaic pattern with odd and even crop origins and distinct channel values."
)
EXPECTED = (
    "Maintain correct channel identity and interpolation coordinates across the transformed image."
)
NEGATIVE = "Resetting mosaic parity after a crop must fail."

_PATTERNS = ("RGGB", "GRBG", "GBRG", "BGGR")
_PLACEMENTS = ("interior", "border", "padded-row", "rotated-output")
_PHASE = {
    "RGGB": {(0, 0): "R", (1, 0): "G", (0, 1): "G", (1, 1): "B"},
    "GRBG": {(0, 0): "G", (1, 0): "R", (0, 1): "B", (1, 1): "G"},
    "GBRG": {(0, 0): "G", (1, 0): "B", (0, 1): "R", (1, 1): "G"},
    "BGGR": {(0, 0): "B", (1, 0): "G", (0, 1): "G", (1, 1): "R"},
}
_PAYLOAD_KEYS = (
    "pattern",
    "cropX",
    "cropY",
    "x",
    "y",
    "placement",
    "resetParity",
    "red",
    "green",
    "blue",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "channel_identity")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep mosaic phase after a crop. Reject a parity reset."""
    pattern, crop_x, crop_y, x, y, placement, reset, red, green, blue = _payload(payload)
    if placement == "rotated-output":
        sensor_x, sensor_y = crop_x + y, crop_y + x
    else:
        sensor_x, sensor_y = crop_x + x, crop_y + y
    channel = _PHASE[pattern][(sensor_x % 2, sensor_y % 2)]
    value = {"R": red, "G": green, "B": blue}[channel]
    preserved = [
        f"pattern:{pattern}",
        f"crop:{crop_x},{crop_y}",
        f"placement:{placement}",
        f"sensor:{sensor_x},{sensor_y}",
        f"interp:{sensor_x},{sensor_y}",
        f"red:{red}",
        f"green:{green}",
        f"blue:{blue}",
        f"channel:{channel}:{value}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    if reset:
        return _result(
            "rejected",
            reasons + [NEGATIVE],
            ["mosaic-parity-reset", f"ignored-phase:{x % 2},{y % 2}"],
            preserved,
            ["crop parity was reset"],
        )
    reasons.append(f"{pattern} channel {channel} at sensor {sensor_x},{sensor_y}")
    return _result(
        "channel_identity",
        reasons,
        [],
        preserved,
        ["channel identity is not a physical CFA measurement"],
    )


def _coord(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(label + " must be a non-negative int")
    return value


def _channel(value: object, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(label + " must be a positive int")
    return value


def _payload(payload: object) -> tuple[str, int, int, int, int, str, bool, int, int, int]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    pattern = payload["pattern"]
    if pattern not in _PATTERNS:
        raise ValueError("pattern is unknown")
    crop_x = _coord(payload["cropX"], "cropX")
    crop_y = _coord(payload["cropY"], "cropY")
    x = _coord(payload["x"], "x")
    y = _coord(payload["y"], "y")
    placement = payload["placement"]
    if placement not in _PLACEMENTS:
        raise ValueError("placement is unknown")
    reset = payload["resetParity"]
    if type(reset) is not bool:
        raise ValueError("resetParity must be a bool")
    red = _channel(payload["red"], "red")
    green = _channel(payload["green"], "green")
    blue = _channel(payload["blue"], "blue")
    if len({red, green, blue}) != 3:
        raise ValueError("channel values must be distinct")
    return pattern, crop_x, crop_y, x, y, placement, reset, red, green, blue


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("parity decision cannot be qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
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
