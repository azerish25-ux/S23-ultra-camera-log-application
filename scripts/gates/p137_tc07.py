"""TC-P137-07 Parameter matching alters content.

Host reference. Look matching may touch declared rendering parameters only.
Facial geometry, texture replacement, text, fine patterns, and moving objects
are unrequested synthesis. A generated scene is not preserved camera footage.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P137-07",
    "phase": "P137",
    "workstream": 18,
    "name": "Parameter matching alters content",
    "intervention": "Use an automatic look suggestion that changes facial geometry or replaces scene texture.",
    "expected": "Reject unrequested content synthesis and restrict matching to declared rendering parameters.",
    "negative": "A visually similar generated scene is not preserved camera footage.",
    "repeat": "Repeat faces, text, fine patterns, and moving objects.",
}

PAYLOAD_KEYS = ("evidenceId", "repeat", "footageId", "outputId", "parameters", "alters")


def _load_gate():
    path = Path(__file__).resolve().parent / "p137_define_the_movie_evidence_schema.py"
    spec = importlib.util.spec_from_file_location("p137_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    judged = _GATE.judge_match(
        payload["footageId"],
        payload["outputId"],
        payload["parameters"],
        payload["alters"],
    )
    reasons = [
        CASE["expected"],
        _GATE.counts_reason(judged["stateCounts"]),
        "preservedFootage=" + judged["preservedFootage"],
    ]
    preserved = [evidence, {
        "stateCounts": judged["stateCounts"],
        "preservedFootage": judged["preservedFootage"],
        "parameters": judged["parameters"],
        "alters": judged["alters"],
        "footageId": judged["footageId"],
    }]
    return _GATE.finish_host(CASE["id"], evidence, list(judged["faults"]), reasons, preserved, repeat)
