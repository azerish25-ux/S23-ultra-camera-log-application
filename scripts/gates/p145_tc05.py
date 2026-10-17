"""TC-P145-05 Thermal safety pressure.

Host fixture. When thermal policy requires action, optional work is reduced
or capture stops, and the retained take stays preserved. Bypassing protection
to hold an advertised rate is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P145-05",
    "phase": "P145",
    "workstream": 19,
    "name": "Thermal safety pressure",
    "intervention": "Exercise sustained workloads until the operating-system thermal policy requires action.",
    "expected": "Reduce optional work or stop capture according to the documented preservation policy.",
    "negative": "Bypassing protection to sustain an advertised rate must fail.",
    "repeat": "Repeat warm starts, charging, longer duration, and combined rendering load where safely testable.",
}

NEGATIVE_TOKEN = "bypassing-protection-to-sustain-advertised-rate"
POLICY_IGNORED = "preservation-policy-not-followed"
POLICIES = ("reduce-optional", "stop-capture", "bypass")
CONDITIONS = ("warm-start", "charging", "longer-duration", "combined-rendering")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "layers",
    "releasePassed",
    "releaseSummary",
    "thermalActionRequired",
    "policy",
    "optionalWorkReduced",
    "captureStopped",
    "advertisedRateSustained",
    "takePreserved",
    "condition",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p145_build_the_layered_automated_test_system.py"
    spec = importlib.util.spec_from_file_location("p145_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_layers(payload, {
        "thermalActionRequired",
        "policy",
        "optionalWorkReduced",
        "captureStopped",
        "advertisedRateSustained",
        "takePreserved",
        "condition",
    })
    faults = list(bundle["faults"])
    required = _GATE.require_bool(payload["thermalActionRequired"], "thermalActionRequired")
    policy = _GATE.require_text(payload["policy"], "policy")
    _GATE.require(policy in POLICIES, "policy is not recognized")
    reduced = _GATE.require_bool(payload["optionalWorkReduced"], "optionalWorkReduced")
    stopped = _GATE.require_bool(payload["captureStopped"], "captureStopped")
    sustained = _GATE.require_bool(payload["advertisedRateSustained"], "advertisedRateSustained")
    preserved = _GATE.require_bool(payload["takePreserved"], "takePreserved")
    condition = _GATE.require_text(payload["condition"], "condition")
    _GATE.require(condition in CONDITIONS, "condition is not recognized")
    protected = reduced or stopped
    bypassing = policy == "bypass" or (sustained and not protected)
    followed = (
        (policy == "reduce-optional" and reduced and preserved)
        or (policy == "stop-capture" and stopped and preserved)
    )
    if bypassing:
        faults.append(NEGATIVE_TOKEN)
    if required and not preserved:
        faults.append(POLICY_IGNORED)
    if required and policy != "bypass" and not followed:
        faults.append(POLICY_IGNORED)
    extra = [{
        "thermalActionRequired": required,
        "policy": policy,
        "optionalWorkReduced": reduced,
        "captureStopped": stopped,
        "advertisedRateSustained": sustained,
        "takePreserved": preserved,
        "condition": condition,
        "followed": followed and not bypassing,
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        POLICY_IGNORED: CASE["expected"],
    }
    return _GATE.finish_layers(CASE, bundle, faults, extra, texts)
