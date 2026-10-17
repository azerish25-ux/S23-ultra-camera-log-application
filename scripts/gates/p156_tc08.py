"""TC-P156-08 Unreproducible research closure.

Host reference. A promotional reel cannot substitute for an engineering
archive. Closing research without failed experiments and setup details is
rejected because the decision cannot be reconstructed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P156-08",
    "phase": "P156",
    "workstream": 20,
    "name": "Unreproducible research closure",
    "intervention": "Archive only favorable outputs while omitting failed experiments and essential setup details.",
    "expected": "Preserve enough evidence to reconstruct decisions and reproduce qualified results independently.",
    "negative": "A promotional reel cannot substitute for an engineering archive.",
    "repeat": "Repeat fresh-maintainer reproduction of capture, film rendering, optics, and rejected hypotheses.",
}

NEGATIVE_TOKEN = "promotional-reel-substitutes-for-archive"
INCOMPLETE_ARCHIVE = "archive-cannot-reconstruct-decisions"
ARCHIVE_KEYS = {"favorableOutputs", "failedExperiments", "setupDetails", "promotionalReelOnly"}
EXTRA_KEYS = {"archive"}


def _load_gate():
    path = Path(__file__).resolve().parent / "p156_prepare_a_separate_firmware_risk_gate.py"
    spec = importlib.util.spec_from_file_location("p156_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_entries(value: object, label: str) -> list[str]:
    _GATE.require(isinstance(value, list), label + " must be a list")
    entries = [_GATE.require_text(item, f"{label}[{index}]") for index, item in enumerate(value)]
    _GATE.require(len(entries) == len(set(entries)), label + " entries must be unique")
    return entries


def _parse_archive(value: object) -> dict:
    _GATE.require(isinstance(value, dict), "archive must be an object")
    _GATE.require(set(value) == ARCHIVE_KEYS, "archive keys are invalid")
    return {
        "favorableOutputs": _parse_entries(value["favorableOutputs"], "archive.favorableOutputs"),
        "failedExperiments": _parse_entries(value["failedExperiments"], "archive.failedExperiments"),
        "setupDetails": _parse_entries(value["setupDetails"], "archive.setupDetails"),
        "promotionalReelOnly": _GATE.require_bool(value["promotionalReelOnly"], "archive.promotionalReelOnly"),
    }


def _archive_faults(archive: dict) -> list[str]:
    faults: list[str] = []
    if archive["promotionalReelOnly"]:
        faults.append(NEGATIVE_TOKEN)
    if not archive["failedExperiments"] or not archive["setupDetails"]:
        faults.append(INCOMPLETE_ARCHIVE)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, EXTRA_KEYS)
    archive = _parse_archive(payload["archive"])
    faults = list(bundle["faults"])
    faults.extend(_archive_faults(archive))
    extra = [{
        "favorableOutputs": list(archive["favorableOutputs"]),
        "failedExperiments": list(archive["failedExperiments"]),
        "setupDetails": list(archive["setupDetails"]),
        "promotionalReelOnly": archive["promotionalReelOnly"],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            INCOMPLETE_ARCHIVE: CASE["expected"],
        },
    )
