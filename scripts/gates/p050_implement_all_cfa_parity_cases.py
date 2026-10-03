#!/usr/bin/env python3
"""P050 CFA parity across crops and rotations.

The original CFA origin is carried through cropping and demosaic. Synthetic
planes use distinct constant red, green, and blue codes. Developed RGB may
rotate only after the source mosaic has been interpreted. Resetting the CFA
origin to the top-left of every cropped buffer is the rejected mutant.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P050-01 through TC-P050-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P050"
CASE_ID = "P050"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-cfa-parity-fixture"
METHOD = (
    "Carry the original CFA origin through cropping and demosaic. Test RGGB, "
    "BGGR, GRBG, and GBRG using synthetic planes with distinct constant values. "
    "Rotate developed RGB only after the source mosaic interpretation is "
    "established unless a separately verified mosaic transform is used."
)
FIXTURE = (
    "An odd-offset crop of each CFA with red, green, and blue codes deliberately "
    "far apart."
)
ORACLE = (
    "The resulting channel identity matches the independent fixture without "
    "red-blue swaps or green checkerboards."
)
MUTANT = "Reset CFA origin to the top-left of every cropped buffer."

CFAS = ("RGGB", "BGGR", "GRBG", "GBRG")
# Absolute sensor phase. Index (y % 2) * 2 + (x % 2). Not the crop origin.
PHASE_AT = {
    "RGGB": ("R", "G", "G", "B"),
    "BGGR": ("B", "G", "G", "R"),
    "GRBG": ("G", "R", "B", "G"),
    "GBRG": ("G", "B", "R", "G"),
}
ROTATIONS = (0, 90, 180, 270)
ROTATION_ORDER = "developed-after-interpret"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "codes",
    "planes",
}
CODE_KEYS = {"R", "G", "B"}
PLANE_KEYS = {
    "id",
    "cfa",
    "cropLeft",
    "cropTop",
    "width",
    "height",
    "rowPadding",
    "paddingCode",
    "samples",
    "expectedChannels",
    "developedRotation",
    "rotationOrder",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}
_OPEN = (
    "physical S23 CFA unverified",
    "no separately verified mosaic transform",
    "flat synthetic planes are not a measured colour profile",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def _text(value: object, label: str) -> str:
    require(
        isinstance(value, str) and bool(value) and value == value.strip(),
        label + " must be a non-empty string",
    )
    return value


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision not in _FORBIDDEN, "P050 must not decide qualified or allowed")
    require(
        bool(reasons) and all(isinstance(item, str) and item for item in reasons),
        "reasons must be a non-empty list of strings",
    )
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": _dedupe(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def channel_at(cfa: str, x: int, y: int) -> str:
    """CFA channel at an absolute sensor coordinate."""
    require(cfa in PHASE_AT, "unknown CFA")
    require(type(x) is int and type(y) is int and x >= 0 and y >= 0, "coordinate")
    return PHASE_AT[cfa][(y % 2) * 2 + (x % 2)]


def carried_channel(cfa: str, left: int, top: int, x: int, y: int) -> str:
    """Channel in a cropped buffer. (left, top) is the sensor origin of local (0, 0)."""
    require(type(left) is int and type(top) is int and left >= 0 and top >= 0, "crop origin")
    require(type(x) is int and type(y) is int and x >= 0 and y >= 0, "local coordinate")
    return channel_at(cfa, left + x, top + y)


def reset_origin_channel(cfa: str, x: int, y: int) -> str:
    """Mutant label: pretend the cropped buffer's top-left is CFA phase (0, 0)."""
    return channel_at(cfa, x, y)


def channel_grid(cfa: str, width: int, height: int, left: int, top: int) -> list[list[str]]:
    """Row-major channel identity using the carried sensor origin."""
    require(type(width) is int and type(height) is int and width >= 2 and height >= 2, "plane size")
    return [
        [carried_channel(cfa, left, top, x, y) for x in range(width)]
        for y in range(height)
    ]


def synthetic_plane(
    cfa: str,
    width: int,
    height: int,
    left: int,
    top: int,
    codes: dict[str, int],
) -> list[list[int]]:
    """Fill a crop with one constant code per carried channel."""
    grid = channel_grid(cfa, width, height, left, top)
    return [[codes[channel] for channel in row] for row in grid]


def _view_origin(left: int, top: int, reset: bool) -> tuple[int, int]:
    if reset:
        return 0, 0
    return left, top


def partition(
    cfa: str,
    left: int,
    top: int,
    samples: list[list[int]],
    reset: bool = False,
) -> dict[str, list[int]]:
    """Bucket sample codes by a carried or reset phase label."""
    origin_left, origin_top = _view_origin(left, top, reset)
    buckets: dict[str, list[int]] = {"R": [], "G": [], "B": []}
    for y, row in enumerate(samples):
        for x, value in enumerate(row):
            buckets[channel_at(cfa, origin_left + x, origin_top + y)].append(value)
    return buckets


