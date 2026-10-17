"""TC-P137-02 Whole-film overgeneralization.

Host reference. Several acquisition methods stay as scene variants. A title
match, or one method assigned to every shot, does not become every scene's
technical recipe. Scene-level unknowns remain null.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P137-02",
    "phase": "P137",
    "workstream": 18,
    "name": "Whole-film overgeneralization",
    "intervention": "Provide a source describing several acquisition methods and attempt to assign one to every shot.",
    "expected": "Represent supported variants and preserve uncertainty at scene level.",
    "negative": "A title match alone must not establish every scene\u2019s technical recipe.",
    "repeat": "Repeat mixed color/monochrome, mixed formats, and location-specific stock choices.",
}

PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "variants",
    "assignToEveryShot",
    "titleMatchOnly",
    "sceneUnknowns",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p137_define_the_movie_evidence_schema.py"
    spec = importlib.util.spec_from_file_location("p137_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    judged = _GATE.judge_variants(
        payload["variants"],
        payload["assignToEveryShot"],
        payload["titleMatchOnly"],
        payload["sceneUnknowns"],
    )
    reasons = [
        CASE["expected"],
        _GATE.counts_reason(judged["stateCounts"]),
        "variants=" + str(len(judged["variants"])),
    ]
    preserved = [evidence, {
        "stateCounts": judged["stateCounts"],
        "variants": judged["variants"],
        "sceneUnknowns": judged["sceneUnknowns"],
    }]
    return _GATE.finish_host(CASE["id"], evidence, list(judged["faults"]), reasons, preserved, repeat)
