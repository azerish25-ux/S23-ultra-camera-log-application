"""TC-P137-03 Creative edit overwrites evidence.

Host reference. Aperture, grade, or grain edits create a new reconstruction
version. Historical production facts stay put. User preferences must not
replace sourced metadata, and a reconstruction must not be relabelled fact.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P137-03",
    "phase": "P137",
    "workstream": 18,
    "name": "Creative edit overwrites evidence",
    "intervention": "Change virtual aperture, grade, or grain inside a user derivative recipe.",
    "expected": "Create a new reconstruction version without altering historical production facts.",
    "negative": "User preferences must not replace the cinematographer\u2019s sourced metadata.",
    "repeat": "Repeat recipe save, rename, share, and update from a newer catalogue package.",
}

PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "historical",
    "derivative",
    "operation",
    "changed",
    "historicalVersion",
    "derivativeVersion",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p137_define_the_movie_evidence_schema.py"
    spec = importlib.util.spec_from_file_location("p137_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    judged = _GATE.judge_derivative(
        payload["historical"],
        payload["derivative"],
        payload["operation"],
        payload["changed"],
        payload["historicalVersion"],
        payload["derivativeVersion"],
    )
    reasons = [
        CASE["expected"],
        _GATE.counts_reason(judged["stateCounts"]),
        "operation=" + judged["operation"],
        "version " + judged["historicalVersion"] + " -> " + judged["derivativeVersion"],
    ]
    preserved = [evidence, {
        "stateCounts": judged["stateCounts"],
        "historicalFacts": judged["historicalFacts"],
        "derivativeVersion": judged["derivativeVersion"],
        "changed": judged["changed"],
        "retainedFields": judged["derivative"]["retainedFields"],
    }]
    return _GATE.finish_host(CASE["id"], evidence, list(judged["faults"]), reasons, preserved, repeat)
