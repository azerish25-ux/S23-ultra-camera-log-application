"""TC-P101-08 Integrated load and thermal drift.

Host reference. Live or deferred operation is chosen from the full workload.
Standalone model latency is not a frame-rate guarantee.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P101-08"
NAME = "Integrated load and thermal drift"
INTERVENTION = "Run inference alongside actual capture, rendering, and encoding for a sustained interval."
EXPECTED = "Measure complete workload behavior and choose live or deferred operation from evidence."
NEGATIVE = "Standalone model latency must not become a full-camera frame-rate guarantee."
REPEAT = "Repeat cold start, warm operation, memory pressure, and severe thermal conditions."
NEGATIVE_TOKEN = "standalone-model-latency-become-full-camera"

_SPEC = importlib.util.spec_from_file_location(
    "p101_integrate_the_first_on_device_inference_path_tc08",
    Path(__file__).resolve().parent / "p101_integrate_the_first_on_device_inference_path.py",
)
_PHASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PHASE)

PAYLOAD_KEYS = ("evidenceId", "repeat", *_PHASE.LOAD_KEYS)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence, repeat = _PHASE.parse_evidence_repeat(payload)
    section = {key: payload[key] for key in _PHASE.LOAD_KEYS}
    rejected, reasons = _PHASE.assess_load(section)
    return _PHASE.finish_case(
        CASE_ID, NAME, EXPECTED, repeat, evidence, rejected, reasons, NEGATIVE, REPEAT,
    )
