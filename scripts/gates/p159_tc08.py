"""TC-P159-08 Unreproducible research closure.

Host reference. An archive that keeps only favorable outputs, or that omits
failed experiments and essential setup, cannot reconstruct the decision. A
promotional reel is not an engineering archive.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P159-08",
    "phase": "P159",
    "workstream": 20,
    "name": "Unreproducible research closure",
    "intervention": "Archive only favorable outputs while omitting failed experiments and essential setup details.",
    "expected": "Preserve enough evidence to reconstruct decisions and reproduce qualified results independently.",
    "negative": "A promotional reel cannot substitute for an engineering archive.",
    "repeat": "Repeat fresh-maintainer reproduction of capture, film rendering, optics, and rejected hypotheses.",
}

NEGATIVE_TOKEN = "promotional-reel-substitutes-for-archive"
FAILED_OMITTED = "failed-experiments-omitted"
SETUP_OMITTED = "essential-setup-omitted"
FAVORABLE_ONLY = "favorable-only-archive"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "baseline_stable",
    "stabilityNoted",
    "baselineRank",
    "candidates",
    "records",
    "promotionalReelOnly",
)
RECORD_KEYS = {"id", "outcome", "setupIncluded"}


def _load_gate():
    path = Path(__file__).resolve().parent / "p159_explore_higher_quality_computational_optics.py"
    spec = importlib.util.spec_from_file_location("p159_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_records(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list) and bool(value), "records must be a non-empty list")
    records = []
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict), f"records[{index}] must be an object")
        _GATE.require(set(item) == RECORD_KEYS, f"records[{index}] keys are invalid")
        outcome = _GATE.require_text(item["outcome"], f"records[{index}].outcome")
        _GATE.require(outcome in _GATE.RECORD_OUTCOMES, f"records[{index}].outcome is not recognized")
        records.append({
            "id": _GATE.require_text(item["id"], f"records[{index}].id"),
            "outcome": outcome,
            "setupIncluded": _GATE.require_bool(item["setupIncluded"], f"records[{index}].setupIncluded"),
        })
    ids = [record["id"] for record in records]
    _GATE.require(len(ids) == len(set(ids)), "record ids must be unique")
    return records


def _archive_faults(records: list[dict], promotional: bool) -> list[str]:
    faults: list[str] = []
    if promotional:
        faults.append(NEGATIVE_TOKEN)
    if not any(record["outcome"] == "failed" for record in records):
        faults.append(FAILED_OMITTED)
        faults.append(FAVORABLE_ONLY)
    if any(record["setupIncluded"] is False for record in records):
        faults.append(SETUP_OMITTED)
    return _GATE.dedupe(faults)


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    records = _parse_records(payload["records"])
    promotional = _GATE.require_bool(payload["promotionalReelOnly"], "promotionalReelOnly")
    faults = list(bundle["faults"])
    faults.extend(_archive_faults(records, promotional))
    extra = [{
        "promotionalReelOnly": promotional,
        "outcomes": [record["outcome"] for record in records],
        "setupIncluded": [record["setupIncluded"] for record in records],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            FAILED_OMITTED: CASE["expected"],
            SETUP_OMITTED: CASE["expected"],
            FAVORABLE_ONLY: CASE["expected"],
        },
    )
