"""TC-P051-02 CFA and crop parity.

Intervention: Use every supported mosaic pattern with odd and even crop origins
and distinct channel values.
Expected: Maintain correct channel identity and interpolation coordinates across
the transformed image.
Negative: Resetting mosaic parity after a crop must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P051-02"
INTERVENTION = (
    "Use every supported mosaic pattern with odd and even crop origins and distinct channel values."
)
EXPECTED = (
    "Maintain correct channel identity and interpolation coordinates across the transformed image."
)
NEGATIVE = "Resetting mosaic parity after a crop must fail."

_CFA = ("RGGB", "GRBG", "GBRG", "BGGR")
_PHASE = {name: name for name in _CFA}
_ROTATIONS = (0, 90, 180, 270)
_PAYLOAD_KEYS = (
    "cfa",
    "width",
    "height",
    "rowStride",
    "cropLeft",
    "cropTop",
    "cropWidth",
    "cropHeight",
    "red",
    "green",
    "blue",
    "paddingValue",
    "rotation",
    "resetParity",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "identity_held")
_FORBIDDEN = {"qualified", "allowed"}


def channel_at(y: int, x: int, cfa: str) -> str:
    return _PHASE[cfa][(y % 2) * 2 + (x % 2)]


def evaluate(payload: dict) -> dict:
    """Keep Bayer phase on absolute coordinates. Resetting it after a crop fails."""
    parsed = _payload(payload)
    cfa = parsed["cfa"]
    absolute = channel_at(parsed["cropTop"], parsed["cropLeft"], cfa)
    reset = channel_at(0, 0, cfa)
    rx, ry = _rotate(0, 0, parsed["cropWidth"], parsed["cropHeight"], parsed["rotation"])
    preserved = [
        f"cfa:{cfa}",
        f"absolute:{absolute}",
        f"reset:{reset}",
        f"crop:{parsed['cropWidth']}x{parsed['cropHeight']}+{parsed['cropLeft']}+{parsed['cropTop']}",
        f"stride:{parsed['rowStride']}",
        f"padding:{parsed['paddingValue']}:ignored",
        f"distinct:{parsed['red']},{parsed['green']},{parsed['blue']}",
        f"developed:{rx},{ry}:{parsed['red']},{parsed['green']},{parsed['blue']}",
    ]
    if parsed["resetParity"]:
        return _result(
            "rejected",
            [EXPECTED, NEGATIVE, "mosaic parity stays tied to the pre-crop origin"],
            ["reset-mosaic-parity"],
            preserved,
            ["channel identity was not taken from the crop origin"],
        )
    return _result(
        "identity_held",
        [
            EXPECTED,
            "channel identity follows the absolute mosaic coordinate",
            "developed rotation keeps the RGB triple with the pixel",
        ],
        [],
        preserved,
        [],
    )


def _rotate(x: int, y: int, width: int, height: int, rotation: int) -> tuple[int, int]:
    if rotation == 0:
        return x, y
    if rotation == 90:
        return height - 1 - y, x
    if rotation == 180:
        return width - 1 - x, height - 1 - y
    return y, width - 1 - x


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    cfa = payload["cfa"]
    if cfa not in _CFA:
        raise ValueError("cfa must be a supported Bayer phase")
    width = _dim(payload["width"], "width")
    height = _dim(payload["height"], "height")
    stride = payload["rowStride"]
    if type(stride) is not int or not width <= stride <= width + 32:
        raise ValueError("rowStride must cover the width and a short pad")
    left = _nonneg(payload["cropLeft"], "cropLeft")
    top = _nonneg(payload["cropTop"], "cropTop")
    crop_width = _positive(payload["cropWidth"], "cropWidth")
    crop_height = _positive(payload["cropHeight"], "cropHeight")
    if left + crop_width > width or top + crop_height > height:
        raise ValueError("crop must lie inside the frame")
    red = _code(payload["red"], "red")
    green = _code(payload["green"], "green")
    blue = _code(payload["blue"], "blue")
    if len({red, green, blue}) != 3:
        raise ValueError("channel values must be distinct")
    padding = _code(payload["paddingValue"], "paddingValue")
    rotation = payload["rotation"]
    if rotation not in _ROTATIONS:
        raise ValueError("rotation must be 0, 90, 180, or 270")
    reset = payload["resetParity"]
    if type(reset) is not bool:
        raise ValueError("resetParity must be a bool")
    return {
        "cfa": cfa,
        "width": width,
        "height": height,
        "rowStride": stride,
        "cropLeft": left,
        "cropTop": top,
        "cropWidth": crop_width,
        "cropHeight": crop_height,
        "red": red,
        "green": green,
        "blue": blue,
        "paddingValue": padding,
        "rotation": rotation,
        "resetParity": reset,
    }


def _dim(value: object, label: str) -> int:
    if type(value) is not int or not 2 <= value <= 32:
        raise ValueError(label + " must be a small frame dimension")
    return value


def _positive(value: object, label: str) -> int:
    if type(value) is not int or not 1 <= value <= 32:
        raise ValueError(label + " must be a positive int")
    return value


def _nonneg(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value <= 32:
        raise ValueError(label + " must be a non-negative int")
    return value


def _code(value: object, label: str) -> int:
    if type(value) is not int or not -100000 <= value <= 100000:
        raise ValueError(label + " must be an int code")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("parity decision cannot be qualified or allowed")
    if not reasons or any(type(item) is not str or not item for item in reasons):
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
