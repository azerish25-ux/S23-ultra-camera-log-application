"""TC-P101-04 Offline asset unavailability.

Host reference. A missing or corrupt local asset with networking disabled must
report the missing capability and leave capture usable.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P101-04"
NAME = "Offline asset unavailability"
INTERVENTION = "Disable networking and remove or corrupt a required local model asset."
EXPECTED = "Report the missing capability while preserving ordinary capture and source retention."
NEGATIVE = "An offline camera must not hang waiting for an undisclosed cloud dependency."
REPEAT = "Repeat first installation, asset update, and a previously working offline session."
NEGATIVE_TOKEN = "offline-camera-hang-waiting-undisclosed-cloud"

_SPEC = importlib.util.spec_from_file_location(
    "p101_integrate_the_first_on_device_inference_path_tc04",
    Path(__file__).resolve().parent / "p101_integrate_the_first_on_device_inference_path.py",
)
_PHASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PHASE)

PAYLOAD_KEYS = ("evidenceId", "repeat", *_PHASE.OFFLINE_KEYS)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence, repeat = _PHASE.parse_evidence_repeat(payload)
    section = {key: payload[key] for key in _PHASE.OFFLINE_KEYS}
    rejected, reasons = _PHASE.assess_offline(section)
    return _PHASE.finish_case(
        CASE_ID, NAME, EXPECTED, repeat, evidence, rejected, reasons, NEGATIVE, REPEAT,
    )
