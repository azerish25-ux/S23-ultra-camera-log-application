"""TC-P137-04 Offline search ambiguity.

Host reference. Misspelled titles, alternate titles, and stock names resolve
against the local catalogue. Each candidate keeps its evidence status. A
remote generation call is never performed and must not be required.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P137-04",
    "phase": "P137",
    "workstream": 18,
    "name": "Offline search ambiguity",
    "intervention": "Search misspelled titles, alternate titles, or stock names without network access.",
    "expected": "Return relevant local candidates with transparent matching and evidence status.",
    "negative": "A remote generation call must not be required for basic catalogue lookup.",
    "repeat": "Repeat filtered searches for format, monochrome, and scene family.",
}

PAYLOAD_KEYS = ("evidenceId", "repeat", "query", "filters", "remoteRequired")


def _load_gate():
    path = Path(__file__).resolve().parent / "p137_define_the_movie_evidence_schema.py"
    spec = importlib.util.spec_from_file_location("p137_gate_for_tc04", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    judged = _GATE.search_catalogue(payload["query"], payload["filters"], payload["remoteRequired"])
    reasons = [
        CASE["expected"],
        _GATE.counts_reason(judged["stateCounts"]),
        "networkUsed=" + str(judged["networkUsed"]).lower(),
        "candidates=" + str(len(judged["candidates"])),
    ]
    preserved = [evidence, {
        "stateCounts": judged["stateCounts"],
        "candidates": judged["candidates"],
        "networkUsed": judged["networkUsed"],
    }]
    return _GATE.finish_host(CASE["id"], evidence, list(judged["faults"]), reasons, preserved, repeat)
