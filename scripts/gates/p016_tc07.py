"""TC-P016-07 codec interface asymmetry on the first slice.

Each codec interface is judged on its own. Main10 advertising does not imply
P010 Image support or arbitrary surface conversion. A usable ten-bit
alternative stays in the result. This host case does not claim ten-bit
fidelity on a physical S23.
"""

from __future__ import annotations

CASE_ID = "TC-P016-07"
INTERVENTION = (
    "Expose one usable ten-bit input interface while another interface on the same codec is unavailable."
)
EXPECTED = (
    "Qualify each interface independently and retain useful alternatives without hidden precision downgrade."
)
NEGATIVE = "Main10 advertising must not imply P010 Image support or arbitrary surface conversion."
INTERFACE_NAMES = ("surface", "byte_buffer", "image", "encoder", "decoder")
_INTERFACE_FIELDS = ("name", "usable", "tenBit")
_PAYLOAD_KEYS = (
    "interfaces",
    "main10Advertised",
    "surfaceConversionClaimed",
    "advertisedSize",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("partial", "interfaces_usable", "unavailable")
_FALSE_IMAGE_CLAIM = "main10-implies-p010-image"
_FALSE_SURFACE_CLAIM = "arbitrary-surface-conversion"
_ORACLE_PRESERVED = ("file-retained", "playback:separate", "cadence:separate")
_NOT_ENDURANCE = "not-endurance-certified"


def evaluate(payload: dict) -> dict:
    """Judge codec interfaces without treating Main10 as P010 Image support."""
    interfaces, main10, surface_conversion, advertised_size = _payload(payload)
    usable = [item["name"] for item in interfaces if item["usable"]]
    unusable = [item["name"] for item in interfaces if not item["usable"]]
    image_unusable = any(item["name"] == "image" and not item["usable"] for item in interfaces)

    if usable and unusable:
        decision = "partial"
    elif usable:
        decision = "interfaces_usable"
    else:
        decision = "unavailable"

    rejected = list(unusable)
    if main10 and image_unusable:
        rejected.append(_FALSE_IMAGE_CLAIM)
        if decision == "interfaces_usable":
            decision = "partial"
    if surface_conversion:
        rejected.append(_FALSE_SURFACE_CLAIM)
        if decision == "interfaces_usable":
            decision = "partial"

    preserved = list(usable)
    for item in interfaces:
        if item["name"] == "surface" and item["usable"] and item["tenBit"]:
            if "surface" not in preserved:
                preserved.insert(0, "surface")
    preserved.append(advertised_size)

    reasons = _reasons(decision, interfaces, main10, image_unusable, surface_conversion)
    if main10 and image_unusable and decision == "interfaces_usable":
        raise ValueError(NEGATIVE)
    if surface_conversion and decision == "interfaces_usable":
        raise ValueError(NEGATIVE)
    if decision not in _DECISIONS or decision in {"qualified", "allowed"}:
        raise ValueError("invalid decision")
    return _finish(decision, reasons, rejected, preserved, [])


def _reasons(
    decision: str,
    interfaces: list[dict],
    main10: bool,
    image_unusable: bool,
    surface_conversion: bool,
) -> list[str]:
    if decision == "interfaces_usable":
        reasons = ["every listed codec interface is usable on its own"]
    elif decision == "partial":
        reasons = ["codec interfaces are judged independently"]
    else:
        reasons = ["no listed codec interface is usable"]
    if main10 and image_unusable:
        reasons.append(
            "main10-implies-p010-image: Main10 advertising does not imply P010 Image support"
        )
    if surface_conversion:
        reasons.append(
            "arbitrary-surface-conversion: Main10 advertising does not imply arbitrary surface conversion"
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


def _finish(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError(f"{CASE_ID} must not decide qualified or allowed")
    kept = list(preserved)
    for token in _ORACLE_PRESERVED:
        if token not in kept:
            kept.append(token)
    if advertised_missing(kept):
        raise ValueError("advertised size must be preserved")
    questions = list(open_questions)
    if _NOT_ENDURANCE not in questions:
        questions.append(_NOT_ENDURANCE)
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": kept,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result


def advertised_missing(preserved: list[str]) -> bool:
    return not any("x" in item and item not in _ORACLE_PRESERVED and ":" not in item for item in preserved)


def _payload(payload: object) -> tuple[list[dict], bool, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError(
            "payload keys must be interfaces, main10Advertised, surfaceConversionClaimed, and advertisedSize"
        )
    interfaces = payload["interfaces"]
    if not isinstance(interfaces, list) or not interfaces:
        raise ValueError("interfaces must be a non-empty list")
    parsed = [_interface(item) for item in interfaces]
    names = [item["name"] for item in parsed]
    if len(names) != len(set(names)):
        raise ValueError("interface names must be unique")
    main10 = payload["main10Advertised"]
    if type(main10) is not bool:
        raise ValueError("main10Advertised must be a bool")
    surface_conversion = payload["surfaceConversionClaimed"]
    if type(surface_conversion) is not bool:
        raise ValueError("surfaceConversionClaimed must be a bool")
    advertised_size = payload["advertisedSize"]
    if not isinstance(advertised_size, str) or not advertised_size or advertised_size != advertised_size.strip():
        raise ValueError("advertisedSize must be a non-empty string")
    return parsed, main10, surface_conversion, advertised_size


def _interface(item: object) -> dict:
    if not isinstance(item, dict):
        raise ValueError("interface must be a dict")
    if set(item) != set(_INTERFACE_FIELDS):
        raise ValueError("interface fields must be name, usable, and tenBit")
    name = item["name"]
    if name not in INTERFACE_NAMES:
        raise ValueError("interface name must be surface, byte_buffer, image, encoder, or decoder")
    if type(item["usable"]) is not bool:
        raise ValueError("usable must be a bool")
    if type(item["tenBit"]) is not bool:
        raise ValueError("tenBit must be a bool")
    return {"name": name, "usable": item["usable"], "tenBit": item["tenBit"]}
