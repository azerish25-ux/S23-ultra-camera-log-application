"""TC-P137-08 Preference mistaken for factual accuracy.

Host reference. User ratings stay preference scores. A higher rating on a
reconstructed recipe does not promote stock or lens to fact. Popularity
cannot certify an identification.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P137-08",
    "phase": "P137",
    "workstream": 18,
    "name": "Preference mistaken for factual accuracy",
    "intervention": "Give a popular reconstructed recipe higher user ratings than a well-sourced alternative.",
    "expected": "Keep appearance preference separate from evidence completeness and historical claims.",
    "negative": "Popularity cannot certify a stock or lens identification.",
    "repeat": "Repeat blind comparisons, expert review, and conflicting production sources.",
}

PAYLOAD_KEYS = ("evidenceId", "repeat", "recipes")


def _load_gate():
    path = Path(__file__).resolve().parent / "p137_define_the_movie_evidence_schema.py"
    spec = importlib.util.spec_from_file_location("p137_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    judged = _GATE.judge_preferences(payload["recipes"])
    reasons = [
        CASE["expected"],
        _GATE.counts_reason(judged["stateCounts"]),
        "preferenceSeparate=" + str(judged["preferenceSeparate"]).lower(),
    ]
    preserved = [evidence, {
        "stateCounts": judged["stateCounts"],
        "preferences": judged["preferences"],
        "recipes": judged["recipes"],
        "preferenceSeparate": judged["preferenceSeparate"],
    }]
    return _GATE.finish_host(CASE["id"], evidence, list(judged["faults"]), reasons, preserved, repeat)
