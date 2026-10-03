"""TC-P060-04 P010 plane geometry fault.

Intervention: Change row stride, crop, plane arrangement, or sample alignment
while keeping nominal dimensions.
Expected: Handle only explicitly supported layouts with bounds checks and exact
unpacked-code verification.
Negative: Writing ten-bit values into the low six-bit-aligned position must fail.
"""

from __future__ import annotations


CASE_ID = "TC-P060-04"
INTERVENTION = (
    "Change row stride, crop, plane arrangement, or sample alignment while keeping nominal dimensions."
)
EXPECTED = "Handle only explicitly supported layouts with bounds checks and exact unpacked-code verification."
NEGATIVE = "Writing ten-bit values into the low six-bit-aligned position must fail."
REPEAT = "Repeat with padded rows, chroma endpoints, and unsupported plane layouts."

_LAYOUTS = ("420-interleaved", "420-planar", "422-interleaved", "444-planar", "contiguous-guess")
_ALIGNMENTS = ("msb", "lsb")
_PLANES = ("luma", "chroma")
_LUMA_CODES = {"64", "940"}
_CHROMA_CODES = {"64", "512", "960"}
_PAYLOAD_KEYS = (
    "nominalWidth",
    "nominalHeight",
    "rowStride",
    "pixelStride",
    "cropLeft",
    "cropTop",
    "cropRight",
    "cropBottom",
    "planeLayout",
    "alignment",
    "plane",
    "code",
    "guard",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Unpack one crop sample only for an explicit supported P010 layout."""
    geo = _payload(payload)
    preserved = [
        f"nominal:{geo['nominalWidth']}x{geo['nominalHeight']}",
        f"stride:{geo['rowStride']}/{geo['pixelStride']}",
        f"crop:{geo['cropLeft']},{geo['cropTop']},{geo['cropRight']},{geo['cropBottom']}",
        f"layout:{geo['planeLayout']}",
        f"alignment:{geo['alignment']}",
        f"plane:{geo['plane']}",
        f"code:{geo['code']}",
        f"guard:{geo['guard']}",
    ]
    reasons = [EXPECTED, INTERVENTION, f"nominal {geo['nominalWidth']}x{geo['nominalHeight']}"]
    rejected: list[str] = []
    questions = [f"repeat coverage includes {REPEAT}"]
    if geo["planeLayout"] != "420-interleaved":
        rejected.append("unknown-plane-layout")
        reasons.append("unsupported plane layout was rejected and not guessed")
        preserved.append("written:no")
        preserved.append("unpacked:not-guessed")
        return _result("rejected", reasons, rejected, preserved, questions)
    needed = 2 if geo["plane"] == "luma" else 4
    if geo["pixelStride"] != needed:
        rejected.append("unsupported-pixel-stride")
        reasons.append("pixel stride was not rewritten into a guessed contiguous layout")
        preserved.append("written:no")
        return _result("rejected", reasons, rejected, preserved, questions)
    crop_w = geo["cropRight"] - geo["cropLeft"]
    crop_h = geo["cropBottom"] - geo["cropTop"]
    if geo["plane"] == "chroma" and (
        geo["cropLeft"] % 2 or geo["cropTop"] % 2 or crop_w % 2 or crop_h % 2
    ):
        rejected.append("alignment-bounds")
        preserved.append("written:no")
        reasons.append("chroma crop is not aligned to a 4:2:0 site")
        return _result("rejected", reasons, rejected, preserved, questions)
    origin_x = geo["cropLeft"] // (2 if geo["plane"] == "chroma" else 1)
    origin_y = geo["cropTop"] // (2 if geo["plane"] == "chroma" else 1)
    offset = origin_y * geo["rowStride"] + origin_x * geo["pixelStride"]
    row_limit = (origin_y + 1) * geo["rowStride"]
    sample_bytes = 2 if geo["plane"] == "luma" else 4
    nominal_span = geo["nominalWidth"] * (2 if geo["plane"] == "luma" else 2)
    if geo["plane"] == "chroma":
        nominal_span = (geo["nominalWidth"] // 2) * geo["pixelStride"]
    if (
        offset < 0
        or offset + sample_bytes > row_limit
        or geo["rowStride"] < nominal_span
        or geo["rowStride"] % 2 != 0
    ):
        rejected.append("bounds-violation")
        reasons.append("bounds checks failed before a sample was written")
        preserved.append("written:no")
        return _result("rejected", reasons, rejected, preserved, questions)
    padding = geo["rowStride"] - nominal_span
    word = geo["code"] << 6 if geo["alignment"] == "msb" else geo["code"]
    height = geo["nominalHeight"] // 2 if geo["plane"] == "chroma" else geo["nominalHeight"]
    buffer = bytearray([geo["guard"]]) * (geo["rowStride"] * height)
    buffer[offset] = word & 0xFF
    buffer[offset + 1] = (word >> 8) & 0xFF
    unpacked = ((buffer[offset] | (buffer[offset + 1] << 8)) >> 6) & 0x3FF
    pad_index = origin_y * geo["rowStride"] + nominal_span
    padding_ok = padding > 0 and all(buffer[index] == geo["guard"] for index in range(pad_index, row_limit))
    preserved.append(f"packed-word:{word}")
    preserved.append(f"unpacked:{unpacked}")
    preserved.append("padding-untouched:" + ("yes" if padding_ok else "no"))
    preserved.append(f"row-padding:{padding}")
    if geo["alignment"] == "lsb":
        rejected.append("low-six-bit-aligned-position")
        reasons.append(NEGATIVE)
        reasons.append("high-bit unpack did not accept the low six-bit-aligned store")
        return _result("rejected", reasons, rejected, preserved, questions)
    if unpacked != geo["code"] or not padding_ok:
        rejected.append("unpacked-code-mismatch")
        return _result("rejected", reasons, rejected, preserved, questions)
    reasons.append(f"unpacked code {unpacked} matched and padding stayed {geo['guard']}")
    return _result("unpacked", reasons, rejected, preserved, questions)


def _uint(value: object, name: str, limit: int) -> int:
    if not isinstance(value, str) or not value.isdigit() or (len(value) > 1 and value[0] == "0"):
        raise ValueError(f"{name} must be a canonical integer string")
    number = int(value)
    if not 0 <= number <= limit:
        raise ValueError(f"{name} is out of range")
    return number


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    layout = payload["planeLayout"]
    if layout not in _LAYOUTS:
        raise ValueError("planeLayout is unsupported")
    alignment = payload["alignment"]
    if alignment not in _ALIGNMENTS:
        raise ValueError("alignment must be msb or lsb")
    plane = payload["plane"]
    if plane not in _PLANES:
        raise ValueError("plane must be luma or chroma")
    width = _uint(payload["nominalWidth"], "nominalWidth", 32)
    height = _uint(payload["nominalHeight"], "nominalHeight", 32)
    if width % 2 or height % 2 or width < 2 or height < 2:
        raise ValueError("nominal dimensions must be even and at least 2")
    left = _uint(payload["cropLeft"], "cropLeft", 32)
    top = _uint(payload["cropTop"], "cropTop", 32)
    right = _uint(payload["cropRight"], "cropRight", 32)
    bottom = _uint(payload["cropBottom"], "cropBottom", 32)
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError("crop is outside the nominal frame")
    if left == 0 and top == 0 and right == width and bottom == height:
        raise ValueError("crop must be a nonzero inset")
    code_text = payload["code"]
    allowed = _LUMA_CODES if plane == "luma" else _CHROMA_CODES
    if code_text not in allowed:
        raise ValueError("code must be a known endpoint")
    return {
        "nominalWidth": width,
        "nominalHeight": height,
        "rowStride": _uint(payload["rowStride"], "rowStride", 4096),
        "pixelStride": _uint(payload["pixelStride"], "pixelStride", 64),
        "cropLeft": left,
        "cropTop": top,
        "cropRight": right,
        "cropBottom": bottom,
        "planeLayout": layout,
        "alignment": alignment,
        "plane": plane,
        "code": int(code_text),
        "guard": _uint(payload["guard"], "guard", 255),
    }


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P060-04 must not yield qualified or allowed")
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
