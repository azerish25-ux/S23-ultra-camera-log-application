"""TC-P101-01 Model identity substitution.

Host reference. Identity is the SHA-256 of content plus precision and runtime.
A filename match does not keep a cached depth result.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P101-01"
NAME = "Model identity substitution"
INTERVENTION = "Replace a model asset with another variant or converted file while retaining a cached result."
EXPECTED = "Invalidate incompatible caches and report the actual model identity before accepting depth output."
NEGATIVE = "A filename match alone must not establish identical weights."
REPEAT = "Repeat with precision changes, runtime versions, and different model variants."
NEGATIVE_TOKEN = "filename-match-alone-establish-identical-weights"

_SPEC = importlib.util.spec_from_file_location(
    "p101_integrate_the_first_on_device_inference_path",
    Path(__file__).resolve().parent / "p101_integrate_the_first_on_device_inference_path.py",
)
_PHASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PHASE)

PAYLOAD_KEYS = ("evidenceId", "repeat", *_PHASE.MODEL_KEYS)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence, repeat = _PHASE.parse_evidence_repeat(payload)
    section = {key: payload[key] for key in _PHASE.MODEL_KEYS}
    rejected, reasons = _PHASE.assess_model_cache(section)
    return _PHASE.finish_case(
        CASE_ID, NAME, EXPECTED, repeat, evidence, rejected, reasons, NEGATIVE, REPEAT,
    )
