"""TC-P144-02 Whole-film overgeneralization.

Several acquisition methods stay as supported variants with scene-level
uncertainty. A title match alone does not establish every scene's recipe.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P144-02",
    "phase": "P144",
    "workstream": 18,
    "name": "Whole-film overgeneralization",
    "intervention": "Provide a source describing several acquisition methods and attempt to assign one to every shot.",
    "expected": "Represent supported variants and preserve uncertainty at scene level.",
    "negative": "A title match alone must not establish every scene\u2019s technical recipe.",
    "repeat": "Repeat mixed color/monochrome, mixed formats, and location-specific stock choices.",
}

TITLE_MATCH = "title-match-alone-does-not-establish-scene-recipe"
ASSIGN_ALL = "one-acquisition-method-assigned-to-every-shot"
NO_VARIANTS = "supported-variants-not-represented"
NO_UNCERTAINTY = "scene-level-uncertainty-not-preserved"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "acquisition_methods",
    "assign_one_to_every_shot",
    "title_match_only",
    "supported_variants",
    "scene_uncertainty_preserved",
    "recipe",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p144_validate_recipe_fidelity_and_honesty.py"
    spec = importlib.util.spec_from_file_location("p144_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _texts(value: object, label: str) -> list[str]:
    _GATE.require(isinstance(value, list) and value, label + " must be a non-empty list")
    return [_GATE.require_text(item, label) for item in value]


def evaluate(payload: dict) -> dict:
    _GATE.require_keys(payload, set(PAYLOAD_KEYS))
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    methods = _texts(payload["acquisition_methods"], "acquisition_methods")
    _GATE.require(len(methods) >= 2, "acquisition_methods must describe several methods")
    assign_all = _GATE.require_bool(payload["assign_one_to_every_shot"], "assign_one_to_every_shot")
    title_only = _GATE.require_bool(payload["title_match_only"], "title_match_only")
    variants = _texts(payload["supported_variants"], "supported_variants") if payload["supported_variants"] else []
    if payload["supported_variants"]:
        _GATE.require(isinstance(payload["supported_variants"], list), "supported_variants must be a list")
    else:
        _GATE.require(isinstance(payload["supported_variants"], list), "supported_variants must be a list")
    uncertainty = _GATE.require_bool(payload["scene_uncertainty_preserved"], "scene_uncertainty_preserved")
    scored = _GATE.score_recipe(payload["recipe"], "recipe")
    faults = list(scored["faults"])
    if title_only:
        faults.append(TITLE_MATCH)
    if assign_all:
        faults.append(ASSIGN_ALL)
    if not variants:
        faults.append(NO_VARIANTS)
    if not uncertainty:
        faults.append(NO_UNCERTAINTY)
    outside = [item for item in variants if item not in set(methods)]
    _GATE.require(not outside, "supported_variants must come from the stated acquisition methods")
    record = {
        "acquisition_methods": methods,
        "supported_variants": variants,
        "assign_one_to_every_shot": assign_all,
        "title_match_only": title_only,
        "scene_uncertainty_preserved": uncertainty,
        "report": scored["report"],
    }
    texts = {
        TITLE_MATCH: CASE["negative"],
        ASSIGN_ALL: "one acquisition method must not be assigned to every shot",
        NO_VARIANTS: "supported variants must be represented",
        NO_UNCERTAINTY: "scene-level uncertainty must be preserved",
    }
    return _GATE.case_result(CASE, evidence, repeat, faults, [record], texts)
