"""TC-P149-02 Critical mutant survives.

Host reference. The critical mutant ignores severe thermal status to keep an
advertised frame rate. The gate must reject that payload. High line coverage
does not replace a failed detection.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P149-02",
    "phase": "P149",
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
    "thermalStatus",
    "continueCapture",
    "controlledStop",
    "advertisedFpsClaimed",
    "optionalPreviewReduced",
    "footagePreserved",
    "sampleDurationSeconds",
    "frameRateGuaranteeClaimed",
    "measuredOnDevice",
    "envelopeStatus",
    "configuration",
    "ambientCelsius",
    "deviceState",
    "lineCoverage",
    "mutantDetected",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p149_establish_thermal_and_endurance_acceptance.py"
    spec = importlib.util.spec_from_file_location("p149_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _suite_killed_canonical_mutant() -> bool:
    result = _GATE.evaluate(_GATE.canonical_severe_mutant())
    return (
        result["decision"] == "rejected"
        and _GATE.ADVERTISED_FPS_IGNORED_SEVERE in result["rejectedClaims"]
        and result["decision"] not in {"qualified", "allowed"}
    )


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    coverage = _GATE.require_number(payload["lineCoverage"], "lineCoverage")
    _GATE.require(0 <= coverage <= 1, "lineCoverage must be between 0 and 1")
    detected = _GATE.require_bool(payload["mutantDetected"], "mutantDetected")
    faults = list(bundle["faults"])
    killed = _suite_killed_canonical_mutant()
    if not killed or not detected:
        faults.append(_GATE.MUTANT_NOT_DETECTED)
    if coverage >= _GATE.HIGH_COVERAGE and not detected:
        faults.append(NEGATIVE_TOKEN)
    extra = [{
        "lineCoverage": coverage,
        "mutantDetected": detected,
        "canonicalMutantKilled": killed,
        "ignoredSevereForAdvertisedFps": bundle["snapshot"]["ignoredSevereForAdvertisedFps"],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            _GATE.MUTANT_NOT_DETECTED: CASE["expected"],
        },
    )
