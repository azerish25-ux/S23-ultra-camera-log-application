"""TC-P142-01 Missing production fact.

Host reference. An unknown lens, stock, or release stays unknown. A clearly
labelled creative reconstruction is allowed. A plausible equipment guess marked
documented is rejected. The bounded parameter suggestion is still only a
suggestion.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P142-01",
    "phase": "P142",
    "workstream": 18,
    "name": "Missing production fact",
    "intervention": "Remove verified lens or scene-specific stock information from an otherwise complete movie record.",
    "expected": "Keep the fact unknown while allowing a clearly labelled creative reconstruction.",
    "negative": "A plausible equipment guess marked documented must fail.",
    "repeat": "Repeat camera, lens, stock, process, and release-version fields.",
}

NEGATIVE_TOKEN = "plausible-equipment-guess-marked-documented"
UNKNOWN_FILLED = "unknown-production-fact-filled"
UNLABELLED = "creative-reconstruction-not-labelled"
FACT_FIELDS = ("camera", "lens", "stock", "process", "release_version")
FACT_KEYS = {"status", "documented", "value", "label"}
PAYLOAD_KEYS = ("evidenceId", "repeat", "source", "reference", "suggestion", "facts")


def _load_gate():
    path = Path(__file__).resolve().parent / "p142_implement_constrained_reference_matching.py"
    spec = importlib.util.spec_from_file_location("p142_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _fact(value: object, label: str) -> dict:
    _GATE.require(isinstance(value, dict) and set(value) == FACT_KEYS, label + " keys are invalid")
    status = _GATE.require_text(value["status"], label + ".status")
    _GATE.require(status in {"known", "unknown", "guess"}, label + ".status is not recognized")
    documented = _GATE.require_bool(value["documented"], label + ".documented")
    raw_value = value["value"]
    if raw_value is not None:
        raw_value = _GATE.require_text(raw_value, label + ".value")
    label_value = value["label"]
    if label_value is not None:
        label_value = _GATE.require_text(label_value, label + ".label")
        _GATE.require(
            label_value in {"historical", "creative-reconstruction"},
            label + ".label is not recognized",
        )
    return {
        "status": status,
        "documented": documented,
        "value": raw_value,
        "label": label_value,
    }


def clean_facts(**overrides):
    facts = {
        "camera": {"status": "known", "documented": True, "value": "Alexa 35", "label": "historical"},
        "lens": {"status": "unknown", "documented": False, "value": None, "label": None},
        "stock": {
            "status": "guess",
            "documented": False,
            "value": "labelled creative stock note",
            "label": "creative-reconstruction",
        },
        "process": {"status": "known", "documented": True, "value": "bleach bypass", "label": "historical"},
        "release_version": {"status": "unknown", "documented": False, "value": None, "label": None},
    }
    for field, replacement in overrides.items():
        facts[field] = replacement
    return facts


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    raw = payload["facts"]
    _GATE.require(isinstance(raw, dict) and set(raw) == set(FACT_FIELDS), "facts keys are invalid")
    facts = {field: _fact(raw[field], "facts." + field) for field in FACT_FIELDS}
    for field in FACT_FIELDS:
        fact = facts[field]
        if fact["documented"] and fact["status"] != "known":
            faults.append(NEGATIVE_TOKEN)
        if fact["status"] == "unknown" and (
            fact["value"] is not None or fact["documented"] or fact["label"] is not None
        ):
            faults.append(UNKNOWN_FILLED)
        if fact["status"] == "guess":
            if fact["label"] != "creative-reconstruction":
                faults.append(UNLABELLED)
            if fact["value"] is None:
                raise ValueError(field + " guess needs a labelled value")
        if fact["status"] == "known":
            if not fact["documented"] or fact["value"] is None or fact["label"] != "historical":
                raise ValueError(field + " known fact is incomplete")
    extra = [{
        "field": field,
        "status": facts[field]["status"],
        "documented": facts[field]["documented"],
        "label": facts[field]["label"],
    } for field in FACT_FIELDS]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            UNKNOWN_FILLED: "an unknown production fact must stay unknown",
            UNLABELLED: CASE["expected"],
        },
    )
