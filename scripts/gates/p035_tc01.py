"""TC-P035-01 packing boundary corruption.

Intervention: Perturb packed sample boundaries, row padding, or crop parity
while preserving plausible image dimensions.
Expected: Decode using the declared layout or reject the unsupported
arrangement before processing color.
Negative: Treating every RAW buffer as contiguous sixteen-bit pixels must fail.
"""

from __future__ import annotations

CASE_ID = "TC-P035-01"
INTERVENTION = (
    "Perturb packed sample boundaries, row padding, or crop parity while preserving "
    "plausible image dimensions."
)
EXPECTED = (
    "Decode using the declared layout or reject the unsupported arrangement before "
    "processing color."
)
NEGATIVE = "Treating every RAW buffer as contiguous sixteen-bit pixels must fail."

FORMATS = ("RAW_SENSOR", "RAW10", "RAW12")
CFAS = ("RGGB", "GRBG", "GBRG", "BGGR")
SAMPLES = ("minimum", "maximum", "alternating")
PERTURBATIONS = ("none", "packed_boundary", "row_padding", "crop_parity")
READERS = ("declared", "contiguous_u16")
MAX_CODE = {"RAW_SENSOR": 65535, "RAW10": 1023, "RAW12": 4095}
CFA_PHASE = {
    "RGGB": ("R", "G", "G", "B"),
    "GRBG": ("G", "R", "B", "G"),
    "GBRG": ("G", "B", "R", "G"),
    "BGGR": ("B", "G", "G", "R"),
}
_PAYLOAD_KEYS = (
    "format",
    "width",
    "height",
    "rowStride",
    "cropLeft",
    "cropTop",
    "cfa",
    "sample",
    "perturbation",
    "reader",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "decoded")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Decode a declared layout, or reject a perturbed one before color."""
    fmt, width, height, stride, left, top, cfa, sample, perturbation, reader = _payload(payload)
    preserved = [
        f"format:{fmt}",
        f"size:{width}x{height}",
        f"stride:{stride}",
        f"crop:{left},{top}",
        f"cfa:{cfa}",
        f"sample:{sample}",
    ]
    if reader == "contiguous_u16":
        return _result(
            "rejected",
            [EXPECTED, NEGATIVE, "contiguous sixteen-bit pixels are not a packed layout"],
            ["contiguous-sixteen-bit-pixels"],
            preserved,
            ["color processing not started"],
        )
    if perturbation == "packed_boundary":
        return _result(
            "rejected",
            [EXPECTED, "packed sample boundary is unsupported for the declared layout"],
            ["unsupported-packing-boundary"],
            preserved,
            ["color processing not started"],
        )
    if perturbation == "row_padding":
        return _result(
            "rejected",
            [EXPECTED, "row padding does not form a supported stride"],
            ["unsupported-row-padding"],
            preserved,
            ["color processing not started"],
        )
    if perturbation == "crop_parity":
        return _result(
            "rejected",
            [EXPECTED, "crop parity no longer matches the odd-origin CFA phase"],
            ["unsupported-crop-parity"],
            preserved,
            ["color processing not started"],
        )
    phase = CFA_PHASE[cfa][(top % 2) * 2 + (left % 2)]
    preserved.append(f"cfa-at:{left},{top}={phase}")
    if sample in {"minimum", "alternating"}:
        preserved.append("code:0")
    if sample in {"maximum", "alternating"}:
        preserved.append(f"code:{MAX_CODE[fmt]}")
    return _result(
        "decoded",
        [
            EXPECTED,
            "declared layout accepted before any color transform",
            "odd crop keeps the absolute CFA phase",
        ],
        [],
        preserved,
        ["no demosaic applied", "no color transform applied"],
    )


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    fmt = payload["format"]
    cfa = payload["cfa"]
    sample = payload["sample"]
    perturbation = payload["perturbation"]
    reader = payload["reader"]
    if fmt not in FORMATS or cfa not in CFAS or sample not in SAMPLES:
        raise ValueError("unknown format, cfa, or sample")
    if perturbation not in PERTURBATIONS or reader not in READERS:
        raise ValueError("unknown perturbation or reader")
    width = payload["width"]
    height = payload["height"]
    stride = payload["rowStride"]
    left = payload["cropLeft"]
    top = payload["cropTop"]
    for name, value in (
        ("width", width),
        ("height", height),
        ("rowStride", stride),
        ("cropLeft", left),
        ("cropTop", top),
    ):
        if type(value) is not int or value < 0:
            raise ValueError(name + " must be a non-negative int")
    if height % 2 != 0 or height < 2 or width < 2:
        raise ValueError("plausible even dimensions required")
    if perturbation == "packed_boundary":
        if width % 4 == 0:
            raise ValueError("packed boundary perturbation must break the group width")
    elif width % 4 != 0:
        raise ValueError("declared width must be a multiple of 4")
    packed = _packed_bytes(fmt, width) if width % 4 == 0 else None
    if perturbation == "none":
        if packed is None or not packed < stride <= packed + 32:
            raise ValueError("declared stride must keep padding")
        if left % 2 != 1 or top % 2 != 1:
            raise ValueError("declared crop must begin on an odd coordinate")
        if left >= width or top >= height:
            raise ValueError("crop outside the buffer")
    elif perturbation == "row_padding":
        if packed is None or stride > packed:
            raise ValueError("row padding perturbation must not leave a valid pad")
    elif perturbation == "crop_parity":
        if left % 2 == 1 and top % 2 == 1:
            raise ValueError("crop parity perturbation must flip an odd origin")
    return fmt, width, height, stride, left, top, cfa, sample, perturbation, reader


def _packed_bytes(fmt: str, width: int) -> int:
    if fmt == "RAW_SENSOR":
        return width * 2
    if fmt == "RAW10":
        return (width // 4) * 5
    return (width // 2) * 3


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("packing decision cannot be qualified or allowed")
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
