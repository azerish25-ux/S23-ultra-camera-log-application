"""TC-P143-02 Whole-film overgeneralization.

Host reference. Supported acquisition variants stay at scene level. A title
match alone must not assign one technical recipe to every scene. Release looks
stay distinct.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P143-02",
    "phase": "P143",
    "workstream": 18,
    "name": "Whole-film overgeneralization",
    "intervention": "Provide a source describing several acquisition methods and attempt to assign one to every shot.",
    "expected": "Represent supported variants and preserve uncertainty at scene level.",
    "negative": "A title match alone must not establish every scene’s technical recipe.",
    "repeat": "Repeat mixed color/monochrome, mixed formats, and location-specific stock choices.",
}

NEGATIVE_TOKEN = "title-match-assigns-every-scene"
OVERGENERALIZED = "whole-film-overgeneralization"
UNCERTAINTY_ERASED = "scene-uncertainty-erased"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "looks",
    "dropAmbiguous",
    "acquisitionMethods",
    "titleMatchOnly",
    "assignedToEveryScene",
    "sceneVariants",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p143_support_release_specific_and_scene_specific_looks.py"
    spec = importlib.util.spec_from_file_location("p143_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _variants(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list) and len(value) >= 1, "sceneVariants must be a non-empty list")
    parsed = []
    for index, item in enumerate(value):
        label = f"sceneVariants[{index}]"
        _GATE.require(isinstance(item, dict), label + " must be an object")
        _GATE.require(set(item) == {"scene_id", "method", "uncertain"}, label + " keys are invalid")
        scene_id = _GATE.require_text(item["scene_id"], label + ".scene_id")
        method = item["method"]
        if method is not None:
            method = _GATE.require_text(method, label + ".method")
        uncertain = _GATE.require_bool(item["uncertain"], label + ".uncertain")
        parsed.append({"scene_id": scene_id, "method": method, "uncertain": uncertain})
    return parsed


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    methods_value = payload["acquisitionMethods"]
    _GATE.require(isinstance(methods_value, list) and len(methods_value) >= 1, "acquisitionMethods must be a non-empty list")
    methods = []
    for index, item in enumerate(methods_value):
        methods.append(_GATE.require_text(item, f"acquisitionMethods[{index}]"))
    title_match = _GATE.require_bool(payload["titleMatchOnly"], "titleMatchOnly")
    assigned = _GATE.require_bool(payload["assignedToEveryScene"], "assignedToEveryScene")
    variants = _variants(payload["sceneVariants"])
    if title_match:
        faults.append(NEGATIVE_TOKEN)
    methods_used = {item["method"] for item in variants if item["method"] is not None}
    if assigned and len(methods) > 1 and (len(methods_used) <= 1 or title_match):
        faults.append(OVERGENERALIZED)
    if assigned and any(item["uncertain"] and item["method"] is not None for item in variants):
        faults.append(UNCERTAINTY_ERASED)
    if any(item["uncertain"] and item["method"] is not None and title_match for item in variants):
        faults.append(UNCERTAINTY_ERASED)
    uncertain_ids = [item["scene_id"] for item in variants if item["uncertain"] and item["method"] is None]
    extra = [{
        "acquisitionMethods": methods,
        "titleMatchOnly": title_match,
        "assignedToEveryScene": assigned,
        "sceneVariants": variants,
        "uncertainSceneIds": uncertain_ids,
    }]
    return _GATE.finish_case(CASE, bundle, faults, extra, {
        NEGATIVE_TOKEN: CASE["negative"],
        OVERGENERALIZED: "supported variants must stay at scene level",
        UNCERTAINTY_ERASED: "scene-level uncertainty must be preserved",
    })
