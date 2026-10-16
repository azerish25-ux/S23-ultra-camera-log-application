"""TC-P101-06 Stale depth result.

Host reference. A depth result must carry the source timestamp and crop.
A bare float list is not an identity.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P101-06"
NAME = "Stale depth result"
INTERVENTION = "Delay inference until its result no longer matches the current source timestamp or crop."
EXPECTED = "Reject or explicitly reproject the result under a validated policy rather than applying it blindly."
NEGATIVE = "A float array without temporal and geometric identity must not be accepted."
REPEAT = "Repeat rapid camera movement, rotation, source switches, and scene cuts."
NEGATIVE_TOKEN = "float-array-without-temporal-geometric-identity"

_SPEC = importlib.util.spec_from_file_location(
    "p101_integrate_the_first_on_device_inference_path_tc06",
    Path(__file__).resolve().parent / "p101_integrate_the_first_on_device_inference_path.py",
)
_PHASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_PHASE)

PAYLOAD_KEYS = ("evidenceId", "repeat", *_PHASE.DEPTH_KEYS)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence, repeat = _PHASE.parse_evidence_repeat(payload)
    section = {key: payload[key] for key in _PHASE.DEPTH_KEYS}
    rejected, reasons = _PHASE.assess_depth(section)
    return _PHASE.finish_case(
        CASE_ID, NAME, EXPECTED, repeat, evidence, rejected, reasons, NEGATIVE, REPEAT,
    )
