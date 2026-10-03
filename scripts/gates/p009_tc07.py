"""TC-P009-07 codec interface asymmetry.

Each codec interface is qualified on its own. Main10 advertising does not
imply P010 Image support. A usable ten-bit surface or byte buffer is kept
even when Image is unusable; precision is not silently downgraded.
"""

from __future__ import annotations

CASE_ID = "TC-P009-07"
INTERFACE_NAMES = ("surface", "byte_buffer", "image", "encoder", "decoder")
_INTERFACE_FIELDS = ("name", "usable", "tenBit")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_MAIN10_IMAGE_CLAIM = "main10-implies-p010-image"


def evaluate(payload: dict) -> dict:
    """Qualify codec interfaces independently.

    Returns exactly caseId, decision, reasons, rejectedClaims,
    preservedResults, and openQuestions. Raises ValueError if payload is
    invalid. Decision is partial, qualified, or unavailable. Main10 plus an
    unusable image interface is never qualified.
    """
    interfaces, main10 = _payload(payload)
    usable = [item["name"] for item in interfaces if item["usable"]]
    unusable = [item["name"] for item in interfaces if not item["usable"]]
    image_unusable = any(item["name"] == "image" and not item["usable"] for item in interfaces)
    main10_does_not_imply_image = main10 and image_unusable

    if usable and unusable:
        decision = "partial"
    elif usable:
        decision = "qualified"
    else:
        decision = "unavailable"

    if main10_does_not_imply_image and decision == "qualified":
        raise ValueError("main10 advertising must not qualify an unusable image interface")

    reasons = [_decision_reason(decision)]
    if main10_does_not_imply_image:
        reasons.append("main10 advertising does not imply p010 image support")
        unusable.append(_MAIN10_IMAGE_CLAIM)

    kept_tenbit = [
        item["name"]
        for item in interfaces
        if item["usable"] and item["tenBit"] and item["name"] in {"surface", "byte_buffer"}
    ]
    if image_unusable and kept_tenbit:
        reasons.append(
            f"{', '.join(kept_tenbit)} retained without precision downgrade"
        )

    if not reasons:
        raise ValueError("reasons required")

    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": unusable,
        "preservedResults": usable,
        "openQuestions": [],
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result


def _decision_reason(decision: str) -> str:
    if decision == "qualified":
        return "every codec interface qualified independently"
    if decision == "partial":
        return "codec interfaces qualified independently"
    return "no usable codec interface"


def _payload(payload: object) -> tuple[list[dict], bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != {"interfaces", "main10Advertised"}:
        raise ValueError("payload keys must be interfaces and main10Advertised")
    main10 = payload["main10Advertised"]
    if not isinstance(main10, bool):
        raise ValueError("main10Advertised must be a bool")
    interfaces = payload["interfaces"]
    if not isinstance(interfaces, list) or not interfaces:
        raise ValueError("interfaces must be a non-empty list")
    parsed = [_interface(item) for item in interfaces]
    names = [item["name"] for item in parsed]
    if len(names) != len(set(names)):
        raise ValueError("interface names must be unique")
    return parsed, main10


def _interface(item: object) -> dict:
    if not isinstance(item, dict):
        raise ValueError("interface must be a dict")
    if set(item) != set(_INTERFACE_FIELDS):
        raise ValueError("invalid interface fields")
    name = item["name"]
    if name not in INTERFACE_NAMES:
        raise ValueError("name must be surface, byte_buffer, image, encoder, or decoder")
    if not isinstance(item["usable"], bool):
        raise ValueError("usable must be a bool")
    if not isinstance(item["tenBit"], bool):
        raise ValueError("tenBit must be a bool")
    return item
