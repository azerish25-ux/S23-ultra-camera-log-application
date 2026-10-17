"""TC-P145-02 Critical mutant survives.

Host fixture. A plausible fault must make the relevant regression fail.
High line coverage without that failure is not protection. A skipped relevant
test is not a kill and is not a pass.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P145-02",
    "phase": "P145",
    "workstream": 19,
    "name": "Critical mutant survives",
    "intervention": "Insert a plausible fault into a production seam and run the intended regression suite.",
    "expected": "Require the relevant test to fail; surviving critical mutants expose insufficient assertions.",
    "negative": "High line coverage without fault detection must not count as adequate protection.",
    "repeat": "Repeat timestamp pairing, source retention, range signalling, and checkpoint identity mutants.",
}

NEGATIVE_TOKEN = "high-line-coverage-without-fault-detection"
SURVIVED = "critical-mutant-survived"
MUTANTS = ("timestamp-pairing", "source-retention", "range-signalling", "checkpoint-identity")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "layers",
    "releasePassed",
    "releaseSummary",
    "mutant",
    "relevantTestId",
    "lineCoverage",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p145_build_the_layered_automated_test_system.py"
    spec = importlib.util.spec_from_file_location("p145_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_layers(payload, {"mutant", "relevantTestId", "lineCoverage"})
    faults = list(bundle["faults"])
    mutant = _GATE.require_text(payload["mutant"], "mutant")
    _GATE.require(mutant in MUTANTS, "mutant is not in the critical catalogue")
    relevant = _GATE.require_text(payload["relevantTestId"], "relevantTestId")
    coverage = _GATE.require_number(payload["lineCoverage"], "lineCoverage")
    _GATE.require(0.0 <= coverage <= 1.0, "lineCoverage must be between 0 and 1")
    test = bundle["index"].get(relevant)
    killed = test is not None and test["outcome"] == "failed"
    if not killed:
        faults.append(SURVIVED)
        if coverage >= _GATE.COVERAGE_HIGH:
            faults.append(NEGATIVE_TOKEN)
    extra = [{
        "mutant": mutant,
        "relevantTestId": relevant,
        "relevantOutcome": None if test is None else test["outcome"],
        "lineCoverage": coverage,
        "killed": killed,
    }]
    texts = {
        SURVIVED: CASE["expected"],
        NEGATIVE_TOKEN: CASE["negative"],
    }
    return _GATE.finish_layers(CASE, bundle, faults, extra, texts)
