"""TC-P137-05 Publicly accessible but unlicensed asset.

Host reference. A web-accessible still, LUT, or profile keeps its citation.
Unknown redistribution permission excludes the bytes from the release bundle.
Public visibility is not a redistribution licence.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P137-05",
    "phase": "P137",
    "workstream": 18,
    "name": "Publicly accessible but unlicensed asset",
    "intervention": "Offer a web-accessible still, LUT, or profile whose redistribution permission is unknown.",
    "expected": "Retain appropriate citation metadata while excluding unapproved bytes from the release bundle.",
    "negative": "Public visibility must not be treated as a redistribution licence.",
    "repeat": "Repeat promotional images, commercial LUTs, and research model weights.",
}

PAYLOAD_KEYS = ("evidenceId", "repeat", "asset")


def _load_gate():
    path = Path(__file__).resolve().parent / "p137_define_the_movie_evidence_schema.py"
    spec = importlib.util.spec_from_file_location("p137_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    judged = _GATE.judge_asset(payload["asset"])
    reasons = [
        CASE["expected"],
        _GATE.counts_reason(judged["stateCounts"]),
        "citation=" + judged["citation"],
        "bytesInBundle=" + str(judged["bytesInBundle"]).lower(),
    ]
    preserved = [evidence, {
        "stateCounts": judged["stateCounts"],
        "citation": judged["citation"],
        "kind": judged["kind"],
        "redistribution": judged["redistribution"],
        "bytesInBundle": judged["bytesInBundle"],
        "bundleExcluded": judged["bundleExcluded"],
    }]
    return _GATE.finish_host(CASE["id"], evidence, list(judged["faults"]), reasons, preserved, repeat)
