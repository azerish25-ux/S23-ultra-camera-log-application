"""TC-P056-02 CFA and crop parity.

Intervention: Use every supported mosaic pattern with odd and even crop origins
and distinct channel values.
Expected: Maintain correct channel identity and interpolation coordinates across
the transformed image.
Negative: Resetting mosaic parity after a crop must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P056-02"
INTERVENTION = (
    "Use every supported mosaic pattern with odd and even crop origins and distinct channel values."
)
EXPECTED = (
    "Maintain correct channel identity and interpolation coordinates across the transformed image."
)
NEGATIVE = "Resetting mosaic parity after a crop must fail."

_MOSAIC = {
    "RGGB": ("R", "G", "G", "B"),
    "BGGR": ("B", "G", "G", "R"),
    "GRBG": ("G", "R", "B", "G"),
    "GBRG": ("G", "B", "R", "G"),
}
_SITES = ("interior", "border", "padded-row", "rotated")
_ROTATIONS = (0, 90, 180, 270)
_PAYLOAD_KEYS = (
    "pattern",
    "originX",
    "originY",
    "channel",
    "resetParity",
    "site",
    "rotation",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_CHANNELS = {"R", "G", "B"}


def expected_channel(pattern: str, origin_x: int, origin_y: int, rotation: int) -> str:
    """Channel at the crop origin after an even-frame rotation. 180 flips both parities."""
    x, y = origin_x, origin_y
    if rotation == 90:
        x, y = origin_y, origin_x + 1
    elif rotation == 180:
        x, y = origin_x + 1, origin_y + 1
    elif rotation == 270:
        x, y = origin_y + 1, origin_x
    return _MOSAIC[pattern][(y % 2) * 2 + (x % 2)]


def evaluate(payload: dict) -> dict:
    """Keep mosaic parity through the crop. Resetting it is rejected."""
    pattern, origin_x, origin_y, channel, reset, site, rotation = _payload(payload)
    expected = expected_channel(pattern, origin_x, origin_y, rotation)
    preserved = [
        f"pattern:{pattern}",
        f"origin:{origin_x},{origin_y}",
        f"site:{site}",
        f"rotation:{rotation}",
        f"expected:{expected}",
        f"stated:{channel}",
    ]
    rejected: list[str] = []
    questions: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"crop origin {origin_x},{origin_y} on {pattern}"]
    if reset:
        decision = "rejected"
        rejected.append("mosaic-parity-reset")
        reasons.append(NEGATIVE)
        reasons.append(f"parity reset would report {_MOSAIC[pattern][0]} instead of {expected}")
        questions.append("mosaic phase was not restarted at the crop origin")
    elif channel != expected:
        decision = "rejected"
        rejected.append("channel-mismatch")
        reasons.append(f"stated channel {channel} is not {expected}")
        questions.append("channel identity was not rewritten")
    else:
        decision = "parity-kept"
        reasons.append(f"channel {expected} stays with coordinate {origin_x},{origin_y}")
        questions.append(f"{site} parity retained")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, int, int, str, bool, str, int]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    pattern = payload["pattern"]
    if pattern not in _MOSAIC:
        raise ValueError("pattern is unsupported")
    origin_x = payload["originX"]
    origin_y = payload["originY"]
    if type(origin_x) is not int or origin_x < 0 or type(origin_y) is not int or origin_y < 0:
        raise ValueError("origin must be a non-negative int")
    channel = payload["channel"]
    if channel not in _CHANNELS:
        raise ValueError("channel must be R, G, or B")
    reset = payload["resetParity"]
    if type(reset) is not bool:
        raise ValueError("resetParity must be a bool")
    site = payload["site"]
    if site not in _SITES:
        raise ValueError("site is unsupported")
    rotation = payload["rotation"]
    if rotation not in _ROTATIONS:
        raise ValueError("rotation must be 0, 90, 180, or 270")
    return pattern, origin_x, origin_y, channel, reset, site, rotation


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P056-02 must not yield qualified or allowed")
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
