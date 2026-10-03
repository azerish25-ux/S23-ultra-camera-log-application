"""TC-P011-07 codec interface asymmetry.

Qualify each codec interface independently. Main10 advertising does not imply
P010 Image support or a hidden ten-bit upgrade. A usable surface stays
preserved when Image is unusable.
"""

from __future__ import annotations

import math


CASE_ID = "TC-P011-07"
INTERVENTION = (
    "Expose one usable ten-bit input interface while another interface on the same codec is unavailable."
)
EXPECTED = (
    "Qualify each interface independently and retain useful alternatives without hidden precision downgrade."
)
NEGATIVE = "Main10 advertising must not imply P010 Image support or arbitrary surface conversion."
INTERFACE_NAMES = ("surface", "byte_buffer", "image", "encoder", "decoder")
_INTERFACE_KEYS = ("name", "usable", "tenBit")
_PAYLOAD_KEYS = (
    "interfaces",
    "main10Advertised",
    "advertisedSize",
    "aeMin",
    "aeMax",
    "requestedFps",
    "containerTimestampsAssigned",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FALSE_IMAGE_CLAIM = "main10-implies-p010-image"
_FORBIDDEN = {"qualified", "allowed", "native_fixed_24"}


def evaluate(payload: dict) -> dict:
    """Keep each codec interface separate. Main10 is not P010 Image support."""
    interfaces, main10, advertised_size, ae_min, ae_max, requested, timestamps = _payload(payload)
    usable = [item["name"] for item in interfaces if item["usable"]]
    unusable = [item["name"] for item in interfaces if not item["usable"]]
    image_usable = any(item["name"] == "image" and item["usable"] for item in interfaces)
    if usable and unusable:
        decision = "partial"
    elif usable:
        decision = "interface_available"
    else:
        decision = "unavailable"
    rejected = list(unusable)
    if main10 and not image_usable:
        rejected.append(_FALSE_IMAGE_CLAIM)
        if decision == "interface_available":
            decision = "partial"
        reasons_false = "Main10 advertising does not imply P010 Image support"
    else:
        reasons_false = ""
    preserved = list(usable)
    for item in interfaces:
        if item["name"] == "surface" and item["usable"] and item["tenBit"] and "surface" not in preserved:
            preserved.insert(0, "surface")
    preserved.append(advertised_size)
    preserved.append(f"ae:{_text(ae_min)}-{_text(ae_max)}")
    preserved.append(f"requested:{_text(requested)}")
    reasons = [f"decision {decision} across {', '.join(item['name'] for item in interfaces)}"]
    if usable:
        reasons.append("usable interfaces retained without a hidden precision downgrade")
    if unusable:
        reasons.append("unusable interfaces stay unqualified")
    if reasons_false:
        reasons.append(reasons_false)
    if timestamps:
        rejected.append("native-fixed-24")
        reasons.append("container timestamps do not certify native fixed 24")
    reasons.append("interface availability is not ten-bit fidelity")
    if main10 and not image_usable and decision == "interface_available":
        raise ValueError(NEGATIVE)
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object):
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    interfaces = payload["interfaces"]
    if not isinstance(interfaces, list) or not interfaces:
        raise ValueError("interfaces must be a non-empty list")
    parsed = [_interface(item) for item in interfaces]
    names = [item["name"] for item in parsed]
    if len(names) != len(set(names)):
        raise ValueError("interface names must be unique")
    main10 = payload["main10Advertised"]
    timestamps = payload["containerTimestampsAssigned"]
    if type(main10) is not bool or type(timestamps) is not bool:
        raise ValueError("main10Advertised and containerTimestampsAssigned must be bools")
    advertised = _size(payload["advertisedSize"])
    ae_min = _rate(payload["aeMin"], "aeMin")
    ae_max = _rate(payload["aeMax"], "aeMax")
    if _cmp(ae_min, ae_max) > 0:
        raise ValueError("aeMin must not exceed aeMax")
    requested = _rate(payload["requestedFps"], "requestedFps")
    return parsed, main10, advertised, ae_min, ae_max, requested, timestamps


def _interface(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != set(_INTERFACE_KEYS):
        raise ValueError("invalid interface fields")
    name = value["name"]
    if name not in INTERFACE_NAMES:
        raise ValueError("interface name must be surface, byte_buffer, image, encoder, or decoder")
    if type(value["usable"]) is not bool or type(value["tenBit"]) is not bool:
        raise ValueError("usable and tenBit must be bools")
    return {"name": name, "usable": value["usable"], "tenBit": value["tenBit"]}


def _size(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("advertisedSize must be a string")
    width, sep, height = value.partition("x")
    if sep != "x" or not width.isdigit() or width[0] == "0" or not height.isdigit() or height[0] == "0":
        raise ValueError("advertisedSize must look like 3840x2160")
    return value


def _rate(value: object, context: str) -> tuple[int, int]:
    if not isinstance(value, dict) or set(value) != {"numerator", "denominator"}:
        raise ValueError(context + " must be a numerator/denominator object")
    numerator = value["numerator"]
    denominator = value["denominator"]
    if type(numerator) is not int or type(denominator) is not int:
        raise ValueError(context + " must use ints")
    if numerator <= 0 or denominator <= 0:
        raise ValueError(context + " must be positive")
    if math.gcd(numerator, denominator) != 1:
        raise ValueError(context + " must be reduced")
    return numerator, denominator


def _text(rate: tuple[int, int]) -> str:
    return f"{rate[0]}/{rate[1]}"


def _cmp(left: tuple[int, int], right: tuple[int, int]) -> int:
    gap = left[0] * right[1] - right[0] * left[1]
    return (gap > 0) - (gap < 0)


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in _FORBIDDEN:
        raise ValueError("TC-P011-07 must not yield qualified, allowed, or native_fixed_24")
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
