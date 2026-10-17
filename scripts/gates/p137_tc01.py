"""TC-P137-01 Missing production fact.

Host reference. Removing a verified lens or scene-specific stock leaves that
field unknown. A reconstructed virtual lens may remain. Filling the missing
lens with a guessed name marked documented or fact is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P137-01",
    "phase": "P137",
    "workstream": 18,
    "name": "Missing production fact",
    "intervention": "Remove verified lens or scene-specific stock information from an otherwise complete movie record.",
    "expected": "Keep the fact unknown while allowing a clearly labelled creative reconstruction.",
    "negative": "A plausible equipment guess marked documented must fail.",
    "repeat": "Repeat camera, lens, stock, process, and release-version fields.",
}

PAYLOAD_KEYS = ("evidenceId", "repeat", "record", "removed", "filledLens")


def _load_gate():
    path = Path(__file__).resolve().parent / "p137_define_the_movie_evidence_schema.py"
    spec = importlib.util.spec_from_file_location("p137_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    record = _GATE.strip_fields(payload["record"], payload["removed"])
    filled = payload["filledLens"]
    if filled is not None:
        _GATE.require(isinstance(filled, dict), "filledLens must be an object or null")
        _GATE.require(filled.get("name") == "lens", "filledLens must name the production lens")
        replaced = False
        for index, field in enumerate(record["fields"]):
            if field.get("name") == "lens":
                record["fields"][index] = filled
                replaced = True
                break
        if not replaced:
            record["fields"].append(filled)
    judged = _GATE.judge_record(record)
    detail = _GATE.detail_from_judged(judged)
    reasons = [CASE["expected"], _GATE.counts_reason(judged["stateCounts"])]
    lens = detail["productionLens"]
    virtual = detail["virtualLens"]
    if lens is not None and lens["state"] == "unknown" and lens["value"] is None:
        reasons.append("production lens retained as unknown")
    if virtual is not None and virtual["state"] == "reconstruction":
        reasons.append("virtual lens kept as reconstruction")
    preserved = [evidence, detail]
    return _GATE.finish_host(CASE["id"], evidence, list(judged["faults"]), reasons, preserved, repeat)
