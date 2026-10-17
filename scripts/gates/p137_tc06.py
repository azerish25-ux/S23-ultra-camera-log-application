"""TC-P137-06 Reference edition conflict.

Host reference. Theatrical, digital, HDR, and unidentified references stay
separate when their appearance differs. Averaging them into one historical
fact is rejected. Uncertainty remains an unknown rather than a fabricated look.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P137-06",
    "phase": "P137",
    "workstream": 18,
    "name": "Reference edition conflict",
    "intervention": "Supply references from different film releases or display assumptions with different appearance.",
    "expected": "Keep separate targets or explicit uncertainty rather than inventing one definitive look.",
    "negative": "Averaging inconsistent editions into a historical fact must fail.",
    "repeat": "Repeat theatrical, digital, HDR, and unidentified reference versions.",
}

PAYLOAD_KEYS = ("evidenceId", "repeat", "references", "definitive")


def _load_gate():
    path = Path(__file__).resolve().parent / "p137_define_the_movie_evidence_schema.py"
    spec = importlib.util.spec_from_file_location("p137_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    judged = _GATE.judge_editions(payload["references"], payload["definitive"])
    reasons = [
        CASE["expected"],
        _GATE.counts_reason(judged["stateCounts"]),
        "distinctAppearances=" + str(judged["distinctAppearances"]),
    ]
    preserved = [evidence, {
        "stateCounts": judged["stateCounts"],
        "references": judged["references"],
        "definitive": judged["definitive"],
        "distinctAppearances": judged["distinctAppearances"],
    }]
    return _GATE.finish_host(CASE["id"], evidence, list(judged["faults"]), reasons, preserved, repeat)
