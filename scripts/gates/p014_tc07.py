"""TC-P014-07 codec interface asymmetry.

Qualify each codec interface independently. Main10 advertising does not imply
P010 Image support. A usable ten-bit surface stays preserved when Image is
unusable. The advertised stream size is always retained.
"""

from __future__ import annotations

CASE_ID = "TC-P014-07"
INTERVENTION = (
    "Expose one usable ten-bit input interface while another interface on the same codec is unavailable."
)
EXPECTED = (
    "Qualify each interface independently and retain useful alternatives without "
    "hidden precision downgrade."
)
NEGATIVE = "Main10 advertising must not imply P010 Image support or arbitrary surface conversion."
INTERFACE_NAMES = ("surface", "byte_buffer", "image", "encoder", "decoder")
_INTERFACE_FIELDS = ("name", "usable", "tenBit")
_PAYLOAD_KEYS = ("interfaces", "main10Advertised", "advertisedSize")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("partial", "qualified", "unavailable")
_FALSE_IMAGE_CLAIM = "main10-implies-p010-image"


def evaluate(payload: dict) -> dict:
    """Qualify codec interfaces without treating Main10 as P010 Image support.

    Returns exactly caseId, decision, reasons, rejectedClaims,
    preservedResults, and openQuestions. Raises ValueError if payload is
    invalid. decision is partial when usability is mixed, qualified when
    every listed interface is usable, and unavailable when none are.
    """
    interfaces, main10, advertised_size = _payload(payload)
    usable = [item["name"] for item in interfaces if item["usable"]]
    unusable = [item["name"] for item in interfaces if not item["usable"]]
    image_unusable = any(item["name"] == "image" and not item["usable"] for item in interfaces)

    if usable and unusable:
        decision = "partial"
    elif usable:
        decision = "qualified"
    else:
        decision = "unavailable"

    rejected = list(unusable)
    if main10 and image_unusable:
        rejected.append(_FALSE_IMAGE_CLAIM)
        if decision == "qualified":
            decision = "partial"

    preserved = list(usable)
    for item in interfaces:
        if item["name"] == "surface" and item["usable"] and item["tenBit"]:
            if "surface" not in preserved:
                preserved.insert(0, "surface")
    preserved.append(advertised_size)

    reasons = _reasons(decision, interfaces, main10, image_unusable)
    if main10 and image_unusable and decision == "qualified":
        raise ValueError("Main10 advertising must not qualify P010 Image support")
    if decision not in _DECISIONS:
        raise ValueError("invalid decision")

    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": [],
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result


def _reasons(
    decision: str,
    interfaces: list[dict],
    main10: bool,
    image_unusable: bool,
) -> list[str]:
    if decision == "qualified":
        reasons = ["every listed codec interface is usable"]
    elif decision == "partial":
        reasons = ["codec interfaces are qualified independently"]
    else:
        reasons = ["no listed codec interface is usable"]
    if main10 and image_unusable:
        reasons.append(
            "main10-implies-p010-image: Main10 advertising does not imply P010 Image support"
        )
    surface = next((item for item in interfaces if item["name"] == "surface"), None)
    image = next((item for item in interfaces if item["name"] == "image"), None)
    if (
        surface is not None
        and surface["usable"]
        and surface["tenBit"]
        and image is not None
        and not image["usable"]
    ):
        reasons.append("usable ten-bit surface is preserved while image is unusable")
    eight_bit = [item["name"] for item in interfaces if item["usable"] and not item["tenBit"]]
    if eight_bit:
        names = ", ".join(eight_bit)
        reasons.append(
            f"no hidden precision downgrade: {names} usable without ten-bit is not upgraded"
        )
    if not reasons:
        raise ValueError("reasons required")
    return reasons


def _payload(payload: object) -> tuple[list[dict], bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("payload keys must be interfaces, main10Advertised, and advertisedSize")
    interfaces = payload["interfaces"]
    if not isinstance(interfaces, list) or not interfaces:
        raise ValueError("interfaces must be a non-empty list")
    parsed = [_interface(item) for item in interfaces]
    names = [item["name"] for item in parsed]
    if len(names) != len(set(names)):
        raise ValueError("interface names must be unique")
    main10 = payload["main10Advertised"]
    if not isinstance(main10, bool):
        raise ValueError("main10Advertised must be a bool")
    advertised_size = payload["advertisedSize"]
    if not isinstance(advertised_size, str) or not advertised_size:
        raise ValueError("advertisedSize must be a non-empty string")
    return parsed, main10, advertised_size


def _interface(item: object) -> dict:
    if not isinstance(item, dict):
        raise ValueError("interface must be a dict")
    if set(item) != set(_INTERFACE_FIELDS):
        raise ValueError("interface fields must be name, usable, and tenBit")
    name = item["name"]
    if name not in INTERFACE_NAMES:
        raise ValueError("interface name must be surface, byte_buffer, image, encoder, or decoder")
    if not isinstance(item["usable"], bool):
        raise ValueError("usable must be a bool")
    if not isinstance(item["tenBit"], bool):
        raise ValueError("tenBit must be a bool")
    return {"name": name, "usable": item["usable"], "tenBit": item["tenBit"]}
