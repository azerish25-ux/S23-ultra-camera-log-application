"""TC-P140-06 Reference edition conflict.

Host reference. Distinct releases stay distinct. Averaging them into one
historical look is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P140-06",
    "phase": "P140",
    "workstream": 18,
    "name": "Reference edition conflict",
    "intervention": "Supply references from different film releases or display assumptions with different appearance.",
    "expected": "Keep separate targets or explicit uncertainty rather than inventing one definitive look.",
    "negative": "Averaging inconsistent editions into a historical fact must fail.",
    "repeat": "Repeat theatrical, digital, HDR, and unidentified reference versions.",
}
NEGATIVE_TOKEN = "averaged-inconsistent-editions-into-historical-fact"
EDITION_KEYS = ("editionId", "release", "display", "appearance")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "title",
    "editions",
    "averagedIntoSingleFact",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p140_implement_offline_search_and_filtering.py"
    spec = importlib.util.spec_from_file_location("p140_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    title = _GATE.require_text(payload["title"], "title")
    editions = payload["editions"]
    _GATE.require(isinstance(editions, list) and len(editions) >= 2, "editions must contain at least two targets")
    parsed: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, edition in enumerate(editions):
        _GATE.require(isinstance(edition, dict) and set(edition) == set(EDITION_KEYS), f"editions[{index}] keys are invalid")
        edition_id = _GATE.require_text(edition["editionId"], f"editions[{index}].editionId")
        _GATE.require(edition_id not in seen, "duplicate edition id")
        seen.add(edition_id)
        parsed.append({
            "editionId": edition_id,
            "release": _GATE.require_text(edition["release"], f"editions[{index}].release"),
            "display": _GATE.require_text(edition["display"], f"editions[{index}].display"),
            "appearance": _GATE.require_text(edition["appearance"], f"editions[{index}].appearance"),
        })
    averaged = _GATE.require_bool(payload["averagedIntoSingleFact"], "averagedIntoSingleFact")
    appearances = {item["appearance"] for item in parsed}
    displays = {item["display"] for item in parsed}
    inconsistent = len(appearances) > 1 or len(displays) > 1 or any(item["appearance"] == "unidentified" for item in parsed)
    faults: list[str] = []
    if averaged and inconsistent:
        faults.append(NEGATIVE_TOKEN)
    records = [
        {
            "id": item["editionId"],
            "title": title,
            "release": item["release"],
            "display": item["display"],
            "appearance": item["appearance"],
            "evidenceStatus": "unknown" if item["appearance"] == "unidentified" else "separate-target",
            "privateRecipe": False,
        }
        for item in parsed
    ]
    index = _GATE.build_token_index(records)
    found = _GATE.retrieve(index, title)
    again = _GATE.retrieve(index, title)
    _GATE.require(found == again, "edition lookup was not deterministic")
    _GATE.require("averaged-look" not in found, "averaged edition must not be indexed")
    preserved = [
        evidence,
        {
            "editionIds": found,
            "editions": parsed,
            "averagedIntoSingleFact": False,
            "uncertaintyKept": any(item["appearance"] == "unidentified" for item in parsed),
        },
    ]
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + _GATE.ORACLE,
        CASE["expected"],
        "repeat " + repeat,
        "editionIds=" + ",".join(found),
    ]
    if NEGATIVE_TOKEN in faults:
        reasons.append(CASE["negative"])
    if not faults:
        reasons.append("editions stay separate; no averaged historical look")
    return _GATE.finish_result(CASE["id"], evidence, faults, reasons, preserved, [CASE["repeat"], repeat])
