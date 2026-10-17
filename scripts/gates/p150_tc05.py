"""TC-P150-05 Thermal safety pressure.

Host reference. When thermal policy requires action, optional work is reduced
or capture stops. Bypassing that protection to hold an advertised rate is rejected.
The release-plan update rule still applies.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P150-05",
    "phase": "P150",
    "workstream": 19,
    "name": "Thermal safety pressure",
    "intervention": "Exercise sustained workloads until the operating-system thermal policy requires action.",
    "expected": "Reduce optional work or stop capture according to the documented preservation policy.",
    "negative": "Bypassing protection to sustain an advertised rate must fail.",
    "repeat": "Repeat warm starts, charging, longer duration, and combined rendering load where safely testable.",
}

NEGATIVE_TOKEN = "protection-bypassed-for-advertised-rate"
THERMAL_IGNORED = "thermal-action-ignored"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "build_type",
    "signing",
    "update_preserves_private_footage",
    "warns_footage_loss",
    "recommends_uninstall",
    "labelled_production_update",
    "source_revision",
    "recorded_source_revision",
    "is_update",
    "thermalActionRequired",
    "optionalWorkReduced",
    "captureStopped",
    "advertisedRateSustained",
    "protectionBypassed",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p150_prepare_signing_and_reproducible_distribution.py"
    spec = importlib.util.spec_from_file_location("p150_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _thermal_faults(payload: dict) -> tuple[list[str], dict]:
    required = _GATE.require_bool(payload["thermalActionRequired"], "thermalActionRequired")
    reduced = _GATE.require_bool(payload["optionalWorkReduced"], "optionalWorkReduced")
    stopped = _GATE.require_bool(payload["captureStopped"], "captureStopped")
    sustained = _GATE.require_bool(payload["advertisedRateSustained"], "advertisedRateSustained")
    bypassed = _GATE.require_bool(payload["protectionBypassed"], "protectionBypassed")
    faults: list[str] = []
    if required and not reduced and not stopped:
        faults.append(THERMAL_IGNORED)
    if bypassed and sustained:
        faults.append(NEGATIVE_TOKEN)
    observed = {
        "thermalActionRequired": required,
        "optionalWorkReduced": reduced,
        "captureStopped": stopped,
        "advertisedRateSustained": sustained,
        "protectionBypassed": bypassed,
    }
    return faults, observed


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    thermal_faults, observed = _thermal_faults(payload)
    faults = list(bundle["faults"])
    faults.extend(thermal_faults)
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [observed],
        {
            NEGATIVE_TOKEN: CASE["negative"],
            THERMAL_IGNORED: CASE["expected"],
        },
    )
