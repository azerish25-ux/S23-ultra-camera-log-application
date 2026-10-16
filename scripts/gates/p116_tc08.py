"""TC-P116-08 Combined temporal effects.

Host fixture. Stabilization, virtual focus, motion integration, and film
finishing are judged together. Independent passes do not replace that
regression. Estimated frames stay origin=estimated.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

CASE_ID = "TC-P116-08"
NAME = "Combined temporal effects"
INTERVENTION = "Enable stabilization, virtual focus, motion integration, and film finishing on the same difficult clip."
EXPECTED = "Preserve shared geometry and timing without doubled edges, unstable masks, or unexplained cadence changes."
NEGATIVE = "Independent success of each effect cannot replace the combined regression."
REPEAT = "Repeat scene cuts, chunk resumes, and low-confidence motion estimates."
NEGATIVE_TOKEN = "independent-success-replaces-combined-regression"
DOUBLED_TOKEN = "doubled-edges"
UNSTABLE_TOKEN = "unstable-masks"
CADENCE_TOKEN = "unexplained-cadence-change"
GEOMETRY_TOKEN = "shared-geometry-not-preserved"
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
    "rgbGeometryId",
    "depthGeometryId",
    "captured",
    "estimated",
    "withheldMidpoint",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_SPEC = importlib.util.spec_from_file_location(
    "p116_evaluate_interpolation_without_hidden_hallucination",
    Path(__file__).resolve().parent / "p116_evaluate_interpolation_without_hidden_hallucination.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _number(value, label: str) -> float:
    if type(value) is bool or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


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
    if not isinstance(effects, list) or sorted(effects) != sorted(REQUIRED_EFFECTS) or len(effects) != len(REQUIRED_EFFECTS):
        raise ValueError("effects must list the four combined temporal effects once")
    passes = payload["independentPass"]
    if not isinstance(passes, dict) or set(passes) != set(REQUIRED_EFFECTS):
        raise ValueError("independentPass must cover each combined effect")
    if any(type(passes[name]) is not bool for name in REQUIRED_EFFECTS):
        raise ValueError("independentPass values must be bools")
    if type(payload["combinedMeasured"]) is not bool or type(payload["maskStable"]) is not bool:
        raise ValueError("combined flags must be bools")
    if type(payload["cadenceExplained"]) is not bool:
        raise ValueError("cadenceExplained must be a bool")
    if type(payload["combinedEdgeCount"]) is not int or payload["combinedEdgeCount"] < 0:
        raise ValueError("combinedEdgeCount must be a non-negative int")
    source = _number(payload["sourceCadence"], "sourceCadence")
    output = _number(payload["outputCadence"], "outputCadence")
    if source <= 0 or output <= 0:
        raise ValueError("cadence must be positive")
    rgb_id = payload["rgbGeometryId"]
    depth_id = payload["depthGeometryId"]
    if not isinstance(rgb_id, str) or not rgb_id.strip() or not isinstance(depth_id, str) or not depth_id.strip():
        raise ValueError("geometry ids must be non-empty strings")
    timeline = _CORE.evaluate_timeline(
        payload["captured"], payload["estimated"], payload["withheldMidpoint"]
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(timeline["reasons"])
    reasons.append("independent passes are not a substitute for the combined regression")
    rejected = list(timeline["rejectedClaims"])
    if not payload["combinedMeasured"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if payload["combinedEdgeCount"] != 1:
        rejected.append(DOUBLED_TOKEN)
        reasons.append("combined edges must stay single")
    if not payload["maskStable"]:
        rejected.append(UNSTABLE_TOKEN)
        reasons.append("combined mask must stay stable")
    if not math.isclose(source, output, rel_tol=0.0, abs_tol=1e-12) and not payload["cadenceExplained"]:
        rejected.append(CADENCE_TOKEN)
        reasons.append("cadence changed without an explanation")
    if rgb_id != depth_id:
        rejected.append(GEOMETRY_TOKEN)
        reasons.append("rgb and depth geometry ids diverged")
    preserved = [evidence]
    preserved.extend(timeline["preservedResults"])
    decision = "rejected" if rejected else "recorded"
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
