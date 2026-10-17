#!/usr/bin/env python3
"""P135 Build side-by-side comparison tools.

Host fixture only. This module does not probe a device and does not qualify a
physical S23. A comparison has a left side and a right side. Each side carries
source_sha256, frame_index, transfer, and contrast_boost.

Match rule: both source hashes and both frame indexes must match. Mismatched
frames are rejected. contrast_boost must be 1 on each side. Both transfers
must be declared. The synchronized playback offset must be 0 unless that
offset is explicitly disclosed. Automatic contrast boost is rejected.
Differing display transforms and duration mappings stay visible and must not
be presented as a fair matched test.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P135"
WORKSTREAM = 17
TITLE = "Build side-by-side comparison tools"
GOAL = "Help users judge real improvements with matched inputs and controllable viewing."
METHOD = (
    "Provide synchronized playback, split views, exposure-consistent comparisons, effect bypass, "
    "and recipe metadata. Avoid comparing different moments or differently scaled thumbnails. "
    "Allow inspecting clean source and processed output without accidental double transforms."
)
FIXTURE = "Two renders of the same clip with different duration mappings and different display transforms."
ORACLE = (
    "The comparison aligns time explicitly and makes differing transforms visible rather than "
    "implying a fair matched test."
)
MUTANT = "Compare unrelated frames and automatically boost one version\u2019s contrast."
DELIVERABLE = "Comparison viewer and synchronized playback tests"
DEPENDENCIES = ("P134",)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p135-comparison"
CLAIM = "side-by-side-comparison-host-fixture"
FIXTURE_FRAME_INDEX = 24
FIXTURE_LEFT_TRANSFER = "bt709"
FIXTURE_RIGHT_TRANSFER = "hlg"
FIXTURE_DURATION_LEFT = "source-duration"
FIXTURE_DURATION_RIGHT = "display-duration"
FIXTURE_RECIPE = "print-sim-v1"

MATCH_RULE = (
    "both source hashes and frame indexes must match; "
    "mismatched frames are rejected; "
    "contrast_boost must be 1; "
    "both transfers must be declared; "
    "sync offset must be 0 unless explicitly disclosed; "
    "automatic contrast boost is rejected"
)

MISMATCHED_SOURCE = "mismatched-source-sha256"
MISMATCHED_FRAMES = "mismatched-frames"
UNDECLARED_TRANSFER = "undeclared-transfer"
CONTRAST_NOT_UNITY = "contrast-boost-not-unity"
AUTOMATIC_CONTRAST_BOOST = "automatic-contrast-boost"
UNDISCLOSED_OFFSET = "undisclosed-sync-offset"
MUTANT_CLAIM = "unrelated-frames-and-automatic-contrast-boost"
HIDDEN_TRANSFORMS = "differing-transforms-not-visible"
FAIR_MATCH_IMPLIED = "fair-matched-test-implied"
UNDISCLOSED_DURATION = "undisclosed-duration-mapping"
DIFFERENT_SCALES = "differently-scaled-thumbnails"
DOUBLE_TRANSFORM = "accidental-double-transform"
EFFECT_BYPASS_MISSING = "effect-bypass-unavailable"
RECIPE_MISSING = "recipe-metadata-missing"
EXPOSURE_INCONSISTENT = "exposure-inconsistent-comparison"
SPLIT_VIEW_MISSING = "split-view-not-provided"

SIDE_KEYS = ("source_sha256", "frame_index", "transfer", "contrast_boost")
COMPARISON_KEYS = (
    "left",
    "right",
    "sync_offset",
    "offset_disclosed",
    "duration_mapping_left",
    "duration_mapping_right",
    "duration_mapping_disclosed",
    "transforms_visible",
    "implies_fair_match",
    "scale_left",
    "scale_right",
    "effect_bypass",
    "recipe_metadata",
    "double_transform",
    "exposure_consistent",
    "split_view",
    "automatic_contrast_boost",
)
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "comparison",
}
EVALUATE_KEYS = {"caseId", "evidenceId", "claim", "applyMutant", "comparison"}
COMMON_KEYS = {"evidenceId", "repeat", "comparison"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]
SHA256_TEXT = re.compile(r"^[0-9a-fA-F]{64}\Z")
COMPLETE_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?\Z")

FAULT_TEXT = {
    MISMATCHED_SOURCE: "both source hashes must match",
    MISMATCHED_FRAMES: "mismatched frames are rejected",
    UNDECLARED_TRANSFER: "both transfers must be declared",
    CONTRAST_NOT_UNITY: "contrast_boost must be 1 on both sides",
    AUTOMATIC_CONTRAST_BOOST: "automatic contrast boost is rejected",
    UNDISCLOSED_OFFSET: "synchronized playback offset must be 0 unless an explicit offset is disclosed",
    MUTANT_CLAIM: MUTANT,
    HIDDEN_TRANSFORMS: "differing display transforms must be visible",
    FAIR_MATCH_IMPLIED: "a comparison must not imply a fair matched test when inputs differ",
    UNDISCLOSED_DURATION: "different duration mappings must be disclosed",
    DIFFERENT_SCALES: "differently scaled thumbnails must not be compared",
    DOUBLE_TRANSFORM: "accidental double transforms are rejected",
    EFFECT_BYPASS_MISSING: "effect bypass must be available",
    RECIPE_MISSING: "recipe metadata must be present",
    EXPOSURE_INCONSISTENT: "comparisons must be exposure-consistent",
    SPLIT_VIEW_MISSING: "a split view must be provided",
}

UNFAIR_TOKENS = frozenset({
    MISMATCHED_SOURCE,
    MISMATCHED_FRAMES,
    UNDECLARED_TRANSFER,
    CONTRAST_NOT_UNITY,
    AUTOMATIC_CONTRAST_BOOST,
    UNDISCLOSED_OFFSET,
    HIDDEN_TRANSFORMS,
    FAIR_MATCH_IMPLIED,
    UNDISCLOSED_DURATION,
    DIFFERENT_SCALES,
    DOUBLE_TRANSFORM,
    EXPOSURE_INCONSISTENT,
})

FIXTURE_SOURCE_SHA256 = hashlib.sha256(b"p135|same-clip|two-renders").hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_text(value: object, label: str) -> str:
    require(
        isinstance(value, str) and bool(value.strip()) and value == value.strip(),
        label + " must be a non-empty string",
    )
    return value


def require_bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def require_number(value: object, label: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number",
    )
    number = float(value)
    require(math.isfinite(number), label + " must be finite")
    return number


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def normalize_transfer(value: str) -> str:
    return "".join(ch for ch in value.casefold() if ch.isalnum())


def same_sha(left: str, right: str) -> bool:
    return left.casefold() == right.casefold()


def same_transfer(left: str, right: str) -> bool:
    return normalize_transfer(left) == normalize_transfer(right)


def is_unity(value: float) -> bool:
    return value == 1.0


def is_zero(value: float) -> bool:
    return value == 0.0


def close_scale(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=1e-12)


def transfer_declared(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def parse_side(value: Any, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    require(set(value) == set(SIDE_KEYS), label + " keys are invalid")
    source_sha = value["source_sha256"]
    require(
        isinstance(source_sha, str) and SHA256_TEXT.fullmatch(source_sha) is not None,
        label + ".source_sha256 must be 64 hex characters",
    )
    frame_index = value["frame_index"]
    require(type(frame_index) is int and frame_index >= 0, label + ".frame_index must be a non-negative int")
    transfer = value["transfer"]
    if transfer is not None:
        require(isinstance(transfer, str), label + ".transfer must be a string or null")
        if transfer.strip() and transfer != transfer.strip():
            raise ValueError(label + ".transfer must be trimmed")
    contrast_boost = require_number(value["contrast_boost"], label + ".contrast_boost")
    return {
        "source_sha256": source_sha,
        "frame_index": frame_index,
        "transfer": transfer,
        "contrast_boost": contrast_boost,
    }


def parse_comparison(value: Any, label: str = "comparison") -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    require(set(value) == set(COMPARISON_KEYS), label + " keys are invalid")
    left = parse_side(value["left"], label + ".left")
    right = parse_side(value["right"], label + ".right")
    sync_offset = require_number(value["sync_offset"], label + ".sync_offset")
    offset_disclosed = require_bool(value["offset_disclosed"], label + ".offset_disclosed")
    duration_left = require_text(value["duration_mapping_left"], label + ".duration_mapping_left")
    duration_right = require_text(value["duration_mapping_right"], label + ".duration_mapping_right")
    duration_disclosed = require_bool(value["duration_mapping_disclosed"], label + ".duration_mapping_disclosed")
    transforms_visible = require_bool(value["transforms_visible"], label + ".transforms_visible")
    implies_fair = require_bool(value["implies_fair_match"], label + ".implies_fair_match")
    scale_left = require_number(value["scale_left"], label + ".scale_left")
    scale_right = require_number(value["scale_right"], label + ".scale_right")
    require(scale_left > 0 and scale_right > 0, label + " scales must be positive")
    effect_bypass = require_bool(value["effect_bypass"], label + ".effect_bypass")
    recipe = value["recipe_metadata"]
    require(isinstance(recipe, str), label + ".recipe_metadata must be a string")
    if recipe.strip() and recipe != recipe.strip():
        raise ValueError(label + ".recipe_metadata must be trimmed")
    double_transform = require_bool(value["double_transform"], label + ".double_transform")
    exposure_consistent = require_bool(value["exposure_consistent"], label + ".exposure_consistent")
    split_view = require_bool(value["split_view"], label + ".split_view")
    automatic = require_bool(value["automatic_contrast_boost"], label + ".automatic_contrast_boost")
    return {
        "left": left,
        "right": right,
        "sync_offset": sync_offset,
        "offset_disclosed": offset_disclosed,
        "duration_mapping_left": duration_left,
        "duration_mapping_right": duration_right,
        "duration_mapping_disclosed": duration_disclosed,
        "transforms_visible": transforms_visible,
        "implies_fair_match": implies_fair,
        "scale_left": scale_left,
        "scale_right": scale_right,
        "effect_bypass": effect_bypass,
        "recipe_metadata": recipe,
        "double_transform": double_transform,
        "exposure_consistent": exposure_consistent,
        "split_view": split_view,
        "automatic_contrast_boost": automatic,
    }


def analyze_comparison(comparison: dict[str, Any]) -> dict[str, Any]:
    """Apply the match rule and the viewing constraints to one comparison."""
    left = comparison["left"]
    right = comparison["right"]
    sources_match = same_sha(left["source_sha256"], right["source_sha256"])
    frames_match = left["frame_index"] == right["frame_index"]
    transfers_declared = transfer_declared(left["transfer"]) and transfer_declared(right["transfer"])
    transfers_differ = False
    if transfers_declared:
        transfers_differ = not same_transfer(left["transfer"], right["transfer"])
    contrast_unity = is_unity(left["contrast_boost"]) and is_unity(right["contrast_boost"])
    automatic = comparison["automatic_contrast_boost"] is True
    offset_accepted = is_zero(comparison["sync_offset"]) or comparison["offset_disclosed"] is True
    duration_differ = (
        comparison["duration_mapping_left"].casefold() != comparison["duration_mapping_right"].casefold()
    )
    scales_match = close_scale(comparison["scale_left"], comparison["scale_right"])
    recipe_present = bool(comparison["recipe_metadata"].strip())
    inputs_differ = (
        (not sources_match)
        or (not frames_match)
        or transfers_differ
        or duration_differ
        or (not scales_match)
        or (not contrast_unity)
        or automatic
        or (not offset_accepted)
        or comparison["double_transform"] is True
        or comparison["exposure_consistent"] is not True
    )
    faults: list[str] = []
    if not sources_match:
        faults.append(MISMATCHED_SOURCE)
    if not frames_match:
        faults.append(MISMATCHED_FRAMES)
    if not transfers_declared:
        faults.append(UNDECLARED_TRANSFER)
    if not contrast_unity:
        faults.append(CONTRAST_NOT_UNITY)
    if automatic:
        faults.append(AUTOMATIC_CONTRAST_BOOST)
    if not offset_accepted:
        faults.append(UNDISCLOSED_OFFSET)
    if (not frames_match) and ((not contrast_unity) or automatic):
        faults.append(MUTANT_CLAIM)
    if duration_differ and comparison["duration_mapping_disclosed"] is not True:
        faults.append(UNDISCLOSED_DURATION)
    if transfers_differ and comparison["transforms_visible"] is not True:
        faults.append(HIDDEN_TRANSFORMS)
    if comparison["implies_fair_match"] is True and inputs_differ:
        faults.append(FAIR_MATCH_IMPLIED)
    if not scales_match:
        faults.append(DIFFERENT_SCALES)
    if comparison["double_transform"] is True:
        faults.append(DOUBLE_TRANSFORM)
    if comparison["effect_bypass"] is not True:
        faults.append(EFFECT_BYPASS_MISSING)
    if not recipe_present:
        faults.append(RECIPE_MISSING)
    if comparison["exposure_consistent"] is not True:
        faults.append(EXPOSURE_INCONSISTENT)
    if comparison["split_view"] is not True:
        faults.append(SPLIT_VIEW_MISSING)
    matched_inputs = (
        sources_match
        and frames_match
        and transfers_declared
        and contrast_unity
        and not automatic
        and offset_accepted
    )
    return {
        "left": left,
        "right": right,
        "sync_offset": comparison["sync_offset"],
        "offset_disclosed": comparison["offset_disclosed"],
        "sourcesMatch": sources_match,
        "framesMatch": frames_match,
        "transfersDeclared": transfers_declared,
        "transfersDiffer": transfers_differ,
        "contrastBoostUnity": contrast_unity,
        "automaticContrastBoost": automatic,
        "offsetAccepted": offset_accepted,
        "durationMappingsDiffer": duration_differ,
        "durationMappingDisclosed": comparison["duration_mapping_disclosed"],
        "transformsVisible": comparison["transforms_visible"],
        "impliesFairMatch": comparison["implies_fair_match"],
        "scalesMatch": scales_match,
        "effectBypass": comparison["effect_bypass"],
        "recipeMetadata": comparison["recipe_metadata"],
        "doubleTransform": comparison["double_transform"],
        "exposureConsistent": comparison["exposure_consistent"],
        "splitView": comparison["split_view"],
        "matchedInputs": matched_inputs,
        "faults": dedupe(faults),
    }


def comparison_reasons(info: dict[str, Any]) -> list[str]:
    reasons = [MATCH_RULE]
    if info["sourcesMatch"]:
        reasons.append("source hashes match")
    else:
        reasons.append("source hashes differ")
    if info["framesMatch"]:
        reasons.append("frames match at index " + str(info["left"]["frame_index"]))
    else:
        reasons.append(
            "mismatched frames: left="
            + str(info["left"]["frame_index"])
            + " right="
            + str(info["right"]["frame_index"])
        )
    if info["transfersDeclared"]:
        reasons.append(
            "transfers declared: left="
            + str(info["left"]["transfer"])
            + " right="
            + str(info["right"]["transfer"])
        )
    else:
        reasons.append("a transfer is undeclared")
    if info["transfersDiffer"]:
        reasons.append("display transforms differ and must stay visible")
    if info["contrastBoostUnity"]:
        reasons.append("contrast_boost is 1 on both sides")
    else:
        reasons.append("contrast_boost is not 1")
    if info["automaticContrastBoost"]:
        reasons.append("automatic contrast boost is set")
    if info["offsetAccepted"] and is_zero(info["sync_offset"]):
        reasons.append("synchronized playback offset is 0")
    elif info["offsetAccepted"]:
        reasons.append("synchronized playback offset is explicitly disclosed")
    else:
        reasons.append("synchronized playback offset is not 0 and was not disclosed")
    reasons.append("matchedInputs=" + ("true" if info["matchedInputs"] else "false"))
    if info["durationMappingsDiffer"]:
        state = "disclosed" if info["durationMappingDisclosed"] else "undisclosed"
        reasons.append("duration mappings differ; " + state)
    return reasons


def public_comparison(info: dict[str, Any]) -> dict[str, Any]:
    return {
        "left": info["left"],
        "right": info["right"],
        "sync_offset": info["sync_offset"],
        "offset_disclosed": info["offset_disclosed"],
        "sourcesMatch": info["sourcesMatch"],
        "framesMatch": info["framesMatch"],
        "transfersDeclared": info["transfersDeclared"],
        "transfersDiffer": info["transfersDiffer"],
        "contrastBoostUnity": info["contrastBoostUnity"],
        "automaticContrastBoost": info["automaticContrastBoost"],
        "offsetAccepted": info["offsetAccepted"],
        "durationMappingsDiffer": info["durationMappingsDiffer"],
        "durationMappingDisclosed": info["durationMappingDisclosed"],
        "transformsVisible": info["transformsVisible"],
        "impliesFairMatch": info["impliesFairMatch"],
        "scalesMatch": info["scalesMatch"],
        "effectBypass": info["effectBypass"],
        "recipeMetadata": info["recipeMetadata"],
        "doubleTransform": info["doubleTransform"],
        "exposureConsistent": info["exposureConsistent"],
        "splitView": info["splitView"],
        "matchedInputs": info["matchedInputs"],
    }


def status_label(info: dict[str, Any]) -> str:
    if info["sourcesMatch"] and info["framesMatch"]:
        return "matched-frame-" + str(info["left"]["frame_index"])
    return "unmatched"


def format_offset(value: float) -> str:
    if is_zero(value):
        return "0"
    return format(value, ".12g")


def make_side(**overrides: Any) -> dict[str, Any]:
    side = {
        "source_sha256": FIXTURE_SOURCE_SHA256,
        "frame_index": FIXTURE_FRAME_INDEX,
        "transfer": FIXTURE_LEFT_TRANSFER,
        "contrast_boost": 1,
    }
    side.update(overrides)
    return side


def make_comparison(**overrides: Any) -> dict[str, Any]:
    comparison = {
        "left": make_side(transfer=FIXTURE_LEFT_TRANSFER),
        "right": make_side(transfer=FIXTURE_RIGHT_TRANSFER),
        "sync_offset": 0,
        "offset_disclosed": False,
        "duration_mapping_left": FIXTURE_DURATION_LEFT,
        "duration_mapping_right": FIXTURE_DURATION_RIGHT,
        "duration_mapping_disclosed": True,
        "transforms_visible": True,
        "implies_fair_match": False,
        "scale_left": 1,
        "scale_right": 1,
        "effect_bypass": True,
        "recipe_metadata": FIXTURE_RECIPE,
        "double_transform": False,
        "exposure_consistent": True,
        "split_view": True,
        "automatic_contrast_boost": False,
    }
    comparison.update(overrides)
    return comparison


def replace_side(comparison: dict[str, Any], which: str, **overrides: Any) -> dict[str, Any]:
    require(which in {"left", "right"}, "side must be left or right")
    updated = dict(comparison)
    side = dict(comparison[which])
    side.update(overrides)
    updated[which] = side
    return updated


def fixture_document() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "comparison": make_comparison(),
    }


def assemble(
    case_id: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    open_questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    decision = "rejected" if faults else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": dedupe(faults),
        "preservedResults": preserved,
        "openQuestions": list(open_questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(OPEN_QUESTION in result["openQuestions"], "open question missing")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    return result


def _decide(
    case_id: str,
    evidence: str,
    claim: str,
    apply_mutant: bool,
    comparison: dict[str, Any],
) -> dict[str, Any]:
    info = analyze_comparison(comparison)
    faults = list(info["faults"])
    if apply_mutant and MUTANT_CLAIM not in faults:
        faults.append(MUTANT_CLAIM)
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "goal: " + GOAL,
        "method: " + METHOD,
        "fixture: " + FIXTURE,
        "oracle: " + ORACLE,
    ]
    reasons.extend(comparison_reasons(info))
    ordered = dedupe(faults)
    for token in ordered:
        reasons.append(FAULT_TEXT[token])
    if MUTANT_CLAIM in ordered:
        reasons.append("mutant rejected: " + MUTANT)
    if not ordered:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append(
            "comparison recorded; inputs match and viewing stays controllable; not a physical qualification"
        )
    preserved = [evidence, public_comparison(info), claim]
    return assemble(case_id, ordered, reasons, preserved, NON_CLAIM_QUESTIONS, evidence)


def begin_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(COMMON_KEYS) | set(extra_keys), "invalid payload keys")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    repeat = require_text(payload["repeat"], "repeat")
    comparison = parse_comparison(payload["comparison"], "comparison")
    info = analyze_comparison(comparison)
    return {
        "evidence": evidence,
        "repeat": repeat,
        "comparison": comparison,
        "info": info,
        "faults": list(info["faults"]),
    }


def finish_case(
    case: dict,
    bundle: dict,
    faults: list[str],
    extra_preserved: list,
    fault_text: dict | None = None,
) -> dict[str, Any]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        case["expected"],
        "repeat " + bundle["repeat"],
    ]
    reasons.extend(comparison_reasons(bundle["info"]))
    ordered = dedupe(faults)
    for token in ordered:
        reasons.append(text.get(token, token))
    if MUTANT_CLAIM in ordered:
        reasons.append("mutant rejected: " + MUTANT)
    if not ordered:
        reasons.append("comparison recorded; inputs match and viewing stays controllable; not a physical qualification")
    preserved = [bundle["evidence"], public_comparison(bundle["info"]), *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], ordered, reasons, preserved, questions, bundle["evidence"])


def assess(document: dict) -> dict[str, Any]:
    """Record a matched comparison or reject an unfair one."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = require_text(document["evidenceId"], "evidenceId")
    claim = require_text(document["claim"], "claim")
    apply_mutant = require_bool(document["applyMutant"], "applyMutant")
    comparison = parse_comparison(document["comparison"], "comparison")
    return _decide(PHASE, evidence, claim, apply_mutant, comparison)


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a comparison payload, or the phase document when one is given."""
    require(isinstance(payload, dict), "payload must be an object")
    if "schemaVersion" in payload or "implementationBaseRevision" in payload:
        return assess(payload)
    require(set(payload) == EVALUATE_KEYS, "invalid payload keys")
    case_id = require_text(payload["caseId"], "caseId")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    claim = require_text(payload["claim"], "claim")
    apply_mutant = require_bool(payload["applyMutant"], "applyMutant")
    comparison = parse_comparison(payload["comparison"], "comparison")
    return _decide(case_id, evidence, claim, apply_mutant, comparison)


def parse_complete_number(text: str, label: str) -> tuple[float | None, str]:
    require(isinstance(text, str), label + " must be a string")
    stripped = text.strip()
    if COMPLETE_NUMBER.fullmatch(stripped) is None:
        return None, "incomplete"
    value = float(stripped)
    if not math.isfinite(value):
        return None, "invalid"
    return value, "complete"
