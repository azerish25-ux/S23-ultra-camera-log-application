"""TC-P153-05 Advertised unlock without delivery.

Host reference. Changing capability metadata or expanding a mode menu does not
prove useful capture when no valid sensor samples arrived. The acquisition
hypothesis fails unless it is left unclaimed. A newly visible setting is not
proof of useful capture.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

VISIBLE_NOT_CAPTURE = "visible-setting-is-not-useful-capture"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "hypotheses",
    "questions",
    "plan",
    "limiter",
    "applyMutant",
    "menu_expanded",
    "metadata_changed",
    "sensor_samples",
    "acquisition_claimed",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p153_identify_the_actual_blocked_capability.py"
    spec = importlib.util.spec_from_file_location("p153_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()
CASE = dict(_GATE.CASES[4])


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    menu = _GATE.require_bool(payload["menu_expanded"], "menu_expanded")
    metadata = _GATE.require_bool(payload["metadata_changed"], "metadata_changed")
    samples = _GATE.require_int(payload["sensor_samples"], "sensor_samples")
    _GATE.require(samples >= 0, "sensor_samples must be >= 0")
    claimed = _GATE.require_bool(payload["acquisition_claimed"], "acquisition_claimed")
    useful = samples > 0
    advertised = menu or metadata
    faults = list(bundle["faults"])
    if (advertised or claimed) and not useful and claimed:
        faults.append(VISIBLE_NOT_CAPTURE)
    extra = [{
        "menu_expanded": menu,
        "metadata_changed": metadata,
        "sensor_samples": samples,
        "acquisition_claimed": claimed,
        "acquisitionFailed": not useful,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {VISIBLE_NOT_CAPTURE: CASE["negative"]},
    )


def example_payload(**overrides):
    payload = _GATE.core_payload(repeat="sample-receipt")
    payload.update({
        "menu_expanded": True,
        "metadata_changed": True,
        "sensor_samples": 0,
        "acquisition_claimed": False,
    })
    payload.update(overrides)
    return payload
