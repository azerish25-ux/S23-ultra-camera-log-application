"""TC-P153-01 Wrong bottleneck attribution.

Host reference. A storage or scheduling limit is not a hidden firmware
restriction. Controlled isolation is required before a low-level modification
is proposed. Assuming every slow path is vendor blocking is rejected. This is
not an applyNegative stub: the presented cause, the proposal, and the
hypothesis blame are compared.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

PRESENTED = frozenset({
    "storage",
    "scheduling",
    "codec",
    "thermal",
    "firmware",
    "denied-camera-mode",
    "app",
})
PROPOSED = frozenset({"none", "app", "firmware"})
SLOW_CAUSES = frozenset({"storage", "scheduling"})
SLOW_PATH_VENDOR = "slow-path-assumed-vendor-blocking"
ISOLATION_REQUIRED = "isolation-required-before-low-level-modification"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "hypotheses",
    "questions",
    "plan",
    "limiter",
    "applyMutant",
    "presented_cause",
    "isolated",
    "proposed_modification",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p153_identify_the_actual_blocked_capability.py"
    spec = importlib.util.spec_from_file_location("p153_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()
CASE = dict(_GATE.CASES[0])


def _assumes_vendor(payload: dict, hypotheses: list[dict]) -> bool:
    if payload["proposed_modification"] == "firmware":
        return True
    return any(
        row["blamed"] == "firmware" or _GATE.is_samsung(row["vendor"]) for row in hypotheses
    )


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    presented = _GATE.require_text(payload["presented_cause"], "presented_cause")
    _GATE.require(presented in PRESENTED, "presented_cause is not recognized")
    isolated = _GATE.require_bool(payload["isolated"], "isolated")
    proposed = _GATE.require_text(payload["proposed_modification"], "proposed_modification")
    _GATE.require(proposed in PROPOSED, "proposed_modification is not recognized")
    faults = list(bundle["faults"])
    if presented in SLOW_CAUSES and _assumes_vendor(payload, bundle["hypotheses"]):
        faults.append(SLOW_PATH_VENDOR)
    if proposed == "firmware" and not isolated:
        faults.append(ISOLATION_REQUIRED)
    extra = [{
        "presented_cause": presented,
        "isolated": isolated,
        "proposed_modification": proposed,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            SLOW_PATH_VENDOR: CASE["negative"],
            ISOLATION_REQUIRED: CASE["expected"],
        },
    )


def example_payload(**overrides):
    payload = _GATE.core_payload(repeat="acquisition-only")
    payload.update({
        "presented_cause": "storage",
        "isolated": True,
        "proposed_modification": "none",
    })
    payload.update(overrides)
    return payload
