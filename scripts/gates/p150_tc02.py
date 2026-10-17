"""TC-P150-02 Critical mutant survives.

Host reference. A critical mutant that the regression does not detect survives.
High line coverage does not replace that kill. The release-plan update rule
still applies, including the uninstall-without-warning mutant.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P150-02",
    "phase": "P150",
    "workstream": 19,
    "name": "Critical mutant survives",
    "intervention": "Insert a plausible fault into a production seam and run the intended regression suite.",
    "expected": "Require the relevant test to fail; surviving critical mutants expose insufficient assertions.",
    "negative": "High line coverage without fault detection must not count as adequate protection.",
    "repeat": "Repeat timestamp pairing, source retention, range signalling, and checkpoint identity mutants.",
}

NEGATIVE_TOKEN = "coverage-without-fault-detection"
CRITICAL_MUTANT_SURVIVED = "critical-mutant-survived"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "build_type",
    "signing",
    "update_preserves_private_footage",
    "warns_footage_loss",
    "recommends_uninstall",
    "labelled_production_update",
    "source_revision",
    "recorded_source_revision",
    "is_update",
    "lineCoverage",
    "mutantDetected",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p150_prepare_signing_and_reproducible_distribution.py"
    spec = importlib.util.spec_from_file_location("p150_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    coverage = payload["lineCoverage"]
    _GATE.require(
        isinstance(coverage, (int, float)) and not isinstance(coverage, bool),
        "lineCoverage must be a number",
    )
    coverage = float(coverage)
    _GATE.require(0 <= coverage <= 1, "lineCoverage must be between 0 and 1")
    detected = _GATE.require_bool(payload["mutantDetected"], "mutantDetected")
    faults = list(bundle["faults"])
    if not detected:
        faults.append(CRITICAL_MUTANT_SURVIVED)
        if coverage >= _GATE.HIGH_COVERAGE:
            faults.append(NEGATIVE_TOKEN)
    extra = [{
        "lineCoverage": coverage,
        "mutantDetected": detected,
        "uninstallWithoutWarning": bundle["snapshot"]["uninstall_without_warning"],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            CRITICAL_MUTANT_SURVIVED: CASE["expected"],
        },
    )
