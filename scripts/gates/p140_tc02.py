"""TC-P140-02 Whole-film overgeneralization.

Host reference. Mixed acquisition stays on the scenes that support it. A title
match does not assign one recipe to every scene.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P140-02",
    "phase": "P140",
    "workstream": 18,
    "name": "Whole-film overgeneralization",
    "intervention": "Provide a source describing several acquisition methods and attempt to assign one to every shot.",
    "expected": "Represent supported variants and preserve uncertainty at scene level.",
    "negative": "A title match alone must not establish every scene\u2019s technical recipe.",
    "repeat": "Repeat mixed color/monochrome, mixed formats, and location-specific stock choices.",
}
NEGATIVE_TOKEN = "title-match-alone-establishes-every-scene-recipe"
WIPED = "scene-level-uncertainty-wiped"
SCENE_KEYS = ("sceneId", "acquisition", "monochrome", "format", "stock", "location", "uncertain")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "movieId",
    "title",
    "scenes",
    "assignOneMethodToEveryScene",
    "uncertaintyWiped",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p140_implement_offline_search_and_filtering.py"
    spec = importlib.util.spec_from_file_location("p140_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_scenes(scenes: object) -> list[dict]:
    _GATE.require(isinstance(scenes, list) and len(scenes) >= 2, "scenes must contain at least two variants")
    parsed: list[dict] = []
    seen: set[str] = set()
    for index, scene in enumerate(scenes):
        _GATE.require(isinstance(scene, dict) and set(scene) == set(SCENE_KEYS), f"scenes[{index}] keys are invalid")
        scene_id = _GATE.require_text(scene["sceneId"], f"scenes[{index}].sceneId")
        _GATE.require(scene_id not in seen, "duplicate scene id")
        seen.add(scene_id)
        parsed.append({
            "sceneId": scene_id,
            "acquisition": _GATE.require_text(scene["acquisition"], f"scenes[{index}].acquisition"),
            "monochrome": _GATE.require_bool(scene["monochrome"], f"scenes[{index}].monochrome"),
            "format": _GATE.require_text(scene["format"], f"scenes[{index}].format"),
            "stock": _GATE.require_text(scene["stock"], f"scenes[{index}].stock"),
            "location": _GATE.require_text(scene["location"], f"scenes[{index}].location"),
            "uncertain": _GATE.require_bool(scene["uncertain"], f"scenes[{index}].uncertain"),
        })
    return parsed


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    movie_id = _GATE.require_text(payload["movieId"], "movieId")
    title = _GATE.require_text(payload["title"], "title")
    scenes = _parse_scenes(payload["scenes"])
    assign_all = _GATE.require_bool(payload["assignOneMethodToEveryScene"], "assignOneMethodToEveryScene")
    wiped = _GATE.require_bool(payload["uncertaintyWiped"], "uncertaintyWiped")
    faults: list[str] = []
    if assign_all:
        faults.append(NEGATIVE_TOKEN)
    if wiped:
        faults.append(WIPED)
    records = [{
        "id": movie_id,
        "title": title,
        "evidenceStatus": "partial",
        "privateRecipe": False,
    }]
    for scene in scenes:
        records.append({
            "id": scene["sceneId"],
            "title": title,
            "stockNames": [scene["stock"]],
            "formats": [scene["format"]],
            "sceneFamilies": [scene["location"]],
            "acquisition": scene["acquisition"],
            "monochrome": scene["monochrome"],
            "evidenceStatus": "unknown" if scene["uncertain"] else "documented",
            "privateRecipe": False,
        })
    index = _GATE.build_token_index(records)
    title_ids = _GATE.retrieve(index, title)
    title_ids_again = _GATE.retrieve(index, title)
    _GATE.require(title_ids == title_ids_again, "title lookup was not deterministic")
    stock_ids = [
        _GATE.retrieve(index, scene["stock"], {"formats": scene["format"]})
        for scene in scenes
    ]
    acquisitions = sorted({scene["acquisition"] for scene in scenes})
    preserved = [
        evidence,
        {
            "movieId": movie_id,
            "titleIds": title_ids,
            "sceneRecipes": scenes,
            "acquisitions": acquisitions,
            "stockLookups": stock_ids,
            "singleRecipeAssigned": False,
        },
    ]
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + _GATE.ORACLE,
        CASE["expected"],
        "repeat " + repeat,
        "variants=" + ",".join(acquisitions),
    ]
    if NEGATIVE_TOKEN in faults:
        reasons.append(CASE["negative"])
    if not faults:
        reasons.append("scene variants stay separate; title match is not a whole-film recipe")
    return _GATE.finish_result(CASE["id"], evidence, faults, reasons, preserved, [CASE["repeat"], repeat])
