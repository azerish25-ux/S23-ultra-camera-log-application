"""TC-P146-02 Critical mutant survives.

Host reference. A mutant with expected_detection true and detected false is a
surviving critical mutant. High line coverage does not replace that kill.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P146-02",
    "phase": "P146",
    "workstream": 19,
    "name": "Critical mutant survives",
    "intervention": "Insert a plausible fault into a production seam and run the intended regression suite.",
    "expected": "Require the relevant test to fail; surviving critical mutants expose insufficient assertions.",
    "negative": "High line coverage without fault detection must not count as adequate protection.",
    "repeat": "Repeat timestamp pairing, source retention, range signalling, and checkpoint identity mutants.",
}

NEGATIVE_TOKEN = "coverage-without-fault-detection"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "samples",
    "shuffled",
    "reportedSum",
    "reportedShuffledSum",
    "propertySuite",
    "catalogue",
    "lineCoverage",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p146_add_property_and_mutation_testing.py"
    spec = importlib.util.spec_from_file_location("p146_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    coverage = _GATE.require_number(payload["lineCoverage"], "lineCoverage")
    _GATE.require(0 <= coverage <= 1, "lineCoverage must be between 0 and 1")
    faults = list(bundle["faults"])
    survived = bundle["snapshot"]["survivedMutants"]
    if coverage >= _GATE.HIGH_COVERAGE and survived:
        faults.append(NEGATIVE_TOKEN)
    extra = [{"lineCoverage": coverage, "survivedMutants": list(survived)}]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {NEGATIVE_TOKEN: CASE["negative"]},
    )
