#!/usr/bin/env python3
"""P142 Implement constrained reference matching.

Host reference only. This module does not probe a device and does not qualify
a physical S23. A matcher may suggest numeric renderer parameters only:
exposure, contrast, and saturation, each inside declared bounds. The fit is
log2(reference mean luma / source mean luma) for exposure and the reference
over source ratio for contrast and saturation. Texture is analyzed and not
applied.

If output_sha256 differs from source_sha256 and the result is labelled source
footage, reject. Neural stylization (method stylize) that changes pixels is
rejected as faithful source. Face landmark drift, when provided, above the
declared maximum is rejected. Suggestions outside bounds are rejected. A
suggestion that keeps the source hash and stays in bounds is recorded as a
parameter suggestion, not a new source. Lighting and composition mismatch stay
visible; the grade does not recreate lighting geometry.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P142"
WORKSTREAM = 18
TITLE = "Implement constrained reference matching"
GOAL = "Use optional analysis to suggest renderer parameters without replacing source content."
METHOD = (
    "Analyze approved reference material for broad color, tone, texture, and contrast characteristics. "
    "Fit bounded parameters in our renderer, preserve scene structure, and expose the result as a suggestion. "
    "Keep lighting and composition mismatch visible as limitations."
)
FIXTURE = "A reference shot with dramatic directional lighting and a user source recorded under flat overhead light."
ORACLE = "The tool proposes a bounded grade but does not claim to recreate the missing lighting geometry."
MUTANT = "Use unconstrained neural stylization and call altered faces faithful source footage."
DELIVERABLE = "Parameter suggestion prototype and structure-preservation tests"
DEPENDENCIES = ("P141",)

OPEN_QUESTION = "physical S23 measurement was not run"
OPEN_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
    "lighting geometry was not recreated from the reference",
]

EXPOSURE_MIN = -2.0
EXPOSURE_MAX = 2.0
CONTRAST_MIN = 0.5
CONTRAST_MAX = 1.5
SATURATION_MIN = 0.0
SATURATION_MAX = 2.0
MAX_FACE_LANDMARK_DRIFT = 0.02
PARAMETER_NAMES = ("exposure", "contrast", "saturation")
DECLARED_BOUNDS = {
    "exposure": (EXPOSURE_MIN, EXPOSURE_MAX),
    "contrast": (CONTRAST_MIN, CONTRAST_MAX),
    "saturation": (SATURATION_MIN, SATURATION_MAX),
}
METHOD_PARAMETERS = "parameters"
METHOD_STYLIZE = "stylize"
LABEL_PARAMETER = "parameter-suggestion"
LABEL_SOURCE = "source-footage"
LABEL_FAITHFUL = "faithful-source"
SOURCE_LABELS = frozenset({LABEL_SOURCE, LABEL_FAITHFUL})
ALLOWED_LABELS = frozenset({LABEL_PARAMETER, LABEL_SOURCE, LABEL_FAITHFUL})

FIXTURE_LIGHTING = "flat-overhead"
REFERENCE_LIGHTING = "dramatic-directional"
FIXTURE_COMPOSITION = "flat-overhead-coverage"
REFERENCE_COMPOSITION = "dramatic-directional-key"
EVIDENCE_ID = "p142-reference-match"
CLAIM = "constrained-parameter-suggestion-host-reference"
LIGHTING_LIMITATION = "lighting-geometry-mismatch"
COMPOSITION_LIMITATION = "composition-mismatch"

UNAPPROVED_REFERENCE = "unapproved-reference-material"
NON_PARAMETER_METHOD = "matcher-may-suggest-numeric-parameters-only"
STYLIZE_CHANGED_PIXELS = "neural-stylization-changed-pixels-not-faithful-source"
PARAMETER_OUT_OF_BOUNDS = "parameter-outside-declared-bounds"
FIT_MISMATCH = "suggestion-does-not-match-reference-fit"
LABELLED_SOURCE_FOOTAGE = "altered-output-labelled-source-footage"
HASH_CHANGED = "parameter-suggestion-must-preserve-source-hash"
LANDMARK_DRIFT = "face-landmark-drift-above-declared-max"
FACIAL_GEOMETRY = "facial-geometry-change-rejected"
SCENE_TEXTURE = "scene-texture-replacement-rejected"
NEW_SOURCE = "parameter-suggestion-is-not-a-new-source"
LIGHTING_GEOMETRY = "claimed-recreated-lighting-geometry"
MISLABELLED = "suggestion-not-labelled-parameter-suggestion"
MUTANT_TOKEN = "unconstrained-neural-stylization-called-faithful-source"

FAULT_ORDER = (
    UNAPPROVED_REFERENCE,
    NON_PARAMETER_METHOD,
    STYLIZE_CHANGED_PIXELS,
    PARAMETER_OUT_OF_BOUNDS,
    FIT_MISMATCH,
    LABELLED_SOURCE_FOOTAGE,
    HASH_CHANGED,
    LANDMARK_DRIFT,
    FACIAL_GEOMETRY,
    SCENE_TEXTURE,
    NEW_SOURCE,
    LIGHTING_GEOMETRY,
    MISLABELLED,
    MUTANT_TOKEN,
)

NOT_SOURCE_FOOTAGE = (
    "an output whose output_sha256 differs from source_sha256 and is labelled source footage",
    "neural stylization (method stylize) that changes pixels",
    "a result whose face landmark drift is above the declared maximum",
    "a suggestion outside declared exposure, contrast, or saturation bounds",
    "a parameter suggestion; keeping the source hash records a suggestion, not a new source",
    "a visually similar generated scene",
    "unconstrained neural stylization called faithful source footage",
)

SOURCE_KEYS = (
    "source_sha256",
    "lighting",
    "composition",
    "mean_luma",
    "contrast",
    "saturation",
    "texture_energy",
)
REFERENCE_KEYS = (
    "approved",
    "lighting",
    "composition",
    "mean_luma",
    "contrast",
    "saturation",
    "texture_energy",
)
SUGGESTION_KEYS = (
    "method",
    "exposure",
    "contrast",
    "saturation",
    "output_sha256",
    "label",
    "face_landmark_drift",
    "claims_new_source",
    "recreates_lighting_geometry",
    "replaces_scene_texture",
    "changes_facial_geometry",
)
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "source",
    "reference",
    "suggestion",
}
EVALUATE_KEYS = {
    "caseId",
    "evidenceId",
    "claim",
    "applyMutant",
    "source",
    "reference",
    "suggestion",
}
COMMON_KEYS = {"evidenceId", "repeat", "source", "reference", "suggestion"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
SHA256_TEXT = re.compile(r"^[0-9a-fA-F]{64}\Z")
FIT_ABS = 1e-9
FIT_REL = 1e-9

FIXTURE_SOURCE_SHA256 = hashlib.sha256(
    b"P142|flat-overhead|user-source|dramatic-directional-reference-not-copied"
).hexdigest()
ALTERED_OUTPUT_SHA256 = hashlib.sha256(b"P142|stylized-pixels|not-source").hexdigest()

FAULT_TEXT = {
    UNAPPROVED_REFERENCE: "reference material must be approved before a parameter fit",
    NON_PARAMETER_METHOD: "a matcher may suggest numeric parameters only",
    STYLIZE_CHANGED_PIXELS: (
        "neural stylization (method stylize) that changes pixels is not faithful source footage"
    ),
    PARAMETER_OUT_OF_BOUNDS: "suggestion outside declared exposure, contrast, or saturation bounds",
    FIT_MISMATCH: "suggestion parameters do not match the reference fit",
    LABELLED_SOURCE_FOOTAGE: (
        "output_sha256 differs from source_sha256 and the result is labelled source footage"
    ),
    HASH_CHANGED: "a parameter suggestion must keep the source hash and is not a new source",
    LANDMARK_DRIFT: "face landmark drift is above the declared maximum",
    FACIAL_GEOMETRY: "facial geometry must not be changed by reference matching",
    SCENE_TEXTURE: "scene texture must not be replaced by reference matching",
    NEW_SOURCE: "a parameter suggestion is not a new source",
    LIGHTING_GEOMETRY: ORACLE,
    MISLABELLED: "a kept-hash in-bounds suggestion is recorded as a parameter suggestion, not as source footage",
    MUTANT_TOKEN: MUTANT,
}


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


def require_sha(value: object, label: str) -> str:
    require(
        isinstance(value, str) and SHA256_TEXT.fullmatch(value) is not None,
        label + " must be 64 hex characters",
    )
    return value


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def order_faults(faults: list[str]) -> list[str]:
    known = [token for token in FAULT_ORDER if token in faults]
    rest = [token for token in faults if token not in FAULT_ORDER]
    return dedupe(known + rest)


def same_sha(left: str, right: str) -> bool:
    return left.casefold() == right.casefold()


def norm_label(value: str) -> str:
    return " ".join(value.casefold().split())


def value_in_bounds(name: str, value: float) -> bool:
    low, high = DECLARED_BOUNDS[name]
    return low <= value <= high


def out_of_bounds_names(values: dict[str, float]) -> list[str]:
    return [name for name in PARAMETER_NAMES if not value_in_bounds(name, values[name])]


def close_parameter(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=FIT_REL, abs_tol=FIT_ABS)


def fit_bounded_parameters(source: dict[str, Any], reference: dict[str, Any]) -> dict[str, float]:
    """Fit exposure, contrast, and saturation. Does not clamp into bounds."""
    source_luma = require_number(source["mean_luma"], "source.mean_luma")
    reference_luma = require_number(reference["mean_luma"], "reference.mean_luma")
    source_contrast = require_number(source["contrast"], "source.contrast")
    reference_contrast = require_number(reference["contrast"], "reference.contrast")
    source_saturation = require_number(source["saturation"], "source.saturation")
    reference_saturation = require_number(reference["saturation"], "reference.saturation")
    require(source_luma > 0 and reference_luma > 0, "mean_luma must be positive")
    require(source_contrast > 0 and reference_contrast > 0, "contrast must be positive")
    require(source_saturation > 0, "source.saturation must be positive")
    require(reference_saturation >= 0, "reference.saturation must be >= 0")
    return {
        "exposure": math.log2(reference_luma / source_luma),
        "contrast": reference_contrast / source_contrast,
        "saturation": reference_saturation / source_saturation,
    }


def _characteristics(value: Any, label: str, keys: tuple[str, ...], *, approved: bool) -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    require(set(value) == set(keys), label + " keys are invalid")
    parsed: dict[str, Any] = {}
    if approved:
        parsed["approved"] = require_bool(value["approved"], label + ".approved")
    if "source_sha256" in keys:
        parsed["source_sha256"] = require_sha(value["source_sha256"], label + ".source_sha256")
    parsed["lighting"] = require_text(value["lighting"], label + ".lighting")
    parsed["composition"] = require_text(value["composition"], label + ".composition")
    for name in ("mean_luma", "contrast", "saturation", "texture_energy"):
        parsed[name] = require_number(value[name], label + "." + name)
    require(parsed["texture_energy"] >= 0, label + ".texture_energy must be >= 0")
    return parsed


def parse_source(value: Any) -> dict[str, Any]:
    return _characteristics(value, "source", SOURCE_KEYS, approved=False)


def parse_reference(value: Any) -> dict[str, Any]:
    return _characteristics(value, "reference", REFERENCE_KEYS, approved=True)


def parse_suggestion(value: Any) -> dict[str, Any]:
    require(isinstance(value, dict), "suggestion must be an object")
    require(set(value) == set(SUGGESTION_KEYS), "suggestion keys are invalid")
    method = require_text(value["method"], "suggestion.method")
    label = require_text(value["label"], "suggestion.label")
    require(label in ALLOWED_LABELS, "suggestion.label is not recognized")
    drift = value["face_landmark_drift"]
    if drift is not None:
        drift = require_number(drift, "suggestion.face_landmark_drift")
        require(drift >= 0, "suggestion.face_landmark_drift must be >= 0")
    return {
        "method": method,
        "exposure": require_number(value["exposure"], "suggestion.exposure"),
        "contrast": require_number(value["contrast"], "suggestion.contrast"),
        "saturation": require_number(value["saturation"], "suggestion.saturation"),
        "output_sha256": require_sha(value["output_sha256"], "suggestion.output_sha256"),
        "label": label,
        "face_landmark_drift": drift,
        "claims_new_source": require_bool(value["claims_new_source"], "suggestion.claims_new_source"),
        "recreates_lighting_geometry": require_bool(
            value["recreates_lighting_geometry"], "suggestion.recreates_lighting_geometry"
        ),
        "replaces_scene_texture": require_bool(
            value["replaces_scene_texture"], "suggestion.replaces_scene_texture"
        ),
        "changes_facial_geometry": require_bool(
            value["changes_facial_geometry"], "suggestion.changes_facial_geometry"
        ),
    }


def limitations_for(source: dict[str, Any], reference: dict[str, Any]) -> list[str]:
    limits: list[str] = []
    if norm_label(source["lighting"]) != norm_label(reference["lighting"]):
        limits.append(LIGHTING_LIMITATION)
    if norm_label(source["composition"]) != norm_label(reference["composition"]):
        limits.append(COMPOSITION_LIMITATION)
    return limits


def analyze_match(source: dict[str, Any], reference: dict[str, Any], suggestion: dict[str, Any]) -> dict[str, Any]:
    """Apply the constrained matcher. The source hash is what later results keep."""
    fit = fit_bounded_parameters(source, reference)
    method = suggestion["method"].casefold()
    same = same_sha(source["source_sha256"], suggestion["output_sha256"])
    labelled_source = suggestion["label"] in SOURCE_LABELS
    suggested = {name: suggestion[name] for name in PARAMETER_NAMES}
    fit_outside = out_of_bounds_names(fit)
    suggestion_outside = out_of_bounds_names(suggested)
    faults: list[str] = []
    if reference["approved"] is not True:
        faults.append(UNAPPROVED_REFERENCE)
    if method != METHOD_PARAMETERS:
        faults.append(NON_PARAMETER_METHOD)
    if method == METHOD_STYLIZE and not same:
        faults.append(STYLIZE_CHANGED_PIXELS)
    if fit_outside or suggestion_outside:
        faults.append(PARAMETER_OUT_OF_BOUNDS)
    if any(not close_parameter(fit[name], suggested[name]) for name in PARAMETER_NAMES):
        faults.append(FIT_MISMATCH)
    if not same and labelled_source:
        faults.append(LABELLED_SOURCE_FOOTAGE)
    if not same and method == METHOD_PARAMETERS:
        faults.append(HASH_CHANGED)
    drift = suggestion["face_landmark_drift"]
    if drift is not None and drift > MAX_FACE_LANDMARK_DRIFT:
        faults.append(LANDMARK_DRIFT)
    if suggestion["changes_facial_geometry"]:
        faults.append(FACIAL_GEOMETRY)
    if suggestion["replaces_scene_texture"]:
        faults.append(SCENE_TEXTURE)
    if suggestion["claims_new_source"]:
        faults.append(NEW_SOURCE)
    if suggestion["recreates_lighting_geometry"]:
        faults.append(LIGHTING_GEOMETRY)
    if suggestion["label"] != LABEL_PARAMETER:
        faults.append(MISLABELLED)
    return {
        "fit": fit,
        "withinBounds": not fit_outside and not suggestion_outside,
        "hashMatchesSource": same,
        "outside": dedupe(fit_outside + suggestion_outside),
        "limitations": limitations_for(source, reference),
        "faults": order_faults(faults),
        "source": source,
        "reference": reference,
        "suggestion": suggestion,
    }


def public_record(info: dict[str, Any], faults: list[str]) -> dict[str, Any]:
    suggestion = info["suggestion"]
    source = info["source"]
    role = "parameter-suggestion" if not faults else "rejected-match"
    return {
        "role": role,
        "source_sha256": source["source_sha256"],
        "output_sha256": suggestion["output_sha256"],
        "method": suggestion["method"],
        "exposure": suggestion["exposure"],
        "contrast": suggestion["contrast"],
        "saturation": suggestion["saturation"],
        "newSource": False,
        "label": LABEL_PARAMETER if role == "parameter-suggestion" else suggestion["label"],
        "limitations": list(info["limitations"]),
        "faceLandmarkDrift": suggestion["face_landmark_drift"],
        "withinBounds": info["withinBounds"],
        "hashMatchesSource": info["hashMatchesSource"],
    }


def match_reasons(info: dict[str, Any], faults: list[str]) -> list[str]:
    fit = info["fit"]
    source = info["source"]
    reference = info["reference"]
    suggestion = info["suggestion"]
    reasons = [
        "texture_energy analyzed; not a renderer parameter",
        "source texture_energy="
        + format(source["texture_energy"], ".12g")
        + " reference texture_energy="
        + format(reference["texture_energy"], ".12g"),
        "fit exposure="
        + format(fit["exposure"], ".12g")
        + " contrast="
        + format(fit["contrast"], ".12g")
        + " saturation="
        + format(fit["saturation"], ".12g"),
        "declared bounds exposure=["
        + format(EXPOSURE_MIN, ".12g")
        + ","
        + format(EXPOSURE_MAX, ".12g")
        + "] contrast=["
        + format(CONTRAST_MIN, ".12g")
        + ","
        + format(CONTRAST_MAX, ".12g")
        + "] saturation=["
        + format(SATURATION_MIN, ".12g")
        + ","
        + format(SATURATION_MAX, ".12g")
        + "] maxFaceLandmarkDrift="
        + format(MAX_FACE_LANDMARK_DRIFT, ".12g"),
    ]
    if info["limitations"]:
        reasons.append(
            "lighting and composition mismatch remain visible; the grade does not recreate lighting geometry"
        )
        reasons.append("limitations=" + ",".join(info["limitations"]))
    else:
        reasons.append("no lighting or composition mismatch was declared")
    reasons.append(
        "source_sha256="
        + source["source_sha256"]
        + " output_sha256="
        + suggestion["output_sha256"]
        + " method="
        + suggestion["method"]
        + " label="
        + suggestion["label"]
    )
    if not faults:
        reasons.append("recorded as a parameter suggestion, not a new source")
        reasons.append("source hash retained")
    for token in faults:
        text = FAULT_TEXT.get(token, token)
        if token == PARAMETER_OUT_OF_BOUNDS and info["outside"]:
            text = text + ": " + ",".join(info["outside"])
        reasons.append(text)
    return reasons


def make_source(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "source_sha256": FIXTURE_SOURCE_SHA256,
        "lighting": FIXTURE_LIGHTING,
        "composition": FIXTURE_COMPOSITION,
        "mean_luma": 0.5,
        "contrast": 1.0,
        "saturation": 1.0,
        "texture_energy": 0.22,
    }
    value.update(overrides)
    return value


def make_reference(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "approved": True,
        "lighting": REFERENCE_LIGHTING,
        "composition": REFERENCE_COMPOSITION,
        "mean_luma": 1.0,
        "contrast": 1.2,
        "saturation": 0.85,
        "texture_energy": 0.61,
    }
    value.update(overrides)
    return value


def make_suggestion(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "method": METHOD_PARAMETERS,
        "exposure": 0.0,
        "contrast": 1.0,
        "saturation": 1.0,
        "output_sha256": FIXTURE_SOURCE_SHA256,
        "label": LABEL_PARAMETER,
        "face_landmark_drift": None,
        "claims_new_source": False,
        "recreates_lighting_geometry": False,
        "replaces_scene_texture": False,
        "changes_facial_geometry": False,
    }
    value.update(overrides)
    return value


def fixture_source() -> dict[str, Any]:
    return make_source()


def fixture_reference() -> dict[str, Any]:
    return make_reference()


def fixture_suggestion() -> dict[str, Any]:
    source = fixture_source()
    fit = fit_bounded_parameters(source, fixture_reference())
    return make_suggestion(
        exposure=fit["exposure"],
        contrast=fit["contrast"],
        saturation=fit["saturation"],
        output_sha256=source["source_sha256"],
    )


def fixture_document() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "source": fixture_source(),
        "reference": fixture_reference(),
        "suggestion": fixture_suggestion(),
    }


def assemble(
    case_id: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    open_questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    ordered = order_faults(faults)
    decision = "rejected" if ordered else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": ordered,
        "preservedResults": preserved,
        "openQuestions": list(open_questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(isinstance(result["reasons"], list) and result["reasons"], "reasons must be non-empty")
    require(all(isinstance(item, str) and item for item in result["reasons"]), "reasons must be non-empty strings")
    require(isinstance(result["rejectedClaims"], list), "rejectedClaims must be a list")
    if decision == "recorded":
        require(result["rejectedClaims"] == [], "recorded result cannot reject claims")
    else:
        require(result["rejectedClaims"], "rejected result needs a claim")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(OPEN_QUESTION in result["openQuestions"], "open question missing")
    require(result["preservedResults"][1]["newSource"] is False, "a suggestion must not be stored as a new source")
    return result


def decide(
    case_id: str,
    evidence: str,
    claim: str,
    apply_mutant: bool,
    source: dict[str, Any],
    reference: dict[str, Any],
    suggestion: dict[str, Any],
    preamble: list[str] | None = None,
) -> dict[str, Any]:
    info = analyze_match(source, reference, suggestion)
    faults = list(info["faults"])
    if apply_mutant:
        faults.append(MUTANT_TOKEN)
    ordered = order_faults(faults)
    reasons = [
        "host reference only; not a physical S23 measurement",
        "goal: " + GOAL,
        "method: " + METHOD,
        "fixture: " + FIXTURE,
        "oracle: " + ORACLE,
    ]
    if preamble:
        reasons.extend(preamble)
    reasons.extend(match_reasons(info, ordered))
    if MUTANT_TOKEN in ordered:
        reasons.append("mutant rejected: " + MUTANT)
    if not ordered:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("selection recorded; not a physical qualification")
    preserved = [evidence, public_record(info, ordered), claim]
    return assemble(case_id, ordered, reasons, preserved, OPEN_QUESTIONS, evidence)


def assess(document: dict[str, Any]) -> dict[str, Any]:
    """Record an in-bounds parameter suggestion or reject source-footage claims."""
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
    source = parse_source(document["source"])
    reference = parse_reference(document["reference"])
    suggestion = parse_suggestion(document["suggestion"])
    return decide(PHASE, evidence, claim, apply_mutant, source, reference, suggestion)


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one matcher suggestion. Invalid shapes raise ValueError."""
    require(isinstance(payload, dict), "payload must be an object")
    missing = EVALUATE_KEYS - set(payload)
    extra = set(payload) - EVALUATE_KEYS
    require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))
    case_id = require_text(payload["caseId"], "caseId")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    claim = require_text(payload["claim"], "claim")
    apply_mutant = require_bool(payload["applyMutant"], "applyMutant")
    source = parse_source(payload["source"])
    reference = parse_reference(payload["reference"])
    suggestion = parse_suggestion(payload["suggestion"])
    return decide(case_id, evidence, claim, apply_mutant, source, reference, suggestion)


def begin_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(COMMON_KEYS) | set(extra_keys), "invalid payload keys")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    repeat = require_text(payload["repeat"], "repeat")
    source = parse_source(payload["source"])
    reference = parse_reference(payload["reference"])
    suggestion = parse_suggestion(payload["suggestion"])
    info = analyze_match(source, reference, suggestion)
    return {
        "evidence": evidence,
        "repeat": repeat,
        "source": source,
        "reference": reference,
        "suggestion": suggestion,
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
    ordered = order_faults(faults)
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        case["expected"],
        "repeat " + bundle["repeat"],
    ]
    reasons.extend(match_reasons(bundle["info"], ordered))
    for token in ordered:
        if token in text and text[token] not in reasons:
            reasons.append(text[token])
    if not ordered:
        reasons.append("parameter suggestion recorded; not a new source; not a physical qualification")
    preserved = [bundle["evidence"], public_record(bundle["info"], ordered), *extra_preserved]
    questions = list(OPEN_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], ordered, reasons, preserved, questions, bundle["evidence"])
