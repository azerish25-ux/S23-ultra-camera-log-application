"""TC-P120-08 Combined temporal effects.

Host fixture. Stabilization, virtual focus, motion integration, and film
finishing are judged together with the combined motion-optics report.
Independent passes and a shutter-only spot-check do not replace that regression.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P120-08"
NAME = "Combined temporal effects"
INTERVENTION = (
    "Enable stabilization, virtual focus, motion integration, and film finishing on the same difficult clip."
)
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
    "combinationPassed",
    "report",
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
)

_SPEC = importlib.util.spec_from_file_location(
    "p120_validate_combined_motion_and_optics",
    Path(__file__).resolve().parent / "p120_validate_combined_motion_and_optics.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def evaluate(payload: dict) -> dict:
    evidence, repeat = _CORE.require_payload(payload, PAYLOAD_KEYS)
    effects = payload["effects"]
    _CORE.require(
        isinstance(effects, list)
        and sorted(effects) == sorted(REQUIRED_EFFECTS)
        and len(effects) == len(REQUIRED_EFFECTS),
        "effects must list the four combined temporal effects once",
    )
    passes = payload["independentPass"]
    _CORE.require(
        isinstance(passes, dict) and set(passes) == set(REQUIRED_EFFECTS),
        "independentPass must cover each combined effect",
    )
    _CORE.require(all(type(passes[name]) is bool for name in REQUIRED_EFFECTS), "independentPass values must be bools")
    _CORE.require(type(payload["combinedMeasured"]) is bool and type(payload["maskStable"]) is bool, "combined flags must be bools")
    _CORE.require(type(payload["cadenceExplained"]) is bool, "cadenceExplained must be a bool")
    _CORE.require(
        type(payload["combinedEdgeCount"]) is int and not isinstance(payload["combinedEdgeCount"], bool) and payload["combinedEdgeCount"] >= 0,
        "combinedEdgeCount must be a non-negative int",
    )
    source = _CORE.require_number(payload["sourceCadence"], "sourceCadence")
    output = _CORE.require_number(payload["outputCadence"], "outputCadence")
    _CORE.require(source > 0 and output > 0, "cadence must be positive")
    rgb_id = payload["rgbGeometryId"]
    depth_id = payload["depthGeometryId"]
    _CORE.require(
        isinstance(rgb_id, str) and rgb_id.strip() and isinstance(depth_id, str) and depth_id.strip(),
        "geometry ids must be non-empty strings",
    )
    judgement = _CORE.judge_report(payload["report"], combination_passed=payload["combinationPassed"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(judgement["reasons"])
    reasons.append("independent passes are not a substitute for the combined regression")
    rejected = list(judgement["rejectedClaims"])
    if not payload["combinedMeasured"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("defectOrigin=compositing")
    if payload["combinedEdgeCount"] != 1:
        rejected.append(DOUBLED_TOKEN)
        reasons.append("combined edges must stay single")
    if not payload["maskStable"]:
        rejected.append(UNSTABLE_TOKEN)
        reasons.append("combined mask must stay stable")
    cadence_changed = not _CORE.exposures_match(source, output)
    if cadence_changed and not payload["cadenceExplained"]:
        rejected.append(CADENCE_TOKEN)
        reasons.append("cadence changed without an explanation")
    report_ready = _CORE.MISSING_FIELDS not in rejected and _CORE.EXPOSURE_MISMATCH not in rejected
    if report_ready:
        fps = _CORE.require_number(payload["report"]["fps"], "fps")
        if not _CORE.exposures_match(source, fps):
            rejected.append(CADENCE_TOKEN)
            reasons.append("combined report fps must match source cadence")
    if rgb_id != depth_id:
        rejected.append(GEOMETRY_TOKEN)
        reasons.append("rgb and depth geometry ids diverged")
        reasons.append("defectOrigin=depth")
    preserved = [evidence]
    preserved.extend(judgement["preservedResults"])
    return _CORE.assemble_result(
        case_id=CASE_ID,
        evidence=evidence,
        reasons=reasons,
        rejected=rejected,
        preserved=preserved,
        repeat_note=REPEAT,
    )
