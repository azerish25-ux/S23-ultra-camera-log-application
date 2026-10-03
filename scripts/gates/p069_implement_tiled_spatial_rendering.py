#!/usr/bin/env python3
"""P069 tiled spatial rendering planner and boundary equivalence check.

Each node halo is that node's kernel support (its maximum kernel). The planner
reads an overlap equal to the sum of the spatial halos, runs blur then
halation on that overlap, applies lens and grain in global coordinates, and
crops only after those dependencies finish. The assembled tiles are compared
with an untiled reference at boundaries and corners.

The deliberate mutant — every effect applied independently inside tiles
without overlap — is rejected. It leaves a seam and a repeated grain block.
This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P069-01 through TC-P069-08.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


PHASE = "P069"
CASE_ID = "P069"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-tiled-spatial-rendering-fixture"
METHOD = (
    "Compute each node halo from the maximum kernel support, process overlap regions, "
    "and crop only after dependencies finish. Use global coordinates for grain and lens "
    "effects. Compare tiled and untiled reference outputs at boundaries and corners."
)
FIXTURE = (
    "A bright impulse centered exactly on a tile boundary with halation, blur, "
    "and deterministic grain enabled."
)
ORACLE = (
    "The assembled result matches the declared untiled tolerance and contains no seam "
    "or repeated grain block."
)
MUTANT = "Apply every effect independently inside tiles without overlap."
DECLARED_PATH = "declared"
MUTANT_PATH = "independent-tiles"
PATHS = (DECLARED_PATH, MUTANT_PATH)
EFFECTS = ("blur", "halation", "lens", "grain")
SPATIAL = ("blur", "halation")
COORDINATE = ("lens", "grain")
REQUIRED_EFFECTS = EFFECTS
HOST_LIMIT = "host fixture does not qualify a physical S23 or a measured tiled render"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SUPPORT = re.compile(r"0|[1-9][0-9]*")
TOLERANCE = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
IMPULSE_VALUE = re.compile(r"[1-9][0-9]*")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "planner",
    "nodes",
    "impulse",
}
PLANNER_KEYS = {
    "width",
    "height",
    "tileSize",
    "tolerance",
    "cropAfterDependencies",
    "globalCoordinates",
}
NODE_KEYS = {"id", "effect", "kernelSupport"}
IMPULSE_KEYS = {"x", "y", "value"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "withheld", "assembled_match"}
_MAX_EXTENT = 64
_MAX_SUPPORT = 8


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


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def _extent(value: object, label: str) -> int:
    require(type(value) is int and 1 <= value <= _MAX_EXTENT, label + " must be an int from 1 to 64")
    return value


def _support(value: object, label: str) -> str:
    require(
        isinstance(value, str) and SUPPORT.fullmatch(value) is not None and int(value) <= _MAX_SUPPORT,
        label + " must be a canonical kernel support from 0 to 8",
    )
    return value


def node_halo(node: dict) -> int:
    """Halo equals the node's kernel support, which is that node's maximum kernel."""
    return int(node["kernelSupport"])


def required_overlap(nodes: list[dict]) -> int:
    """Overlap that must be processed before the final crop.

    Each spatial stage consumes its own halo. The crop waits until every
    dependency has finished, so the input overlap is the sum of spatial halos
    and is therefore at least the maximum kernel support.
    """
    return sum(node_halo(node) for node in nodes if node["effect"] in SPATIAL)


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is a P069 tiled-rendering fixture."""
    exact_keys(document, DOCUMENT_KEYS, "tile plan")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P069")
    require(document["mapId"] == MAP_ID, "mapId must be s23-tiled-spatial-rendering-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "tile plan needs the P069 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    planner = exact_keys(document["planner"], PLANNER_KEYS, "planner")
    width = _extent(planner["width"], "width")
    height = _extent(planner["height"], "height")
    tile = _extent(planner["tileSize"], "tileSize")
    require(width % tile == 0 and height % tile == 0, "tileSize must divide width and height")
    tolerance = planner["tolerance"]
    require(isinstance(tolerance, str) and TOLERANCE.fullmatch(tolerance) is not None, "tolerance must be canonical")
    require(Decimal(tolerance) >= 0, "tolerance must be non-negative")
    _bool(planner["cropAfterDependencies"], "cropAfterDependencies")
    _bool(planner["globalCoordinates"], "globalCoordinates")
    nodes = document["nodes"]
    require(type(nodes) is list and nodes, "nodes must be a non-empty list")
    seen: set[str] = set()
    effects: list[str] = []
    for index, raw in enumerate(nodes):
        node = exact_keys(raw, NODE_KEYS, f"node {index}")
        effect = node["effect"]
        require(effect in EFFECTS, f"node {index} effect is unsupported")
        require(node["id"] == effect, f"node {index} id must match its effect")
        require(effect not in seen, "duplicate effect: " + effect)
        seen.add(effect)
        effects.append(effect)
        support = _support(node["kernelSupport"], f"node {effect} kernelSupport")
        if effect in SPATIAL:
            require(int(support) >= 1, f"node {effect} spatial kernel support must be at least 1")
        else:
            require(support == "0", f"node {effect} coordinate kernel support must be 0")
    ranks = [EFFECTS.index(effect) for effect in effects]
    require(ranks == sorted(ranks), "nodes must follow blur, halation, lens, grain order")
    impulse = exact_keys(document["impulse"], IMPULSE_KEYS, "impulse")
    x = impulse["x"]
    y = impulse["y"]
    require(type(x) is int and 0 <= x < width, "impulse x is outside the image")
    require(type(y) is int and 0 <= y < height, "impulse y is outside the image")
    value = impulse["value"]
    require(
        isinstance(value, str) and IMPULSE_VALUE.fullmatch(value) is not None and int(value) <= 9999,
        "impulse value must be a canonical positive integer",
    )


def _blank(width: int, height: int) -> list[list[int]]:
    return [[0] * width for _ in range(height)]


def _source(width: int, height: int, x: int, y: int, value: int) -> list[list[int]]:
    image = _blank(width, height)
    image[y][x] = value
    return image


def _box(image: list[list[int]], radius: int) -> list[list[int]]:
    height = len(image)
    width = len(image[0])
    out = _blank(width, height)
    for y in range(height):
        for x in range(width):
            total = 0
            for dy in range(-radius, radius + 1):
                yy = y + dy
                if yy < 0 or yy >= height:
                    continue
                row = image[yy]
                for dx in range(-radius, radius + 1):
                    xx = x + dx
                    if 0 <= xx < width:
                        total += row[xx]
            out[y][x] = total
    return out


def _lens(x: int, y: int) -> int:
    return (x * 3 + y * 5) % 7


def _grain(x: int, y: int) -> int:
    return (x * 17 + y * 31 + 7) % 5


def _coordinate(x: int, y: int, tile: int, local: bool, use_lens: bool, use_grain: bool) -> int:
    sx, sy = (x % tile, y % tile) if local else (x, y)
    value = 0
    if use_lens:
        value += _lens(sx, sy)
    if use_grain:
        value += _grain(sx, sy)
    return value


def _add_coordinates(
    image: list[list[int]],
    tile: int,
    local: bool,
    use_lens: bool,
    use_grain: bool,
    origin_x: int = 0,
    origin_y: int = 0,
) -> tuple[list[list[int]], list[list[int]]]:
    height = len(image)
    width = len(image[0])
    out = _blank(width, height)
    coords = _blank(width, height)
    for y in range(height):
        for x in range(width):
            amount = _coordinate(origin_x + x, origin_y + y, tile, local, use_lens, use_grain)
            coords[y][x] = amount
            out[y][x] = image[y][x] + amount
    return out, coords


def _spatial(image: list[list[int]], nodes: list[dict], independent: bool) -> list[list[int]]:
    spatial = [node for node in nodes if node["effect"] in SPATIAL]
    if not spatial:
        return [row[:] for row in image]
    if independent:
        acc = _blank(len(image[0]), len(image))
        for node in spatial:
            filtered = _box(image, node_halo(node))
            for y in range(len(acc)):
                for x in range(len(acc[0])):
                    acc[y][x] += filtered[y][x]
        return acc
    buf = [row[:] for row in image]
    for node in spatial:
        buf = _box(buf, node_halo(node))
    return buf


def _zero_outside(image: list[list[int]], tx: int, ty: int, tile: int) -> list[list[int]]:
    height = len(image)
    width = len(image[0])
    out = _blank(width, height)
    for y in range(ty, min(ty + tile, height)):
        row = image[y]
        dest = out[y]
        for x in range(tx, min(tx + tile, width)):
            dest[x] = row[x]
    return out


def _extract(image: list[list[int]], x0: int, y0: int, x1: int, y1: int) -> list[list[int]]:
    width = x1 - x0
    height = y1 - y0
    out = _blank(width, height)
    source_h = len(image)
    source_w = len(image[0])
    for ly in range(height):
        gy = y0 + ly
        if gy < 0 or gy >= source_h:
            continue
        row = image[gy]
        dest = out[ly]
        for lx in range(width):
            gx = x0 + lx
            if 0 <= gx < source_w:
                dest[lx] = row[gx]
    return out


def _flags(nodes: list[dict]) -> tuple[bool, bool]:
    effects = {node["effect"] for node in nodes}
    return "lens" in effects, "grain" in effects


def render_untiled(nodes: list[dict], source: list[list[int]], tile: int) -> tuple[list[list[int]], list[list[int]]]:
    """Chain spatial kernels, then add lens and grain in global coordinates."""
    use_lens, use_grain = _flags(nodes)
    spatial = _spatial(source, nodes, False)
    return _add_coordinates(spatial, tile, False, use_lens, use_grain)


def _render_tiled(
    nodes: list[dict],
    source: list[list[int]],
    tile: int,
    overlap: int,
    local: bool,
    independent: bool,
    crop_between: bool,
) -> tuple[list[list[int]], list[list[int]]]:
    height = len(source)
    width = len(source[0])
    assembled = _blank(width, height)
    coordinates = _blank(width, height)
    use_lens, use_grain = _flags(nodes)
    for ty in range(0, height, tile):
        for tx in range(0, width, tile):
            if overlap > 0:
                x0 = tx - overlap
                y0 = ty - overlap
                window = _extract(source, x0, y0, tx + tile + overlap, ty + tile + overlap)
                spatial = _spatial(window, nodes, False)
                combined, coords = _add_coordinates(spatial, tile, local, use_lens, use_grain, x0, y0)
                for y in range(tile):
                    for x in range(tile):
                        assembled[ty + y][tx + x] = combined[overlap + y][overlap + x]
                        coordinates[ty + y][tx + x] = coords[overlap + y][overlap + x]
                continue
            masked = _zero_outside(source, tx, ty, tile)
            if independent:
                spatial = _spatial(masked, nodes, True)
            else:
                buf = masked
                for node in nodes:
                    if node["effect"] not in SPATIAL:
                        continue
                    buf = _box(buf, node_halo(node))
                    if crop_between:
                        buf = _zero_outside(buf, tx, ty, tile)
                spatial = buf
            combined, coords = _add_coordinates(spatial, tile, local, use_lens, use_grain)
            for y in range(ty, ty + tile):
                for x in range(tx, tx + tile):
                    assembled[y][x] = combined[y][x]
                    coordinates[y][x] = coords[y][x]
    return assembled, coordinates


def _seam_pixel(x: int, y: int, tile: int, width: int, height: int) -> bool:
    vertical = (x % tile == 0 and x > 0) or ((x + 1) % tile == 0 and x + 1 < width)
    horizontal = (y % tile == 0 and y > 0) or ((y + 1) % tile == 0 and y + 1 < height)
    return vertical or horizontal


def _on_corner(x: int, y: int, tile: int, width: int, height: int) -> bool:
    return x > 0 and y > 0 and x % tile == 0 and y % tile == 0 and x < width and y < height


def _repeated_block(field: list[list[int]], tile: int) -> bool:
    height = len(field)
    width = len(field[0])
    saw = False
    for y in range(height):
        row = field[y]
        for x in range(width):
            if x + tile < width:
                saw = True
                if row[x] != row[x + tile]:
                    return False
            if y + tile < height:
                saw = True
                if field[y][x] != field[y + tile][x]:
                    return False
    return saw


def _max_delta(left: list[list[int]], right: list[list[int]]) -> int:
    delta = 0
    for y in range(len(left)):
        for x in range(len(left[0])):
            delta = max(delta, abs(left[y][x] - right[y][x]))
    return delta


def _has_seam(tiled: list[list[int]], untiled: list[list[int]], tile: int) -> bool:
    height = len(tiled)
    width = len(tiled[0])
    for y in range(height):
        for x in range(width):
            if _seam_pixel(x, y, tile, width, height) and tiled[y][x] != untiled[y][x]:
                return True
    return False


def _samples(tiled: list[list[int]], untiled: list[list[int]], x: int, y: int) -> list[str]:
    height = len(tiled)
    width = len(tiled[0])
    lines: list[str] = []
    for sy in (y - 1, y):
        for sx in (x - 1, x):
            if 0 <= sx < width and 0 <= sy < height:
                lines.append(f"sample:{sx},{sy}:tiled={tiled[sy][sx]}:untiled={untiled[sy][sx]}")
    return lines


def _inventory(
    document: dict,
    nodes: list[dict],
    applied_overlap: int,
    applied_global: bool,
    applied_independent: bool,
    boundary: bool,
    corner: bool,
    delta: int,
    seam: bool,
    repeated: bool,
    samples: list[str],
    path: str,
) -> list[str]:
    planner = document["planner"]
    impulse = document["impulse"]
    preserved = [
        f"impulse:{impulse['x']},{impulse['y']}:value={impulse['value']}",
        f"extent:{planner['width']}x{planner['height']}",
        f"tile-size:{planner['tileSize']}",
        f"tolerance:{planner['tolerance']}",
        "effects:" + ",".join(node["effect"] for node in nodes),
    ]
    for node in nodes:
        kind = "spatial" if node["effect"] in SPATIAL else "coordinate"
        preserved.append(
            f"node:{node['id']}:halo={node_halo(node)}:kernel={node['kernelSupport']}:kind={kind}"
        )
    preserved.extend(
        [
            "max-kernel-support:" + str(max(node_halo(node) for node in nodes)),
            "required-overlap:" + str(required_overlap(nodes)),
            "applied-overlap:" + str(applied_overlap),
            "crop-after-dependencies:" + str(planner["cropAfterDependencies"]).lower(),
            "global-coordinates:" + str(planner["globalCoordinates"]).lower(),
            "applied-global:" + str(applied_global).lower(),
            "applied-independent:" + str(applied_independent).lower(),
            "boundary:" + str(boundary).lower(),
            "corner:" + str(corner).lower(),
            "max-delta:" + str(delta),
            "seam:" + str(seam).lower(),
            "repeated-grain:" + str(repeated).lower(),
            "reference:untiled",
            "path:" + path,
        ]
    )
    preserved.extend(samples)
    return preserved


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS, "unexpected decision")
    require(decision not in _FORBIDDEN, "P069 must not decide qualified or allowed")
    require(
        bool(reasons) and all(isinstance(item, str) and item for item in reasons),
        "reasons must be a non-empty list of strings",
    )
    for items in (rejected, preserved, questions):
        require(all(isinstance(item, str) and item for item in items), "result lists must be non-empty strings")
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


