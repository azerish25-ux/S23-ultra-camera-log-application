"""TC-P157-08 Unreproducible research closure.

Host reference. Favorable outputs do not replace failed experiments or setup
details. A fresh maintainer still needs capture, film rendering, optics, and
rejected hypotheses. A promotional reel is not an engineering archive.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P157-08",
    "phase": "P157",
    "workstream": 20,
    "name": "Unreproducible research closure",
    "intervention": "Archive only favorable outputs while omitting failed experiments and essential setup details.",
    "expected": "Preserve enough evidence to reconstruct decisions and reproduce qualified results independently.",
    "negative": "A promotional reel cannot substitute for an engineering archive.",
    "repeat": "Repeat fresh-maintainer reproduction of capture, film rendering, optics, and rejected hypotheses.",
}

NEGATIVE_TOKEN = "promotional-reel-substitutes-for-archive"
FAILED_TOKEN = "failed-experiments-omitted"
SETUP_TOKEN = "setup-details-omitted"
REPRODUCTION_TOKEN = "reproduction-evidence-incomplete"
REQUIRED_DOMAINS = ("capture", "film-rendering", "optics", "rejected-hypotheses")
RECORD_KEYS = {"id", "favorable", "setup", "domain"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "protocolKind",
    "deviceExperimentCompleted",
    "baselinePreserved",
    "checksum",
    "logId",
    "failureTriggers",
    "thermalSafeguardDisabled",
    "capabilityMetadataFalsified",
    "experiments",
    "records",
    "promotionalReelOnly",
    "reproductionDomains",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p157_design_instrumented_low_level_experiments.py"
    spec = importlib.util.spec_from_file_location("p157_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_records(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list) and bool(value), "records must be a non-empty list")
    rows = []
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict), f"records[{index}] must be an object")
        _GATE.require(set(item) == RECORD_KEYS, f"records[{index}] keys are invalid")
        domain = _GATE.require_text(item["domain"], f"records[{index}].domain")
        _GATE.require(domain in REQUIRED_DOMAINS, f"records[{index}].domain is not recognized")
        setup = item["setup"]
        _GATE.require(isinstance(setup, str), f"records[{index}].setup must be a string")
        rows.append({
            "id": _GATE.require_text(item["id"], f"records[{index}].id"),
            "favorable": _GATE.require_bool(item["favorable"], f"records[{index}].favorable"),
            "setup": setup,
            "domain": domain,
        })
    ids = [row["id"] for row in rows]
    _GATE.require(len(ids) == len(set(ids)), "record ids must be unique")
    return rows


def _parse_domains(value: object) -> list[str]:
    _GATE.require(isinstance(value, list), "reproductionDomains must be a list")
    domains = [_GATE.require_text(item, f"reproductionDomains[{index}]") for index, item in enumerate(value)]
    _GATE.require(len(domains) == len(set(domains)), "reproductionDomains must be unique")
    for domain in domains:
        _GATE.require(domain in REQUIRED_DOMAINS, "reproduction domain is not recognized: " + domain)
    return domains


def _archive_faults(records: list[dict], promotional: bool, domains: list[str]) -> list[str]:
    faults: list[str] = []
    if promotional:
        faults.append(NEGATIVE_TOKEN)
    if not any(row["favorable"] is False for row in records):
        faults.append(FAILED_TOKEN)
    if any(not row["setup"].strip() or row["setup"] != row["setup"].strip() for row in records):
        faults.append(SETUP_TOKEN)
    covered = {row["domain"] for row in records if row["setup"].strip() and row["setup"] == row["setup"].strip()}
    if set(REQUIRED_DOMAINS) - set(domains) or set(REQUIRED_DOMAINS) - covered:
        faults.append(REPRODUCTION_TOKEN)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    records = _parse_records(payload["records"])
    promotional = _GATE.require_bool(payload["promotionalReelOnly"], "promotionalReelOnly")
    domains = _parse_domains(payload["reproductionDomains"])
    faults = list(bundle["faults"])
    faults.extend(_archive_faults(records, promotional, domains))
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [{
            "promotionalReelOnly": promotional,
            "reproductionDomains": domains,
            "failedRecordIds": [row["id"] for row in records if row["favorable"] is False],
            "recordIds": [row["id"] for row in records],
        }],
        {
            NEGATIVE_TOKEN: CASE["negative"],
            FAILED_TOKEN: CASE["intervention"],
            SETUP_TOKEN: CASE["expected"],
            REPRODUCTION_TOKEN: CASE["expected"],
        },
    )
