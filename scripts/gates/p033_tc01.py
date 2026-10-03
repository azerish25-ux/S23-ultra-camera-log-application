"""TC-P033-01 packing boundary corruption.

Perturb packed sample boundaries, row padding, or crop parity while keeping
plausible image dimensions. Decode only a declared supported layout. Reject
anything else before color. Treating every RAW buffer as contiguous
sixteen-bit pixels is the negative control and is never a success.
"""

from __future__ import annotations

CASE_ID = "TC-P033-01"
INTERVENTION = (
    "Perturb packed sample boundaries, row padding, or crop parity while preserving "
    "plausible image dimensions."
)
EXPECTED = (
    "Decode using the declared layout or reject the unsupported arrangement before processing color."
)
NEGATIVE = "Treating every RAW buffer as contiguous sixteen-bit pixels must fail."
REPEATS = ("minimum and maximum codes", "odd crops", "all supported CFA patterns")
CFAS = ("RGGB", "GRBG", "GBRG", "BGGR")
PACKINGS = ("uint16le-tight", "uint16le-padded", "packed10")
CODES = ("min", "max", "mid")
_PAYLOAD_KEYS = (
    "width",
    "height",
    "cfa",
    "packing",
    "rowPaddingBytes",
    "crop",
    "sampleCode",
    "assumeContiguous16",
    "inventory",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_LIMIT = 16384


def evaluate(payload: dict) -> dict:
    """Accept a declared layout, or reject it before color."""
    data = _payload(payload)
    supported, detail = _layout(data)
    rejected: list[str] = []
    reasons = ["sample code " + data["sampleCode"], "layout " + data["packing"]]
    if data["assumeContiguous16"]:
        rejected.append("contiguous-sixteen-bit")
        reasons.append(NEGATIVE)
    if not supported:
        rejected.append("unsupported-layout")
        reasons.append("rejected before processing color: " + detail)
        reasons.append(EXPECTED)
    if rejected:
        decision = "rejected"
    else:
        decision = "layout_declared"
        reasons.append(EXPECTED)
        reasons.append("layout_declared is not color processing and not physical qualification")
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P033-01 must not yield qualified or allowed")
    questions = ["color processing was not started"] if decision == "rejected" else []
    return _result(decision, reasons, rejected, _preserved(data), questions)


def _layout(data: dict) -> tuple[bool, str]:
    packing = data["packing"]
    padding = data["rowPaddingBytes"]
    if packing == "packed10":
        return False, "packed10"
    if packing == "uint16le-tight" and padding != 0:
        return False, "row-padding"
    if packing == "uint16le-padded" and padding <= 0:
        return False, "row-padding"
    if data["width"] % 2 or data["height"] % 2:
        return False, "sample-boundary"
    crop = data["crop"]
    if crop != "full":
        left, top, width, height = crop
        if left % 2 or top % 2 or width % 2 or height % 2:
            return False, "odd-crop"
        if width <= 0 or height <= 0 or left + width > data["width"] or top + height > data["height"]:
            return False, "crop-outside"
    return True, "declared"


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    width = _positive(payload["width"], "width")
    height = _positive(payload["height"], "height")
    if width > _LIMIT or height > _LIMIT:
        raise ValueError("dimensions exceed the plausible host limit")
    cfa = payload["cfa"]
    if cfa not in CFAS:
        raise ValueError("cfa must be a supported Bayer pattern")
    packing = payload["packing"]
    if packing not in PACKINGS:
        raise ValueError("packing is not in the host vocabulary")
    padding = payload["rowPaddingBytes"]
    if type(padding) is not int or padding < 0:
        raise ValueError("rowPaddingBytes must be a non-negative int")
    crop = _crop(payload["crop"], width, height)
    code = payload["sampleCode"]
    if code not in CODES:
        raise ValueError("sampleCode must be min, max, or mid")
    return {
        "width": width,
        "height": height,
        "cfa": cfa,
        "packing": packing,
        "rowPaddingBytes": padding,
        "crop": crop,
        "sampleCode": code,
        "assumeContiguous16": _bool(payload["assumeContiguous16"], "assumeContiguous16"),
        "inventory": _tokens(payload["inventory"], "inventory"),
    }


def _crop(value: object, width: int, height: int) -> str | tuple[int, int, int, int]:
    if value == "full":
        return "full"
    if not isinstance(value, str):
        raise ValueError("crop must be full or left,top,width,height")
    parts = value.split(",")
    if len(parts) != 4:
        raise ValueError("crop must be full or left,top,width,height")
    numbers = []
    for part in parts:
        if not part.isdigit() or (len(part) > 1 and part[0] == "0"):
            raise ValueError("crop components must be canonical non-negative integers")
        numbers.append(int(part))
    left, top, crop_width, crop_height = numbers
    if left + crop_width > width or top + crop_height > height:
        raise ValueError("crop must lie inside the image")
    if crop_width <= 0 or crop_height <= 0:
        raise ValueError("crop extent must be positive")
    return (left, top, crop_width, crop_height)


def _preserved(data: dict) -> list[str]:
    crop = data["crop"]
    crop_text = "full" if crop == "full" else ",".join(str(part) for part in crop)
    preserved = list(data["inventory"])
    preserved.extend([
        str(data["width"]) + "x" + str(data["height"]),
        "cfa:" + data["cfa"],
        "packing:" + data["packing"],
        "padding:" + str(data["rowPaddingBytes"]),
        "crop:" + crop_text,
        "code:" + data["sampleCode"],
    ])
    return preserved


def _positive(value: object, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive int")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _tokens(value: object, name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    items = []
    for item in value:
        if not isinstance(item, str) or not item or item != item.strip():
            raise ValueError(f"{name} items must be non-empty strings")
        items.append(item)
    if len(items) != len(set(items)):
        raise ValueError(f"{name} must be unique")
    return items


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P033-01 must not yield qualified or allowed")
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
