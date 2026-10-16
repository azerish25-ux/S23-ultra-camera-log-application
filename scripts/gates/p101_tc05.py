"""TC-P101-05 Delegate failure and fallback.

Host reference. Only the explicit cpu-reference fallback, or a disabled depth
path with a reason, is accepted. Silent backend changes and uploads fail.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P101-05"
NAME = "Delegate failure and fallback"
INTERVENTION = "Fail runtime or delegate initialization while a preview or development job is active."
EXPECTED = "Use only an explicitly qualified fallback or disable optional depth processing with a clear reason."
NEGATIVE = "Silently changing to an untested backend or uploading frames must fail."
REPEAT = "Repeat CPU, GPU, and available accelerator configurations as applicable."
NEGATIVE_TOKEN = "silently-changing-untested-backend-uploading-frames"

_SPEC = importlib.util.spec_from_file_location(
    "p101_integrate_the_first_on_device_inference_path_tc05",
    Path(__file__).resolve().parent / "p101_integrate_the_first_on_device_inference_path.py",
)
_PHASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PHASE)

PAYLOAD_KEYS = ("evidenceId", "repeat", *_PHASE.DELEGATE_KEYS)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence, repeat = _PHASE.parse_evidence_repeat(payload)
    section = {key: payload[key] for key in _PHASE.DELEGATE_KEYS}
    rejected, reasons = _PHASE.assess_delegate(section)
    return _PHASE.finish_case(
        CASE_ID, NAME, EXPECTED, repeat, evidence, rejected, reasons, NEGATIVE, REPEAT,
    )
