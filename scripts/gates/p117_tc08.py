"""TC-P117-08 Combined temporal effects.

Host fixture. Stabilization, virtual focus, motion integration, and film
finishing are judged together. Independent passes do not replace that
regression. Shared geometry is the phase translation and crop, not a
separate per-effect coordinate system.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P117-08"
NAME = "Combined temporal effects"
INTERVENTION = "Enable stabilization, virtual focus, motion integration, and film finishing on the same difficult clip."
EXPECTED = "Preserve shared geometry and timing without doubled edges, unstable masks, or unexplained cadence changes."
NEGATIVE = "Independent success of each effect cannot replace the combined regression."
REPEAT = "Repeat scene cuts, chunk resumes, and low-confidence motion estimates."
NEGATIVE_TOKEN = "independent-success-replaces-combined-regression"
DOUBLED_TOKEN = "doubled-edges"
UNSTABLE_TOKEN = "unstable-masks"
CADENCE_TOKEN = "unexplained-cadence-change"
LOW_CONFIDENCE_TOKEN = "low-confidence-motion-estimate"
CUT_TOKEN = "undeclared-scene-cut"
REQUIRED_EFFECTS = (
    "stabilization",
    "virtualFocus",
    "motionIntegration",
    "filmFinishing",
)
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "effects",
    "independentPass",
    "combinedMeasured",
    "combinedEdgeCount",
    "maskStable",
    "sourceCadence",
    "outputCadence",
    "cadenceExplained",
    "motionConfidence",
    "confidenceFloor",
    "sceneCut",
    "cutDeclared",
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
    effects = payload["effects"]
    if (
        not isinstance(effects, list)
        or sorted(effects) != sorted(REQUIRED_EFFECTS)
        or len(effects) != len(REQUIRED_EFFECTS)
    ):
        raise ValueError("effects must list the four combined temporal effects once")
    passes = payload["independentPass"]
    if not isinstance(passes, dict) or set(passes) != set(REQUIRED_EFFECTS):
        raise ValueError("independentPass must cover each combined effect")
    if any(type(passes[name]) is not bool for name in REQUIRED_EFFECTS):
        raise ValueError("independentPass values must be bools")
    for name in ("combinedMeasured", "maskStable", "cadenceExplained", "sceneCut", "cutDeclared"):
        if type(payload[name]) is not bool:
            raise ValueError(name + " must be a bool")
    if type(payload["combinedEdgeCount"]) is not int or isinstance(payload["combinedEdgeCount"], bool):
        raise ValueError("combinedEdgeCount must be an int")
    if payload["combinedEdgeCount"] < 0:
        raise ValueError("combinedEdgeCount must be non-negative")
    source = _CORE.require_number(payload["sourceCadence"], "sourceCadence")
    output = _CORE.require_number(payload["outputCadence"], "outputCadence")
    confidence = _CORE.require_number(payload["motionConfidence"], "motionConfidence")
    floor = _CORE.require_number(payload["confidenceFloor"], "confidenceFloor")
    if source <= 0.0 or output <= 0.0:
        raise ValueError("cadence must be positive")
    if not 0.0 <= confidence <= 1.0 or not 0.0 <= floor <= 1.0:
        raise ValueError("motion confidence must be in [0, 1]")
    analysis = _CORE.evaluate_geometry(payload["geometry"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(analysis["reasons"])
    reasons.append("independent passes are not a substitute for the combined regression")
    rejected = list(analysis["rejectedClaims"])
    if not payload["combinedMeasured"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if payload["combinedEdgeCount"] != 1:
        rejected.append(DOUBLED_TOKEN)
        reasons.append("combined edges must stay single")
    if not payload["maskStable"]:
        rejected.append(UNSTABLE_TOKEN)
        reasons.append("combined mask must stay stable")
    if not _CORE.close(source, output) and not payload["cadenceExplained"]:
        rejected.append(CADENCE_TOKEN)
        reasons.append("cadence changed without an explanation")
    if confidence < floor:
        rejected.append(LOW_CONFIDENCE_TOKEN)
        reasons.append("low-confidence motion estimate cannot silently pass the combined regression")
    if payload["sceneCut"] and not payload["cutDeclared"]:
        rejected.append(CUT_TOKEN)
        reasons.append("scene cut was not declared in the combined regression")
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
