"""TC-P101-07 Confidence misrepresentation.

Host reference. Scores stay labelled uncalibrated and rendering reliance is reduced.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P101-07"
NAME = "Confidence misrepresentation"
INTERVENTION = "Provide unstable or unreliable predictions while their confidence metadata claims certainty."
EXPECTED = "Expose uncalibrated confidence and reduce rendering reliance according to the declared policy."
NEGATIVE = "An arbitrary confidence score must not be presented as a calibrated probability."
REPEAT = "Repeat transparent surfaces, low texture, mirrors, and unfamiliar scenes."
NEGATIVE_TOKEN = "arbitrary-confidence-score-presented-calibrated-probability"

_SPEC = importlib.util.spec_from_file_location(
    "p101_integrate_the_first_on_device_inference_path_tc07",
    Path(__file__).resolve().parent / "p101_integrate_the_first_on_device_inference_path.py",
)
_PHASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PHASE)

PAYLOAD_KEYS = ("evidenceId", "repeat", *_PHASE.CONFIDENCE_KEYS)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence, repeat = _PHASE.parse_evidence_repeat(payload)
    section = {key: payload[key] for key in _PHASE.CONFIDENCE_KEYS}
    rejected, reasons = _PHASE.assess_confidence(section)
    return _PHASE.finish_case(
        CASE_ID, NAME, EXPECTED, repeat, evidence, rejected, reasons, NEGATIVE, REPEAT,
    )
