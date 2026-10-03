"""TC-P015-07 codec interface asymmetry.

Each codec interface is qualified independently. Main10 advertising does not
imply P010 Image support or arbitrary surface conversion. A usable ten-bit
alternative is retained. A hidden precision downgrade is rejected. The
decision is never qualified or allowed.
"""

from __future__ import annotations

CASE_ID = "TC-P015-07"
INTERVENTION = "Expose one usable ten-bit input interface while another interface on the same codec is unavailable."
EXPECTED = (
    "Qualify each interface independently and retain useful alternatives without hidden precision downgrade."
)
NEGATIVE = "Main10 advertising must not imply P010 Image support or arbitrary surface conversion."
REPEAT = "Repeat across surface, byte-buffer, Image, encoder, and decoder paths."
INTERFACE_NAMES = ("surface", "byte_buffer", "image", "encoder", "decoder")
_INTERFACE_FIELDS = ("name", "usable", "tenBit")
_PAYLOAD_KEYS = ("interfaces", "main10Advertised", "precisionDowngrade")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FALSE_IMAGE = "main10-implies-p010-image"
_FALSE_SURFACE = "arbitrary-surface-conversion"
_DOWNGRADE = "hidden-precision-downgrade"
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Qualify codec interfaces without treating Main10 as P010 Image support."""
    interfaces, main10, downgrade = _payload(payload)
    usable = [item["name"] for item in interfaces if item["usable"]]
    unusable = [item["name"] for item in interfaces if not item["usable"]]
    image_unusable = any(item["name"] == "image" and not item["usable"] for item in interfaces)
    ten_bit = [item["name"] for item in interfaces if item["usable"] and item["tenBit"]]
    rejected = list(unusable)
    reasons = ["each interface is qualified independently"]
    if main10 and image_unusable:
        rejected.append(_FALSE_IMAGE)
        rejected.append(_FALSE_SURFACE)
        reasons.append("Main10 advertising does not imply P010 Image support or arbitrary surface conversion")
    if downgrade:
        rejected.append(_DOWNGRADE)
        reasons.append("hidden precision downgrade is rejected")
    if usable and unusable:
        decision = "partial"
        reasons.append("useful alternatives are retained")
    elif usable and not downgrade:
        decision = "interface_specific"
        reasons.append("every listed interface is usable; this is not ten-bit fidelity certification")
    elif usable and downgrade:
        decision = "partial"
        reasons.append("usable interfaces are retained without accepting the downgrade")
    else:
        decision = "unavailable"
        reasons.append("no listed codec interface is usable")
    if main10 and image_unusable and decision in _FORBIDDEN:
        raise ValueError("Main10 advertising must not qualify P010 Image support")
    if downgrade and decision in _FORBIDDEN:
        raise ValueError("hidden precision downgrade must not be qualified or allowed")
    preserved = [item["name"] for item in interfaces]
    if ten_bit and not all(name in preserved for name in ten_bit):
        raise ValueError("usable ten-bit alternatives must be retained")
    return _result(decision, reasons, rejected, preserved, [])


def _payload(payload: object) -> tuple[list[dict], bool, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    main10 = payload["main10Advertised"]
    downgrade = payload["precisionDowngrade"]
    if type(main10) is not bool:
        raise ValueError("main10Advertised must be a bool")
    if type(downgrade) is not bool:
        raise ValueError("precisionDowngrade must be a bool")
    interfaces = payload["interfaces"]
    if not isinstance(interfaces, list) or len(interfaces) != len(INTERFACE_NAMES):
        raise ValueError("interfaces must list surface, byte_buffer, image, encoder, and decoder")
    seen: list[str] = []
    checked: list[dict] = []
    for index, item in enumerate(interfaces):
        if not isinstance(item, dict) or set(item) != set(_INTERFACE_FIELDS):
            raise ValueError(f"interfaces[{index}] has invalid fields")
        name = item["name"]
        if name not in INTERFACE_NAMES:
            raise ValueError(f"interfaces[{index}] name is not a known path")
        if name in seen:
            raise ValueError("duplicate interface: " + name)
        seen.append(name)
        if type(item["usable"]) is not bool or type(item["tenBit"]) is not bool:
            raise ValueError(f"interfaces[{index}] usable and tenBit must be bools")
        if not item["usable"] and item["tenBit"]:
            raise ValueError(f"interfaces[{index}] unavailable interface cannot claim tenBit")
        checked.append(item)
    if set(seen) != set(INTERFACE_NAMES):
        raise ValueError("interfaces must include every codec path")
    return checked, main10, downgrade


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    if decision in _FORBIDDEN or not reasons:
        raise ValueError("invalid decision or reasons")
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
