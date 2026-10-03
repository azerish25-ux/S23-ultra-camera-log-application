#!/usr/bin/env python3
"""P053 defect correction that keeps real highlights, on a host fixture.

A measured hot-pixel map plus a conservative local test can replace a
persistent defect. A sparse bright pixel is not enough: a real specular
highlight may be isolated and may move. Corrections are stored as a confidence
mask, applied only in the declared scene-linear source domain, and the
unmodified original stays in the inventory.

The deliberate mutant — remove every isolated bright pixel using one intensity
threshold — is rejected. This module does not probe a device, does not qualify
a physical S23, and does not execute TC-P053-01 through TC-P053-08.
"""

from __future__ import annotations

import math
import re
from typing import Any


PHASE = "P053"
CASE_ID = "P053"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-defect-correction-fixture"
METHOD = (
    "Combine measured defect maps with conservative local tests. Store confidence "
    "and correction masks. Do not replace every isolated bright pixel, because real "
    "highlights may be sparse. Apply corrections in a declared source domain and "
    "retain the unmodified original."
)
FIXTURE = "A measured hot pixel adjacent to a real small moving specular highlight."
ORACLE = (
    "The persistent defect is corrected while the moving highlight is preserved and "
    "corrections remain inspectable."
)
MUTANT = "Remove every isolated bright pixel using one intensity threshold."
HOST_LIMIT = "this host fixture does not qualify a physical S23"
DECLARED_DOMAIN = "scene-linear"
DECLARED_TEST = "measured-defect-map"
MUTANT_TEST = "intensity-threshold"
MUTANT_ACCEPT = "threshold_cleaned"
SOLE_TESTS = (DECLARED_TEST, MUTANT_TEST)
DOMAINS = ("scene-linear", "display-encoded", "logarithmic")
ROLES = ("defect", "highlight", "background")
KINDS = ("hot",)
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[a-z0-9-]+$")
UINT = re.compile(r"0|[1-9][0-9]*")
FRACTION = re.compile(r"(0|[1-9][0-9]*)/([1-9][0-9]*)")
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "sourceDomain",
    "intensityThreshold",
    "sensorSaturation",
    "retainOriginal",
    "neighborhoodRadius",
    "minPersistence",
    "minConfidence",
    "minDarkSupport",
    "background",
    "width",
    "height",
    "defectMap",
    "frames",
}
DEFECT_KEYS = {"id", "x", "y", "kind", "confidence"}
FRAME_KEYS = {"id", "samples"}
SAMPLE_KEYS = {"x", "y", "value", "role"}
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "withheld", "highlight_preserved"}


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


def _token(value: object, label: str) -> str:
    require(isinstance(value, str) and TOKEN.fullmatch(value) is not None,
            label + " must be a lowercase token")
    return value


def _uint_text(value: object, label: str) -> str:
    require(isinstance(value, str) and UINT.fullmatch(value) is not None,
            label + " must be a canonical non-negative integer string")
    return value


def _positive_int(value: object, label: str) -> int:
    require(type(value) is int and not isinstance(value, bool) and value > 0,
            label + " must be a positive int")
    return value


def _nonneg_int(value: object, label: str) -> int:
    require(type(value) is int and not isinstance(value, bool) and value >= 0,
            label + " must be a non-negative int")
    return value


def _fraction(value: object, label: str) -> tuple[int, int]:
    require(isinstance(value, str), label + " must be a reduced fraction string")
    match = FRACTION.fullmatch(value)
    require(match is not None, label + " must be a reduced fraction string")
    numerator = int(match.group(1))
    denominator = int(match.group(2))
    require(math.gcd(numerator, denominator) == 1, label + " must be reduced")
    return numerator, denominator