def green_checkerboard(
    cfa: str,
    left: int,
    top: int,
    samples: list[list[int]],
    reset: bool = False,
) -> bool:
    """True when sites labeled green do not share one constant code."""
    greens = partition(cfa, left, top, samples, reset)["G"]
    return len(greens) >= 2 and len(set(greens)) > 1


def red_blue_swap(
    cfa: str,
    left: int,
    top: int,
    samples: list[list[int]],
    codes: dict[str, int],
    reset: bool = False,
) -> bool:
    """True when the red bucket holds the blue code and the blue bucket the red code."""
    buckets = partition(cfa, left, top, samples, reset)
    reds = buckets["R"]
    blues = buckets["B"]
    if not reds or not blues:
        return False
    if len(set(reds)) != 1 or len(set(blues)) != 1:
        return False
    return reds[0] == codes["B"] and blues[0] == codes["R"]


def demosaic(
    cfa: str,
    left: int,
    top: int,
    samples: list[list[int]],
) -> list[list[tuple[int, int, int]]]:
    """Develop a constant-per-channel crop. Mixed buckets are not a colour.

    Missing channels are the unique carried-phase code, not a resample of the
    cropped buffer as if its top-left were phase zero.
    """
    buckets = partition(cfa, left, top, samples, reset=False)
    constants: dict[str, int] = {}
    for channel, values in buckets.items():
        require(bool(values), "missing channel " + channel)
        require(len(set(values)) == 1, "channel " + channel + " is not constant")
        constants[channel] = values[0]
    pixel = (constants["R"], constants["G"], constants["B"])
    return [[pixel for _ in row] for row in samples]


