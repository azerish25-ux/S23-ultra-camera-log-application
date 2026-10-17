"""TC-P141-02 Whole-film overgeneralization.

Host fixture. Several acquisition methods stay as variants. Uncertainty is
kept at scene level. A title match alone does not write one recipe onto
every shot. Rights are still judged per asset.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P141-02",
    "phase": "P141",
    "workstream": 18,
    "name": "Whole-film overgeneralization",
    "intervention": "Provide a source describing several acquisition methods and attempt to assign one to every shot.",
    "expected": "Represent supported variants and preserve uncertainty at scene level.",
    "negative": "A title match alone must not establish every scene\u2019s technical recipe.",
    "repeat": "Repeat mixed color/monochrome, mixed formats, and location-specific stock choices.",
}

NEGATIVE_TOKEN = "title-match-alone-establishes-recipe"
ONE_RECIPE = "one-recipe-assigned-to-every-shot"
SCENE_KEYS = {"scene_id", "acquisition", "recipe", "uncertain"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "assets",
    "titleMatchOnly",
    "scenes",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p141_manage_reference_media_rights_and_attribution.py"
    spec = importlib.util.spec_from_file_location("p141_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_scenes(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list) and len(value) >= 1, "scenes must be a non-empty list")
    parsed = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict) and set(item) == SCENE_KEYS, f"scenes[{index}] keys are invalid")
        scene_id = _GATE.require_text(item["scene_id"], f"scenes[{index}].scene_id")
        _GATE.require(scene_id not in seen, "duplicate scene_id " + scene_id)
        seen.add(scene_id)
        acquisition = _GATE.require_text(item["acquisition"], f"scenes[{index}].acquisition")
        recipe = item["recipe"]
        if recipe is not None:
            recipe = _GATE.require_text(recipe, f"scenes[{index}].recipe")
        uncertain = _GATE.require_bool(item["uncertain"], f"scenes[{index}].uncertain")
        parsed.append(
            {
                "scene_id": scene_id,
                "acquisition": acquisition,
                "recipe": recipe,
                "uncertain": uncertain,
            }
        )
    return parsed


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    title_only = _GATE.require_bool(payload["titleMatchOnly"], "titleMatchOnly")
    scenes = _parse_scenes(payload["scenes"])
    if title_only:
        faults.append(NEGATIVE_TOKEN)
    acquisitions = {scene["acquisition"] for scene in scenes}
    recipes = [scene["recipe"] for scene in scenes]
    assigned = [recipe for recipe in recipes if recipe is not None]
    if len(acquisitions) > 1 and len(assigned) == len(scenes) and len(set(assigned)) == 1:
        faults.append(ONE_RECIPE)
    extra = [{
        "titleMatchOnly": title_only,
        "sceneCount": len(scenes),
        "acquisitions": sorted(acquisitions),
        "uncertainSceneIds": [scene["scene_id"] for scene in scenes if scene["uncertain"]],
        "recipes": [{"scene_id": scene["scene_id"], "recipe": scene["recipe"]} for scene in scenes],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            ONE_RECIPE: "one technical recipe must not be assigned to every shot when acquisition methods differ",
        },
    )
