"""TC-P155-03 Unexplored reversible alternative.

Host reference. One failed P010 route does not prove that all ten-bit encoding
is impossible while another public route is untested or still available.
Declaring the broader capture goal blocked is rejected unless every listed
path was tried and unavailable. The comparative rule still applies.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P155-03",
    "phase": "P155",
    "workstream": 20,
    "name": "Unexplored reversible alternative",
    "intervention": "Fail one codec or camera interface while another public route remains untested.",
    "expected": "Evaluate plausible reversible alternatives before declaring the broader capture goal blocked.",
    "negative": "One failed P010 route must not prove all ten-bit encoding impossible.",
    "repeat": "Repeat surface input, reduced geometry, deferred processing, and scheduling changes.",
}

NEGATIVE_TOKEN = "one-failed-p010-proves-all-ten-bit-impossible"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "alternatives",
    "conclusion",
    "declaresAllTenBitEncodingImpossible",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p155_evaluate_reversible_application_level_alternatives.py"
    spec = importlib.util.spec_from_file_location("p155_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _p010_failed(rows: list[dict]) -> bool:
    return any("p010" in row["name"].lower() and row["result"] == "unavailable" for row in rows)


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    declares = _GATE.require_bool(
        payload["declaresAllTenBitEncodingImpossible"],
        "declaresAllTenBitEncodingImpossible",
    )
    rows = [
        {"name": row["name"], "tried": row["tried"], "result": row["result"]}
        for row in bundle["snapshot"]["alternatives"]
    ]
    faults = list(bundle["faults"])
    if declares and not _GATE.honestly_all_unavailable(rows):
        faults.append(NEGATIVE_TOKEN)
    if declares and _p010_failed(rows) and any(row["result"] != "unavailable" for row in rows):
        if NEGATIVE_TOKEN not in faults:
            faults.append(NEGATIVE_TOKEN)
    extra = [{
        "declaresAllTenBitEncodingImpossible": declares,
        "p010Failed": _p010_failed(rows),
        "results": [row["result"] for row in rows],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {NEGATIVE_TOKEN: CASE["negative"]},
    )
