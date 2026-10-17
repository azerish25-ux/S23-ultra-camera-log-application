"""TC-P152-02 Critical mutant survives.

Host reference. A critical mutant with detected false survives. High line
coverage does not replace that kill. The dossier release rule still applies.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P152-02",
    "phase": "P152",
    "workstream": 19,
    "name": "Critical mutant survives",
    "intervention": "Insert a plausible fault into a production seam and run the intended regression suite.",
    "expected": "Require the relevant test to fail; surviving critical mutants expose insufficient assertions.",
    "negative": "High line coverage without fault detection must not count as adequate protection.",
    "repeat": "Repeat timestamp pairing, source retention, range signalling, and checkpoint identity mutants.",
}

NEGATIVE_TOKEN = "coverage-without-fault-detection"
SURVIVOR = "critical-mutant-survived"
MUTANT_KEYS = {"id", "critical", "detected"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "visualQuality",
    "release_decision",
    "citedRiskIds",
    "risks",
    "evidence",
    "lineCoverage",
    "mutants",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p152_run_the_production_readiness_review.py"
    spec = importlib.util.spec_from_file_location("p152_gate_for_tc02", path)
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
            "critical": _GATE.require_bool(item["critical"], f"mutants[{index}].critical"),
            "detected": _GATE.require_bool(item["detected"], f"mutants[{index}].detected"),
        })
    ids = [row["id"] for row in rows]
    _GATE.require(len(ids) == len(set(ids)), "mutant ids must be unique")
    return rows


def _survivor_faults(coverage: float, mutants: list[dict]) -> tuple[list[str], list[str]]:
    survived = [row["id"] for row in mutants if row["critical"] and not row["detected"]]
    faults: list[str] = []
    if survived:
        faults.append(SURVIVOR)
    if coverage >= _GATE.HIGH_COVERAGE and survived:
        faults.append(NEGATIVE_TOKEN)
    return faults, survived


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    coverage = _GATE.require_number(payload["lineCoverage"], "lineCoverage")
    _GATE.require(0 <= coverage <= 1, "lineCoverage must be between 0 and 1")
    mutants = _parse_mutants(payload["mutants"])
    faults = list(bundle["faults"])
    survivor_faults, survived = _survivor_faults(coverage, mutants)
    faults.extend(survivor_faults)
    extra = [{"lineCoverage": coverage, "survivedMutants": survived}]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            SURVIVOR: CASE["expected"],
        },
    )
