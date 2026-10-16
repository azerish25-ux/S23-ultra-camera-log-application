"""TC-P102-03 Conversion accuracy regression.

Host reference. Withheld scenes are hashed, de-duplicated by exact SHA-256,
and scored for held-out tag coverage. A model that runs without a numerical
comparison is not qualified. Errors above the declared tolerances fail.
"""

from __future__ import annotations

import hashlib
import math
import re

CASE_ID = "TC-P102-03"
NAME = "Conversion accuracy regression"
INTERVENTION = "Compare exported or quantized model results against the approved host baseline on withheld scenes."
EXPECTED = "Meet declared depth and boundary tolerances or remain experimental despite successful loading."
NEGATIVE = "A model that merely runs is not numerically qualified."
REPEAT = "Repeat hair, glass, low light, thin objects, and saturated illumination."
NEGATIVE_TOKEN = "model-merely-runs-numerically-qualified"
REQUIRED_TAGS = ("hair", "glass", "low light", "thin objects", "saturated")
ALLOWED_TAGS = frozenset(REQUIRED_TAGS) | frozenset({
    "mirrors",
    "textured",
    "portrait",
    "simple background",
})
EASY_TAGS = frozenset({"textured", "portrait", "simple background"})
PAYLOAD_KEYS = {
    "evidenceId",
    "repeat",
    "modelRuns",
    "numericallyCompared",
    "depthTolerance",
    "boundaryTolerance",
    "scenes",
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
    "depthError",
    "boundaryError",
}
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


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _finite(value: object, label: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), label + " must be a number")
    number = float(value)
    _require(math.isfinite(number) and number >= 0, label + " must be a non-negative finite number")
    return number


def _scene(value: object, index: int) -> dict:
    _require(isinstance(value, dict) and set(value) == SCENE_KEYS, f"scene {index} keys are invalid")
    scene_id = value["sceneId"]
    _require(isinstance(scene_id, str) and TOKEN.fullmatch(scene_id) is not None, f"scene {index} sceneId")
    content = value["content"]
    _require(isinstance(content, str) and content.strip() and content == content.strip(), f"scene {index} content")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    _require(value["contentSha256"] == digest, f"scene {index} contentSha256 does not match content")
    tags = value["tags"]
    _require(isinstance(tags, list) and tags, f"scene {index} tags")
    for tag in tags:
        _require(isinstance(tag, str) and tag in ALLOWED_TAGS, f"scene {index} unknown tag")
    _require(len(tags) == len(set(tags)), f"scene {index} duplicate tags")
    _require(value["split"] in {"train", "held_out"}, f"scene {index} split")
    frames = value["frameCount"]
    _require(type(frames) is int and frames >= 1, f"scene {index} frameCount")
    _require(value["depthKind"] in {"metric", "relative"}, f"scene {index} depthKind")
    _require(value["depthUnit"] in {"metres", "relative"}, f"scene {index} depthUnit")
    return {
        "sceneId": scene_id,
        "contentSha256": digest,
        "tags": list(tags),
        "split": value["split"],
        "frameCount": frames,
        "depthKind": value["depthKind"],
        "depthUnit": value["depthUnit"],
        "depthError": _finite(value["depthError"], f"scene {index} depthError"),
        "boundaryError": _finite(value["boundaryError"], f"scene {index} boundaryError"),
    }


def evaluate(payload: dict) -> dict:
    _require(isinstance(payload, dict) and set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    _require(type(payload["modelRuns"]) is bool, "modelRuns must be a bool")
    _require(type(payload["numericallyCompared"]) is bool, "numericallyCompared must be a bool")
    depth_tol = _finite(payload["depthTolerance"], "depthTolerance")
    boundary_tol = _finite(payload["boundaryTolerance"], "boundaryTolerance")
    _require(depth_tol > 0 and boundary_tol > 0, "tolerances must be positive")
    raw = payload["scenes"]
    _require(isinstance(raw, list) and 1 <= len(raw) <= 24, "scenes must list 1 to 24 entries")
    scenes = [_scene(item, index) for index, item in enumerate(raw)]
    ids = [scene["sceneId"] for scene in scenes]
    _require(len(ids) == len(set(ids)), "sceneId values must be unique")

    seen: set[str] = set()
    unique = []
    for scene in scenes:
        if scene["contentSha256"] in seen:
            continue
        seen.add(scene["contentSha256"])
        unique.append(scene)
    held = [scene for scene in unique if scene["split"] == "held_out"]
    train_hashes = {scene["contentSha256"] for scene in scenes if scene["split"] == "train"}
    held_hashes = {scene["contentSha256"] for scene in scenes if scene["split"] == "held_out"}
    held_tags: set[str] = set()
    for scene in held:
        held_tags.update(scene["tags"])
    present = sum(1 for tag in REQUIRED_TAGS if tag in held_tags)
    total = len(REQUIRED_TAGS)
    frames = sum(scene["frameCount"] for scene in unique)

    rejected: list[str] = []
    reasons = [
        f"{CASE_ID} {NAME}",
        EXPECTED,
        f"repeat {repeat}",
        "near-duplicate rejection uses exact hash equality",
        f"coverage-score={present}/{total}",
        f"unique scenes {len(unique)} of {len(scenes)}",
    ]
    if len(unique) != len(scenes):
        rejected.append("duplicate-content-hash")
        reasons.append("duplicate content hashes are not new scenes")
    if not held_hashes:
        rejected.append("held-out-empty")
    if train_hashes & held_hashes:
        rejected.append("held-out-train-hash-overlap")
    missing = [tag for tag in REQUIRED_TAGS if tag not in held_tags]
    if missing:
        rejected.append("missing-required-difficult-tag")
        reasons.append("held-out missing " + ", ".join(missing))
    if unique and all(set(scene["tags"]) <= EASY_TAGS for scene in unique):
        rejected.append("easy-textured-scenes-only")
    for scene in scenes:
        if scene["depthKind"] == "relative" and scene["depthUnit"] == "metres":
            if "relative-depth-called-metres" not in rejected:
                rejected.append("relative-depth-called-metres")
            reasons.append(scene["sceneId"] + " calls relative depth metres")
    if payload["modelRuns"] and not payload["numericallyCompared"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    elif not payload["modelRuns"]:
        rejected.append("model-did-not-run")
    elif payload["numericallyCompared"]:
        for scene in held:
            if scene["depthError"] > depth_tol or scene["boundaryError"] > boundary_tol:
                if "depth-boundary-tolerance-exceeded" not in rejected:
                    rejected.append("depth-boundary-tolerance-exceeded")
                reasons.append(
                    scene["sceneId"]
                    + f" depth {scene['depthError']} boundary {scene['boundaryError']}"
                )
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("withheld scenes meet declared depth and boundary tolerances")
    return _finish(decision, reasons, rejected, evidence, [f"coverage-score:{present}/{total}", f"frames:{frames}"])


def _finish(decision: str, reasons: list[str], rejected: list[str], evidence: str, extra: list[str]) -> dict:
    _require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, *extra],
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result
