"""TC-P138-02 Whole-film overgeneralization.

Host fixture. A source that documents several acquisition methods must become
separate variants. Scene-level stock and lens stay unknown unless traced.
A title match must not fill every scene.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P138-02",
    "phase": "P138",
    "workstream": 18,
    "name": "Whole-film overgeneralization",
    "intervention": "Provide a source describing several acquisition methods and attempt to assign one to every shot.",
    "expected": "Represent supported variants and preserve uncertainty at scene level.",
    "negative": "A title match alone must not establish every scene’s technical recipe.",
    "repeat": "Repeat mixed color/monochrome, mixed formats, and location-specific stock choices.",
}

NEGATIVE_TOKEN = "title-match-establishes-every-scene"
UNSEPARATED = "supported-variants-not-separated"
SOURCE_METHODS = {"daylight", "low-light", "monochrome", "format"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "family",
    "max_entries",
    "sourceMethods",
    "sceneIds",
    "assignToEveryShot",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p138_build_the_first_sourced_recipe_family.py"
    spec = importlib.util.spec_from_file_location("p138_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _methods(value: object) -> list[str]:
    _GATE.require(isinstance(value, list) and len(value) >= 2, "sourceMethods must list at least two conditions")
    methods: list[str] = []
    for index, item in enumerate(value):
        method = _GATE.require_text(item, f"sourceMethods[{index}]")
        _GATE.require(method in SOURCE_METHODS, "source method is not a supported condition")
        _GATE.require(method not in methods, "duplicate source method")
        methods.append(method)
    return methods


def _scene_ids(value: object, entries: list[dict]) -> list[str]:
    _GATE.require(isinstance(value, list) and len(value) >= 1, "sceneIds must be a non-empty list")
    known = {entry["recipe_id"] for entry in entries}
    scenes: list[str] = []
    for index, item in enumerate(value):
        scene_id = _GATE.require_text(item, f"sceneIds[{index}]")
        _GATE.require(scene_id in known, "scene id is not in the family")
        _GATE.require(scene_id not in scenes, "duplicate scene id")
        scenes.append(scene_id)
    return scenes


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_family_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    methods = _methods(payload["sourceMethods"])
    entries = bundle["analysis"]["entries"]
    scene_ids = _scene_ids(payload["sceneIds"], entries)
    assign_all = _GATE.require_bool(payload["assignToEveryShot"], "assignToEveryShot")
    present = {entry["variant"] for entry in entries}
    if any(method not in present for method in methods):
        faults.append(UNSEPARATED)
    by_id = {entry["recipe_id"]: entry for entry in entries}
    scenes = [by_id[scene_id] for scene_id in scene_ids]
    collapsed = any(entry["stock"] is not None or entry["lens"] is not None for entry in scenes)
    if assign_all or collapsed:
        faults.append(NEGATIVE_TOKEN)
    extra = [{
        "sourceMethods": methods,
        "sceneIds": scene_ids,
        "assignToEveryShot": assign_all,
        "sceneStock": [entry["stock"] for entry in scenes],
        "sceneLens": [entry["lens"] for entry in scenes],
        "variantsPresent": sorted(present),
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            UNSEPARATED: "supported acquisition methods must stay separate variants",
        },
    )
