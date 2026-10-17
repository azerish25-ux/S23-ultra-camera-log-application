"""TC-P140-03 Creative edit overwrites evidence.

Host reference. A user derivative is a new private recipe. Historical production
facts stay on the original record.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P140-03",
    "phase": "P140",
    "workstream": 18,
    "name": "Creative edit overwrites evidence",
    "intervention": "Change virtual aperture, grade, or grain inside a user derivative recipe.",
    "expected": "Create a new reconstruction version without altering historical production facts.",
    "negative": "User preferences must not replace the cinematographer\u2019s sourced metadata.",
    "repeat": "Repeat recipe save, rename, share, and update from a newer catalogue package.",
}
NEGATIVE_TOKEN = "user-preferences-replace-sourced-metadata"
REUSED_ID = "derivative-reused-historical-id"
PUBLISHED = "private-user-recipe-published"
FACT_KEYS = ("aperture", "grade", "grain", "stock", "lens")
DERIVATIVE_KEYS = ("id", "name", "virtualAperture", "grade", "grain", "provenance")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "historicalId",
    "title",
    "originalFacts",
    "historicalAfter",
    "derivative",
    "localOnly",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p140_implement_offline_search_and_filtering.py"
    spec = importlib.util.spec_from_file_location("p140_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _facts(value: object, label: str) -> dict[str, str]:
    _GATE.require(isinstance(value, dict) and set(value) == set(FACT_KEYS), label + " keys are invalid")
    return {key: _GATE.require_text(value[key], label + "." + key) for key in FACT_KEYS}


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    historical_id = _GATE.require_text(payload["historicalId"], "historicalId")
    title = _GATE.require_text(payload["title"], "title")
    original = _facts(payload["originalFacts"], "originalFacts")
    after = _facts(payload["historicalAfter"], "historicalAfter")
    derivative = payload["derivative"]
    _GATE.require(isinstance(derivative, dict) and set(derivative) == set(DERIVATIVE_KEYS), "derivative keys are invalid")
    derivative_id = _GATE.require_text(derivative["id"], "derivative.id")
    name = _GATE.require_text(derivative["name"], "derivative.name")
    virtual_aperture = _GATE.require_text(derivative["virtualAperture"], "derivative.virtualAperture")
    grade = _GATE.require_text(derivative["grade"], "derivative.grade")
    grain = _GATE.require_text(derivative["grain"], "derivative.grain")
    provenance = _GATE.require_text(derivative["provenance"], "derivative.provenance")
    local_only = _GATE.require_bool(payload["localOnly"], "localOnly")
    faults: list[str] = []
    changed = [key for key in FACT_KEYS if original[key] != after[key]]
    if changed:
        faults.append(NEGATIVE_TOKEN)
    if derivative_id == historical_id:
        faults.append(REUSED_ID)
    if not local_only:
        faults.append(PUBLISHED)
    historical = {
        "id": historical_id,
        "title": title,
        "stockNames": [original["stock"]],
        "lens": original["lens"],
        "evidenceStatus": "documented",
        "privateRecipe": False,
        "aperture": original["aperture"],
        "grade": original["grade"],
        "grain": original["grain"],
    }
    user_recipe = {
        "id": derivative_id,
        "title": name,
        "stockNames": [original["stock"]],
        "evidenceStatus": "user-reconstruction",
        "privateRecipe": True,
        "virtualAperture": virtual_aperture,
        "grade": grade,
        "grain": grain,
    }
    catalogue = [historical] if local_only else [historical, {**user_recipe, "privateRecipe": False}]
    index = _GATE.build_token_index(catalogue)
    found = _GATE.retrieve(index, title)
    again = _GATE.retrieve(index, title)
    _GATE.require(found == again, "catalogue lookup was not deterministic")
    preserved = [
        evidence,
        {
            "historicalId": historical_id,
            "originalFacts": original,
            "changedFields": changed,
            "derivativeId": derivative_id,
            "provenance": provenance,
            "localOnly": local_only,
            "publicIds": found,
            "privateExcluded": derivative_id if local_only else None,
        },
    ]
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + _GATE.ORACLE,
        CASE["expected"],
        "repeat " + repeat,
    ]
    if NEGATIVE_TOKEN in faults:
        reasons.append(CASE["negative"])
    if not faults:
        reasons.append("historical facts unchanged; derivative stays a private reconstruction")
    return _GATE.finish_result(CASE["id"], evidence, faults, reasons, preserved, [CASE["repeat"], repeat])
