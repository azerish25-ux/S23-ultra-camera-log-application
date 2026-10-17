"""TC-P145-08 Critical preservation defect.

Host fixture. Deleting the sole retained take blocks release until the defect
is fixed and a reproducing regression test passes. Excellent visual quality
cannot waive that gate. A skipped regression is not a pass.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P145-08",
    "phase": "P145",
    "workstream": 19,
    "name": "Critical preservation defect",
    "intervention": "Demonstrate a path that deletes the sole retained take despite otherwise excellent visual quality.",
    "expected": "Block release until the defect is fixed and a reproducing regression test passes.",
    "negative": "Aesthetic quality cannot waive a data-loss gate.",
    "repeat": "Repeat capture failure, publication failure, cancellation, and cold-start recovery.",
}

NEGATIVE_TOKEN = "aesthetic-quality-waives-data-loss"
DATA_LOSS = "data-loss-blocks-release"
SKIP_AS_PASS = "counting-skips-as-passes"
OUTCOMES = ("passed", "failed", "skipped", "absent")
EVENTS = ("capture-failure", "publication-failure", "cancellation", "cold-start-recovery")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "layers",
    "releasePassed",
    "releaseSummary",
    "soleTakeDeleted",
    "visualQuality",
    "defectFixed",
    "regressionOutcome",
    "aestheticWaiver",
    "regressionCountedAsPassed",
    "event",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p145_build_the_layered_automated_test_system.py"
    spec = importlib.util.spec_from_file_location("p145_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_layers(payload, {
        "soleTakeDeleted",
        "visualQuality",
        "defectFixed",
        "regressionOutcome",
        "aestheticWaiver",
        "regressionCountedAsPassed",
        "event",
    })
    faults = list(bundle["faults"])
    deleted = _GATE.require_bool(payload["soleTakeDeleted"], "soleTakeDeleted")
    quality = _GATE.require_number(payload["visualQuality"], "visualQuality")
    _GATE.require(0.0 <= quality <= 1.0, "visualQuality must be between 0 and 1")
    fixed = _GATE.require_bool(payload["defectFixed"], "defectFixed")
    regression = _GATE.require_text(payload["regressionOutcome"], "regressionOutcome")
    _GATE.require(regression in OUTCOMES, "regressionOutcome is not recognized")
    waiver = _GATE.require_bool(payload["aestheticWaiver"], "aestheticWaiver")
    counted = _GATE.require_bool(payload["regressionCountedAsPassed"], "regressionCountedAsPassed")
    event = _GATE.require_text(payload["event"], "event")
    _GATE.require(event in EVENTS, "event is not recognized")
    cleared = fixed and regression == "passed"
    blocked = deleted and not cleared
    excellent = quality >= _GATE.EXCELLENT_VISUAL
    if blocked:
        faults.append(DATA_LOSS)
    if blocked and (waiver or excellent):
        faults.append(NEGATIVE_TOKEN)
    if regression != "passed" and counted:
        faults.append(SKIP_AS_PASS)
    if _GATE.SKIPPED_ADDED_INTO_PASSED in faults or _GATE.RELEASE_PASSED_INCLUDES_SKIPPED in faults:
        faults.append(SKIP_AS_PASS)
    extra = [{
        "soleTakeDeleted": deleted,
        "visualQuality": quality,
        "defectFixed": fixed,
        "regressionOutcome": regression,
        "aestheticWaiver": waiver,
        "regressionCountedAsPassed": counted,
        "event": event,
        "blocked": blocked,
    }]
    texts = {
        DATA_LOSS: CASE["expected"],
        NEGATIVE_TOKEN: CASE["negative"],
        SKIP_AS_PASS: "a skipped regression is not a passing regression",
    }
    return _GATE.finish_layers(CASE, bundle, faults, extra, texts)
