"""TC-P113-08 Combined temporal effects.

Stabilization, virtual focus, motion integration, and film finishing are judged
together. Separate per-effect successes do not replace that combined regression.
"""

from __future__ import annotations

import math
import importlib.util
from pathlib import Path

CASE_ID = "TC-P113-08"
NAME = "Combined temporal effects"
INTERVENTION = (
    "Enable stabilization, virtual focus, motion integration, and film finishing "
    "on the same difficult clip."
)
EXPECTED = (
    "Preserve shared geometry and timing without doubled edges, unstable masks, "
    "or unexplained cadence changes."
)
NEGATIVE = "Independent success of each effect cannot replace the combined regression."
REPEAT = "Repeat scene cuts, chunk resumes, and low-confidence motion estimates."
REPEATS = ("scene-cut", "chunk-resume", "low-confidence-motion")
EFFECTS = (
    "stabilization",
    "virtual-focus",
    "motion-integration",
    "film-finishing",
)
NEGATIVE_TOKEN = "independent-success-cannot-replace-combined"

_SPEC = importlib.util.spec_from_file_location(
    "p113_core_tc08",
    Path(__file__).resolve().parent / "p113_implement_shutter_angle_controls_correctly.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)

_PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "effects",
    "combinedEvaluated",
    "individualResultsOnly",
    "sharedGeometryId",
    "geometryIds",
    "cadenceBefore",
    "cadenceAfter",
    "doubledEdges",
    "unstableMasks",
    "motionConfidence",
    "lowConfidenceQualified",
    "sceneCut",
    "historyCrossesCut",
    "chunkResume",
    "stateRestored",
    "shutterAngleDegrees",
    "fps",
    "sensorConfirmed",
    "measurementId",
    "syntheticIntegration",
)


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is not a P113 combined-temporal repeat")
    for name in (
        "combinedEvaluated",
        "individualResultsOnly",
        "doubledEdges",
        "unstableMasks",
        "lowConfidenceQualified",
        "sceneCut",
        "historyCrossesCut",
        "chunkResume",
        "stateRestored",
        "syntheticIntegration",
    ):
        _bool(payload[name], name)
    if not isinstance(payload["effects"], list):
        raise ValueError("effects must be a list")
    effects = tuple(payload["effects"])
    if effects != EFFECTS and set(effects) != set(EFFECTS):
        if any(not isinstance(item, str) or not item for item in effects):
            raise ValueError("effects must be named")
    if set(effects) != set(EFFECTS) or len(effects) != len(EFFECTS):
        raise ValueError("effects must be the four combined temporal effects")
    if not isinstance(payload["sharedGeometryId"], str) or not payload["sharedGeometryId"].strip():
        raise ValueError("sharedGeometryId must be a non-empty string")
    geometry = payload["geometryIds"]
    if not isinstance(geometry, dict) or set(geometry) != set(EFFECTS):
        raise ValueError("geometryIds must cover every combined effect")
    for name, value in geometry.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"geometry id for {name} must be a non-empty string")
    confidence = payload["motionConfidence"]
    if type(confidence) is bool or not isinstance(confidence, (int, float)):
        raise ValueError("motionConfidence must be a real number")
    if not math.isfinite(float(confidence)) or not 0 <= float(confidence) <= 1:
        raise ValueError("motionConfidence must be finite and in [0, 1]")
    before = _CORE.parse_positive(payload["cadenceBefore"], "cadenceBefore")
    after = _CORE.parse_positive(payload["cadenceAfter"], "cadenceAfter")
    fps = _CORE.parse_positive(payload["fps"], "fps")
    result = _CORE.judge_shutter(
        {
            "evidenceId": payload["evidenceId"],
            "shutterAngleDegrees": payload["shutterAngleDegrees"],
            "fps": payload["fps"],
            "syntheticIntegration": payload["syntheticIntegration"],
            "sensorConfirmed": payload["sensorConfirmed"],
            "measurementId": payload["measurementId"],
            "sourceCadenceFps": payload["cadenceBefore"],
            "reportsAngleAsApplied": True,
        },
        CASE_ID,
    )
    extra: list[str] = []
    reasons = [f"{CASE_ID} {NAME}", INTERVENTION, EXPECTED, f"repeat {repeat}", REPEAT]
    if payload["individualResultsOnly"] or not payload["combinedEvaluated"]:
        extra.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    shared = payload["sharedGeometryId"]
    if any(geometry[name] != shared for name in EFFECTS):
        extra.append("shared-geometry-broken")
        reasons.append("stabilization, focus, integration, and finishing do not share geometry")
    if before != after or after != fps:
        extra.append("unexplained-cadence-change")
        reasons.append(
            f"cadence moved from {_CORE.format_number(before)} to {_CORE.format_number(after)} "
            f"against frame rate {_CORE.format_number(fps)}"
        )
    if payload["doubledEdges"]:
        extra.append("doubled-edges")
        reasons.append("combined effects produced doubled edges")
    if payload["unstableMasks"]:
        extra.append("unstable-masks")
        reasons.append("combined effects produced unstable masks")
    if float(confidence) < 0.5 and not payload["lowConfidenceQualified"]:
        extra.append("low-confidence-motion-unqualified")
        reasons.append("low-confidence motion was applied without qualification")
    if payload["sceneCut"] and payload["historyCrossesCut"]:
        extra.append("scene-cut-history-leak")
        reasons.append("history crossed a scene cut")
    if payload["chunkResume"] and not payload["stateRestored"]:
        extra.append("chunk-state-not-restored")
        reasons.append("a chunk resume did not restore temporal state")
    if not extra:
        reasons.append("shared geometry and cadence survived the combined regression")
    preserved = list(result["preservedResults"])
    preserved.append("shared-geometry:" + shared)
    rewritten = _CORE.finish_result(
        result["caseId"],
        result["decision"],
        result["reasons"],
        result["rejectedClaims"],
        preserved,
        result["openQuestions"],
    )
    return _CORE.reject_more(rewritten, extra, reasons)