def _fraction_ge(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] * right[1] >= right[0] * left[1]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _median(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[(len(ordered) - 1) // 2]


def _sample(value: object, index: int, width: int, height: int, seen: set[tuple[int, int]]) -> dict:
    item = exact_keys(value, SAMPLE_KEYS, f"sample {index}")
    x = _nonneg_int(item["x"], f"sample {index} x")
    y = _nonneg_int(item["y"], f"sample {index} y")
    require(x < width and y < height, f"sample {index} is outside the frame")
    require((x, y) not in seen, f"duplicate sample coordinate {x},{y}")
    seen.add((x, y))
    role = item["role"]
    require(role in ROLES, f"sample {index} role is unknown")
    level = int(_uint_text(item["value"], f"sample {index} value"))
    return {"x": x, "y": y, "value": level, "role": role}


def _frame(value: object, index: int, width: int, height: int, seen_ids: set[str]) -> dict:
    item = exact_keys(value, FRAME_KEYS, f"frame {index}")
    ident = _uint_text(item["id"], f"frame {index} id")
    require(ident not in seen_ids, "duplicate frame id: " + ident)
    seen_ids.add(ident)
    samples = item["samples"]
    require(isinstance(samples, list) and samples, f"frame {ident} samples must be a non-empty list")
    seen: set[tuple[int, int]] = set()
    parsed = [_sample(sample, offset, width, height, seen) for offset, sample in enumerate(samples)]
    return {"id": ident, "samples": parsed}


def _defect(value: object, index: int, width: int, height: int, seen_ids: set[str],
            seen_xy: set[tuple[int, int]]) -> dict:
    item = exact_keys(value, DEFECT_KEYS, f"defect {index}")
    ident = _token(item["id"], f"defect {index} id")
    require(ident not in seen_ids, "duplicate defect id: " + ident)
    seen_ids.add(ident)
    x = _nonneg_int(item["x"], f"defect {index} x")
    y = _nonneg_int(item["y"], f"defect {index} y")
    require(x < width and y < height, f"defect {ident} is outside the frame")
    require((x, y) not in seen_xy, f"duplicate defect coordinate {x},{y}")
    seen_xy.add((x, y))
    kind = item["kind"]
    require(kind in KINDS, f"defect {ident} kind must be hot")
    confidence_text = item["confidence"]
    _fraction(confidence_text, f"defect {ident} confidence")
    return {"id": ident, "x": x, "y": y, "kind": kind, "confidence": confidence_text}


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P053 defect-correction fixture shape."""
    exact_keys(document, DOCUMENT_KEYS, "defect document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P053")
    require(document["mapId"] == MAP_ID, "mapId must be s23-defect-correction-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and isinstance(revision, str) and HEX40.fullmatch(revision) is not None,
            "defect document needs the P053 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    require(document["sourceDomain"] in DOMAINS, "sourceDomain is unknown")
    _uint_text(document["intensityThreshold"], "intensityThreshold")
    _uint_text(document["sensorSaturation"], "sensorSaturation")
    _uint_text(document["background"], "background")
    require(type(document["retainOriginal"]) is bool, "retainOriginal must be a bool")
    radius = document["neighborhoodRadius"]
    require(type(radius) is int and 1 <= radius <= 3, "neighborhoodRadius must be 1, 2, or 3")
    _positive_int(document["minPersistence"], "minPersistence")
    _fraction(document["minConfidence"], "minConfidence")
    support = document["minDarkSupport"]
    require(type(support) is int and support >= 1, "minDarkSupport must be a positive int")
    width = _positive_int(document["width"], "width")
    height = _positive_int(document["height"], "height")
    require(width <= 64 and height <= 64, "fixture dimensions must stay at most 64")
    defects = document["defectMap"]
    require(isinstance(defects, list) and defects, "defectMap must be a non-empty list")
    seen_ids: set[str] = set()
    seen_xy: set[tuple[int, int]] = set()
    for index, item in enumerate(defects):
        _defect(item, index, width, height, seen_ids, seen_xy)
    frames = document["frames"]
    require(isinstance(frames, list) and frames, "frames must be a non-empty list")
    frame_ids: set[str] = set()
    parsed_frames = [_frame(item, index, width, height, frame_ids) for index, item in enumerate(frames)]
    roles = {sample["role"] for frame in parsed_frames for sample in frame["samples"]}
    require("defect" in roles and "highlight" in roles, "frames need a defect sample and a highlight sample")
    measured = {(item["x"], item["y"]) for item in defects}
    defect_sites = {
        (sample["x"], sample["y"])
        for frame in parsed_frames
        for sample in frame["samples"]
        if sample["role"] == "defect"
    }
    require(measured & defect_sites, "defect map coordinate must appear as a defect sample")


def _load(document: dict) -> dict[str, Any]:
    width = document["width"]
    height = document["height"]
    seen_ids: set[str] = set()
    seen_xy: set[tuple[int, int]] = set()
    frame_ids: set[str] = set()
    return {
        "domain": document["sourceDomain"],
        "threshold": int(document["intensityThreshold"]),
        "saturation": int(document["sensorSaturation"]),
        "retain": document["retainOriginal"],
        "radius": document["neighborhoodRadius"],
        "min_persistence": document["minPersistence"],
        "min_confidence": _fraction(document["minConfidence"], "minConfidence"),
        "min_dark": document["minDarkSupport"],
        "background": int(document["background"]),
        "width": width,
        "height": height,
        "defects": [
            _defect(item, index, width, height, seen_ids, seen_xy)
            for index, item in enumerate(document["defectMap"])
        ],
        "frames": [
            _frame(item, index, width, height, frame_ids)
            for index, item in enumerate(document["frames"])
        ],
    }


def _value_at(grid: dict[tuple[int, int], int], background: int, x: int, y: int) -> int:
    return grid.get((x, y), background)


def _neighbors(x: int, y: int, width: int, height: int, radius: int) -> list[tuple[int, int]]:
    found: list[tuple[int, int]] = []
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                found.append((nx, ny))
    return found


def _dark_values(loaded: dict[str, Any], frame: dict, x: int, y: int) -> list[int]:
    grid = { (sample["x"], sample["y"]): sample["value"] for sample in frame["samples"] }
    values: list[int] = []
    for nx, ny in _neighbors(x, y, loaded["width"], loaded["height"], loaded["radius"]):
        level = _value_at(grid, loaded["background"], nx, ny)
        if level < loaded["threshold"]:
            values.append(level)
    return values


def _persistence(loaded: dict[str, Any], x: int, y: int) -> int:
    count = 0
    for frame in loaded["frames"]:
        grid = {(sample["x"], sample["y"]): sample["value"] for sample in frame["samples"]}
        if _value_at(grid, loaded["background"], x, y) >= loaded["threshold"]:
            count += 1
    return count


def local_median(loaded: dict[str, Any], frame: dict, x: int, y: int) -> int | None:
    """Median of darker neighbors, or None when support is below the declared minimum."""
    values = _dark_values(loaded, frame, x, y)
    if len(values) < loaded["min_dark"]:
        return None
    return _median(values)


def threshold_removals(loaded: dict[str, Any]) -> list[str]:
    """Pixels the one-threshold mutant would erase. Highlights are included."""
    removed: list[str] = []
    for frame in loaded["frames"]:
        for sample in frame["samples"]:
            if sample["value"] >= loaded["threshold"]:
                removed.append(
                    f"removed:{frame['id']}:{sample['x']},{sample['y']}:{sample['value']}"
                )
    return removed


def _inventory(loaded: dict[str, Any]) -> dict[str, list[str]]:
    originals: list[str] = []
    highlights: list[str] = []
    saturated: list[str] = []
    for frame in loaded["frames"]:
        for sample in frame["samples"]:
            originals.append(
                f"original:{frame['id']}:{sample['x']},{sample['y']}:{sample['value']}:{sample['role']}"
            )
            if sample["role"] == "highlight":
                highlights.append(
                    f"highlight:{frame['id']}:{sample['x']},{sample['y']}:{sample['value']}:preserved"
                )
                on_border = (
                    sample["x"] in (0, loaded["width"] - 1)
                    or sample["y"] in (0, loaded["height"] - 1)
                )
                if on_border or sample["value"] >= loaded["saturation"]:
                    saturated.append(
                        f"saturated-boundary:{frame['id']}:{sample['x']},{sample['y']}"
                    )
    maps = [
        f"map:{item['id']}:{item['x']},{item['y']}:{item['kind']}:{item['confidence']}"
        for item in loaded["defects"]
    ]
    return {
        "originals": originals,
        "highlights": highlights,
        "saturated": saturated,
        "maps": maps,
    }


def _site_block(loaded: dict[str, Any], defect: dict) -> str | None:
    confidence = _fraction(defect["confidence"], defect["id"])
    if not _fraction_ge(confidence, loaded["min_confidence"]):
        return "low-confidence:" + defect["id"]
    if _persistence(loaded, defect["x"], defect["y"]) < loaded["min_persistence"]:
        return "not-persistent:" + defect["id"]
    for frame in loaded["frames"]:
        grid = {(sample["x"], sample["y"]): sample["value"] for sample in frame["samples"]}
        level = _value_at(grid, loaded["background"], defect["x"], defect["y"])
        if level < loaded["threshold"]:
            continue
        if local_median(loaded, frame, defect["x"], defect["y"]) is None:
            return "local-test-failed:" + defect["id"]
    return None


def _corrections(loaded: dict[str, Any], defect: dict) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for frame in loaded["frames"]:
        grid = {(sample["x"], sample["y"]): sample["value"] for sample in frame["samples"]}
        level = _value_at(grid, loaded["background"], defect["x"], defect["y"])
        if level < loaded["threshold"]:
            continue
        replacement = local_median(loaded, frame, defect["x"], defect["y"])
        if replacement is None:
            continue
        found.append({
            "frame": frame["id"],
            "x": defect["x"],
            "y": defect["y"],
            "confidence": defect["confidence"],
            "replacement": replacement,
            "source": level,
        })
    return found


def _highlight_on_map(loaded: dict[str, Any]) -> list[str]:
    mapped = {(item["x"], item["y"]) for item in loaded["defects"]}
    claims: list[str] = []
    for frame in loaded["frames"]:
        for sample in frame["samples"]:
            if sample["role"] == "highlight" and (sample["x"], sample["y"]) in mapped:
                claims.append(
                    f"highlight-on-defect-map:{frame['id']}:{sample['x']},{sample['y']}"
                )
    return claims


def _preserved(loaded: dict[str, Any], inventory: dict[str, list[str]],
               corrections: list[dict[str, Any]]) -> list[str]:
    preserved = [
        "domain:" + loaded["domain"],
        "original-retained:" + ("true" if loaded["retain"] else "false"),
        "threshold:" + str(loaded["threshold"]),
        "background:" + str(loaded["background"]),
    ]
    preserved.extend(inventory["originals"])
    preserved.extend(inventory["maps"])
    preserved.extend(inventory["highlights"])
    preserved.extend(inventory["saturated"])
    for item in corrections:
        preserved.append(
            f"mask:{item['frame']}:{item['x']},{item['y']}:{item['confidence']}"
        )
        preserved.append(
            f"corrected:{item['frame']}:{item['x']},{item['y']}:{item['replacement']}"
        )
    if corrections:
        preserved.append("corrections-inspectable:mask-and-original")
    return preserved


def _questions(extra: list[str]) -> list[str]:
    return _dedupe([*extra, "host fixture is not a physical S23 measurement"])


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS and decision not in _FORBIDDEN and decision != MUTANT_ACCEPT,
            "P053 must not decide qualified, allowed, or threshold_cleaned")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons),
            "reasons must be a non-empty list of strings")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": _dedupe(rejected),
        "preservedResults": list(preserved),
        "openQuestions": _dedupe(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def assess(document: dict, sole_test: str = DECLARED_TEST) -> dict:
    """Correct mapped persistent defects. Reject one-threshold bright-pixel removal.

    sole_test "intensity-threshold" is the mutant. It is rejected even when every
    bright pixel is isolated. Original samples and moving highlights stay in
    preservedResults. The threshold replacement is not installed.
    """
    validate_document(document)
    require(sole_test in SOLE_TESTS,
            "sole_test must be measured-defect-map or intensity-threshold")
    loaded = _load(document)
    inventory = _inventory(loaded)
    removals = threshold_removals(loaded)
    mapped_highlights = _highlight_on_map(loaded)
    blocks = [claim for defect in loaded["defects"] if (claim := _site_block(loaded, defect))]
    candidate_corrections: list[dict[str, Any]] = []
    if not blocks and not mapped_highlights:
        for defect in loaded["defects"]:
            candidate_corrections.extend(_corrections(loaded, defect))
    apply = (
        sole_test == DECLARED_TEST
        and loaded["retain"]
        and loaded["domain"] == DECLARED_DOMAIN
        and not mapped_highlights
        and not blocks
        and bool(candidate_corrections)
    )
    corrections = candidate_corrections if apply else []
    preserved = _preserved(loaded, inventory, corrections)
    reasons = [ORACLE, METHOD]
    rejected = ["intensity-threshold-removal"]
    questions: list[str] = []

    if sole_test == MUTANT_TEST:
        decision = "rejected"
        rejected = ["intensity-threshold-removal", *removals]
        reasons.append(MUTANT)
        reasons.append("one intensity threshold would erase the moving highlight")
        reasons.append("threshold removal was not installed")
        questions.append("intensity-threshold removal was rejected")
    elif not loaded["retain"]:
        decision = "rejected"
        rejected = ["original-discarded", *rejected]
        reasons.append("the unmodified original must be retained")
        questions.append("original discard was rejected")
    elif loaded["domain"] != DECLARED_DOMAIN:
        decision = "rejected"
        rejected = ["undeclared-source-domain:" + loaded["domain"], *rejected]
        reasons.append("corrections stay in the declared scene-linear source domain")
        questions.append("undeclared source domain")
    elif mapped_highlights:
        decision = "rejected"
        rejected = [*mapped_highlights, *rejected]
        reasons.append("a moving highlight listed on the defect map was not corrected")
        questions.append(mapped_highlights[0])
    elif blocks or not candidate_corrections:
        decision = "withheld"
        rejected = [*blocks, *rejected]
        if not blocks:
            rejected = ["no-supported-correction", *rejected]
        reasons.append("no correction was applied; the highlight inventory is unchanged")
        questions.extend(blocks or ["no supported correction"])
    else:
        decision = "highlight_preserved"
        reasons.append(
            "persistent defect corrected in scene-linear; moving highlight preserved"
        )
        reasons.append("confidence masks and the unmodified original remain inspectable")
        questions.append("host correction is not a measured sensor defect map")

    reasons.append(HOST_LIMIT)
    return _result(decision, reasons, rejected, preserved, _questions(questions))
