"""TC-P148-02 Critical mutant survives.

Host reference. A critical mutant that the relevant test does not detect
survives and is rejected. High line coverage does not replace that kill.
The offline privacy rule still applies.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P148-02",
    "phase": "P148",
    "workstream": 19,
    "name": "Critical mutant survives",
    "intervention": "Insert a plausible fault into a production seam and run the intended regression suite.",
    "expected": "Require the relevant test to fail; surviving critical mutants expose insufficient assertions.",
    "negative": "High line coverage without fault detection must not count as adequate protection.",
    "repeat": "Repeat timestamp pairing, source retention, range signalling, and checkpoint identity mutants.",
}

NEGATIVE_TOKEN = "coverage-without-fault-detection"
SURVIVING = "critical-mutant-survived"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "offline_claim",
    "permissions",
    "network_endpoints",
    "analytics_payload",
    "capture_needs_camera",
    "capture_needs_microphone",
    "visible_warnings",
    "hide_warnings",
    "uploads",
    "diagnostic_export",
    "optional_downloads_explicit",
    "operation_requires_network",
    "lineCoverage",
    "faultDetected",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p148_verify_offline_privacy_and_permissions.py"
    spec = importlib.util.spec_from_file_location("p148_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    coverage = _GATE.require_number(payload["lineCoverage"], "lineCoverage")
    _GATE.require(0 <= coverage <= 1, "lineCoverage must be between 0 and 1")
    detected = _GATE.require_bool(payload["faultDetected"], "faultDetected")
    faults = list(bundle["faults"])
    if not detected:
        faults.append(SURVIVING)
        if coverage >= _GATE.HIGH_COVERAGE:
            faults.append(NEGATIVE_TOKEN)
    extra = [{"lineCoverage": coverage, "faultDetected": detected}]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            SURVIVING: CASE["expected"],
        },
    )
