"""TC-P101-02 Preprocessing geometry error.

Host reference. Letterbox scale, pad, and channel order are recorded and the
four corner markers are restored to source coordinates.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P101-02"
NAME = "Preprocessing geometry error"
INTERVENTION = "Use a non-square source with known corner markers and alter resizing, padding, or channel order."
EXPECTED = "Match the specified tensor preparation and restore output coordinates correctly."
NEGATIVE = "Unrecorded stretching or swapped color channels must fail."
REPEAT = "Repeat portrait, landscape, cropped, and rotated source frames."
NEGATIVE_TOKEN = "unrecorded-stretching-swapped-color-channels-fail"

_SPEC = importlib.util.spec_from_file_location(
    "p101_integrate_the_first_on_device_inference_path_tc02",
    Path(__file__).resolve().parent / "p101_integrate_the_first_on_device_inference_path.py",
)
_PHASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PHASE)

PAYLOAD_KEYS = ("evidenceId", "repeat", *_PHASE.GEOMETRY_KEYS)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence, repeat = _PHASE.parse_evidence_repeat(payload)
    section = {key: payload[key] for key in _PHASE.GEOMETRY_KEYS}
    rejected, reasons = _PHASE.assess_geometry(section)
    return _PHASE.finish_case(
        CASE_ID, NAME, EXPECTED, repeat, evidence, rejected, reasons, NEGATIVE, REPEAT,
    )
