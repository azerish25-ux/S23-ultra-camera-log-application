"""TC-P144-01 Missing production fact.

An unknown production fact may stay a labelled creative reconstruction.
A plausible equipment guess marked documented is rejected. Identification
still requires a source; a star rating cannot fill the missing fact.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P144-01",
    "phase": "P144",
    "workstream": 18,
    "name": "Missing production fact",
    "intervention": "Remove verified lens or scene-specific stock information from an otherwise complete movie record.",
    "expected": "Keep the fact unknown while allowing a clearly labelled creative reconstruction.",
    "negative": "A plausible equipment guess marked documented must fail.",
    "repeat": "Repeat camera, lens, stock, process, and release-version fields.",
}

PRODUCTION_FIELDS = frozenset({"camera", "lens", "stock", "process", "release-version"})
GUESS_DOCUMENTED = "plausible-equipment-guess-marked-documented"
UNLABELLED = "unknown-fact-not-labelled-as-creative-reconstruction"
UNKNOWN_IDENTIFIED = "unknown-production-fact-marked-identified"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "field",
    "fact_known",
    "labelled_creative_reconstruction",
    "marked_documented",
    "recipe",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p144_validate_recipe_fidelity_and_honesty.py"
    spec = importlib.util.spec_from_file_location("p144_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    _GATE.require_keys(payload, set(PAYLOAD_KEYS))
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    field = _GATE.require_text(payload["field"], "field")
    _GATE.require(field in PRODUCTION_FIELDS, "field is not a production fact")
    fact_known = _GATE.require_bool(payload["fact_known"], "fact_known")
    labelled = _GATE.require_bool(
        payload["labelled_creative_reconstruction"], "labelled_creative_reconstruction"
    )
    marked = _GATE.require_bool(payload["marked_documented"], "marked_documented")
    scored = _GATE.score_recipe(payload["recipe"], "recipe")
    faults = list(scored["faults"])
    if not fact_known and marked:
        faults.append(GUESS_DOCUMENTED)
    if not fact_known and not labelled:
        faults.append(UNLABELLED)
    if not fact_known and scored["report"]["identification"]["correct"]:
        faults.append(UNKNOWN_IDENTIFIED)
    record = {
        "field": field,
        "known": fact_known,
        "labelled_creative_reconstruction": labelled,
        "marked_documented": marked,
        "report": scored["report"],
    }
    texts = {
        GUESS_DOCUMENTED: CASE["negative"],
        UNLABELLED: "an unknown fact needs a clearly labelled creative reconstruction",
        UNKNOWN_IDENTIFIED: "a missing production fact cannot be marked identified",
    }
    return _GATE.case_result(CASE, evidence, repeat, faults, [record], texts)
