#!/usr/bin/env python3
"""P051 row-streamed bilinear reference demosaic.

The reference averages in-bounds same-channel neighbors at Chebyshev distance
1 and copies a known site. A missing row is omitted from the average. It is
not replicated, not replaced by zero, and not read from a stale slot.
Interpolation does not apply white-balance gains. Three owned row slots cover
output row y; only source rows in [max(0, y-1), min(height-1, y+1)] are live.

Worked border, RGGB, impulse 12 at (0, 1) and zeros elsewhere, pixel (0, 0):
green neighbors are (0, 1)=12 and (1, 0)=0, so G = 12/2 = 6. The row above
is missing and is not a third sample. Pixel (3, 1) of an impulse 12 at (3, 0)
uses three green neighbors, G = 12/3 = 4. Substituting a stale zero for the
missing row below changes that denominator to 4.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P051-01 through TC-P051-08.
"""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any, Callable


PHASE = "P051"
CASE_ID = "P051"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-row-streamed-bilinear-demosaic-fixture"
METHOD = (
    "Implement an explicitly documented bilinear reference with deterministic "
    "border treatment and row ownership. Separate white balance placement from "
    "interpolation decisions. Test constant fields, impulses, edges, "
    "checkerboards, and crop boundaries."
)
FIXTURE = (
    "A small Bayer impulse near each edge and a uniform color field with "
    "padded source rows."
)
ORACLE = (
    "The output matches hand-derived border values and never reads outside "
    "retained source rows."
)
MUTANT = "Read a missing neighboring row from a stale buffer slot."
BORDER_POLICY = (
    "Bilinear support is the in-bounds same-channel neighbors at Chebyshev "
    "distance 1. A known site is copied, not averaged with other sites of the "
    "same channel. Missing rows and columns are omitted from the average. "
    "There is no replication, mirroring, zero-fill, or stale-slot substitution. "
    "Samples at or beyond the owned width are padding and are not samples."
)
WHITE_BALANCE = (
    "Interpolation does not take white-balance gains. Gains are a separate "
    "per-channel linear stage. Before-interpolation and after-interpolation "
    "placement agree because each output channel mixes only that channel. "
    "Scaling a neighbor by the center site's gain is not the reference."
)
ROW_WINDOW = (
    "Three owned row slots. Output row y may read only source rows in "
    "[max(0, y-1), min(height-1, y+1)]. A released slot is stale and must "
    "not be read. Each retained row is an owned copy of the samples inside "
    "the width; later edits to the source row do not change the slot."
)
CFA = ("RGGB", "GRBG", "GBRG", "BGGR")
KINDS = ("uniform", "impulse", "edge", "checkerboard", "crop")
OPEN = (
    "physical S23 capture unverified",
    "bilinear host fixture is not a native or GPU kernel qualification",
    "white balance gains are not a measured camera neutral",
    "no fixed cadence, sensor-derived Log, ten-bit, film-stock, or cinema-camera claim",
)
_PHASE_TEXT = {
    "RGGB": "RGGB",
    "GRBG": "GRBG",
    "GBRG": "GBRG",
    "BGGR": "BGGR",
}
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "borderPolicy",
    "whiteBalance",
    "rowWindow",
    "scenes",
}
SCENE_KEYS = {
    "id",
    "kind",
    "cfa",
    "width",
    "height",
    "rowStride",
    "cropLeft",
    "cropTop",
    "cropWidth",
    "cropHeight",
    "rows",
    "golden",
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
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_CANON = re.compile(r"-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?")
_MAX_DIM = 32
_MAX_ABS = 1 << 20


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


def channel_at(y: int, x: int, cfa: str) -> str:
    """Bayer channel at an absolute mosaic coordinate. Phase is period 2."""
    require(cfa in CFA, "cfa must be a supported Bayer phase")
    require(type(y) is int and type(x) is int, "coordinates must be ints")
    return _PHASE_TEXT[cfa][(y % 2) * 2 + (x % 2)]


def format_fraction(value: Fraction) -> str:
    """Canonical rational text. Integers have no denominator."""
    number = Fraction(value)
    require(number.denominator > 0, "fraction must be normalized")
    if number.denominator == 1:
        return str(number.numerator)
    return f"{number.numerator}/{number.denominator}"


def format_pixel(pixel: tuple[Fraction, Fraction, Fraction]) -> str:
    return ",".join(format_fraction(channel) for channel in pixel)


def format_image(image: list[list[tuple[Fraction, Fraction, Fraction]]]) -> list[list[str]]:
    return [[format_pixel(pixel) for pixel in row] for row in image]


def _sample_value(value: object, label: str) -> int:
    require(type(value) is int and -_MAX_ABS <= value <= _MAX_ABS, label + " sample out of range")
    return value


class RowWindow:
    """Three owned slots. Released rows stay stale and are not readable."""

    def __init__(self) -> None:
        self.slots: list[list[int] | None] = [None, None, None]
        self.slot_rows: list[int | None] = [None, None, None]
        self.last_stale: list[int] | None = None
        self.reads: list[tuple[int, int, str]] = []

    def open_frame(self) -> None:
        """Drop every slot. A new frame must not see the previous frame."""
        self.slots = [None, None, None]
        self.slot_rows = [None, None, None]
        self.last_stale = None
        self.reads = []

    def load(self, rows: list[list[int]], y: int, width: int, height: int) -> None:
        needed = list(range(max(0, y - 1), min(height, y + 2)))
        for index in range(3):
            held = self.slot_rows[index]
            if held is not None and held not in needed:
                self.last_stale = self.slots[index]
                self.slots[index] = None
                self.slot_rows[index] = None
        for row_index in needed:
            if row_index in self.slot_rows:
                continue
            slot = self.slot_rows.index(None)
            source = rows[row_index]
            require(len(source) >= width, "source row is shorter than the owned width")
            self.slots[slot] = [int(source[col]) for col in range(width)]
            self.slot_rows[slot] = row_index
        live = {item for item in self.slot_rows if item is not None}
        require(live == set(needed), "retained rows drifted from the kernel window")

    def owned(self, y: int, x: int) -> int:
        for index in range(3):
            if self.slot_rows[index] == y:
                slot = self.slots[index]
                require(slot is not None, "empty slot")
                self.reads.append((y, x, "owned"))
                return slot[x]
        raise ValueError("row is not in the retained window")


def _interpolate(
    sample_at: Callable[[int, int], int | None],
    y: int,
    x: int,
    cfa: str,
    channel: str,
) -> Fraction:
    if channel_at(y, x, cfa) == channel:
        owned = sample_at(y, x)
        require(owned is not None, "known site must be an owned sample")
        return Fraction(owned)
    total = Fraction(0)
    count = 0
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            ny = y + dy
            nx = x + dx
            if channel_at(ny, nx, cfa) != channel:
                continue
            sample = sample_at(ny, nx)
            if sample is None:
                continue
            total += Fraction(sample)
            count += 1
    require(count > 0, "bilinear support missing at " + f"{y},{x}:{channel}")
    return total / count


def _reader(
    window: RowWindow,
    width: int,
    height: int,
    *,
    mutant: bool,
):
    def sample_at(y: int, x: int) -> int | None:
        if x < 0 or x >= width or y < 0 or y >= height:
            if mutant and window.last_stale is not None and 0 <= x < width:
                window.reads.append((y, x, "stale"))
                return window.last_stale[x]
            window.reads.append((y, x, "missing"))
            return None
        return window.owned(y, x)

    return sample_at


def stream_demosaic(
    rows: list[list[int]],
    cfa: str,
    width: int,
    height: int,
    *,
    mutant: bool = False,
    initial_stale: list[int] | None = None,
) -> tuple[list[list[tuple[Fraction, Fraction, Fraction]]], list[tuple[int, int, str]]]:
    """Demosaic through a three-row window.

    ``mutant`` reads a missing neighboring row from ``initial_stale`` and, once
    a slot is released, from that stale slot. The honest path never does this.
    """
    require(cfa in CFA, "cfa must be a supported Bayer phase")
    require(type(width) is int and type(height) is int, "width and height must be ints")
    require(2 <= width <= _MAX_DIM and 2 <= height <= _MAX_DIM, "fixture dimensions out of bounds")
    require(len(rows) == height, "row count must equal height")
    require(mutant or initial_stale is None, "honest demosaic has no stale row")
    if initial_stale is not None:
        require(mutant, "initial stale row is the mutant path")
        require(len(initial_stale) == width, "stale row must match the owned width")
    window = RowWindow()
    window.open_frame()
    if initial_stale is not None:
        window.last_stale = [int(item) for item in initial_stale]
    image: list[list[tuple[Fraction, Fraction, Fraction]]] = []
    for y in range(height):
        window.load(rows, y, width, height)
        sample_at = _reader(window, width, height, mutant=mutant)
        row: list[tuple[Fraction, Fraction, Fraction]] = []
        for x in range(width):
            pixel = tuple(_interpolate(sample_at, y, x, cfa, channel) for channel in "RGB")
            row.append(pixel)  # type: ignore[arg-type]
        image.append(row)
    if not mutant:
        require(all(tag != "stale" for _, _, tag in window.reads), "honest path read a stale slot")
        require(
            all(0 <= y < height and 0 <= x < width for y, x, tag in window.reads if tag == "owned"),
            "owned read left the frame",
        )
    return image, list(window.reads)


def demosaic(
    rows: list[list[int]],
    cfa: str,
    width: int | None = None,
    height: int | None = None,
) -> list[list[tuple[Fraction, Fraction, Fraction]]]:
    """Honest bilinear reference. Gains are not applied."""
    require(rows and isinstance(rows, list), "rows must be a non-empty list")
    owned_width = width if width is not None else len(rows[0])
    owned_height = height if height is not None else len(rows)
    image, _reads = stream_demosaic(rows, cfa, owned_width, owned_height, mutant=False)
    return image


def demosaic_stale_mutant(
    rows: list[list[int]],
    cfa: str,
    width: int,
    height: int,
    initial_stale: list[int] | None = None,
) -> list[list[tuple[Fraction, Fraction, Fraction]]]:
    """The rejected reader. Missing rows come from a stale buffer slot."""
    image, _reads = stream_demosaic(
        rows,
        cfa,
        width,
        height,
        mutant=True,
        initial_stale=initial_stale,
    )
    return image


def scale_mosaic(
    rows: list[list[int]],
    cfa: str,
    width: int,
    gains: tuple[Fraction, Fraction, Fraction],
) -> list[list[Fraction]]:
    """Scale each owned sample by its own channel gain. Padding is copied raw."""
    scaled: list[list[Fraction]] = []
    for y, row in enumerate(rows):
        new_row: list[Fraction] = []
        for x in range(width):
            gain = gains["RGB".index(channel_at(y, x, cfa))]
            new_row.append(Fraction(int(row[x])) * gain)
        scaled.append(new_row)
    return scaled


def apply_white_balance(
    image: list[list[tuple[Fraction, Fraction, Fraction]]],
    gains: tuple[Fraction, Fraction, Fraction],
) -> list[list[tuple[Fraction, Fraction, Fraction]]]:
    """Per-channel gains after interpolation. This is not a camera neutral."""
    balanced: list[list[tuple[Fraction, Fraction, Fraction]]] = []
    for row in image:
        balanced.append(
            [
                (
                    pixel[0] * gains[0],
                    pixel[1] * gains[1],
                    pixel[2] * gains[2],
                )
                for pixel in row
            ]
        )
    return balanced


def demosaic_fractions(
    rows: list[list[Fraction]],
    cfa: str,
    width: int,
    height: int,
) -> list[list[tuple[Fraction, Fraction, Fraction]]]:
    """Same bilinear rule for fractional samples (white balance before interpolation)."""
    require(len(rows) == height, "row count must equal height")
    image: list[list[tuple[Fraction, Fraction, Fraction]]] = []

    def sample_at_factory(frame: list[list[Fraction]]):
        def sample_at(y: int, x: int) -> Fraction | None:
            if y < 0 or y >= height or x < 0 or x >= width:
                return None
            return frame[y][x]

        return sample_at

    sample_at = sample_at_factory(rows)
    for y in range(height):
        row: list[tuple[Fraction, Fraction, Fraction]] = []
        for x in range(width):
            pixel = []
            for channel in "RGB":
                if channel_at(y, x, cfa) == channel:
                    pixel.append(Fraction(sample_at(y, x)))  # type: ignore[arg-type]
                    continue
                total = Fraction(0)
                count = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny = y + dy
                        nx = x + dx
                        if channel_at(ny, nx, cfa) != channel:
                            continue
                        sample = sample_at(ny, nx)
                        if sample is None:
                            continue
                        total += sample
                        count += 1
                require(count > 0, "bilinear support missing")
                pixel.append(total / count)
            row.append((pixel[0], pixel[1], pixel[2]))
        image.append(row)
    return image


def demosaic_mixed_gains(
    rows: list[list[int]],
    cfa: str,
    width: int,
    height: int,
    gains: tuple[Fraction, Fraction, Fraction],
) -> list[list[tuple[Fraction, Fraction, Fraction]]]:
    """Rejected placement: every neighbor is scaled by the center site's gain."""
    image: list[list[tuple[Fraction, Fraction, Fraction]]] = []
    for y in range(height):
        row: list[tuple[Fraction, Fraction, Fraction]] = []
        for x in range(width):
            center_gain = gains["RGB".index(channel_at(y, x, cfa))]
            pixel = []
            for channel in "RGB":
                if channel_at(y, x, cfa) == channel:
                    pixel.append(Fraction(int(rows[y][x])) * center_gain)
                    continue
                total = Fraction(0)
                count = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny = y + dy
                        nx = x + dx
                        if not (0 <= ny < height and 0 <= nx < width):
                            continue
                        if channel_at(ny, nx, cfa) != channel:
                            continue
                        total += Fraction(int(rows[ny][nx])) * center_gain
                        count += 1
                require(count > 0, "mixed placement lost support")
                pixel.append(total / count)
            row.append((pixel[0], pixel[1], pixel[2]))
        image.append(row)
    return image


def crop_image(
    image: list[list[tuple[Fraction, Fraction, Fraction]]],
    left: int,
    top: int,
    width: int,
    height: int,
) -> list[list[tuple[Fraction, Fraction, Fraction]]]:
    return [row[left : left + width] for row in image[top : top + height]]


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
    require(decision not in _FORBIDDEN, "P051 must not decide qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons), "reasons required")
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


def _canon_pixel(text: object, label: str) -> str:
    require(isinstance(text, str), label + " golden pixel must be a string")
    parts = text.split(",")
    require(len(parts) == 3, label + " golden pixel must be r,g,b")
    for part in parts:
        require(_CANON.fullmatch(part) is not None, label + " golden component is not canonical")
        if "/" in part:
            numerator, denominator = part.split("/")
            require(Fraction(int(numerator), int(denominator)).denominator != 1, label + " integer must not use a denominator")
            require(int(numerator) != 0, label + " zero must be canonical 0")
    return text


def _scene(value: object, index: int, seen: set[str]) -> dict:
    item = exact_keys(value, SCENE_KEYS, f"scene {index}")
    ident = item["id"]
    require(isinstance(ident, str) and ident and ident == ident.strip(), f"scene {index} id")
    require(ident not in seen, "duplicate scene id")
    seen.add(ident)
    require(item["kind"] in KINDS, f"scene {index} kind")
    require(item["cfa"] in CFA, f"scene {index} cfa")
    width = item["width"]
    height = item["height"]
    stride = item["rowStride"]
    require(type(width) is int and 2 <= width <= _MAX_DIM, f"scene {index} width")
    require(type(height) is int and 2 <= height <= _MAX_DIM, f"scene {index} height")
    require(type(stride) is int and width <= stride <= _MAX_DIM + 16, f"scene {index} stride")
    for key in ("cropLeft", "cropTop"):
        require(type(item[key]) is int and item[key] >= 0, f"scene {index} {key}")
    require(type(item["cropWidth"]) is int and item["cropWidth"] >= 1, f"scene {index} cropWidth")
    require(type(item["cropHeight"]) is int and item["cropHeight"] >= 1, f"scene {index} cropHeight")
    require(item["cropLeft"] + item["cropWidth"] <= width, f"scene {index} crop exceeds width")
    require(item["cropTop"] + item["cropHeight"] <= height, f"scene {index} crop exceeds height")
    rows = item["rows"]
    require(type(rows) is list and len(rows) == height, f"scene {index} rows")
    for y, row in enumerate(rows):
        require(type(row) is list and len(row) == stride, f"scene {index} row {y} length")
        for x, sample in enumerate(row):
            _sample_value(sample, f"scene {index} sample {y},{x}")
    golden = item["golden"]
    require(type(golden) is list and len(golden) == item["cropHeight"], f"scene {index} golden height")
    for y, row in enumerate(golden):
        require(type(row) is list and len(row) == item["cropWidth"], f"scene {index} golden width")
        for x, pixel in enumerate(row):
            _canon_pixel(pixel, f"scene {index} golden {y},{x}")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P051 demosaic fixture."""
    exact_keys(document, DOCUMENT_KEYS, "demosaic document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P051")
    require(document["mapId"] == MAP_ID, "mapId drifted")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and _HEX40.fullmatch(revision or "") is not None, "base revision drifted")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    require(document["borderPolicy"] == BORDER_POLICY, "border policy drifted")
    require(document["whiteBalance"] == WHITE_BALANCE, "white balance note drifted")
    require(document["rowWindow"] == ROW_WINDOW, "row window note drifted")
    scenes = document["scenes"]
    require(type(scenes) is list and scenes, "scenes must be a non-empty list")
    seen: set[str] = set()
    for index, scene in enumerate(scenes):
        _scene(scene, index, seen)
    kinds = {item["kind"] for item in scenes}
    for kind in KINDS:
        require(kind in kinds, "missing scene kind " + kind)
    edges = {"top", "bottom", "left", "right"}
    impulse_ids = {item["id"] for item in scenes if item["kind"] == "impulse"}
    for edge in edges:
        require(any(edge in ident for ident in impulse_ids), "missing impulse near the " + edge + " edge")
    require(any(item["rowStride"] > item["width"] for item in scenes), "fixture needs a padded source row")


def reference_crop(scene: dict) -> list[list[str]]:
    """Honest demosaic of one scene, then the declared crop. No stale reads."""
    image = demosaic(scene["rows"], scene["cfa"], scene["width"], scene["height"])
    cropped = crop_image(
        image,
        scene["cropLeft"],
        scene["cropTop"],
        scene["cropWidth"],
        scene["cropHeight"],
    )
    return format_image(cropped)


def _inventory(document: dict) -> list[str]:
    preserved: list[str] = []
    for scene in document["scenes"]:
        ident = scene["id"]
        preserved.append(f"scene:{ident}")
        preserved.append(f"cfa:{ident}:{scene['cfa']}")
        preserved.append(f"size:{ident}:{scene['width']}x{scene['height']}")
        preserved.append(f"stride:{ident}:{scene['rowStride']}")
        preserved.append(
            f"crop:{ident}:{scene['cropWidth']}x{scene['cropHeight']}+{scene['cropLeft']}+{scene['cropTop']}"
        )
        preserved.append(f"border:{ident}:0,0:{scene['golden'][0][0]}")
        if scene["rowStride"] > scene["width"]:
            preserved.append(f"padding:{ident}")
    return preserved


def assess(document: dict, *, read_stale: bool = False) -> dict[str, Any]:
    """Match stored goldens. The stale-slot reader is rejected and keeps the inventory."""
    validate_document(document)
    preserved = _inventory(document)
    questions = list(OPEN)
    if read_stale:
        return _result(
            "rejected",
            [
                MUTANT,
                ORACLE,
                "a missing neighboring row was not taken from a stale buffer slot",
                "rejecting the mutant does not qualify a device demosaic",
            ],
            ["stale-buffer-slot"],
            preserved,
            questions,
        )
    mismatched: list[str] = []
    for scene in document["scenes"]:
        if reference_crop(scene) != scene["golden"]:
            mismatched.append(scene["id"])
    if mismatched:
        return _result(
            "rejected",
            [ORACLE, "hand-derived border values did not match the stored golden"],
            [f"golden-mismatch:{ident}" for ident in mismatched],
            preserved,
            questions,
        )
    uniform = next(item for item in document["scenes"] if item["kind"] == "uniform" and item["cfa"] == "RGGB")
    gains = (Fraction(2), Fraction(1), Fraction(1, 2))
    honest = demosaic(uniform["rows"], uniform["cfa"], uniform["width"], uniform["height"])
    after = apply_white_balance(honest, gains)
    scaled_rows = scale_mosaic(uniform["rows"], uniform["cfa"], uniform["width"], gains)
    before = demosaic_fractions(scaled_rows, uniform["cfa"], uniform["width"], uniform["height"])
    require(before == after, "before and after white balance diverged on a linear reference")
    mixed = demosaic_mixed_gains(
        uniform["rows"], uniform["cfa"], uniform["width"], uniform["height"], gains
    )
    require(mixed != after, "mixed gain placement must not match the separated reference")
    return _result(
        "matched",
        [
            ORACLE,
            "hand-derived border values matched",
            "missing neighboring rows were omitted, not read from a stale slot",
            "padding beyond the owned width was not sampled",
            "white balance stayed outside the interpolation",
        ],
        [],
        preserved,
        questions,
    )
