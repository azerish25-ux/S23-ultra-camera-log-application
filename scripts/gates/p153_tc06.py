"""TC-P153-06 Computational capture overclaim.

Host reference. A merge of more than one exposure is computational acquisition.
It must be labeled as a merge, and motion artifacts and retained information
are measured separately. Presenting that merge as one unchanged sensor
exposure is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

PRESENTED = frozenset({
    "single-unchanged-sensor-exposure",
    "computational-merge",
    "single-exposure",
})
MERGE_PROVENANCE = "merge-cannot-erase-source-sampling-provenance"
UNMEASURED_MERGE = "computational-merge-artifacts-and-information-unmeasured"
LABEL = "computational-acquisition-not-labeled"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "hypotheses",
    "questions",
    "plan",
    "limiter",
    "applyMutant",
    "exposure_count",
    "presented_as",
    "motion_artifacts_measured",
    "retained_information_measured",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p153_identify_the_actual_blocked_capability.py"
    spec = importlib.util.spec_from_file_location("p153_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()
CASE = dict(_GATE.CASES[5])


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    count = _GATE.require_int(payload["exposure_count"], "exposure_count")
    _GATE.require(count >= 1, "exposure_count must be >= 1")
    presented = _GATE.require_text(payload["presented_as"], "presented_as")
    _GATE.require(presented in PRESENTED, "presented_as is not recognized")
    motion = _GATE.require_bool(payload["motion_artifacts_measured"], "motion_artifacts_measured")
    retained = _GATE.require_bool(payload["retained_information_measured"], "retained_information_measured")
    faults = list(bundle["faults"])
    if count > 1:
        if presented == "single-unchanged-sensor-exposure":
            faults.append(MERGE_PROVENANCE)
        if presented != "computational-merge":
            faults.append(LABEL)
        if not motion or not retained:
            faults.append(UNMEASURED_MERGE)
    elif presented == "computational-merge":
        faults.append(LABEL)
    extra = [{
        "exposure_count": count,
        "presented_as": presented,
        "motion_artifacts_measured": motion,
        "retained_information_measured": retained,
        "computational": count > 1,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            MERGE_PROVENANCE: CASE["negative"],
            UNMEASURED_MERGE: CASE["expected"],
            LABEL: CASE["expected"],
        },
    )


def example_payload(**overrides):
    payload = _GATE.core_payload(repeat="moving-subjects")
    payload.update({
        "exposure_count": 1,
        "presented_as": "single-exposure",
        "motion_artifacts_measured": False,
        "retained_information_measured": False,
    })
    payload.update(overrides)
    return payload
