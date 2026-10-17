"""TC-P153-08 Unreproducible research closure.

Host reference. Failed experiments and essential setup details stay in the
archive. A promotional reel, or an archive of only favorable outputs, cannot
replace that record.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

OUTPUT_KEYS = {"id", "favorable"}
FAILURES = "failed-experiments-omitted"
SETUP = "essential-setup-omitted"
REEL = "promotional-reel-is-not-an-engineering-archive"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "hypotheses",
    "questions",
    "plan",
    "limiter",
    "applyMutant",
    "outputs",
    "failed_experiment_ids",
    "archived_failure_ids",
    "setup",
    "required_setup",
    "promotional_only",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p153_identify_the_actual_blocked_capability.py"
    spec = importlib.util.spec_from_file_location("p153_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()
CASE = dict(_GATE.CASES[7])


def _parse_outputs(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list), "outputs must be a list")
    rows = []
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict), f"outputs[{index}] must be an object")
        _GATE.require(set(item) == OUTPUT_KEYS, f"outputs[{index}] keys are invalid")
        rows.append({
            "id": _GATE.require_text(item["id"], f"outputs[{index}].id"),
            "favorable": _GATE.require_bool(item["favorable"], f"outputs[{index}].favorable"),
        })
    ids = [row["id"] for row in rows]
    _GATE.require(len(ids) == len(set(ids)), "output ids must be unique")
    return rows


def _parse_setup(value: object) -> dict[str, str]:
    _GATE.require(isinstance(value, dict), "setup must be an object")
    setup = {}
    for key, item in value.items():
        name = _GATE.require_text(key, "setup key")
        setup[name] = _GATE.require_text(item, "setup." + name)
    return setup


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    outputs = _parse_outputs(payload["outputs"])
    failed = _GATE.require_str_list(
        payload["failed_experiment_ids"], "failed_experiment_ids", allow_empty=True
    )
    archived = _GATE.require_str_list(
        payload["archived_failure_ids"], "archived_failure_ids", allow_empty=True
    )
    setup = _parse_setup(payload["setup"])
    required = _GATE.require_str_list(payload["required_setup"], "required_setup", allow_empty=False)
    promotional = _GATE.require_bool(payload["promotional_only"], "promotional_only")
    missing_failures = [item for item in failed if item not in archived]
    missing_setup = [item for item in required if item not in setup]
    faults = list(bundle["faults"])
    if missing_failures:
        faults.append(FAILURES)
    if missing_setup:
        faults.append(SETUP)
    if promotional:
        faults.append(REEL)
    favorable_only = bool(outputs) and all(row["favorable"] for row in outputs)
    extra = [{
        "outputIds": [row["id"] for row in outputs],
        "favorableOnly": favorable_only,
        "missingFailures": missing_failures,
        "missingSetup": missing_setup,
        "promotional_only": promotional,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            FAILURES: CASE["expected"],
            SETUP: CASE["expected"],
            REEL: CASE["negative"],
        },
    )


def example_payload(**overrides):
    payload = _GATE.core_payload(repeat="fresh-maintainer")
    payload.update({
        "outputs": [
            {"id": "clip-a", "favorable": True},
            {"id": "clip-b", "favorable": False},
        ],
        "failed_experiment_ids": ["exp-codec", "exp-thermal"],
        "archived_failure_ids": ["exp-codec", "exp-thermal"],
        "setup": {
            "device": "host-fixture",
            "software": "p153",
            "capture-settings": "raw-disk",
        },
        "required_setup": ["device", "software", "capture-settings"],
        "promotional_only": False,
    })
    payload.update(overrides)
    return payload
