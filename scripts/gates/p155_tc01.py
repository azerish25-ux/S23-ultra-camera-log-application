"""TC-P155-01 Wrong bottleneck attribution.

Host reference. A slow path caused by storage or scheduling is not evidence of
a hidden firmware restriction. Low-level modification stays unproposed until
acquisition-only, saved-source, development, and encoder-stage measurements
isolate the bottleneck. The comparative alternative rule still applies.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P155-01",
    "phase": "P155",
    "workstream": 20,
    "name": "Wrong bottleneck attribution",
    "intervention": "Present a throughput problem caused by storage or scheduling as evidence of a hidden firmware restriction.",
    "expected": "Require controlled isolation of the bottleneck before low-level modification is proposed.",
    "negative": "Assuming every slow path is vendor blocking must fail.",
    "repeat": "Repeat acquisition-only, saved-source, development, and encoder-stage measurements.",
}

NEGATIVE_TOKEN = "slow-path-assumed-vendor-blocking"
BOTTLENECK_NOT_ISOLATED = "bottleneck-not-isolated"
REQUIRED_STAGES = ("acquisition-only", "saved-source", "development", "encoder-stage")
CAUSES = frozenset({"none", "storage", "scheduling", "firmware", "codec", "sensor", "unknown"})
ATTRIBUTIONS = frozenset({"isolated", "vendor-blocking"})
STAGE_KEYS = frozenset({"name", "slow", "cause"})
FIRMWARE_CAUSES = frozenset({"firmware", "codec"})
APP_CAUSES = frozenset({"storage", "scheduling"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "alternatives",
    "conclusion",
    "stages",
    "attribution",
    "lowLevelModificationProposed",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p155_evaluate_reversible_application_level_alternatives.py"
    spec = importlib.util.spec_from_file_location("p155_gate_for_tc01", path)
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
        name = _GATE.require_text(item["name"], f"stages[{index}].name")
        _GATE.require(name in REQUIRED_STAGES, f"stages[{index}].name is not a measured stage")
        cause = _GATE.require_text(item["cause"], f"stages[{index}].cause")
        _GATE.require(cause in CAUSES, f"stages[{index}].cause is not recognized")
        rows.append({
            "name": name,
            "slow": _GATE.require_bool(item["slow"], f"stages[{index}].slow"),
            "cause": cause,
        })
    names = [row["name"] for row in rows]
    _GATE.require(len(names) == len(set(names)), "stage names must be unique")
    return rows


def _attribution_faults(stages: list[dict], attribution: str, proposed: bool) -> list[str]:
    faults: list[str] = []
    slow = [stage for stage in stages if stage["slow"]]
    app_slow = [stage for stage in slow if stage["cause"] in APP_CAUSES]
    if attribution == "vendor-blocking" and app_slow:
        faults.append(NEGATIVE_TOKEN)
    names = {stage["name"] for stage in stages}
    isolated = names == set(REQUIRED_STAGES) and all(stage["cause"] != "unknown" for stage in stages)
    firmware_only = bool(slow) and all(stage["cause"] in FIRMWARE_CAUSES for stage in slow)
    if proposed and not (isolated and firmware_only and attribution == "isolated"):
        faults.append(BOTTLENECK_NOT_ISOLATED)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    stages = _parse_stages(payload["stages"])
    attribution = _GATE.require_text(payload["attribution"], "attribution")
    _GATE.require(attribution in ATTRIBUTIONS, "attribution is not recognized")
    proposed = _GATE.require_bool(payload["lowLevelModificationProposed"], "lowLevelModificationProposed")
    faults = list(bundle["faults"])
    faults.extend(_attribution_faults(stages, attribution, proposed))
    extra = [{
        "stages": stages,
        "attribution": attribution,
        "lowLevelModificationProposed": proposed,
        "measuredStages": [stage["name"] for stage in stages],
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
