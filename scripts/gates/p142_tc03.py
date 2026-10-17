"""TC-P142-03 Creative edit overwrites evidence.

Host reference. A user grade, aperture, or grain change creates a new recipe
version. It must not replace the cinematographer's sourced metadata, and the
grade stays inside the declared parameter bounds.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P142-03",
    "phase": "P142",
    "workstream": 18,
    "name": "Creative edit overwrites evidence",
    "intervention": "Change virtual aperture, grade, or grain inside a user derivative recipe.",
    "expected": "Create a new reconstruction version without altering historical production facts.",
    "negative": "User preferences must not replace the cinematographer\u2019s sourced metadata.",
    "repeat": "Repeat recipe save, rename, share, and update from a newer catalogue package.",
}

NEGATIVE_TOKEN = "user-preference-replaced-sourced-metadata"
NO_NEW_VERSION = "creative-edit-did-not-create-new-version"
RECIPE_BOUNDS = "recipe-grade-outside-declared-bounds"
HIST_KEYS = ("cinematographer", "lens", "stock", "process", "aperture")
RECIPE_KEYS = {"version", "aperture", "exposure", "contrast", "saturation", "grain"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "source",
    "reference",
    "suggestion",
    "historical",
    "historicalAfter",
    "priorRecipe",
    "recipe",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p142_implement_constrained_reference_matching.py"
    spec = importlib.util.spec_from_file_location("p142_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _historical(value: object, label: str) -> dict:
    _GATE.require(isinstance(value, dict) and set(value) == set(HIST_KEYS), label + " keys are invalid")
    return {key: _GATE.require_text(value[key], label + "." + key) for key in HIST_KEYS}


def _recipe(value: object, label: str) -> dict:
    _GATE.require(isinstance(value, dict) and set(value) == RECIPE_KEYS, label + " keys are invalid")
    grain = _GATE.require_number(value["grain"], label + ".grain")
    _GATE.require(grain >= 0, label + ".grain must be >= 0")
    return {
        "version": _GATE.require_text(value["version"], label + ".version"),
        "aperture": _GATE.require_text(value["aperture"], label + ".aperture"),
        "exposure": _GATE.require_number(value["exposure"], label + ".exposure"),
        "contrast": _GATE.require_number(value["contrast"], label + ".contrast"),
        "saturation": _GATE.require_number(value["saturation"], label + ".saturation"),
        "grain": grain,
    }


def default_historical():
    return {
        "cinematographer": "Jordan Cronenweth",
        "lens": "unknown",
        "stock": "unknown",
        "process": "bleach bypass",
        "aperture": "T2.8",
    }


def default_prior():
    return {
        "version": "recon-1",
        "aperture": "T2.8",
        "exposure": 0,
        "contrast": 1,
        "saturation": 1,
        "grain": 0.1,
    }


def default_recipe():
    return {
        "version": "recon-2",
        "aperture": "T4",
        "exposure": 0.25,
        "contrast": 1.1,
        "saturation": 0.9,
        "grain": 0.2,
    }


def _changed(prior: dict, recipe: dict) -> bool:
    if prior["aperture"] != recipe["aperture"] or prior["version"] == recipe["version"]:
        if prior["aperture"] != recipe["aperture"]:
            return True
    for name in ("exposure", "contrast", "saturation", "grain"):
        if not _GATE.close_parameter(prior[name], recipe[name]):
            return True
    return prior["aperture"] != recipe["aperture"]


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    historical = _historical(payload["historical"], "historical")
    after = _historical(payload["historicalAfter"], "historicalAfter")
    prior = _recipe(payload["priorRecipe"], "priorRecipe")
    recipe = _recipe(payload["recipe"], "recipe")
    if historical != after:
        faults.append(NEGATIVE_TOKEN)
    creative = _changed(prior, recipe)
    if creative and prior["version"] == recipe["version"]:
        faults.append(NO_NEW_VERSION)
    outside = [
        name
        for name in _GATE.PARAMETER_NAMES
        if not _GATE.value_in_bounds(name, recipe[name])
    ]
    if outside:
        faults.append(RECIPE_BOUNDS)
    extra = [{
        "version": recipe["version"],
        "priorVersion": prior["version"],
        "historicalStock": historical["stock"],
        "historicalUnchanged": historical == after,
        "grade": {
            "exposure": recipe["exposure"],
            "contrast": recipe["contrast"],
            "saturation": recipe["saturation"],
        },
    }]
    text = {
        NEGATIVE_TOKEN: CASE["negative"],
        NO_NEW_VERSION: CASE["expected"],
        RECIPE_BOUNDS: "user grade outside declared bounds: " + ",".join(outside),
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, text)
