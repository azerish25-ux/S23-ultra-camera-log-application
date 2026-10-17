"""TC-P159-01 Wrong bottleneck attribution.

Host reference. A throughput problem caused by storage or scheduling is not
evidence of a hidden firmware restriction. Low-level modification requires
controlled isolation first. The optics adoption gate still applies.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P159-01",
    "phase": "P159",
    "workstream": 20,
    "name": "Wrong bottleneck attribution",
    "intervention": (
        "Present a throughput problem caused by storage or scheduling as evidence of a "
        "hidden firmware restriction."
    ),
    "expected": "Require controlled isolation of the bottleneck before low-level modification is proposed.",
    "negative": "Assuming every slow path is vendor blocking must fail.",
    "repeat": "Repeat acquisition-only, saved-source, development, and encoder-stage measurements.",
}

NEGATIVE_TOKEN = "slow-path-assumed-vendor-blocking"
BOTTLENECK_NOT_ISOLATED = "bottleneck-not-isolated"
SLOW_CAUSES = frozenset({"storage", "scheduling"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "baseline_stable",
    "stabilityNoted",
    "baselineRank",
    "candidates",
    "stages",
    "isolated",
    "proposedModification",
    "slowPathAssumedVendorBlocking",
)
STAGE_KEYS = {"id", "cause"}


def _load_gate():
    path = Path(__file__).resolve().parent / "p159_explore_higher_quality_computational_optics.py"
    spec = importlib.util.spec_from_file_location("p159_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_stages(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list) and bool(value), "stages must be a non-empty list")
    stages = []
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict), f"stages[{index}] must be an object")
        _GATE.require(set(item) == STAGE_KEYS, f"stages[{index}] keys are invalid")
        cause = _GATE.require_text(item["cause"], f"stages[{index}].cause")
        _GATE.require(cause in _GATE.STAGE_CAUSES, f"stages[{index}].cause is not recognized")
        stages.append({
            "id": _GATE.require_text(item["id"], f"stages[{index}].id"),
            "cause": cause,
        })
    ids = [stage["id"] for stage in stages]
    _GATE.require(len(ids) == len(set(ids)), "stage ids must be unique")
    return stages


def _attribution_faults(stages: list[dict], isolated: bool, proposed: str, assumed: bool) -> list[str]:
    faults: list[str] = []
    slow = [stage for stage in stages if stage["cause"] in SLOW_CAUSES]
    firmware_cause = any(stage["cause"] == "firmware" for stage in stages)
    if assumed:
        faults.append(NEGATIVE_TOKEN)
    if proposed in {"firmware", "low-level"} and not isolated:
        faults.append(BOTTLENECK_NOT_ISOLATED)
    if proposed in {"firmware", "low-level"} and slow and not firmware_cause:
        faults.append(NEGATIVE_TOKEN)
    return _GATE.dedupe(faults)


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    stages = _parse_stages(payload["stages"])
    isolated = _GATE.require_bool(payload["isolated"], "isolated")
    proposed = _GATE.require_text(payload["proposedModification"], "proposedModification")
    _GATE.require(proposed in _GATE.MODIFICATIONS, "proposedModification is not recognized")
    assumed = _GATE.require_bool(payload["slowPathAssumedVendorBlocking"], "slowPathAssumedVendorBlocking")
    faults = list(bundle["faults"])
    faults.extend(_attribution_faults(stages, isolated, proposed, assumed))
    extra = [{
        "isolated": isolated,
        "proposedModification": proposed,
        "causes": [stage["cause"] for stage in stages],
        "assumedVendorBlocking": assumed,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            BOTTLENECK_NOT_ISOLATED: CASE["expected"],
        },
    )
