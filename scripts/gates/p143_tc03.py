"""TC-P143-03 Creative edit overwrites evidence.

Host reference. Aperture, grade, or grain edits allocate a new reconstruction
version. Historical production facts stay unchanged. User preference must not
replace sourced cinematography metadata. Release looks stay distinct.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P143-03",
    "phase": "P143",
    "workstream": 18,
    "name": "Creative edit overwrites evidence",
    "intervention": "Change virtual aperture, grade, or grain inside a user derivative recipe.",
    "expected": "Create a new reconstruction version without altering historical production facts.",
    "negative": "User preferences must not replace the cinematographer’s sourced metadata.",
    "repeat": "Repeat recipe save, rename, share, and update from a newer catalogue package.",
}

NEGATIVE_TOKEN = "user-preference-replaced-sourced-metadata"
MISSING_VERSION = "edit-without-new-reconstruction-version"
EDIT_FIELDS = frozenset({"aperture", "grade", "grain"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "looks",
    "dropAmbiguous",
    "historicalFacts",
    "derivativeEdits",
    "newVersionId",
    "overwritesHistoricalFacts",
    "preferenceReplacesMetadata",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p143_support_release_specific_and_scene_specific_looks.py"
    spec = importlib.util.spec_from_file_location("p143_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    facts = payload["historicalFacts"]
    _GATE.require(isinstance(facts, dict) and len(facts) >= 1, "historicalFacts must be a non-empty object")
    preserved_facts = {}
    for key, value in facts.items():
        name = _GATE.require_text(key, "historicalFacts key")
        preserved_facts[name] = _GATE.require_text(value, "historicalFacts." + name)
    edits_value = payload["derivativeEdits"]
    _GATE.require(isinstance(edits_value, dict), "derivativeEdits must be an object")
    edits = {}
    for key, value in edits_value.items():
        _GATE.require(key in EDIT_FIELDS, "derivativeEdits field is not aperture, grade, or grain")
        edits[key] = _GATE.require_number(value, "derivativeEdits." + key)
    new_version = payload["newVersionId"]
    if new_version is not None:
        new_version = _GATE.require_text(new_version, "newVersionId")
    overwrites = _GATE.require_bool(payload["overwritesHistoricalFacts"], "overwritesHistoricalFacts")
    preference = _GATE.require_bool(payload["preferenceReplacesMetadata"], "preferenceReplacesMetadata")
    if overwrites or preference:
        faults.append(NEGATIVE_TOKEN)
    if edits and new_version is None:
        faults.append(MISSING_VERSION)
    extra = [{
        "historicalFacts": preserved_facts,
        "derivativeEdits": edits,
        "newVersionId": new_version,
        "overwritesHistoricalFacts": overwrites,
        "preferenceReplacesMetadata": preference,
    }]
    return _GATE.finish_case(CASE, bundle, faults, extra, {
        NEGATIVE_TOKEN: CASE["negative"],
        MISSING_VERSION: "a creative edit must create a new reconstruction version",
    })
