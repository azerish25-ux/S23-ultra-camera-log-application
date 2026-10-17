"""TC-P158-08 Unreproducible research closure.

Host reference. Failed experiments and essential setup details stay in the
archive. A promotional reel cannot substitute for an engineering archive, and
favorable outputs alone cannot close the research record.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P158-08",
    "phase": "P158",
    "workstream": 20,
    "name": "Unreproducible research closure",
    "intervention": "Archive only favorable outputs while omitting failed experiments and essential setup details.",
    "expected": "Preserve enough evidence to reconstruct decisions and reproduce qualified results independently.",
    "negative": "A promotional reel cannot substitute for an engineering archive.",
    "repeat": "Repeat fresh-maintainer reproduction of capture, film rendering, optics, and rejected hypotheses.",
}

NEGATIVE_TOKEN = "promotional-reel-is-not-an-archive"
OMITTED_FAILURES = "failed-experiments-omitted"
SETUP_OMITTED = "setup-details-omitted"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "experimentLabel",
    "captureKind",
    "presentedAs",
    "labelsMergeExplicitly",
    "claimsExtraStops",
    "guaranteedEveryScene",
    "motionAlignment",
    "ghosting",
    "alignmentError",
    "motionArtifacts",
    "retainedHighlights",
    "sourceSampling",
    "motionAssumptions",
    "exposureDifferences",
    "mergeArtifacts",
    "outputLineage",
    "singleExposureBaseline",
    "alternativeRawModes",
    "synchronization",
    "claimsSensorDerivedLog",
    "favorableOutputIds",
    "failedExperimentIds",
    "setupDetails",
    "failuresKnown",
    "promotionalReelOnly",
    "favorableOnly",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p158_explore_advanced_capture_research_independently.py"
    spec = importlib.util.spec_from_file_location("p158_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _archive_faults(
    failed_ids: list[str],
    setup_details: list[str],
    failures_known: int,
    promotional: bool,
    favorable_only: bool,
) -> list[str]:
    _GATE.require(
        len(failed_ids) <= failures_known,
        "failedExperimentIds cannot exceed failuresKnown",
    )
    faults: list[str] = []
    if promotional:
        faults.append(NEGATIVE_TOKEN)
    if favorable_only or len(failed_ids) < failures_known:
        faults.append(OMITTED_FAILURES)
    if not setup_details:
        faults.append(SETUP_OMITTED)
    return faults


def case_payload(**overrides):
    payload = _GATE.core_payload()
    payload.update({
        "repeat": "fresh-maintainer",
        "favorableOutputIds": ["merge-a"],
        "failedExperimentIds": ["ghost-fail", "align-fail"],
        "setupDetails": ["exposure-bracket", "moving-subject", "baseline-id"],
        "failuresKnown": 2,
        "promotionalReelOnly": False,
        "favorableOnly": False,
    })
    payload.update(overrides)
    return payload


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    favorable = _GATE.require_string_list(payload["favorableOutputIds"], "favorableOutputIds", minimum=0)
    failed_ids = _GATE.require_string_list(payload["failedExperimentIds"], "failedExperimentIds", minimum=0)
    setup = _GATE.require_string_list(payload["setupDetails"], "setupDetails", minimum=0)
    failures_known = _GATE.require_int(payload["failuresKnown"], "failuresKnown")
    _GATE.require(failures_known >= 0, "failuresKnown must be >= 0")
    promotional = _GATE.require_bool(payload["promotionalReelOnly"], "promotionalReelOnly")
    favorable_only = _GATE.require_bool(payload["favorableOnly"], "favorableOnly")
    faults = list(bundle["faults"])
    faults.extend(_archive_faults(failed_ids, setup, failures_known, promotional, favorable_only))
    extra = [{
        "favorableOutputIds": favorable,
        "failedExperimentIds": failed_ids,
        "setupDetails": setup,
        "failuresKnown": failures_known,
        "promotionalReelOnly": promotional,
        "favorableOnly": favorable_only,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            OMITTED_FAILURES: CASE["expected"],
            SETUP_OMITTED: CASE["expected"],
        },
    )
