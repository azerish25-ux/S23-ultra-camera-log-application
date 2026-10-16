"""TC-P117-05 Stabilization-depth misalignment.

Host fixture. RGB, depth, and mask translations must match. The crop coverage
fraction and the field of view follow that shared translation. Depth samples
are read from source coordinates through the depth translation only.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P117-05"
NAME = "Stabilization-depth misalignment"
INTERVENTION = "Apply a changing stabilization transform to RGB while depth begins in source coordinates."
EXPECTED = "Transform all relevant geometry consistently and update valid region and field-of-view evidence."
NEGATIVE = "Stabilizing color alone while leaving masks unchanged must fail."
REPEAT = "Repeat crop changes, portrait rotation, and combined camera and subject motion."
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "geometry",
)

_SPEC = importlib.util.spec_from_file_location(
    "p117_integrate_stabilization_with_geometry",
    Path(__file__).resolve().parent / "p117_integrate_stabilization_with_geometry.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    analysis = _CORE.evaluate_geometry(payload["geometry"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(analysis["reasons"])
    rejected = list(analysis["rejectedClaims"])
    if _CORE.MASK_UNTRANSFORMED in rejected:
        reasons.append(NEGATIVE)
    if _CORE.DEPTH_LEFT_IN_SOURCE in rejected:
        reasons.append("depth began in source coordinates and was not transformed with rgb")
    if not rejected:
        reasons.append("shared translation updated the valid region, crop coverage, and field of view")
    preserved = [evidence]
    preserved.extend(analysis["preservedResults"])
    decision = "rejected" if rejected else "recorded"
    return _CORE.seal_result(
        CASE_ID,
        decision,
        reasons,
        rejected,
        preserved,
        ["physical S23 measurement was not run", REPEAT],
    )
