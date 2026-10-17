"""TC-P138-03 Creative edit overwrites evidence.

Host fixture. A user derivative may change virtual aperture, grade, or grain
only by creating a new reconstruction id. It must not replace sourced stock
or lens on the historical family.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P138-03",
    "phase": "P138",
    "workstream": 18,
    "name": "Creative edit overwrites evidence",
    "intervention": "Change virtual aperture, grade, or grain inside a user derivative recipe.",
    "expected": "Create a new reconstruction version without altering historical production facts.",
    "negative": "User preferences must not replace the cinematographer’s sourced metadata.",
    "repeat": "Repeat recipe save, rename, share, and update from a newer catalogue package.",
}

NEGATIVE_TOKEN = "user-preference-replaces-sourced-metadata"
DERIVATIVE_KEYS = {
    "recipe_id",
    "virtualAperture",
    "grade",
    "grain",
    "stock",
    "lens",
    "traces",
    "replacesHistorical",
}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "family",
    "max_entries",
    "derivative",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p138_build_the_first_sourced_recipe_family.py"
    spec = importlib.util.spec_from_file_location("p138_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _optional(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _GATE.require_text(value, label)


def parse_derivative(raw: object, historical_ids: set[str]) -> dict:
    _GATE.require(isinstance(raw, dict), "derivative must be an object")
    _GATE.require(set(raw) == DERIVATIVE_KEYS, "derivative keys are invalid")
    recipe_id = _GATE.require_text(raw["recipe_id"], "derivative recipe_id")
    aperture = _optional(raw["virtualAperture"], "virtualAperture")
    grade = _optional(raw["grade"], "grade")
    grain = _optional(raw["grain"], "grain")
    _GATE.require(
        any(item is not None for item in (aperture, grade, grain)),
        "derivative must change aperture, grade, or grain",
    )
    stock = _optional(raw["stock"], "derivative stock")
    lens = _optional(raw["lens"], "derivative lens")
    _GATE.require(isinstance(raw["traces"], list), "derivative traces must be a list")
    traces = [
        _GATE.parse_trace(item, f"derivative traces[{index}]")
        for index, item in enumerate(raw["traces"])
    ]
    replaces = _GATE.require_bool(raw["replacesHistorical"], "replacesHistorical")
    _GATE.require(recipe_id not in historical_ids, "derivative recipe_id collides with a historical recipe")
    return {
        "recipe_id": recipe_id,
        "virtualAperture": aperture,
        "grade": grade,
        "grain": grain,
        "stock": stock,
        "lens": lens,
        "traces": traces,
        "replacesHistorical": replaces,
    }


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_family_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    historical = bundle["analysis"]["entries"]
    derivative = parse_derivative(payload["derivative"], {entry["recipe_id"] for entry in historical})
    if derivative["replacesHistorical"] or derivative["stock"] is not None or derivative["lens"] is not None:
        faults.append(NEGATIVE_TOKEN)
    if derivative["stock"] is not None and not any(item["field"] == "stock" for item in derivative["traces"]):
        faults.append(_GATE.UNSOURCED_STOCK)
    if derivative["lens"] is not None and not any(item["field"] == "lens" for item in derivative["traces"]):
        faults.append(_GATE.UNSOURCED_LENS)
    facts = [
        {"recipe_id": entry["recipe_id"], "stock": entry["stock"], "lens": entry["lens"]}
        for entry in historical
    ]
    extra = [{
        "derivativeRecipeId": derivative["recipe_id"],
        "virtualAperture": derivative["virtualAperture"],
        "grade": derivative["grade"],
        "grain": derivative["grain"],
        "historicalFacts": facts,
        "replacesHistorical": derivative["replacesHistorical"],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {NEGATIVE_TOKEN: CASE["negative"]},
    )
