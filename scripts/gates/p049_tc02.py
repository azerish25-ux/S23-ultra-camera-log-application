"""TC-P049-02 CFA and crop parity.

Intervention: Use every supported mosaic pattern with odd and even crop
origins and distinct channel values.
Expected: Maintain correct channel identity and interpolation coordinates
across the transformed image.
Negative: Resetting mosaic parity after a crop must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P049-02"
INTERVENTION = (
    "Use every supported mosaic pattern with odd and even crop origins and distinct "
    "channel values."
)
EXPECTED = (
    "Maintain correct channel identity and interpolation coordinates across the "
    "transformed image."
)
NEGATIVE = "Resetting mosaic parity after a crop must fail."

_CFA = ("RGGB", "GRBG", "GBRG", "BGGR")
_SITES = ("interior", "border", "padded-row", "rotated")
_PHASE = {
    "RGGB": {(0, 0): "R", (1, 0): "G", (0, 1): "G", (1, 1): "B"},
    "GRBG": {(0, 0): "G", (1, 0): "R", (0, 1): "B", (1, 1): "G"},
    "GBRG": {(0, 0): "G", (1, 0): "B", (0, 1): "R", (1, 1): "G"},
    "BGGR": {(0, 0): "B", (1, 0): "G", (0, 1): "G", (1, 1): "R"},
}
_PAYLOAD_KEYS = ("cfa", "cropLeft", "cropTop", "x", "y", "site", "resetParityAfterCrop")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "channel_held")
_FORBIDDEN = {"qualified", "allowed"}


def channel_at(cfa: str, x: int, y: int) -> str:
    """Sensor-coordinate channel. Subtracting the crop origin is the mutant."""
    return _PHASE[cfa][(x % 2, y % 2)]


def evaluate(payload: dict) -> dict:
    """Keep mosaic phase in sensor coordinates. A crop must not reset it."""
    cfa, left, top, x, y, site, reset = _payload(payload)
    sensor = channel_at(cfa, x, y)
    reset_channel = channel_at(cfa, x - left, y - top)
    preserved = [
        f"cfa:{cfa}",
        f"crop:{left}+{top}",
        f"pixel:{x},{y}",
        f"channel:{sensor}",
        f"interp:{x},{y}",
        f"site:{site}",
    ]
    reasons = [EXPECTED, "channel identity uses sensor coordinates"]
    if reset:
        rejected = ["mosaic-parity-reset"]
        if reset_channel != sensor:
            rejected.append(f"channel-disagreement:{reset_channel}")
        reasons.append(NEGATIVE)
        reasons.append(f"crop-relative phase would report {reset_channel}")
        questions = ["mosaic parity was not reset to the crop origin"]
        decision = "rejected"
    else:
        rejected = []
        questions = ["interpolation coordinates stay on the sensor grid"]
        decision = "channel_held"
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, int, int, int, int, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    cfa = payload["cfa"]
    if cfa not in _CFA:
        raise ValueError("cfa is unknown")
    left = _nonneg(payload["cropLeft"], "cropLeft")
    top = _nonneg(payload["cropTop"], "cropTop")
    x = _nonneg(payload["x"], "x")
    y = _nonneg(payload["y"], "y")
    if x < left or y < top:
        raise ValueError("pixel is outside the crop")
    site = payload["site"]
    if site not in _SITES:
        raise ValueError("site is unknown")
    reset = payload["resetParityAfterCrop"]
    if type(reset) is not bool:
        raise ValueError("resetParityAfterCrop must be a bool")
    return cfa, left, top, x, y, site, reset


def _nonneg(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(label + " must be a non-negative int")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("decision cannot be qualified or allowed")
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
