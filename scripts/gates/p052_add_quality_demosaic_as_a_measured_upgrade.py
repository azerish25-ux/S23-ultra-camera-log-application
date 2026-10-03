#!/usr/bin/env python3
"""P052 quality-demosaic benchmark against the retained bilinear reference.

The edge-aware candidate is a versioned algorithm (``edge-aware-v1``). It is
compared with the P051 bilinear reference and with the independent RGB scene
the mosaic was sampled from. Declared artifacts are false color, zippering,
and aliasing. Texture loss and color error are regression checks. Edge
contrast is reported and is not an acceptance metric.

The deliberate mutant — heavy sharpening whose increased edge contrast is
reported as restored detail — is rejected. The simpler bilinear reference
stays available for numerical and lifecycle checks.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P052-01 through TC-P052-08.
"""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any


PHASE = "P052"
CASE_ID = "P052"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-quality-demosaic-fixture"
METHOD = (
    "Introduce an edge-aware candidate behind a versioned algorithm identity. "
    "Compare against the reference and independent RAW material for false color, "
    "zippering, texture loss, and aliasing. Retain the simpler reference for "
    "numerical and lifecycle testing."
)
FIXTURE = (
    "Fine repeating fabric, diagonal high-contrast edges, colored point lights, "
    "and a slanted edge chart."
)
ORACLE = (
    "The candidate must improve declared artifacts without unacceptable texture "
    "or color regressions across held-out scenes."
)
MUTANT = (
    "Sharpen the output heavily and report the increased edge contrast as "
    "restored detail."
)
REFERENCE_ID = "bilinear-reference-v1"
CANDIDATE_ID = "edge-aware-v1"
REFERENCE_RULE = (
    "The bilinear reference is retained unchanged. It copies a known site and "
    "averages in-bounds same-channel neighbors at Chebyshev distance 1. Missing "
    "samples are omitted and are not read from a stale row."
)
CANDIDATE_RULE = (
    "edge-aware-v1 estimates missing green along the lower local gradient and "
    "copies chroma along the lower-spread same-channel direction. Equal "
    "gradients fall back to the bilinear neighborhood. The reference identity "
    "is not replaced."
)
DECLARED = ("falseColor", "zippering", "aliasing")
REGRESSION = ("textureLoss", "colorDelta")
METRICS = DECLARED + REGRESSION + ("edgeContrast",)
FIXTURE_KINDS = (
    "fine-repeating-fabric",
    "diagonal-high-contrast",
    "colored-point-lights",
    "slanted-edge",
)
HELD_KINDS = ("independent-raw", "low-light-hair")
CFA = ("RGGB", "GRBG", "GBRG", "BGGR")
PHASE_AT = {
    "RGGB": "RGGB",
    "GRBG": "GRBG",
    "GBRG": "GBRG",
    "BGGR": "BGGR",
}
MEASURED = "measured-comparison"
MUTANT_TEST = "heavy-sharpen"
SOLE_TESTS = (MEASURED, MUTANT_TEST)
SHARPEN_AMOUNT = Fraction(4)
HOST_LIMIT = (
    "host fixture does not qualify a physical S23 or a measured demosaic on a physical sensor"
)
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "referenceId",
    "candidateId",
    "declaredArtifacts",
    "referenceRule",
    "candidateRule",
    "scenes",
}
SCENE_KEYS = {"id", "role", "kind", "cfa", "rgb"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed", "restored-detail"}


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


def format_fraction(value: Fraction) -> str:
    number = Fraction(value)
    if number.denominator == 1:
        return str(number.numerator)
    return f"{number.numerator}/{number.denominator}"


def channel_at(y: int, x: int, cfa: str) -> str:
    require(cfa in CFA, "cfa must be a supported Bayer phase")
    return PHASE_AT[cfa][(y % 2) * 2 + (x % 2)]


def _bilinear():
    try:
        from p051_build_the_row_streamed_reference_demosaic import demosaic
    except ImportError:
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from p051_build_the_row_streamed_reference_demosaic import demosaic
    return demosaic


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision not in _FORBIDDEN, "P052 must not decide qualified, allowed, or restored-detail")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons), "reasons must be non-empty")
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


def _mosaic(rgb: list[list[tuple[int, int, int]]], cfa: str) -> list[list[int]]:
    rows: list[list[int]] = []
    for y, row in enumerate(rgb):
        rows.append([row[x]["RGB".index(channel_at(y, x, cfa))] for x in range(len(row))])
    return rows


