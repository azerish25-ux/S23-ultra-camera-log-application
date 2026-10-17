"""TC-P154-08 Unreproducible research closure.

Host reference. An archive that keeps only favorable outputs, drops failed
experiments, or omits essential setup cannot reconstruct the decision. A
promotional reel does not substitute for that engineering archive.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P154-08",
    "phase": "P154",
    "workstream": 20,
    "name": "Unreproducible research closure",
    "intervention": "Archive only favorable outputs while omitting failed experiments and essential setup details.",
    "expected": "Preserve enough evidence to reconstruct decisions and reproduce qualified results independently.",
    "negative": "A promotional reel cannot substitute for an engineering archive.",
    "repeat": "Repeat fresh-maintainer reproduction of capture, film rendering, optics, and rejected hypotheses.",
}

NEGATIVE_TOKEN = "promotional-reel-substitutes-for-engineering-archive"
FAILED_OMITTED = "failed-experiments-omitted"
SETUP_OMITTED = "essential-setup-omitted"
SETUP_KEYS = ("model", "firmwareApplicability", "method", "seeds")
CASE_FIELDS = {
    "favorableOutputs",
    "failedExperiments",
    "setup",
    "promotionalReelOnly",
}


def _load_gate():
    path = Path(__file__).resolve().parent / "p154_survey_public_firmware_and_hal_information.py"
    spec = importlib.util.spec_from_file_location("p154_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_setup(value: object) -> dict:
    _GATE.require(isinstance(value, dict), "setup must be an object")
    _GATE.require(set(value) == set(SETUP_KEYS), "setup keys are invalid")
    return {key: _GATE.require_text(value[key], "setup." + key) for key in SETUP_KEYS}


def _archive_faults(failed: list[str], setup: dict, reel_only: bool) -> list[str]:
    faults: list[str] = []
    if reel_only:
        faults.append(NEGATIVE_TOKEN)
    if not failed:
        faults.append(FAILED_OMITTED)
    if any(setup[key] == "omitted" for key in SETUP_KEYS):
        faults.append(SETUP_OMITTED)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, CASE_FIELDS)
    favorable = _GATE.parse_string_list(payload["favorableOutputs"], "favorableOutputs", allow_empty=True)
    failed = _GATE.parse_string_list(payload["failedExperiments"], "failedExperiments", allow_empty=True)
    setup = _parse_setup(payload["setup"])
    reel_only = _GATE.require_bool(payload["promotionalReelOnly"], "promotionalReelOnly")
    faults = list(bundle["faults"])
    faults.extend(_archive_faults(failed, setup, reel_only))
    extra = [{
        "favorableOutputs": favorable,
        "failedExperiments": failed,
        "setup": setup,
        "promotionalReelOnly": reel_only,
        "reconstructable": not reel_only and bool(failed) and all(setup[key] != "omitted" for key in SETUP_KEYS),
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            FAILED_OMITTED: CASE["intervention"],
            SETUP_OMITTED: CASE["expected"],
        },
    )
