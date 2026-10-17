"""TC-P160-01 Wrong bottleneck attribution.

Host reference. A storage or scheduling slowdown is not evidence of a hidden
firmware restriction. Low-level modification requires controlled isolation first.
Assuming every slow path is vendor blocking is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P160-01",
    "phase": "P160",
    "workstream": 20,
    "name": "Wrong bottleneck attribution",
    "intervention": "Present a throughput problem caused by storage or scheduling as evidence of a hidden firmware restriction.",
    "expected": "Require controlled isolation of the bottleneck before low-level modification is proposed.",
    "negative": "Assuming every slow path is vendor blocking must fail.",
    "repeat": "Repeat acquisition-only, saved-source, development, and encoder-stage measurements.",
}

NEGATIVE_TOKEN = "slow-path-assumed-vendor-blocking"
ISOLATION_REQUIRED = "bottleneck-not-isolated"
SLOW_CAUSES = frozenset({"storage", "scheduling"})
CAUSES = SLOW_CAUSES | frozenset({"firmware", "sensor", "encoder", "unknown"})
RESTRICTIONS = frozenset({"storage", "scheduling", "firmware", "none", "unknown"})
MEASUREMENTS = frozenset({"acquisition-only", "saved-source", "development", "encoder-stage"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "records",
    "maintenanceNote",
    "only_passes",
    "measurement",
    "cause",
    "claimedRestriction",
    "isolated",
    "proposesLowLevelModification",
    "assumesVendorBlocking",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p160_close_the_programme_with_a_reproducible_evidence_archive.py"
    spec = importlib.util.spec_from_file_location("p160_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _bottleneck_faults(payload: dict) -> dict:
    measurement = _GATE.require_text(payload["measurement"], "measurement")
    _GATE.require(measurement in MEASUREMENTS, "measurement is not a controlled stage")
    cause = _GATE.require_text(payload["cause"], "cause")
    _GATE.require(cause in CAUSES, "cause is not recognized")
    claimed = _GATE.require_text(payload["claimedRestriction"], "claimedRestriction")
    _GATE.require(claimed in RESTRICTIONS, "claimedRestriction is not recognized")
    isolated = _GATE.require_bool(payload["isolated"], "isolated")
    proposes = _GATE.require_bool(payload["proposesLowLevelModification"], "proposesLowLevelModification")
    assumes = _GATE.require_bool(payload["assumesVendorBlocking"], "assumesVendorBlocking")
    faults: list[str] = []
    slow = cause in SLOW_CAUSES
    if slow and (assumes or claimed == "firmware"):
        faults.append(NEGATIVE_TOKEN)
    if proposes and not isolated:
        faults.append(ISOLATION_REQUIRED)
    return {
        "faults": faults,
        "observed": {
            "measurement": measurement,
            "cause": cause,
            "claimedRestriction": claimed,
            "isolated": isolated,
            "proposesLowLevelModification": proposes,
            "assumesVendorBlocking": assumes,
        },
    }


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    judged = _bottleneck_faults(payload)
    faults = list(bundle["faults"])
    faults.extend(judged["faults"])
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [judged["observed"]],
        {
            NEGATIVE_TOKEN: CASE["negative"],
            ISOLATION_REQUIRED: CASE["expected"],
        },
    )