def assess(document: dict, path: str = DECLARED_PATH) -> dict:
    """Compare tiled output with the untiled reference and reject the mutant.

    ``path`` ``independent-tiles`` applies every effect inside each tile with
    no overlap and with tile-local grain and lens coordinates. That path is
    rejected even when the document itself asks for global coordinates. The
    decision is never ``qualified`` or ``allowed``. A rejection keeps the
    impulse, the node halos, and the boundary samples.
    """
    validate_document(document)
    require(path in PATHS, "path must be declared or independent-tiles")
    planner = document["planner"]
    nodes = document["nodes"]
    impulse = document["impulse"]
    width = planner["width"]
    height = planner["height"]
    tile = planner["tileSize"]
    crop_after = planner["cropAfterDependencies"]
    global_coordinates = planner["globalCoordinates"]
    mutant = path == MUTANT_PATH
    overlap = 0 if mutant or not crop_after else required_overlap(nodes)
    local = mutant or not global_coordinates
    independent = mutant
    crop_between = (not crop_after) and not mutant
    source = _source(width, height, impulse["x"], impulse["y"], int(impulse["value"]))
    untiled, global_coords = render_untiled(nodes, source, tile)
    tiled, used_coords = _render_tiled(nodes, source, tile, overlap, local, independent, crop_between)
    delta = _max_delta(tiled, untiled)
    seam = _has_seam(tiled, untiled, tile)
    coordinate_nodes = any(node["effect"] in COORDINATE for node in nodes)
    repeated = _repeated_block(used_coords, tile) if coordinate_nodes else False
    coords_differ = used_coords != global_coords
    boundary = _seam_pixel(impulse["x"], impulse["y"], tile, width, height)
    corner = _on_corner(impulse["x"], impulse["y"], tile, width, height)
    samples = _samples(tiled, untiled, impulse["x"], impulse["y"])
    rejected: list[str] = []
    if seam:
        rejected.append("seam")
    if Decimal(delta) > Decimal(planner["tolerance"]):
        rejected.append("tolerance-exceeded")
    if repeated:
        rejected.append("repeated-grain-block")
    if required_overlap(nodes) > 0 and overlap < required_overlap(nodes):
        rejected.append("missing-overlap")
    if not crop_after:
        rejected.append("cropped-before-dependencies")
    if coordinate_nodes and local and coords_differ:
        rejected.append("local-coordinates")
    if mutant:
        rejected.append("independent-tiles-without-overlap")
    effects = [node["effect"] for node in nodes]
    missing = [effect for effect in REQUIRED_EFFECTS if effect not in effects]
    reasons = [ORACLE, "node halos are the maximum kernel support of each node"]
    questions = [
        "host fixture is not a physical S23 measurement",
        HOST_LIMIT,
        "integer Chebyshev boxes are not a measured optical halation or cinema lens",
    ]
    if mutant:
        reasons.append(MUTANT)
        reasons.append("independent tiles without overlap do not match the untiled reference")
    if seam:
        reasons.append("tiled and untiled outputs differ on a tile boundary or corner")
    elif delta == 0:
        reasons.append("assembled pixels match the untiled reference")
    if repeated:
        reasons.append("grain or lens coordinates repeat as a tile-sized block")
    if "missing-overlap" in rejected:
        reasons.append("required spatial overlap was not processed before the crop")
    if "cropped-before-dependencies" in rejected:
        reasons.append("the crop ran before spatial dependencies finished")
    if "local-coordinates" in rejected:
        reasons.append("grain and lens did not use global coordinates")
    if not missing and boundary and not rejected:
        reasons.append("boundary and corner samples match the untiled reference inside tolerance")
        reasons.append("no seam and no repeated grain block")
    reasons.append(HOST_LIMIT)
    preserved = _inventory(
        document,
        nodes,
        overlap,
        not local,
        independent,
        boundary,
        corner,
        delta,
        seam,
        repeated,
        samples,
        path,
    )
    if rejected:
        questions.append("rejection kept the impulse, node halos, and boundary samples")
        return _result("rejected", reasons, rejected, preserved, questions)
    if missing or not boundary:
        if missing:
            reasons.append("fixture effects blur, halation, lens, and grain are not all enabled")
            questions.append("missing effects: " + ",".join(missing))
        if not boundary:
            reasons.append("impulse is not centered on a tile boundary, so boundary equivalence is withheld")
            questions.append("move the impulse onto a tile boundary or corner before claiming a match")
        return _result("withheld", reasons, rejected, preserved, questions)
    reasons.append("tiled assembly matched the declared untiled tolerance")
    return _result("assembled_match", reasons, rejected, preserved, questions)
