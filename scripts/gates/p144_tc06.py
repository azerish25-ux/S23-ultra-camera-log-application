"""TC-P144-06 Reference edition conflict.

Different releases and display assumptions keep separate targets or an
explicit uncertainty. Averaging inconsistent editions into one historical
fact is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P144-06",
    "phase": "P144",
    "workstream": 18,
    "name": "Reference edition conflict",
    "intervention": "Supply references from different film releases or display assumptions with different appearance.",
    "expected": "Keep separate targets or explicit uncertainty rather than inventing one definitive look.",
    "negative": "Averaging inconsistent editions into a historical fact must fail.",
    "repeat": "Repeat theatrical, digital, HDR, and unidentified reference versions.",
}

EDITION_KEYS = {"edition_id", "appearance"}
AVERAGED = "averaged-inconsistent-editions-into-historical-fact"
INVENTED = "conflicting-editions-collapsed-into-one-definitive-look"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "editions",
    "separate_targets",
    "uncertainty_explicit",
    "averaged_into_historical_fact",
    "recipe",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p144_validate_recipe_fidelity_and_honesty.py"
    spec = importlib.util.spec_from_file_location("p144_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _edition(value: object, label: str) -> dict:
    _GATE.require(isinstance(value, dict), label + " must be an object")
    _GATE.require(set(value) == EDITION_KEYS, label + " keys are invalid")
    return {
        "edition_id": _GATE.require_text(value["edition_id"], label + ".edition_id"),
        "appearance": _GATE.require_text(value["appearance"], label + ".appearance"),
    }


def evaluate(payload: dict) -> dict:
    _GATE.require_keys(payload, set(PAYLOAD_KEYS))
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    raw = payload["editions"]
    _GATE.require(isinstance(raw, list) and len(raw) >= 2, "editions must contain at least two references")
    editions = [_edition(item, "editions[{}]".format(index)) for index, item in enumerate(raw)]
    separate = _GATE.require_bool(payload["separate_targets"], "separate_targets")
    uncertainty = _GATE.require_bool(payload["uncertainty_explicit"], "uncertainty_explicit")
    averaged = _GATE.require_bool(payload["averaged_into_historical_fact"], "averaged_into_historical_fact")
    scored = _GATE.score_recipe(payload["recipe"], "recipe")
    appearances = {item["appearance"] for item in editions}
    inconsistent = len(appearances) > 1
    faults = list(scored["faults"])
    if inconsistent and averaged:
        faults.append(AVERAGED)
    if inconsistent and not separate and not uncertainty:
        faults.append(INVENTED)
    record = {
        "editions": editions,
        "inconsistent": inconsistent,
        "separate_targets": separate,
        "uncertainty_explicit": uncertainty,
        "averaged_into_historical_fact": averaged,
        "report": scored["report"],
    }
    texts = {
        AVERAGED: CASE["negative"],
        INVENTED: "conflicting editions need separate targets or explicit uncertainty",
    }
    return _GATE.case_result(CASE, evidence, repeat, faults, [record], texts)
