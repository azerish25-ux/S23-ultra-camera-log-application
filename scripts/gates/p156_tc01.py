"""TC-P156-01 Wrong bottleneck attribution.

Host reference. A slow storage or scheduling path is not evidence of a hidden
firmware restriction. Vendor-blocking attribution without controlled isolation
is rejected. Proposing a firmware change before isolation is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P156-01",
    "phase": "P156",
    "workstream": 20,
    "name": "Wrong bottleneck attribution",
    "intervention": "Present a throughput problem caused by storage or scheduling as evidence of a hidden firmware restriction.",
    "expected": "Require controlled isolation of the bottleneck before low-level modification is proposed.",
    "negative": "Assuming every slow path is vendor blocking must fail.",
    "repeat": "Repeat acquisition-only, saved-source, development, and encoder-stage measurements.",
}

NEGATIVE_TOKEN = "slow-path-assumed-vendor-blocking"
NOT_ISOLATED = "bottleneck-not-isolated-before-firmware-change"
STAGE_DOMAINS = frozenset({"acquisition-only", "saved-source", "development", "encoder-stage"})
VENDOR_CAUSES = frozenset({"vendor-blocking", "firmware-restriction"})
STAGE_KEYS = {"id", "domain", "cause", "isolated", "slow"}
EXTRA_KEYS = {"stages", "proposeFirmwareChange"}


def _load_gate():
    path = Path(__file__).resolve().parent / "p156_prepare_a_separate_firmware_risk_gate.py"
    spec = importlib.util.spec_from_file_location("p156_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_stages(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list) and bool(value), "stages must be a non-empty list")
    rows = []
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict), f"stages[{index}] must be an object")
        _GATE.require(set(item) == STAGE_KEYS, f"stages[{index}] keys are invalid")
        domain = _GATE.require_text(item["domain"], f"stages[{index}].domain")
        _GATE.require(domain in STAGE_DOMAINS, f"stages[{index}].domain is not recognized")
        rows.append({
            "id": _GATE.require_text(item["id"], f"stages[{index}].id"),
            "domain": domain,
            "cause": _GATE.require_text(item["cause"], f"stages[{index}].cause"),
            "isolated": _GATE.require_bool(item["isolated"], f"stages[{index}].isolated"),
            "slow": _GATE.require_bool(item["slow"], f"stages[{index}].slow"),
        })
    ids = [row["id"] for row in rows]
    _GATE.require(len(ids) == len(set(ids)), "stage ids must be unique")
    domains = {row["domain"] for row in rows}
    _GATE.require(domains == STAGE_DOMAINS, "stages must cover every measurement domain")
    return rows


def _bottleneck_faults(stages: list[dict], propose_firmware_change: bool) -> list[str]:
    faults: list[str] = []
    for stage in stages:
        if not stage["slow"]:
            continue
        assumed_vendor = stage["cause"] in VENDOR_CAUSES and stage["isolated"] is False
        if assumed_vendor:
            faults.append(NEGATIVE_TOKEN)
        if stage["isolated"] is False and propose_firmware_change:
            faults.append(NOT_ISOLATED)
    return _GATE.dedupe(faults)


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, EXTRA_KEYS)
    stages = _parse_stages(payload["stages"])
    propose = _GATE.require_bool(payload["proposeFirmwareChange"], "proposeFirmwareChange")
    faults = list(bundle["faults"])
    faults.extend(_bottleneck_faults(stages, propose))
    extra = [{
        "stageIds": [stage["id"] for stage in stages],
        "proposeFirmwareChange": propose,
        "isolatedSlow": [
            stage["id"] for stage in stages if stage["slow"] and stage["isolated"]
        ],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            NOT_ISOLATED: CASE["expected"],
        },
    )
