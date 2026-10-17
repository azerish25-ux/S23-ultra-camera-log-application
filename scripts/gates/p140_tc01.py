"""TC-P140-01 Missing production fact.

Host reference. A removed lens or stock fact stays unknown. A creative
reconstruction is allowed only when it is labelled and is not marked documented.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P140-01",
    "phase": "P140",
    "workstream": 18,
    "name": "Missing production fact",
    "intervention": "Remove verified lens or scene-specific stock information from an otherwise complete movie record.",
    "expected": "Keep the fact unknown while allowing a clearly labelled creative reconstruction.",
    "negative": "A plausible equipment guess marked documented must fail.",
    "repeat": "Repeat camera, lens, stock, process, and release-version fields.",
}
NEGATIVE_TOKEN = "plausible-equipment-guess-marked-documented"
UNLABELLED = "creative-reconstruction-not-clearly-labelled"
OVERWROTE = "unknown-fact-not-kept"
FACT_FIELDS = ("camera", "lens", "stock", "process", "releaseVersion")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "recordId",
    "title",
    "facts",
    "documented",
    "guessField",
    "guessValue",
    "creativeReconstruction",
    "reconstructionLabel",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p140_implement_offline_search_and_filtering.py"
    spec = importlib.util.spec_from_file_location("p140_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    record_id = _GATE.require_text(payload["recordId"], "recordId")
    title = _GATE.require_text(payload["title"], "title")
    facts = payload["facts"]
    _GATE.require(isinstance(facts, dict) and set(facts) == set(FACT_FIELDS), "facts keys are invalid")
    for field in FACT_FIELDS:
        _GATE.require_text(facts[field], "facts." + field)
    documented = payload["documented"]
    _GATE.require(isinstance(documented, list), "documented must be a list")
    seen: list[str] = []
    for index, field in enumerate(documented):
        _GATE.require(field in FACT_FIELDS, f"documented[{index}] is not a production fact")
        _GATE.require(field not in seen, "documented fields must be unique")
        seen.append(field)
    guess_field = payload["guessField"]
    _GATE.require(guess_field in FACT_FIELDS, "guessField is not a production fact")
    guess_value = _GATE.require_text(payload["guessValue"], "guessValue")
    creative = _GATE.require_bool(payload["creativeReconstruction"], "creativeReconstruction")
    label = payload["reconstructionLabel"]
    _GATE.require(isinstance(label, str), "reconstructionLabel must be a string")
    fact_value = facts[guess_field]
    labelled = "creative reconstruction" in label.casefold()
    faults: list[str] = []
    if guess_field in documented:
        faults.append(NEGATIVE_TOKEN)
    if fact_value != "unknown":
        faults.append(OVERWROTE)
        if fact_value == guess_value and guess_field in documented:
            faults.append(NEGATIVE_TOKEN)
    elif creative and not labelled:
        faults.append(UNLABELLED)
    record = {
        "id": record_id,
        "title": title,
        "evidenceStatus": "unknown" if fact_value == "unknown" else "documented",
        "camera": facts["camera"],
        "lens": facts["lens"],
        "stockNames": [facts["stock"]],
        "process": facts["process"],
        "releaseVersion": facts["releaseVersion"],
        "privateRecipe": False,
    }
    index = _GATE.build_token_index([record])
    found = _GATE.retrieve(index, title)
    again = _GATE.retrieve(index, title)
    _GATE.require(found == again, "title lookup was not deterministic")
    reconstruction = None
    if creative and labelled and fact_value == "unknown" and guess_field not in documented:
        reconstruction = {
            "label": label,
            "field": guess_field,
            "value": guess_value,
            "documented": False,
        }
    preserved = [
        evidence,
        {
            "id": record_id,
            "unknownField": guess_field,
            "factValue": fact_value,
            "documented": list(documented),
            "searchIds": found,
            "reconstruction": reconstruction,
            "guessExcludedFromDocumentedFacts": guess_field not in documented and fact_value != guess_value,
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
        reasons.append("missing fact stays unknown; reconstruction is labelled and not documented")
    questions = [CASE["repeat"], repeat]
    return _GATE.finish_result(CASE["id"], evidence, faults, reasons, preserved, questions)
