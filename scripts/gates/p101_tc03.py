"""TC-P101-03 Conversion accuracy regression.

Host reference. Exported samples are compared with the host baseline. Loading
is not numerical qualification.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P101-03"
NAME = "Conversion accuracy regression"
INTERVENTION = "Compare exported or quantized model results against the approved host baseline on withheld scenes."
EXPECTED = "Meet declared depth and boundary tolerances or remain experimental despite successful loading."
NEGATIVE = "A model that merely runs is not numerically qualified."
REPEAT = "Repeat hair, glass, low light, thin objects, and saturated illumination."
NEGATIVE_TOKEN = "model-merely-runs-numerically-qualified"

_SPEC = importlib.util.spec_from_file_location(
    "p101_integrate_the_first_on_device_inference_path_tc03",
    Path(__file__).resolve().parent / "p101_integrate_the_first_on_device_inference_path.py",
)
_PHASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PHASE)

PAYLOAD_KEYS = ("evidenceId", "repeat", *_PHASE.CONVERSION_KEYS)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence, repeat = _PHASE.parse_evidence_repeat(payload)
    section = {key: payload[key] for key in _PHASE.CONVERSION_KEYS}
    rejected, reasons = _PHASE.assess_conversion(section)
    return _PHASE.finish_case(
        CASE_ID, NAME, EXPECTED, repeat, evidence, rejected, reasons, NEGATIVE, REPEAT,
    )
