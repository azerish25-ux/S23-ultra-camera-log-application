"""TC-P151-02 Critical mutant survives.

Host reference. A mutant with expected_detection true and detected false is a
surviving critical mutant. High line coverage does not replace that kill.
Release-note badge rules still apply.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P151-02",
    "phase": "P151",
    "workstream": 19,
    "name": "Critical mutant survives",
    "intervention": "Insert a plausible fault into a production seam and run the intended regression suite.",
    "expected": "Require the relevant test to fail; surviving critical mutants expose insufficient assertions.",
    "negative": "High line coverage without fault detection must not count as adequate protection.",
    "repeat": "Repeat timestamp pairing, source retention, range signalling, and checkpoint identity mutants.",
}

NEGATIVE_TOKEN = "coverage-without-fault-detection"
MUTANT_SURVIVED = "critical-mutant-survived"
MUTANT_KEYS = {"id", "expected_detection", "detected", "critical"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "claims",
    "implementedFeatures",
    "aspirationalRequirements",
    "knownFailures",
    "lineCoverage",
    "mutants",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p151_generate_honest_release_notes_and_capability_badges.py"
    spec = importlib.util.spec_from_file_location("p151_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_mutants(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list) and bool(value), "mutants must be a non-empty list")
    rows = []
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict), f"mutants[{index}] must be an object")
        _GATE.require(set(item) == MUTANT_KEYS, f"mutants[{index}] keys are invalid")
        rows.append({
            "id": _GATE.require_text(item["id"], f"mutants[{index}].id"),
            "expected_detection": _GATE.require_bool(
                item["expected_detection"], f"mutants[{index}].expected_detection"
            ),
            "detected": _GATE.require_bool(item["detected"], f"mutants[{index}].detected"),
            "critical": _GATE.require_bool(item["critical"], f"mutants[{index}].critical"),
        })
    ids = [row["id"] for row in rows]
    _GATE.require(len(ids) == len(set(ids)), "mutant ids must be unique")
    return rows


def _mutant_faults(coverage: float, mutants: list[dict]) -> tuple[list[str], list[str]]:
    survived = [
        row["id"]
        for row in mutants
        if row["critical"] and row["expected_detection"] and not row["detected"]
    ]
    faults: list[str] = []
    if survived:
        faults.append(MUTANT_SURVIVED)
        if coverage >= _GATE.HIGH_COVERAGE:
            faults.append(NEGATIVE_TOKEN)
    return faults, survived


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    coverage_value = payload["lineCoverage"]
    _GATE.require(
        isinstance(coverage_value, (int, float)) and not isinstance(coverage_value, bool),
        "lineCoverage must be a number",
    )
    coverage_number = float(coverage_value)
    _GATE.require(coverage_number == coverage_number, "lineCoverage must be finite")
    _GATE.require(0 <= coverage_number <= 1, "lineCoverage must be between 0 and 1")
    mutants = _parse_mutants(payload["mutants"])
    mutant_faults, survived = _mutant_faults(coverage_number, mutants)
    faults = list(bundle["faults"])
    faults.extend(mutant_faults)
    extra = [{"lineCoverage": coverage_number, "survivedMutants": survived}]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            MUTANT_SURVIVED: CASE["expected"],
        },
    )
