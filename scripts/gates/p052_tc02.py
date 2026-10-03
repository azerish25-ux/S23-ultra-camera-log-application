"""TC-P052-02 CFA and crop parity.

Intervention: Use every supported mosaic pattern with odd and even crop
origins and distinct channel values.
Expected: Maintain correct channel identity and interpolation coordinates
across the transformed image.
Negative: Resetting mosaic parity after a crop must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P052-02"
INTERVENTION = (
    "Use every supported mosaic pattern with odd and even crop origins and distinct channel values."
)
EXPECTED = (
    "Maintain correct channel identity and interpolation coordinates across the transformed image."
)
NEGATIVE = "Resetting mosaic parity after a crop must fail."

_CFAS = ("RGGB", "BGGR", "GRBG", "GBRG")
_PHASE = {
    "RGGB": ("R", "G", "G", "B"),
    "BGGR": ("B", "G", "G", "R"),
    "GRBG": ("G", "R", "B", "G"),
    "GBRG": ("G", "B", "R", "G"),
}
_SITES = ("interior", "border", "padded-row", "rotated")
_CHANNELS = ("R", "G", "B")
_PAYLOAD_KEYS = (
    "cfa",
    "cropLeft",
    "cropTop",
    "x",
    "y",
    "site",
    "parityReset",
    "observed",
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
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def channel_at(y: int, x: int, cfa: str) -> str:
    """Absolute Bayer phase. Crop origin is part of the coordinate."""
    return _PHASE[cfa][(y % 2) * 2 + (x % 2)]


def evaluate(payload: dict) -> dict:
    """Keep the carried CFA phase. Resetting it after a crop fails."""
    fields = _payload(payload)
    absolute_y = fields["cropTop"] + fields["y"]
    absolute_x = fields["cropLeft"] + fields["x"]
    expected = channel_at(absolute_y, absolute_x, fields["cfa"])
    reset = channel_at(fields["y"], fields["x"], fields["cfa"])
    preserved = [
        f"cfa:{fields['cfa']}",
        f"crop:{fields['cropLeft']},{fields['cropTop']}",
        f"local:{fields['x']},{fields['y']}",
        f"site:{fields['site']}",
        f"expected:{expected}",
        f"reset-channel:{reset}",
        f"observed:{fields['observed']}",
        f"samples:{fields['red']},{fields['green']},{fields['blue']}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions = ["channel samples stay distinct in the inventory"]
    if fields["parityReset"]:
        decision = "rejected"
        rejected.append("parity-reset")
        reasons.append(NEGATIVE)
        questions.append("mosaic parity reset after the crop was rejected")
    elif fields["observed"] != expected:
        decision = "rejected"
        rejected.append("channel-mismatch")
        reasons.append(f"observed {fields['observed']} is not absolute phase {expected}")
        questions.append("interpolation coordinate kept the carried phase")
    else:
        decision = "aligned"
        reasons.append(f"{fields['cfa']} channel {expected} follows the crop origin")
        questions.append("aligned parity is not a physical CFA measurement")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    cfa = payload["cfa"]
    if cfa not in _CFAS:
        raise ValueError("cfa is unsupported")
    coords = {}
    for name in ("cropLeft", "cropTop", "x", "y"):
        value = payload[name]
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} must be a non-negative int")
        coords[name] = value
    site = payload["site"]
    if site not in _SITES:
        raise ValueError("site is unsupported")
    parity = payload["parityReset"]
    if type(parity) is not bool:
        raise ValueError("parityReset must be a bool")
    observed = payload["observed"]
    if observed not in _CHANNELS:
        raise ValueError("observed channel is unsupported")
    samples = {}
    for name in ("red", "green", "blue"):
        value = payload[name]
        if not isinstance(value, str) or _DECIMAL.fullmatch(value) is None:
            raise ValueError(f"{name} must be a canonical decimal")
        samples[name] = value
    if len({Decimal(samples["red"]), Decimal(samples["green"]), Decimal(samples["blue"])}) != 3:
        raise ValueError("channel values must be distinct")
    return {
        "cfa": cfa,
        "site": site,
        "parityReset": parity,
        "observed": observed,
        **coords,
        **samples,
    }


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P052-02 must not yield qualified or allowed")
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
