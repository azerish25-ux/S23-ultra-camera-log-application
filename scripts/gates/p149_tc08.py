"""TC-P149-08 Critical preservation defect.

Host reference. Deleting the sole retained take blocks release until the defect
is fixed and a reproducing regression passes. Excellent visual quality cannot
waive that data-loss gate.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P149-08",
    "phase": "P149",
    "workstream": 19,
    "name": "Critical preservation defect",
    "intervention": "Demonstrate a path that deletes the sole retained take despite otherwise excellent visual quality.",
    "expected": "Block release until the defect is fixed and a reproducing regression test passes.",
    "negative": "Aesthetic quality cannot waive a data-loss gate.",
    "repeat": "Repeat capture failure, publication failure, cancellation, and cold-start recovery.",
}

NEGATIVE_TOKEN = "aesthetic-quality-cannot-waive-data-loss"
REGRESSION_OPEN = "data-loss-regression-not-passing"
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
    "soleTakeDeleted",
    "visualQuality",
    "defectFixed",
    "regressionExists",
    "regressionPasses",
    "releaseAllowed",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p149_establish_thermal_and_endurance_acceptance.py"
    spec = importlib.util.spec_from_file_location("p149_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _preservation_faults(payload: dict) -> tuple[list[str], dict]:
    deleted = _GATE.require_bool(payload["soleTakeDeleted"], "soleTakeDeleted")
    quality = _GATE.require_text(payload["visualQuality"], "visualQuality")
    fixed = _GATE.require_bool(payload["defectFixed"], "defectFixed")
    exists = _GATE.require_bool(payload["regressionExists"], "regressionExists")
    passes = _GATE.require_bool(payload["regressionPasses"], "regressionPasses")
    allowed = _GATE.require_bool(payload["releaseAllowed"], "releaseAllowed")
    faults: list[str] = []
    closed = fixed and exists and passes
    if deleted and not closed:
        faults.append(REGRESSION_OPEN)
        if allowed or quality.casefold() == "excellent":
            faults.append(NEGATIVE_TOKEN)
    observed = {
        "soleTakeDeleted": deleted,
        "visualQuality": quality,
        "defectFixed": fixed,
        "regressionExists": exists,
        "regressionPasses": passes,
        "releaseAllowed": allowed,
    }
    return faults, observed


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    preservation_faults, observed = _preservation_faults(payload)
    faults = list(bundle["faults"])
    faults.extend(preservation_faults)
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [observed],
        {
            NEGATIVE_TOKEN: CASE["negative"],
            REGRESSION_OPEN: CASE["expected"],
        },
    )
