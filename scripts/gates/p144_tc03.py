"""TC-P144-03 Creative edit overwrites evidence.

Aperture, grade, or grain edits allocate a new reconstruction version.
Historical production facts stay byte-identical. User preference must not
replace the cinematographer's sourced metadata.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P144-03",
    "phase": "P144",
    "workstream": 18,
    "name": "Creative edit overwrites evidence",
    "intervention": "Change virtual aperture, grade, or grain inside a user derivative recipe.",
    "expected": "Create a new reconstruction version without altering historical production facts.",
    "negative": "User preferences must not replace the cinematographer\u2019s sourced metadata.",
    "repeat": "Repeat recipe save, rename, share, and update from a newer catalogue package.",
}

EDITS = frozenset({"aperture", "grade", "grain"})
NO_NEW_VERSION = "creative-edit-missing-new-reconstruction-version"
FACTS_CHANGED = "creative-edit-altered-historical-production-facts"
PREFERENCE_REPLACED = "user-preference-replaced-sourced-metadata"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "edit",
    "parent_version_id",
    "new_version_id",
    "historical_facts",
    "derivative_facts",
    "preference_replaced_sourced_metadata",
    "recipe",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p144_validate_recipe_fidelity_and_honesty.py"
    spec = importlib.util.spec_from_file_location("p144_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    _GATE.require_keys(payload, set(PAYLOAD_KEYS))
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    edit = _GATE.require_text(payload["edit"], "edit")
    _GATE.require(edit in EDITS, "edit is not aperture, grade, or grain")
    parent = _GATE.require_text(payload["parent_version_id"], "parent_version_id")
    new_id = _GATE.require_text(payload["new_version_id"], "new_version_id")
    _GATE.require(isinstance(payload["historical_facts"], dict), "historical_facts must be an object")
    _GATE.require(isinstance(payload["derivative_facts"], dict), "derivative_facts must be an object")
    replaced = _GATE.require_bool(
        payload["preference_replaced_sourced_metadata"], "preference_replaced_sourced_metadata"
    )
    scored = _GATE.score_recipe(payload["recipe"], "recipe")
    faults = list(scored["faults"])
    unchanged = _GATE.same_facts(payload["historical_facts"], payload["derivative_facts"])
    if new_id == parent:
        faults.append(NO_NEW_VERSION)
    if not unchanged:
        faults.append(FACTS_CHANGED)
    if replaced:
        faults.append(PREFERENCE_REPLACED)
    record = {
        "edit": edit,
        "parent_version_id": parent,
        "new_version_id": new_id,
        "historical_facts_unchanged": unchanged,
        "preference_replaced_sourced_metadata": replaced,
        "report": scored["report"],
    }
    texts = {
        NO_NEW_VERSION: "a creative edit must create a new reconstruction version",
        FACTS_CHANGED: "historical production facts must stay unchanged",
        PREFERENCE_REPLACED: CASE["negative"],
    }
    return _GATE.case_result(CASE, evidence, repeat, faults, [record], texts)
