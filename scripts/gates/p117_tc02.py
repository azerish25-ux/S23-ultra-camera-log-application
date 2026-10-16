"""TC-P117-02 Existing blur ambiguity.

Host fixture. Additional synthetic shutter blur is the only qualified step.
Existing blur is not removed. An exact arbitrary conversion claim fails.
Stabilization geometry uses the phase crop contract.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P117-02"
NAME = "Existing blur ambiguity"
INTERVENTION = (
    "Supply sources with different amounts of already-recorded motion blur to the same synthetic-shutter request."
)
EXPECTED = "Apply only qualified additional processing and identify cases that cannot be faithfully reconstructed."
NEGATIVE = "Claiming exact arbitrary shutter conversion from any source must fail."
REPEAT = "Repeat short exposure, long exposure, and undersampled thin motion."
NEGATIVE_TOKEN = "exact-arbitrary-shutter-conversion"
CANNOT_RECONSTRUCT = "existing-blur-cannot-be-faithfully-reconstructed"
UNDERSAMPLED = "undersampled-thin-motion-cannot-be-reconstructed"
SOURCE_KEYS = ("id", "blurSeconds")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "sources",
    "targetExposureSeconds",
    "claimExactConversion",
    "thinMotionUndersampled",
    "geometry",
)

_SPEC = importlib.util.spec_from_file_location(
    "p117_integrate_stabilization_with_geometry",
    Path(__file__).resolve().parent / "p117_integrate_stabilization_with_geometry.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def additional_blur(target_exposure: float, source_blur: float) -> float | None:
    """Qualified added blur. None when the target is shorter than blur already recorded."""
    if target_exposure + _CORE.ABSOLUTE_TOLERANCE < source_blur:
        return None
    return target_exposure - source_blur


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    sources = payload["sources"]
    if not isinstance(sources, list) or not sources:
        raise ValueError("sources must be a non-empty list")
    parsed_sources = []
    seen = set()
    for index, item in enumerate(sources):
        obj = _CORE.require_object(item, f"sources[{index}]", SOURCE_KEYS)
        source_id = _CORE.require_text(obj["id"], f"sources[{index}].id")
        if source_id in seen:
            raise ValueError("duplicate source id")
        seen.add(source_id)
        blur = _CORE.require_number(obj["blurSeconds"], f"sources[{index}].blurSeconds")
        if blur < 0.0:
            raise ValueError("source blur must be non-negative")
        parsed_sources.append((source_id, blur))
    target = _CORE.require_number(payload["targetExposureSeconds"], "targetExposureSeconds")
    if target <= 0.0:
        raise ValueError("target exposure must be positive")
    if type(payload["claimExactConversion"]) is not bool or type(payload["thinMotionUndersampled"]) is not bool:
        raise ValueError("conversion flags must be bools")
    analysis = _CORE.evaluate_geometry(payload["geometry"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(analysis["reasons"])
    rejected = list(analysis["rejectedClaims"])
    preserved_blur = []
    cannot = False
    for source_id, blur in parsed_sources:
        added = additional_blur(target, blur)
        if added is None:
            cannot = True
            preserved_blur.append(source_id + "=unreconstructable")
            reasons.append(source_id + " blur exceeds the target and cannot be removed")
        else:
            token = source_id + "=" + _CORE.format_number(added)
            preserved_blur.append(token)
            reasons.append("qualified additional blur " + token)
    if payload["claimExactConversion"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if cannot:
        rejected.append(CANNOT_RECONSTRUCT)
        reasons.append("existing blur cannot be faithfully reconstructed by adding synthetic shutter")
    if payload["thinMotionUndersampled"]:
        rejected.append(UNDERSAMPLED)
        reasons.append("undersampled thin motion cannot be reconstructed")
    preserved = [evidence, "additionalBlur " + " ".join(preserved_blur)]
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
