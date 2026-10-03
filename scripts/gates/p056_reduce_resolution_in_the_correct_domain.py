#!/usr/bin/env python3
"""P056 scene-linear resolution reduction.

Crop, antialias, and reduce in the scene-linear domain before any log or
display encoding. Geometry changes stay in the provenance. Tiled and untiled
results are compared. Box averaging is not reported as the separable cubic
resample.

The deliberate mutant — average host-logc-toy codes, decode them, and label
that result a scene-linear reduction — is rejected. Numeric agreement on a
constant field does not make the label true.

host-logc-toy is x/(x+1). It is not ARRI LogC, not a sensor log, and not a
film curve. This module does not probe a device, does not qualify a physical
S23, and does not execute TC-P056-01 through TC-P056-08.
"""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any


PHASE = "P056"
CASE_ID = "P056"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-linear-domain-reduction-fixture"
METHOD = (
    "Define crop, antialiasing, and scene-linear reduction before log or display encoding. "
    "Track geometry changes in provenance. Compare tiled and untiled results, and distinguish "
    "simple box averaging from higher-quality resampling choices."
)
FIXTURE = (
    "Alternating dark and bright linear pixels whose arithmetic average differs from the "
    "average of their encoded values."
)
ORACLE = (
    "The output agrees with the declared linear-domain reference and records the actual "
    "reduction ratio."
)
MUTANT = "Average LogC-encoded values and label the result scene-linear reduction."
DOMAIN = "scene-linear"
ENCODING = "host-logc-toy"
BOX = "box"
CUBIC = "cubic"
ANTIALIAS = {BOX: "box-prefilter", CUBIC: "separable-cubic"}
PIPELINE = "crop,antialias,scene-linear-reduction"
LINEAR_DOMAIN = "scene-linear"
LOGC_DOMAIN = "logc"
AVERAGE_DOMAINS = {LINEAR_DOMAIN, LOGC_DOMAIN}
MUTANT_ACCEPT = "scene-linear"
HOST_LIMIT = "host fixture does not qualify a physical S23 or a scene-linear camera master"
CUBIC_TAP = (Fraction(1), Fraction(6), Fraction(1))

HEX40 = re.compile(r"^[0-9a-f]{40}$")
DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "domain",
    "encoding",
    "resampler",
    "antialias",
    "sourceWidth",
    "sourceHeight",
    "outputWidth",
    "outputHeight",
    "crop",
    "pixels",
    "declaredReference",
    "tileSize",
}
CROP_KEYS = {"originX", "originY", "width", "height"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed", MUTANT_ACCEPT}


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


def canonical(value: Fraction) -> str:
    """Render a fraction as a finite decimal or a reduced numerator/denominator."""
    value = Fraction(value.numerator, value.denominator)
    if value < 0:
        return "-" + canonical(-value)
    den = value.denominator
    twos = 0
    fives = 0
    rest = den
    while rest % 2 == 0:
        rest //= 2
        twos += 1
    while rest % 5 == 0:
        rest //= 5
        fives += 1
    if rest != 1:
        return f"{value.numerator}/{value.denominator}"
    digits = max(twos, fives)
    if digits == 0:
        return str(value.numerator)
    scaled = value.numerator * (10 ** digits) // den
    whole = scaled // (10 ** digits)
    frac = scaled % (10 ** digits)
    frac_text = f"{frac:0{digits}d}".rstrip("0")
    if not frac_text:
        return str(whole)
    return f"{whole}.{frac_text}"


def ratio_text(value: Fraction) -> str:
    value = Fraction(value.numerator, value.denominator)
    return f"{value.numerator}/{value.denominator}"


def _decimal(value: object, label: str) -> str:
    require(isinstance(value, str) and DECIMAL.fullmatch(value) is not None, label + " must be a canonical decimal string")
    return value


def _positive_int(value: object, label: str) -> int:
    require(type(value) is int and value > 0, label + " must be a positive int")
    return value


def _nonnegative_int(value: object, label: str) -> int:
    require(type(value) is int and value >= 0, label + " must be a non-negative int")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision not in _FORBIDDEN, "P056 must not decide qualified, allowed, or scene-linear")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons), "reasons must be a non-empty list of strings")
    require(all(isinstance(item, str) and item for item in rejected), "rejectedClaims must be strings")
    require(all(isinstance(item, str) and item for item in preserved), "preservedResults must be strings")
    require(all(isinstance(item, str) and item for item in questions), "openQuestions must be strings")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def encode_host_logc(value: Fraction) -> Fraction:
    """Host compressive code. Not ARRI LogC and not a measured sensor log."""
    require(value >= 0, "host-logc-toy is defined for non-negative linear values")
    return value / (value + 1)


