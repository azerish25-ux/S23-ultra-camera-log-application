"""TC-P145-01 Skipped test laundering.

Host fixture. Passing host tests stay passes. Unavailable hardware and a
failing critical test stay visible. Skips are not passes. Claims that need
the missing or failing evidence are blocked.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P145-01",
    "phase": "P145",
    "workstream": 19,
    "name": "Skipped test laundering",
    "intervention": "Combine passing host tests with unavailable hardware and a failing critical integration test.",
    "expected": "Keep every result category visible and block claims requiring the missing or failing evidence.",
    "negative": "Counting skips as passes must fail.",
    "repeat": "Repeat emulator-only, GPU-unavailable, and physical-codec-unavailable environments.",
}

NEGATIVE_TOKEN = "counting-skips-as-passes"
CLAIM_BLOCKED = "claim-requires-missing-or-failing-evidence"
ENVIRONMENTS = ("emulator-only", "gpu-unavailable", "physical-codec-unavailable")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "layers",
    "releasePassed",
    "releaseSummary",
    "environment",
    "requiresEvidence",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p145_build_the_layered_automated_test_system.py"
    spec = importlib.util.spec_from_file_location("p145_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_layers(payload, {"environment", "requiresEvidence"})
    faults = list(bundle["faults"])
    environment = _GATE.require_text(payload["environment"], "environment")
    _GATE.require(environment in ENVIRONMENTS, "environment is not recognized")
    requires = payload["requiresEvidence"]
    _GATE.require(isinstance(requires, list), "requiresEvidence must be a list")
    gpu_status = bundle["rows"]["gpu"]["status"]
    physical_status = bundle["rows"]["physical"]["status"]
    if environment == "emulator-only":
        if physical_status == "passed":
            faults.append("emulator-only-physical-counted-as-passed")
        if gpu_status == "passed":
            faults.append("emulator-only-gpu-counted-as-passed")
    elif environment == "gpu-unavailable":
        if gpu_status not in {"unavailable", "not-run"}:
            faults.append("gpu-unavailable-misclassified")
    elif physical_status not in {"unavailable", "not-run"}:
        faults.append("physical-codec-unavailable-misclassified")
    for item in requires:
        test_id = _GATE.require_text(item, "requiresEvidence item")
        test = bundle["index"].get(test_id)
        if test is None or test["outcome"] != "passed":
            faults.append(CLAIM_BLOCKED)
            break
    if _GATE.SKIPPED_ADDED_INTO_PASSED in faults or _GATE.RELEASE_PASSED_INCLUDES_SKIPPED in faults:
        faults.append(NEGATIVE_TOKEN)
    extra = [{"environment": environment, "requiresEvidence": list(requires), "categories": ["passed", "failed", "skipped"]}]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        CLAIM_BLOCKED: CASE["expected"],
        "emulator-only-physical-counted-as-passed": "emulator-only physical results are not passes",
        "emulator-only-gpu-counted-as-passed": "emulator-only GPU results are not device passes",
        "gpu-unavailable-misclassified": "a GPU-unavailable environment cannot record the GPU layer as passed or failed",
        "physical-codec-unavailable-misclassified": "an unavailable physical codec is not a pass",
    }
    return _GATE.finish_layers(CASE, bundle, faults, extra, texts)
