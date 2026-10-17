"""TC-P133-02 Source-look label confusion.

Host reference. The actual source and the simulated recipe stay independent.
Renaming a source mode after the virtual format is rejected. Recipe controls
remain separate from capture controls.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P133-02",
    "phase": "P133",
    "workstream": 17,
    "name": "Source-look label confusion",
    "intervention": (
        "Select a large-format film recipe while the underlying source remains a "
        "lower-resolution SDR or experimental RAW route."
    ),
    "expected": "Display the actual source and simulated look independently with their evidence status.",
    "negative": "Renaming a source mode after the virtual format must fail.",
    "repeat": "Repeat preset changes, saved recipe reopening, and export sharing.",
}

NEGATIVE_TOKEN = "renamed-source-mode-after-virtual-format"
LOOK_HIDDEN = "look-not-displayed-independently"
LARGE_FORMAT_UNLABELLED = "large-format-appearance-not-labelled-simulated"
LOOK_EVIDENCE_QUALIFIED = "look-evidence-marked-qualified"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "controls",
    "focusOrder",
    "sourceMode",
    "sourceEvidenceStatus",
    "recipeLabel",
    "recipeEvidenceStatus",
    "displayedSourceLabel",
    "displayedRecipeLabel",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p133_implement_accessible_focus_and_recipe_controls.py"
    spec = importlib.util.spec_from_file_location("p133_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    source_mode = _GATE.require_text(payload["sourceMode"], "sourceMode")
    source_evidence = _GATE.require_text(payload["sourceEvidenceStatus"], "sourceEvidenceStatus")
    recipe_label = _GATE.require_text(payload["recipeLabel"], "recipeLabel")
    recipe_evidence = _GATE.require_text(payload["recipeEvidenceStatus"], "recipeEvidenceStatus")
    displayed_source = _GATE.require_text(payload["displayedSourceLabel"], "displayedSourceLabel")
    displayed_recipe = _GATE.require_text(payload["displayedRecipeLabel"], "displayedRecipeLabel")
    source = _GATE.find_control(bundle["controls"], _GATE.SOURCE_STATUS_ID)
    recipe = _GATE.find_control(bundle["controls"], _GATE.RECIPE_ID)
    source_state = source["state_description"] if source is not None else ""
    recipe_state = recipe["state_description"] if recipe is not None else ""
    renamed = (
        displayed_source != source_mode
        or _GATE.same_label(displayed_source, recipe_label)
        or _GATE.looks_like_virtual_format(displayed_source)
        and not _GATE.looks_like_virtual_format(source_mode)
        or source_mode not in source_state
        or recipe_label.casefold() in source_state.casefold()
        or _GATE.looks_like_virtual_format(source_state)
        and not _GATE.looks_like_virtual_format(source_mode)
        or source_evidence.casefold() in {"qualified", "allowed"}
        or _GATE.looks_like_virtual_format(source_evidence)
    )
    if renamed or source is None:
        faults.append(NEGATIVE_TOKEN)
    if recipe is None or displayed_recipe != recipe_label or recipe_label.casefold() not in recipe_state.casefold():
        faults.append(LOOK_HIDDEN)
    if _GATE.looks_like_virtual_format(recipe_label) and recipe_evidence != "simulated":
        faults.append(LARGE_FORMAT_UNLABELLED)
    if recipe_evidence.casefold() in {"qualified", "allowed"}:
        faults.append(LOOK_EVIDENCE_QUALIFIED)
    extra = [{
        "sourceMode": source_mode,
        "displayedSourceLabel": displayed_source,
        "recipeLabel": recipe_label,
        "displayedRecipeLabel": displayed_recipe,
        "sourceEvidenceStatus": source_evidence,
        "recipeEvidenceStatus": recipe_evidence,
        "sourceState": source_state,
        "recipeState": recipe_state,
        "recipeSeparate": bundle["public"]["recipeSeparate"],
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        LOOK_HIDDEN: "the simulated look must be displayed independently of the source",
        LARGE_FORMAT_UNLABELLED: "a large-format recipe must be labelled simulated",
        LOOK_EVIDENCE_QUALIFIED: "look evidence must not be marked qualified or allowed",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
