"""TC-P013-07 codec interface asymmetry.

Qualify each codec interface on its own. Main10 advertising does not imply
P010 Image support or arbitrary surface conversion. A usable ten-bit surface
stays available when Image is not. Eight-bit usability is not upgraded.
"""

from __future__ import annotations

CASE_ID = "TC-P013-07"
INTERVENTION = (
    "Expose one usable ten-bit input interface while another interface on the "
    "same codec is unavailable."
)
EXPECTED = (
    "Qualify each interface independently and retain useful alternatives "
    "without hidden precision downgrade."
)
NEGATIVE = (
    "Main10 advertising must not imply P010 Image support or arbitrary "
    "surface conversion."
)
INTERFACE_NAMES = ("surface", "byte_buffer", "image", "encoder", "decoder")
_INTERFACE_FIELDS = ("name", "usable", "tenBit")
_PAYLOAD_KEYS = (
    "codecName",
    "profile",
    "interfaces",
    "main10Advertised",
    "soleMain10Criterion",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("partial", "interface_specific", "unavailable", "rejected")
_FALSE_IMAGE_CLAIM = "main10-implies-p010-image"
_FALSE_CONVERSION = "arbitrary-surface-conversion"
_MUTANT_CLAIM = "main10-as-sole-p010-criterion"


def evaluate(payload: dict) -> dict:
    """Qualify codec interfaces without treating Main10 as P010 Image support."""
    codec_name, profile, interfaces, main10, sole = _payload(payload)
    usable = [item["name"] for item in interfaces if item["usable"]]
    unusable = [item["name"] for item in interfaces if not item["usable"]]
    image_unusable = any(item["name"] == "image" and not item["usable"] for item in interfaces)
    preserved = list(usable)
    rejected = list(unusable)
    reasons = [
        f"codec {codec_name} profile {profile}",
        "codec interfaces are qualified independently",
        INTERVENTION,
    ]
    open_questions: list[str] = []

    if sole:
        decision = "rejected"
        rejected.insert(0, _MUTANT_CLAIM)
        reasons.append("advertised Main10 profile is not the sole P010 acceptance criterion")
        if main10 and image_unusable:
            rejected.append(_FALSE_IMAGE_CLAIM)
            rejected.append(_FALSE_CONVERSION)
            reasons.append(NEGATIVE)
        elif main10:
            rejected.append(_FALSE_CONVERSION)
            reasons.append("Main10 advertising is not arbitrary surface conversion")
        for item in interfaces:
            if not item["usable"] and item["name"] in preserved:
                raise ValueError("unusable interface must not be preserved")
    elif usable and unusable:
        decision = "partial"
    elif usable:
        decision = "interface_specific"
        reasons.append("every listed interface was checked on its own")
        reasons.append("interface_specific is not ten-bit fidelity")
    else:
        decision = "unavailable"
        reasons.append("no listed codec interface is usable")

    if not sole and main10 and image_unusable:
        rejected.append(_FALSE_IMAGE_CLAIM)
        rejected.append(_FALSE_CONVERSION)
        reasons.append(NEGATIVE)
        if decision in {"qualified", "allowed", "interface_specific"} and not usable:
            decision = "unavailable"

    surface = next((item for item in interfaces if item["name"] == "surface"), None)
    image = next((item for item in interfaces if item["name"] == "image"), None)
    if (
        surface is not None
        and surface["usable"]
        and surface["tenBit"]
        and image is not None
        and not image["usable"]
    ):
        reasons.append("usable ten-bit surface is retained while P010 Image is unavailable")
        if "surface" not in preserved:
            preserved.insert(0, "surface")

    eight_bit = [item["name"] for item in interfaces if item["usable"] and not item["tenBit"]]
    if eight_bit:
        names = ", ".join(eight_bit)
        reasons.append(
            f"no hidden precision downgrade: {names} usable without ten-bit is not upgraded"
        )
        for name in eight_bit:
            if f"ten-bit:{name}" in preserved:
                raise ValueError("eight-bit interface must not be upgraded")

    if not preserved:
        preserved = [f"codec:{codec_name}:{profile}"]

    if main10 and image_unusable and "image" in preserved:
        raise ValueError("Main10 advertising must not imply P010 Image support")
    if sole and decision in {"qualified", "allowed", "interface_specific"}:
        raise ValueError("sole Main10 criterion must be rejected")
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P013-07 must not yield qualified or allowed")
    if decision not in _DECISIONS:
        raise ValueError("invalid decision")
    if not reasons:
        raise ValueError("reasons required")
    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object) -> tuple[str, str, list[dict], bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError(
            "payload keys must be codecName, profile, interfaces, "
            "main10Advertised, and soleMain10Criterion"
        )
    codec_name = payload["codecName"]
    profile = payload["profile"]
    for label, value in (("codecName", codec_name), ("profile", profile)):
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError(f"{label} must be a non-empty string")
    interfaces = payload["interfaces"]
    if not isinstance(interfaces, list) or not interfaces:
        raise ValueError("interfaces must be a non-empty list")
    parsed = [_interface(item) for item in interfaces]
    names = [item["name"] for item in parsed]
    if len(names) != len(set(names)):
        raise ValueError("interface names must be unique")
    main10 = payload["main10Advertised"]
    sole = payload["soleMain10Criterion"]
    if type(main10) is not bool:
        raise ValueError("main10Advertised must be a bool")
    if type(sole) is not bool:
        raise ValueError("soleMain10Criterion must be a bool")
    return codec_name, profile, parsed, main10, sole


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


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": open_questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
