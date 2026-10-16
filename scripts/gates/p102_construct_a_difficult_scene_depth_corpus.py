#!/usr/bin/env python3
"""P102 Construct a difficult-scene depth corpus.

Host reference only. This module does not probe a device, does not qualify a
physical S23, and does not execute TC-P102-01 through TC-P102-08.

The corpus gate hashes scene content, refuses to count a duplicate SHA-256 as
a new scene, requires a non-empty held-out split disjoint from train, and
scores coverage as the fraction of required difficult tags present in held-out.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P102"
GOAL = "Evaluate the scenes that determine whether synthetic cinema blur is usable."
METHOD = "Include hair, fur, glasses, mirrors, water, smoke, fences, thin wires, low texture, motion blur, low light, and crossing subjects. Obtain consent and rights for all footage. Use synthetic geometry where ground truth is available and honest qualitative labels elsewhere."
FIXTURE = "A scene with a person behind a fence and a reflection that appears at a different apparent depth."
ORACLE = "The evaluation records specific boundary and ordering failures rather than averaging them away in one global score."
MUTANT = "Benchmark only isolated portraits against simple backgrounds."
DELIVERABLE = "Difficult-scene corpus and per-category evaluation protocol"

REQUIRED_TAGS = ("hair", "glass", "low light", "thin objects", "mirrors", "saturated")
EASY_TAGS = frozenset({"textured", "portrait", "simple background"})
ALLOWED_TAGS = frozenset(REQUIRED_TAGS) | EASY_TAGS | frozenset({
    "fur",
    "glasses",
    "water",
    "smoke",
    "fences",
    "thin wires",
    "low texture",
    "motion blur",
    "crossing subjects",
    "reflection",
})
SPLITS = frozenset({"train", "held_out"})
DEPTH_KINDS = frozenset({"metric", "relative"})
DEPTH_UNITS = frozenset({"metres", "relative"})
LABEL_SOURCES = frozenset({"synthetic-geometry", "qualitative"})
METRE_TOKEN = "relative-depth-called-metres"
MISSING_TAG_TOKEN = "missing-required-difficult-tag"
EASY_TOKEN = "easy-textured-scenes-only"
DUPLICATE_TOKEN = "duplicate-content-hash"
HELD_OUT_EMPTY_TOKEN = "held-out-empty"
OVERLAP_TOKEN = "held-out-train-hash-overlap"
GLOBAL_SCORE_TOKEN = "averaged-into-one-global-score"
RIGHTS_TOKEN = "rights-not-cleared"
METRIC_TOKEN = "metric-without-ground-truth"
LABEL_TOKEN = "depth-label-inconsistent"

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "scenes",
    "protocol",
}
SCENE_KEYS = {
    "sceneId",
    "content",
    "contentSha256",
    "tags",
    "split",
    "frameCount",
    "depthKind",
    "depthUnit",
    "labelSource",
    "rightsCleared",
    "boundaryFailures",
    "orderingFailures",
}
PROTOCOL_KEYS = {"recordsPerCategory", "globalScore"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DIGEST = re.compile(r"^[0-9a-f]{64}$")
TOKEN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
OPEN_QUESTIONS = (
    "physical S23 measurement was not run",
    "sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def content_hash(content: str) -> str:
    """SHA-256 of UTF-8 scene content. Near-duplicates compare this digest only."""
    require(isinstance(content, str) and content.strip() and content == content.strip(),
            "content must be a non-empty string")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def coverage_score(held_out_tags: set[str]) -> tuple[int, int]:
    """Return (present, total) required difficult tags in the held-out split."""
    present = sum(1 for tag in REQUIRED_TAGS if tag in held_out_tags)
    return present, len(REQUIRED_TAGS)


def _exact(value: object, keys: set[str], label: str) -> dict:
    require(isinstance(value, dict), label + " must be an object")
    missing = keys - set(value)
    extra = set(value) - keys
    require(not missing, label + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, label + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def _token(value: object, label: str) -> str:
    require(isinstance(value, str) and TOKEN.fullmatch(value) is not None, label + " must be a kebab token")
    return value


def _failures(value: object, label: str) -> list[str]:
    require(isinstance(value, list) and len(value) <= 8, label + " must be a list of at most 8 ids")
    parsed = [_token(item, label) for item in value]
    require(len(parsed) == len(set(parsed)), label + " ids must be unique")
    return parsed


def _number(value: object, label: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), label + " must be a number")
    number = float(value)
    require(number == number and number not in {float("inf"), float("-inf")}, label + " must be finite")
    return number


def _scene(value: object, index: int) -> dict[str, Any]:
    scene = _exact(value, SCENE_KEYS, f"scene {index}")
    scene_id = _token(scene["sceneId"], f"scene {index} sceneId")
    content = scene["content"]
    digest = content_hash(content)
    declared = scene["contentSha256"]
    require(isinstance(declared, str) and DIGEST.fullmatch(declared) is not None,
            f"scene {index} contentSha256 must be 64 lowercase hex characters")
    require(declared == digest, f"scene {index} contentSha256 does not match content")
    tags = scene["tags"]
    require(isinstance(tags, list) and 1 <= len(tags) <= 12, f"scene {index} tags must be a non-empty list")
    parsed_tags: list[str] = []
    for tag in tags:
        require(isinstance(tag, str) and tag in ALLOWED_TAGS, f"scene {index} has an unknown tag")
        parsed_tags.append(tag)
    require(len(parsed_tags) == len(set(parsed_tags)), f"scene {index} tags must be unique")
    split = scene["split"]
    require(split in SPLITS, f"scene {index} split must be train or held_out")
    frames = scene["frameCount"]
    require(type(frames) is int and 1 <= frames <= 100000, f"scene {index} frameCount must be a positive int")
    kind = scene["depthKind"]
    unit = scene["depthUnit"]
    source = scene["labelSource"]
    require(kind in DEPTH_KINDS, f"scene {index} depthKind must be metric or relative")
    require(unit in DEPTH_UNITS, f"scene {index} depthUnit must be metres or relative")
    require(source in LABEL_SOURCES, f"scene {index} labelSource is not recognised")
    require(type(scene["rightsCleared"]) is bool, f"scene {index} rightsCleared must be a bool")
    return {
        "sceneId": scene_id,
        "content": content,
        "contentSha256": digest,
        "tags": parsed_tags,
        "split": split,
        "frameCount": frames,
        "depthKind": kind,
        "depthUnit": unit,
        "labelSource": source,
        "rightsCleared": scene["rightsCleared"],
        "boundaryFailures": _failures(scene["boundaryFailures"], f"scene {index} boundaryFailures"),
        "orderingFailures": _failures(scene["orderingFailures"], f"scene {index} orderingFailures"),
    }


def _parse(document: object) -> dict[str, Any]:
    body = _exact(document, DOCUMENT_KEYS, "document")
    require(type(body["schemaVersion"]) is int and body["schemaVersion"] == 1, "schemaVersion must be 1")
    require(body["phase"] == PHASE, "phase must be " + PHASE)
    require(body["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = body["evidenceId"]
    claim = body["claim"]
    require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
            "evidenceId must be a non-empty string")
    require(isinstance(claim, str) and claim.strip() and claim == claim.strip(),
            "claim must be a non-empty string")
    raw_scenes = body["scenes"]
    require(isinstance(raw_scenes, list) and 1 <= len(raw_scenes) <= 32, "scenes must list 1 to 32 entries")
    scenes = [_scene(item, index) for index, item in enumerate(raw_scenes)]
    identities = [scene["sceneId"] for scene in scenes]
    require(len(identities) == len(set(identities)), "sceneId values must be unique")
    protocol = _exact(body["protocol"], PROTOCOL_KEYS, "protocol")
    require(type(protocol["recordsPerCategory"]) is bool, "recordsPerCategory must be a bool")
    score = protocol["globalScore"]
    if score is not None:
        _number(score, "globalScore")
    return {
        "evidenceId": evidence,
        "claim": claim,
        "scenes": scenes,
        "recordsPerCategory": protocol["recordsPerCategory"],
        "globalScore": score,
    }


def _is_easy(tags: set[str]) -> bool:
    return bool(tags) and tags <= EASY_TAGS and tags.isdisjoint(REQUIRED_TAGS)


def _append(items: list[str], token: str) -> None:
    if token not in items:
        items.append(token)


def assess(document: dict) -> dict[str, Any]:
    """Record a difficult-scene corpus or reject it. Never qualifies the host."""
    parsed = _parse(document)
    scenes: list[dict[str, Any]] = parsed["scenes"]
    rejected: list[str] = []
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "near-duplicate rejection uses exact hash equality",
    ]

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for scene in scenes:
        digest = scene["contentSha256"]
        if digest in seen:
            continue
        seen.add(digest)
        unique.append(scene)
    if len(unique) != len(scenes):
        _append(rejected, DUPLICATE_TOKEN)
        reasons.append(
            f"duplicate content hashes are not new scenes; unique {len(unique)} of {len(scenes)}"
        )

    train_hashes = {scene["contentSha256"] for scene in scenes if scene["split"] == "train"}
    held_hashes = {scene["contentSha256"] for scene in scenes if scene["split"] == "held_out"}
    unique_held = [scene for scene in unique if scene["split"] == "held_out"]
    unique_train = [scene for scene in unique if scene["split"] == "train"]
    if not held_hashes:
        _append(rejected, HELD_OUT_EMPTY_TOKEN)
        reasons.append("held-out split is empty")
    overlap = train_hashes & held_hashes
    if overlap:
        _append(rejected, OVERLAP_TOKEN)
        reasons.append("held-out hashes are not disjoint from train")

    held_tags: set[str] = set()
    for scene in unique_held:
        held_tags.update(scene["tags"])
    present, total = coverage_score(held_tags)
    missing = [tag for tag in REQUIRED_TAGS if tag not in held_tags]
    reasons.append(f"coverage-score={present}/{total}")
    if missing:
        _append(rejected, MISSING_TAG_TOKEN)
        reasons.append("held-out missing required tags: " + ", ".join(missing))

    if unique and all(_is_easy(set(scene["tags"])) for scene in unique):
        _append(rejected, EASY_TOKEN)
        _append(rejected, MUTANT)
        reasons.append("mutant rejected: " + MUTANT)

    for scene in scenes:
        if scene["depthKind"] == "relative" and scene["depthUnit"] == "metres":
            _append(rejected, METRE_TOKEN)
            reasons.append(scene["sceneId"] + " calls relative depth metres")
        elif scene["depthKind"] == "metric" and scene["depthUnit"] != "metres":
            _append(rejected, LABEL_TOKEN)
            reasons.append(scene["sceneId"] + " metric depth is not labelled in metres")
        elif scene["depthKind"] == "relative" and scene["depthUnit"] != "relative":
            _append(rejected, LABEL_TOKEN)
        if scene["depthKind"] == "metric" and scene["labelSource"] != "synthetic-geometry":
            _append(rejected, METRIC_TOKEN)
            reasons.append(scene["sceneId"] + " metric depth lacks synthetic ground truth")
        if not scene["rightsCleared"]:
            _append(rejected, RIGHTS_TOKEN)
            reasons.append(scene["sceneId"] + " has no cleared rights")

    if parsed["globalScore"] is not None or parsed["recordsPerCategory"] is not True:
        _append(rejected, GLOBAL_SCORE_TOKEN)
        reasons.append("per-category boundary and ordering failures must stay specific")

    decision = "rejected" if rejected else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    if decision == "recorded":
        reasons.append("difficult-scene corpus retained for " + parsed["evidenceId"])
        reasons.append("method: " + METHOD)
        reasons.append("fixture: " + FIXTURE)

    preserved = [
        parsed["evidenceId"],
        parsed["claim"],
        f"unique-scenes:{len(unique)}",
        f"listed-scenes:{len(scenes)}",
        f"coverage-score:{present}/{total}",
        f"held-out:{len(unique_held)}",
        f"train:{len(unique_train)}",
    ]
    for scene in unique:
        for failure in scene["boundaryFailures"]:
            preserved.append(f"boundary:{scene['sceneId']}:{failure}")
        for failure in scene["orderingFailures"]:
            preserved.append(f"ordering:{scene['sceneId']}:{failure}")
    result = {
        "caseId": PHASE,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": list(OPEN_QUESTIONS),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(parsed["evidenceId"] in result["preservedResults"], "evidence must be preserved")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the corpus")
    return result