def _edge_aware(
    rows: list[list[int]],
    cfa: str,
) -> list[list[tuple[Fraction, Fraction, Fraction]]]:
    """Directional green plus chroma copy. Ties use the bilinear neighborhood."""
    height = len(rows)
    width = len(rows[0])

    def sample(y: int, x: int) -> Fraction | None:
        if y < 0 or x < 0 or y >= height or x >= width:
            return None
        return Fraction(int(rows[y][x]))

    green: list[list[Fraction | None]] = [[None] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            if channel_at(y, x, cfa) == "G":
                green[y][x] = sample(y, x)
                continue
            horizontal = (sample(y, x - 1), sample(y, x + 1))
            vertical = (sample(y - 1, x), sample(y + 1, x))

            def gradient(pair: tuple[Fraction | None, Fraction | None]) -> Fraction | None:
                left, right = pair
                if left is None or right is None:
                    return None
                return abs(left - right)

            grad_h = gradient(horizontal)
            grad_v = gradient(vertical)
            chosen: tuple[Fraction, Fraction] | None = None
            if grad_h is not None and grad_v is not None:
                if grad_h < grad_v:
                    chosen = horizontal  # type: ignore[assignment]
                elif grad_v < grad_h:
                    chosen = vertical  # type: ignore[assignment]
            elif grad_h is not None:
                chosen = horizontal  # type: ignore[assignment]
            elif grad_v is not None:
                chosen = vertical  # type: ignore[assignment]
            if chosen is None:
                total = Fraction(0)
                count = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny = y + dy
                        nx = x + dx
                        if 0 <= ny < height and 0 <= nx < width and channel_at(ny, nx, cfa) == "G":
                            total += sample(ny, nx)  # type: ignore[operator]
                            count += 1
                require(count > 0, "edge-aware green support missing")
                green[y][x] = total / count
            else:
                green[y][x] = (chosen[0] + chosen[1]) / 2
    image: list[list[tuple[Fraction, Fraction, Fraction]]] = []
    for y in range(height):
        row: list[tuple[Fraction, Fraction, Fraction]] = []
        for x in range(width):
            pixel: list[Fraction | None] = [None, None, None]
            here = channel_at(y, x, cfa)
            pixel["RGB".index(here)] = sample(y, x)
            pixel[1] = green[y][x]
            for channel, index in (("R", 0), ("B", 2)):
                if pixel[index] is not None:
                    continue
                neighbors: list[tuple[int, int, Fraction]] = []
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
                        neighbors.append((dy, dx, sample(ny, nx) - green[ny][nx]))  # type: ignore[operator]
                if not neighbors:
                    pixel[index] = green[y][x]
                    continue
                groups: list[list[Fraction]] = [[], [], []]
                for dy, dx, chroma in neighbors:
                    groups[0 if dy == 0 else 1 if dx == 0 else 2].append(chroma)

                def spread(values: list[Fraction]) -> Fraction | None:
                    if len(values) < 2:
                        return None
                    return max(values) - min(values)

                paired = [(spread(values), values) for values in groups if len(values) >= 2]
                if paired:
                    paired.sort(key=lambda item: (item[0], -len(item[1])))
                    if len(paired) > 1 and paired[0][0] == paired[1][0]:
                        chosen_chroma = [item[2] for item in neighbors]
                    else:
                        chosen_chroma = paired[0][1]
                else:
                    chosen_chroma = [item[2] for item in neighbors]
                pixel[index] = green[y][x] + (sum(chosen_chroma, Fraction(0)) / len(chosen_chroma))
            row.append((pixel[0], pixel[1], pixel[2]))  # type: ignore[arg-type]
        image.append(row)
    return image


def _sharpen(
    image: list[list[tuple[Fraction, Fraction, Fraction]]],
) -> list[list[tuple[Fraction, Fraction, Fraction]]]:
    """Add a heavy unsharp mask. Chroma is unchanged; edge contrast rises."""
    height = len(image)
    width = len(image[0])

    def luma(pixel: tuple[Fraction, Fraction, Fraction]) -> Fraction:
        return (pixel[0] + pixel[1] + pixel[2]) / 3

    sharpened: list[list[tuple[Fraction, Fraction, Fraction]]] = []
    for y in range(height):
        row: list[tuple[Fraction, Fraction, Fraction]] = []
        for x in range(width):
            total = Fraction(0)
            count = 0
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny = y + dy
                nx = x + dx
                if 0 <= ny < height and 0 <= nx < width:
                    total += luma(image[ny][nx])
                    count += 1
            require(count > 0, "sharpen neighborhood missing")
            delta = SHARPEN_AMOUNT * (luma(image[y][x]) - (total / count))
            row.append(tuple(channel + delta for channel in image[y][x]))
        sharpened.append(row)
    return sharpened


def _metrics(
    result: list[list[tuple[Fraction, Fraction, Fraction]]],
    truth: list[list[tuple[Fraction, Fraction, Fraction]]],
) -> dict[str, Fraction]:
    height = len(result)
    width = len(result[0])
    count = height * width
    false_color = Fraction(0)
    zipper = Fraction(0)
    color = Fraction(0)
    for y in range(height):
        for x in range(width):
            red, green, blue = result[y][x]
            true_red, true_green, true_blue = truth[y][x]
            excess = (abs(red - green) + abs(blue - green)) - (
                abs(true_red - true_green) + abs(true_blue - true_green)
            )
            false_color += max(Fraction(0), excess)
            zipper += abs(green - true_green)
            color += abs(red - true_red) + abs(green - true_green) + abs(blue - true_blue)

    def chroma(pixel: tuple[Fraction, Fraction, Fraction]) -> Fraction:
        return abs(pixel[0] - pixel[1]) + abs(pixel[2] - pixel[1])

    def luma(pixel: tuple[Fraction, Fraction, Fraction]) -> Fraction:
        return (pixel[0] + pixel[1] + pixel[2]) / 3

    alias_acc = Fraction(0)
    alias_n = 0
    texture_acc = Fraction(0)
    texture_n = 0
    true_texture = Fraction(0)
    for y in range(height):
        for x in range(1, width - 1):
            alias_acc += abs(
                chroma(result[y][x - 1]) - 2 * chroma(result[y][x]) + chroma(result[y][x + 1])
            )
            alias_n += 1
            texture_acc += abs(luma(result[y][x - 1]) - 2 * luma(result[y][x]) + luma(result[y][x + 1]))
            true_texture += abs(
                luma(truth[y][x - 1]) - 2 * luma(truth[y][x]) + luma(truth[y][x + 1])
            )
            texture_n += 1
    true_alias = Fraction(0)
    for y in range(height):
        for x in range(1, width - 1):
            true_alias += abs(
                chroma(truth[y][x - 1]) - 2 * chroma(truth[y][x]) + chroma(truth[y][x + 1])
            )
    aliasing = Fraction(0)
    if alias_n:
        aliasing = max(Fraction(0), (alias_acc / alias_n) - (true_alias / alias_n))
    texture_loss = Fraction(0)
    if texture_n:
        texture_loss = max(Fraction(0), (true_texture / texture_n) - (texture_acc / texture_n))
    contrast = Fraction(0)
    contrast_n = 0
    for y in range(height):
        for x in range(width - 1):
            contrast += abs(luma(result[y][x + 1]) - luma(result[y][x]))
            contrast_n += 1
    edge = contrast / contrast_n if contrast_n else Fraction(0)
    return {
        "falseColor": false_color / count,
        "zippering": zipper / count,
        "textureLoss": texture_loss,
        "aliasing": aliasing,
        "colorDelta": color / count,
        "edgeContrast": edge,
    }


def _truth(rgb: list) -> list[list[tuple[Fraction, Fraction, Fraction]]]:
    return [[tuple(Fraction(int(channel)) for channel in pixel) for pixel in row] for row in rgb]


def _images(scene: dict) -> tuple[
    dict[str, Fraction],
    dict[str, Fraction],
    dict[str, Fraction],
]:
    truth = _truth(scene["rgb"])
    rows = _mosaic(scene["rgb"], scene["cfa"])
    reference = _bilinear()(rows, scene["cfa"])
    candidate = _edge_aware(rows, scene["cfa"])
    sharpened = _sharpen(candidate)
    return _metrics(reference, truth), _metrics(candidate, truth), _metrics(sharpened, truth)


def _rgb(value: object, label: str) -> list[list[tuple[int, int, int]]]:
    require(type(value) is list and value, label + " must be a non-empty image")
    width = None
    image: list[list[tuple[int, int, int]]] = []
    for y, row in enumerate(value):
        require(type(row) is list and row, label + f" row {y} must be a non-empty list")
        if width is None:
            width = len(row)
        require(len(row) == width, label + " rows must be rectangular")
        parsed: list[tuple[int, int, int]] = []
        for x, pixel in enumerate(row):
            require(type(pixel) is list and len(pixel) == 3, label + f" pixel {y},{x} must be RGB")
            channels = []
            for channel in pixel:
                require(type(channel) is int and 0 <= channel <= 4095, label + f" sample {y},{x} out of range")
                channels.append(channel)
            parsed.append((channels[0], channels[1], channels[2]))
        image.append(parsed)
    height = len(image)
    require(width is not None and 4 <= width <= 16 and 4 <= height <= 16, label + " dimensions out of range")
    require(width % 2 == 0 and height % 2 == 0, label + " dimensions must be even")
    return image


def _scene(value: object, index: int, seen: set[str]) -> dict:
    item = exact_keys(value, SCENE_KEYS, f"scene {index}")
    ident = item["id"]
    require(isinstance(ident, str) and TOKEN.fullmatch(ident) is not None, f"scene {index} id must be a token")
    require(ident not in seen, "duplicate scene id: " + ident)
    seen.add(ident)
    role = item["role"]
    require(role in {"fixture", "held-out"}, f"scene {index} role must be fixture or held-out")
    kind = item["kind"]
    require(isinstance(kind, str) and TOKEN.fullmatch(kind) is not None, f"scene {index} kind must be a token")
    if kind in FIXTURE_KINDS:
        require(role == "fixture", f"scene {index} fixture kind needs role fixture")
    else:
        require(role == "held-out", f"scene {index} non-fixture kind needs role held-out")
    require(item["cfa"] in CFA, f"scene {index} cfa is unsupported")
    _rgb(item["rgb"], f"scene {index}")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P052 quality-demosaic fixture."""
    exact_keys(document, DOCUMENT_KEYS, "demosaic benchmark")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P052")
    require(document["mapId"] == MAP_ID, "mapId must be s23-quality-demosaic-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "benchmark needs the P052 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    require(document["referenceId"] == REFERENCE_ID, "referenceId must be bilinear-reference-v1")
    require(document["candidateId"] == CANDIDATE_ID, "candidateId must be edge-aware-v1")
    require(document["referenceId"] != document["candidateId"], "algorithm identities must differ")
    require(document["declaredArtifacts"] == list(DECLARED), "declaredArtifacts drifted")
    require(document["referenceRule"] == REFERENCE_RULE, "reference rule drifted")
    require(document["candidateRule"] == CANDIDATE_RULE, "candidate rule drifted")
    scenes = document["scenes"]
    require(type(scenes) is list and scenes, "scenes must be a non-empty list")
    seen: set[str] = set()
    for index, scene in enumerate(scenes):
        _scene(scene, index, seen)
    kinds = [scene["kind"] for scene in scenes]
    for kind in FIXTURE_KINDS:
        require(kinds.count(kind) == 1, "fixture kind missing or duplicated: " + kind)
    for kind in HELD_KINDS:
        require(kind in kinds, "held-out kind missing: " + kind)


def _metric_line(scene: dict, name: str, reference: Fraction, candidate: Fraction, sharpened: Fraction) -> str:
    return (
        f"scene:{scene['id']}:{scene['role']}:{scene['kind']}:{name}:"
        f"ref={format_fraction(reference)}:cand={format_fraction(candidate)}:sharp={format_fraction(sharpened)}"
    )


def _inventory(document: dict) -> tuple[list[str], list[dict[str, Any]]]:
    preserved = [
        "reference-retained:" + document["referenceId"],
        "candidate:" + document["candidateId"],
        "mutant-algorithm:heavy-sharpen",
    ]
    reports: list[dict[str, Any]] = []
    for scene in document["scenes"]:
        reference, candidate, sharpened = _images(scene)
        reports.append(
            {
                "scene": scene,
                "reference": reference,
                "candidate": candidate,
                "sharpened": sharpened,
            }
        )
        for name in METRICS:
            preserved.append(_metric_line(scene, name, reference[name], candidate[name], sharpened[name]))
    return preserved, reports


def _claims(scene_id: str, left: dict[str, Fraction], right: dict[str, Fraction]) -> tuple[list[str], bool]:
    claims: list[str] = []
    improved = False
    for name in DECLARED:
        if right[name] > left[name]:
            claims.append(f"{scene_id}:{name}")
        elif right[name] < left[name]:
            improved = True
        elif left[name] > 0:
            claims.append(f"{scene_id}:{name}:shortfall")
    for name in REGRESSION:
        if right[name] > left[name]:
            claims.append(f"{scene_id}:{name}")
    return claims, improved


def sharpen_would_accept(document: dict) -> bool:
    """True when heavy sharpen raises edge contrast on every scene.

    That is the mutant's acceptance story. ``assess`` must not turn it into
    ``selected``, ``qualified``, ``allowed``, or ``restored-detail``.
    """
    validate_document(document)
    _preserved, reports = _inventory(document)
    for report in reports:
        if report["sharpened"]["edgeContrast"] <= report["reference"]["edgeContrast"]:
            return False
    return True


def edge_contrast_gain(document: dict) -> Fraction:
    """Mean candidate-minus-reference edge contrast. Not an acceptance score."""
    validate_document(document)
    _preserved, reports = _inventory(document)
    total = sum(
        (report["candidate"]["edgeContrast"] - report["reference"]["edgeContrast"] for report in reports),
        Fraction(0),
    )
    return total / len(reports)


def selected_identity(document: dict, sole_test: str = MEASURED) -> str:
    """Return the candidate id only when the measured comparison selects it."""
    result = assess(document, sole_test=sole_test)
    if result["decision"] == "selected":
        return document["candidateId"]
    return document["referenceId"]


def assess(document: dict, sole_test: str = MEASURED) -> dict[str, Any]:
    """Select the edge-aware candidate only when declared artifacts improve.

    ``heavy-sharpen`` is the mutant. Increased edge contrast is never restored
    detail. The bilinear reference remains in ``preservedResults`` either way.
    The decision is never ``qualified``, ``allowed``, or ``restored-detail``.
    """
    validate_document(document)
    require(sole_test in SOLE_TESTS, "sole_test must be measured-comparison or heavy-sharpen")
    preserved, reports = _inventory(document)
    questions = [
        "host fixture is not a physical S23 measurement",
        "bilinear reference " + document["referenceId"] + " remains for numerical and lifecycle testing",
        "edge contrast is not restored detail",
    ]
    for scene in document["scenes"]:
        if scene["role"] == "held-out":
            questions.append(f"held-out {scene['id']} ({scene['kind']}) stays in the comparison")
    reasons = [
        ORACLE,
        "declared artifacts are " + ", ".join(DECLARED),
        "texture loss and color delta are regression checks, not edge contrast",
    ]
    rejected: list[str] = []
    improved = False
    for report in reports:
        scene = report["scene"]
        active = report["sharpened"] if sole_test == MUTANT_TEST else report["candidate"]
        claims, scene_improved = _claims(scene["id"], report["reference"], active)
        rejected.extend(claims)
        improved = improved or scene_improved
        for name in DECLARED:
            reasons.append(
                f"{scene['id']} {name} ref {format_fraction(report['reference'][name])} "
                f"cand {format_fraction(report['candidate'][name])}"
            )
    if sole_test == MUTANT_TEST:
        decision = "rejected"
        rejected.insert(0, "sharpen-as-restored-detail")
        reasons.append(MUTANT)
        reasons.append("increased edge contrast is not restored detail")
        questions.append("heavy sharpen was rejected")
    elif rejected:
        decision = "rejected" if any(":shortfall" not in item for item in rejected) else "withheld"
        if any(item.endswith(":shortfall") for item in rejected) and decision != "rejected":
            reasons.append("a declared artifact was not improved where the reference was wrong")
        else:
            reasons.append("artifact or color regression blocks the upgrade")
    elif not improved:
        decision = "withheld"
        reasons.append("no declared artifact improved")
    else:
        decision = "selected"
        reasons.append("edge-aware-v1 improved declared artifacts without a texture or color regression")
        reasons.append("selection does not use edge contrast")
        questions.append("selected is a host algorithm choice, not physical qualification")
    reasons.append(HOST_LIMIT)
    return _result(decision, reasons, rejected, preserved, questions)