def rotate_developed(
    image: list[list[tuple[int, int, int]]],
    degrees: int,
) -> list[list[tuple[int, int, int]]]:
    """Rotate an already developed RGB image clockwise. The mosaic is not relabeled."""
    require(degrees in ROTATIONS, "developed rotation must be 0, 90, 180, or 270")
    require(image and image[0], "developed image must be non-empty")
    turned = image
    for _ in range(degrees // 90):
        height = len(turned)
        width = len(turned[0])
        turned = [
            [turned[height - 1 - col][row] for col in range(height)]
            for row in range(width)
        ]
    return turned


def _codes(value: object) -> dict[str, int]:
    item = exact_keys(value, CODE_KEYS, "codes")
    parsed: dict[str, int] = {}
    for key in ("R", "G", "B"):
        code = item[key]
        require(type(code) is int and code >= 0, "code " + key + " must be a non-negative int")
        parsed[key] = code
    values = (parsed["R"], parsed["G"], parsed["B"])
    require(len(set(values)) == 3, "red, green, and blue codes must be distinct")
    gaps = [abs(values[i] - values[j]) for i in range(3) for j in range(i + 1, 3)]
    require(min(gaps) >= 100, "channel codes must be far apart")
    return parsed


def _plane(value: object, index: int, codes: dict[str, int], seen: set[str]) -> dict:
    item = exact_keys(value, PLANE_KEYS, f"plane {index}")
    ident = _text(item["id"], f"plane {index} id")
    require(ident not in seen, "duplicate plane id: " + ident)
    seen.add(ident)
    cfa = item["cfa"]
    require(cfa in CFAS, f"plane {index} cfa")
    left = item["cropLeft"]
    top = item["cropTop"]
    width = item["width"]
    height = item["height"]
    require(type(left) is int and type(top) is int and left >= 0 and top >= 0, "crop origin")
    require(type(width) is int and 2 <= width <= 8, "width")
    require(type(height) is int and 2 <= height <= 8, "height")
    require(left % 2 == 1 or top % 2 == 1, "crop offset must be odd on at least one axis")
    padding = item["rowPadding"]
    pad_code = item["paddingCode"]
    require(type(padding) is int and padding >= 0, "rowPadding")
    require(type(pad_code) is int and pad_code >= 0, "paddingCode")
    require(pad_code not in codes.values(), "padding code must not be a channel code")
    samples = item["samples"]
    expected = synthetic_plane(cfa, width, height, left, top, codes)
    require(samples == expected, "samples must be the carried-origin synthetic plane")
    channels = channel_grid(cfa, width, height, left, top)
    require(item["expectedChannels"] == channels, "expectedChannels must use the carried origin")
    require(item["developedRotation"] in ROTATIONS, "developedRotation")
    require(item["rotationOrder"] == ROTATION_ORDER, "rotation must follow mosaic interpretation")
    for row in samples:
        require(pad_code not in row, "padding must stay outside the sample plane")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P050 CFA parity fixture."""
    exact_keys(document, DOCUMENT_KEYS, "cfa parity document")
    require(
        type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
        "schemaVersion must be 1",
    )
    require(document["phase"] == PHASE, "phase must be P050")
    require(document["mapId"] == MAP_ID, "mapId must be s23-cfa-parity-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "cfa parity document needs the P050 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    codes = _codes(document["codes"])
    planes = document["planes"]
    require(type(planes) is list and planes, "planes must be a non-empty list")
    seen: set[str] = set()
    parsed = [_plane(item, index, codes, seen) for index, item in enumerate(planes)]
    present = {item["cfa"] for item in parsed}
    require(present == set(CFAS), "fixture must include an odd-offset crop of each CFA")
    single_axis = any(item["cropLeft"] % 2 != item["cropTop"] % 2 for item in parsed)
    require(single_axis, "fixture must include a single-axis odd crop")


def grid_text(channels: list[list[str]]) -> str:
    return "/".join("".join(row) for row in channels)


def inventory(document: dict) -> list[str]:
    """Evidence kept even when a later check fails."""
    codes = document["codes"]
    rows = [f"codes:R{codes['R']},G{codes['G']},B{codes['B']}"]
    for plane in document["planes"]:
        ident = plane["id"]
        rows.append(
            f"{ident}:{plane['cfa']}@{plane['cropLeft']},{plane['cropTop']}:"
            f"{grid_text(plane['expectedChannels'])}"
        )
        rows.append(f"pad:{ident}:{plane['rowPadding']}:{plane['paddingCode']}")
        rows.append(
            f"rotation:{ident}:{plane['developedRotation']}:{plane['rotationOrder']}"
        )
    return rows


def assess(document: dict) -> dict:
    """Match developed channel identity to the independent fixture.

    Decision is ``matched`` only when every odd-offset crop keeps its carried
    CFA origin, with no red-blue swap and no green checkerboard. It is never
    ``qualified`` or ``allowed``.
    """
    validate_document(document)
    codes = document["codes"]
    expected_rgb = (codes["R"], codes["G"], codes["B"])
    rejected: list[str] = []
    for plane in document["planes"]:
        image = demosaic(plane["cfa"], plane["cropLeft"], plane["cropTop"], plane["samples"])
        rotated = rotate_developed(image, plane["developedRotation"])
        colors = {pixel for row in rotated for pixel in row}
        if colors != {expected_rgb}:
            rejected.append("identity:" + plane["id"])
        if red_blue_swap(
            plane["cfa"], plane["cropLeft"], plane["cropTop"], plane["samples"], codes, False
        ):
            rejected.append("red-blue-swap:" + plane["id"])
        if green_checkerboard(
            plane["cfa"], plane["cropLeft"], plane["cropTop"], plane["samples"], False
        ):
            rejected.append("green-checkerboard:" + plane["id"])
    preserved = inventory(document)
    if rejected:
        decision = "rejected"
        reasons = [ORACLE, "channel identity did not match the independent fixture"]
    else:
        decision = "matched"
        reasons = [
            ORACLE,
            "channel identity matches the independent fixture",
            "no red-blue swap",
            "no green checkerboard",
            "developed RGB rotated only after mosaic interpretation",
            "original CFA origin carried through the odd-offset crop",
        ]
    return _result(decision, reasons, rejected, preserved, list(_OPEN))


def apply_origin_reset(document: dict) -> dict:
    """Reject the mutant that restarts CFA phase at each crop's top-left.

    Carried-origin inventory stays in preservedResults. Reset labels are extra
    evidence of the disagreement, not a replacement colour.
    """
    validate_document(document)
    codes = document["codes"]
    preserved = inventory(document)
    rejected = ["cfa-origin-reset"]
    reasons = [
        MUTANT,
        ORACLE,
        "cropped buffer origin was not treated as CFA phase zero",
    ]
    for plane in document["planes"]:
        reset = channel_grid(plane["cfa"], plane["width"], plane["height"], 0, 0)
        preserved.append(f"reset:{plane['id']}:{grid_text(reset)}")
        if reset != plane["expectedChannels"]:
            reasons.append("origin reset disagrees:" + plane["id"])
        if red_blue_swap(
            plane["cfa"],
            plane["cropLeft"],
            plane["cropTop"],
            plane["samples"],
            codes,
            True,
        ):
            reasons.append("red-blue swap:" + plane["id"])
            rejected.append("red-blue-swap:" + plane["id"])
        if green_checkerboard(
            plane["cfa"], plane["cropLeft"], plane["cropTop"], plane["samples"], True
        ):
            reasons.append("green checkerboard:" + plane["id"])
            rejected.append("green-checkerboard:" + plane["id"])
    return _result("rejected", reasons, rejected, preserved, list(_OPEN))