def decode_host_logc(value: Fraction) -> Fraction:
    require(value < 1, "host-logc-toy code must be below one")
    return value / (1 - value)


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is a P056 linear-reduction fixture."""
    exact_keys(document, DOCUMENT_KEYS, "reduction")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P056")
    require(document["mapId"] == MAP_ID, "mapId must be s23-linear-domain-reduction-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "reduction needs the P056 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    require(document["domain"] == DOMAIN, "domain must be scene-linear")
    require(document["encoding"] == ENCODING, "encoding must be host-logc-toy")
    resampler = document["resampler"]
    require(resampler in ANTIALIAS, "resampler must be box or cubic")
    require(document["antialias"] == ANTIALIAS[resampler], "antialias does not match the resampler")
    source_w = _positive_int(document["sourceWidth"], "sourceWidth")
    source_h = _positive_int(document["sourceHeight"], "sourceHeight")
    _positive_int(document["outputWidth"], "outputWidth")
    _positive_int(document["outputHeight"], "outputHeight")
    _positive_int(document["tileSize"], "tileSize")
    crop = exact_keys(document["crop"], CROP_KEYS, "crop")
    origin_x = _nonnegative_int(crop["originX"], "crop originX")
    origin_y = _nonnegative_int(crop["originY"], "crop originY")
    crop_w = _positive_int(crop["width"], "crop width")
    crop_h = _positive_int(crop["height"], "crop height")
    require(origin_x + crop_w <= source_w, "crop exceeds source width")
    require(origin_y + crop_h <= source_h, "crop exceeds source height")
    pixels = document["pixels"]
    require(type(pixels) is list and len(pixels) == source_w * source_h, "pixels must cover the source frame")
    for index, item in enumerate(pixels):
        _decimal(item, f"pixel {index}")
    declared = document["declaredReference"]
    require(
        type(declared) is list and len(declared) == document["outputWidth"] * document["outputHeight"],
        "declaredReference must cover the output",
    )
    for index, item in enumerate(declared):
        _decimal(item, f"declaredReference {index}")


def _frame(document: dict) -> list[list[Fraction]]:
    width = document["sourceWidth"]
    values = [Fraction(item) for item in document["pixels"]]
    return [values[row * width:(row + 1) * width] for row in range(document["sourceHeight"])]


def cropped_frame(document: dict) -> list[list[Fraction]]:
    """Return the cropped scene-linear window. Pixels outside the crop stay in the source inventory."""
    validate_document(document)
    crop = document["crop"]
    frame = _frame(document)
    y0 = crop["originY"]
    x0 = crop["originX"]
    return [row[x0:x0 + crop["width"]] for row in frame[y0:y0 + crop["height"]]]


def _upscale(document: dict) -> bool:
    crop = document["crop"]
    return document["outputWidth"] > crop["width"] or document["outputHeight"] > crop["height"]


def reduction_ratio(document: dict) -> Fraction:
    """Actual output-area / crop-area ratio. Greater than one is not a reduction."""
    validate_document(document)
    crop = document["crop"]
    return Fraction(document["outputWidth"] * document["outputHeight"], crop["width"] * crop["height"])


def _box_grid(frame: list[list[Fraction]], out_w: int, out_h: int) -> list[list[Fraction]]:
    height = len(frame)
    width = len(frame[0])
    require(width % out_w == 0 and height % out_h == 0, "reduction bins must be integer")
    bin_w = width // out_w
    bin_h = height // out_h
    grid: list[list[Fraction]] = []
    for oy in range(out_h):
        row: list[Fraction] = []
        for ox in range(out_w):
            total = Fraction(0)
            for y in range(oy * bin_h, (oy + 1) * bin_h):
                for x in range(ox * bin_w, (ox + 1) * bin_w):
                    total += frame[y][x]
            row.append(total / (bin_w * bin_h))
        grid.append(row)
    return grid


def _tap(samples: list[Fraction], index: int) -> Fraction:
    def at(cursor: int) -> Fraction:
        if cursor < 0:
            cursor = 0
        if cursor >= len(samples):
            cursor = len(samples) - 1
        return samples[cursor]
    left, center, right = CUBIC_TAP
    return (left * at(index - 1) + center * at(index) + right * at(index + 1)) / 8


def _cubic_grid(box: list[list[Fraction]]) -> list[list[Fraction]]:
    """Separable [1, 6, 1] / 8 on the box grid. Edges replicate. This is not box averaging."""
    height = len(box)
    width = len(box[0])
    horizontal: list[list[Fraction]] = []
    for row in box:
        horizontal.append([_tap(row, index) for index in range(width)])
    output: list[list[Fraction]] = [[Fraction(0) for _ in range(width)] for _ in range(height)]
    for x in range(width):
        column = [horizontal[y][x] for y in range(height)]
        tapped = [_tap(column, y) for y in range(height)]
        for y in range(height):
            output[y][x] = tapped[y]
    return output


def _flatten(grid: list[list[Fraction]]) -> list[Fraction]:
    values: list[Fraction] = []
    for row in grid:
        values.extend(row)
    return values


def box_values(document: dict) -> list[Fraction]:
    """Scene-linear box means of the crop. Raises when an axis is upscaled."""
    validate_document(document)
    require(not _upscale(document), "box values are unavailable for an upscale")
    frame = cropped_frame(document)
    return _flatten(_box_grid(frame, document["outputWidth"], document["outputHeight"]))


def cubic_values(document: dict) -> list[Fraction]:
    """Higher-quality separable cubic on the scene-linear box grid."""
    validate_document(document)
    require(not _upscale(document), "cubic values are unavailable for an upscale")
    frame = cropped_frame(document)
    box = _box_grid(frame, document["outputWidth"], document["outputHeight"])
    return _flatten(_cubic_grid(box))


def logc_box_values(document: dict) -> list[Fraction]:
    """Mutant: average host-logc-toy codes inside each bin, then decode.

    The decode is not a scene-linear reduction, including when a constant bin
    makes the number equal the linear mean.
    """
    validate_document(document)
    require(not _upscale(document), "log averages are unavailable for an upscale")
    frame = cropped_frame(document)
    out_w = document["outputWidth"]
    out_h = document["outputHeight"]
    height = len(frame)
    width = len(frame[0])
    require(width % out_w == 0 and height % out_h == 0, "reduction bins must be integer")
    bin_w = width // out_w
    bin_h = height // out_h
    values: list[Fraction] = []
    for oy in range(out_h):
        for ox in range(out_w):
            total = Fraction(0)
            count = bin_w * bin_h
            for y in range(oy * bin_h, (oy + 1) * bin_h):
                for x in range(ox * bin_w, (ox + 1) * bin_w):
                    total += encode_host_logc(frame[y][x])
            values.append(decode_host_logc(total / count))
    return values


def _tile_values(document: dict, kind: str) -> list[Fraction]:
    frame = cropped_frame(document)
    out_w = document["outputWidth"]
    out_h = document["outputHeight"]
    height = len(frame)
    width = len(frame[0])
    tile = document["tileSize"]
    require(width % out_w == 0 and height % out_h == 0, "reduction bins must be integer")
    bin_w = width // out_w
    bin_h = height // out_h
    require(width % tile == 0 and height % tile == 0, "tileSize must divide the cropped frame")
    require(tile % bin_w == 0 and tile % bin_h == 0, "tileSize must contain whole reduction bins")
    step_x = tile // bin_w
    step_y = tile // bin_h
    grid: list[list[Fraction | None]] = [[None for _ in range(out_w)] for _ in range(out_h)]
    for origin_y in range(0, height, tile):
        for origin_x in range(0, width, tile):
            sub = [row[origin_x:origin_x + tile] for row in frame[origin_y:origin_y + tile]]
            if kind == BOX:
                reduced = _flatten(_box_grid(sub, step_x, step_y))
            else:
                reduced = _flatten(_cubic_grid(_box_grid(sub, step_x, step_y)))
            base_y = origin_y // bin_h
            base_x = origin_x // bin_w
            cursor = 0
            for y in range(step_y):
                for x in range(step_x):
                    grid[base_y + y][base_x + x] = reduced[cursor]
                    cursor += 1
    return _flatten(grid)  # type: ignore[arg-type]


def declared_values(document: dict) -> list[Fraction]:
    validate_document(document)
    return [Fraction(item) for item in document["declaredReference"]]


def _computed(document: dict, kind: str) -> list[Fraction]:
    if kind == BOX:
        return box_values(document)
    return cubic_values(document)


def _samples_text(values: list[Fraction] | None) -> str:
    if values is None:
        return "unavailable"
    return ",".join(canonical(item) for item in values)


def _preserved(
    document: dict,
    box: list[Fraction] | None,
    cubic: list[Fraction] | None,
    logc: list[Fraction] | None,
    tiled: list[Fraction] | None,
    untiled: list[Fraction] | None,
    ratio: Fraction,
) -> list[str]:
    preserved = [f"pixel:{index}:{pixel}" for index, pixel in enumerate(document["pixels"])]
    for label, values in (("box", box), ("cubic", cubic), ("logc-average", logc)):
        if values is None:
            preserved.append(f"{label}:unavailable")
        else:
            preserved.extend(f"{label}:{index}:{canonical(value)}" for index, value in enumerate(values))
    preserved.extend(
        f"declared:{index}:{item}" for index, item in enumerate(document["declaredReference"])
    )
    crop = document["crop"]
    full = (
        crop["originX"] == 0
        and crop["originY"] == 0
        and crop["width"] == document["sourceWidth"]
        and crop["height"] == document["sourceHeight"]
    )
    preserved.extend(
        [
            "reduction-ratio:" + ratio_text(ratio),
            "axes:" + ratio_text(Fraction(document["outputWidth"], crop["width"]))
            + "x"
            + ratio_text(Fraction(document["outputHeight"], crop["height"])),
            f"crop:{crop['originX']},{crop['originY']},{crop['width']}x{crop['height']}",
            "geometry:full-frame-crop" if full else "geometry:cropped",
            "antialias:" + document["antialias"],
            "resampler:" + document["resampler"],
            "pipeline:" + PIPELINE,
            "tiled:" + _samples_text(tiled),
            "untiled:" + _samples_text(untiled),
            "domain:" + document["domain"],
            "encoding:" + document["encoding"],
            "tile-size:" + str(document["tileSize"]),
            f"size:{document['sourceWidth']}x{document['sourceHeight']}->{document['outputWidth']}x{document['outputHeight']}",
        ]
    )
    return preserved


def assess(document: dict, average_domain: str = LINEAR_DOMAIN) -> dict:
    """Judge a reduction against the linear-domain reference.

    ``average_domain="logc"`` is the mutant. It is rejected even when a constant
    field makes the decoded code average equal the linear mean. The decision is
    never ``qualified``, ``allowed``, or ``scene-linear``.
    """
    validate_document(document)
    require(average_domain in AVERAGE_DOMAINS, "average_domain must be scene-linear or logc")
    ratio = reduction_ratio(document)
    upscale = _upscale(document)
    questions = [
        "host fixture is not a physical S23 measurement",
        "reduction ratio is fixture geometry, not a measured camera mode",
        "host-logc-toy is not ARRI LogC, sensor-derived Log, or film-stock fidelity",
    ]
    reasons = [
        ORACLE,
        "pipeline " + PIPELINE + " keeps encoding after the reduction",
        "reduction ratio " + ratio_text(ratio),
    ]
    rejected: list[str] = []
    box: list[Fraction] | None = None
    cubic: list[Fraction] | None = None
    logc: list[Fraction] | None = None
    tiled: list[Fraction] | None = None
    untiled: list[Fraction] | None = None
    if upscale:
        rejected.append("mislabeled-upscale")
        reasons.append("an axis increase is upscaling and must not be labeled a reduction")
        questions.append("upscale samples were not invented")
    elif ratio >= 1:
        rejected.append("not-a-reduction")
        reasons.append("output area is not lower than the crop")
    if not upscale:
        kind = document["resampler"]
        box = box_values(document)
        cubic = cubic_values(document)
        logc = logc_box_values(document)
        untiled = _computed(document, kind)
        tiled = _tile_values(document, kind)
        declared = declared_values(document)
        if tiled != untiled:
            rejected.append("tile-mismatch")
            reasons.append("tiled and untiled " + kind + " results disagree")
        else:
            reasons.append("tiled and untiled " + kind + " results agree")
        if untiled != declared:
            rejected.append("reference-mismatch")
            reasons.append("output does not agree with the declared linear-domain reference")
        else:
            reasons.append("output agrees with the declared linear-domain reference")
        if box != cubic:
            reasons.append("box averaging and separable cubic resampling are distinct")
            questions.append("box average was not reported as the cubic resample")
        else:
            reasons.append("box and cubic agree on this crop")
        if logc != box:
            reasons.append("encoded-value average differs from the scene-linear box mean")
        else:
            reasons.append("encoded-value average matches the linear mean only because the bins are constant")
    if average_domain == LOGC_DOMAIN:
        rejected.insert(0, "logc-average-labeled-scene-linear")
        reasons.append(MUTANT)
        reasons.append("averaging host-logc-toy codes is not a scene-linear reduction")
        if logc is not None and box is not None and logc != box:
            rejected.append("encoded-average-disagrees")
        questions.append("log-domain average was not accepted as scene-linear reduction")
        decision = "rejected"
    elif rejected:
        decision = "rejected"
    else:
        decision = "linear-reduced"
        reasons.append("linear-reduced is a host fixture label, not physical qualification")
    reasons.append(HOST_LIMIT)
    preserved = _preserved(document, box, cubic, logc, tiled, untiled, ratio)
    return _result(decision, reasons, rejected, preserved, questions)
