#!/usr/bin/env python3
"""P158 Explore advanced capture research independently.

Host reference only. This module does not probe a device and does not qualify
a physical S23. Multi-frame HDR, alternative RAW modes, and synchronization are
experiments. An experiment label must be experimental. Advertising merged
dynamic range (claims_extra_stops > 0) without a motion_alignment test result
is rejected. Multi-frame HDR must report ghosting or alignment error, not hide
it. Alternative RAW modes stay unavailable unless a measurement id exists.
The decision is never qualified. Do not claim sensor-derived Log.

Motion rule: an experiment label must be experimental. Advertising merged
dynamic range (claims_extra_stops > 0) without a motion_alignment test result
is rejected. Multi-frame HDR must report ghosting or alignment error, not hide
it. Alternative RAW modes stay unavailable unless a measurement id exists.
The decision is never qualified. Do not claim sensor-derived Log.
"""

from __future__ import annotations

from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P158"
WORKSTREAM = 20
TITLE = "Explore advanced capture research independently"
GOAL = (
    "Investigate multi-frame HDR, alternative RAW modes, and synchronization only as "
    "clearly labelled experiments."
)
METHOD = (
    "Define source sampling, motion assumptions, exposure differences, merge artifacts, "
    "and output lineage. Compare against single-exposure baselines. Multi-frame "
    "computational capture must not be presented as a single unmodified sensor exposure "
    "or guaranteed dynamic-range increase in every scene."
)
FIXTURE = "A moving subject across differently exposed frames used for a computational HDR merge."
ORACLE = (
    "The report measures motion artifacts and retained highlight information separately "
    "and labels the merge explicitly."
)
MUTANT = "Advertise merged dynamic range without testing motion or alignment failures."
DELIVERABLE = "Advanced capture experiment and motion-aware acceptance plan"
DEPENDENCIES = ("P157",)

MOTION_RULE = (
    "An experiment label must be experimental. Advertising merged dynamic range "
    "(claims_extra_stops > 0) without a motion_alignment test result is rejected. "
    "Multi-frame HDR must report ghosting or alignment error, not hide it. "
    "Alternative RAW modes stay unavailable unless a measurement id exists. "
    "The decision is never qualified. Do not claim sensor-derived Log."
)

EXPERIMENT_LABEL = "experimental"
OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p158-advanced-capture"
CLAIM = "advanced-capture-experiment-host-reference"
BASELINE_EVIDENCE_ID = "p158-single-exposure-baseline"
COMPUTATIONAL_LABEL = "computational-acquisition"
SENSOR_DERIVED_LOG_TEXT = "sensor-derived Log"

LABEL_NOT_EXPERIMENTAL = "experiment-label-not-experimental"
MERGED_DR_WITHOUT_MOTION = "merged-dynamic-range-without-motion-alignment"
HIDDEN_MERGE_ARTIFACT = "multi-frame-hdr-hid-ghosting-or-alignment-error"
ALT_RAW_WITHOUT_MEASUREMENT = "alternative-raw-without-measurement-id"
SENSOR_DERIVED_LOG = "sensor-derived-log-claimed"
PRESENTED_AS_UNMODIFIED_SENSOR = "presented-as-single-unmodified-sensor-exposure"
MERGE_NOT_LABELLED = "merge-not-labelled-explicitly"
GUARANTEED_EVERY_SCENE = "guaranteed-dynamic-range-every-scene"
MOTION_AND_HIGHLIGHTS_NOT_SEPARATE = "motion-artifacts-and-highlights-not-separate"
EXPOSURE_DIFFERENCE_MISSING = "exposure-differences-missing"
LINEAGE_INCOMPLETE = "output-lineage-incomplete"
MERGE_ARTIFACT_UNLISTED = "merge-artifact-omitted"

RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = frozenset({"recorded", "rejected"})
CAPTURE_KINDS = frozenset({
    "multi-frame-hdr",
    "single-exposure",
    "alternative-raw",
    "synchronization",
})
PRESENTED_AS = frozenset({
    "computational-merge",
    "single-unmodified-sensor-exposure",
    "labelled-experiment",
})
MOTION_STATUS = frozenset({"pass", "fail"})
MOTION_ALIGNMENT_KEYS = frozenset({"status", "error", "frames"})
ARTIFACT_KEYS = frozenset({"reported", "hidden", "magnitude"})
MEASURED_KEYS = frozenset({"measured", "value"})
RAW_MODE_KEYS = frozenset({"id", "available", "measurementId"})
BASELINE_KEYS = frozenset({"evidenceId", "retainedHighlights"})
SYNC_KEYS = frozenset({"labelled", "offsetMeasured", "offsetMs"})
NON_CLAIM_QUESTIONS = (
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
    "multi-frame HDR is an experiment and is not a guaranteed dynamic-range increase",
)
CORE_KEYS = frozenset({
    "evidenceId",
    "claim",
    "applyMutant",
    "experimentLabel",
    "captureKind",
    "presentedAs",
    "labelsMergeExplicitly",
    "claimsExtraStops",
    "guaranteedEveryScene",
    "motionAlignment",
    "ghosting",
    "alignmentError",
    "motionArtifacts",
    "retainedHighlights",
    "sourceSampling",
    "motionAssumptions",
    "exposureDifferences",
    "mergeArtifacts",
    "outputLineage",
    "singleExposureBaseline",
    "alternativeRawModes",
    "synchronization",
    "claimsSensorDerivedLog",
})
DOCUMENT_KEYS = CORE_KEYS | {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
}
CASE_COMMON_KEYS = CORE_KEYS | {"repeat"}
MAX_LIST = 64

FAULT_TEXT = {
    LABEL_NOT_EXPERIMENTAL: "experiment label must be experimental",
    MERGED_DR_WITHOUT_MOTION: (
        "advertising merged dynamic range (claims_extra_stops > 0) without a "
        "motion_alignment test result"
    ),
    HIDDEN_MERGE_ARTIFACT: (
        "multi-frame HDR must report ghosting or alignment error, not hide it"
    ),
    ALT_RAW_WITHOUT_MEASUREMENT: (
        "alternative RAW modes stay unavailable unless a measurement id exists"
    ),
    SENSOR_DERIVED_LOG: "sensor-derived Log is not claimed",
    PRESENTED_AS_UNMODIFIED_SENSOR: (
        "multi-frame computational capture must not be presented as a single unmodified "
        "sensor exposure"
    ),
    MERGE_NOT_LABELLED: ORACLE,
    GUARANTEED_EVERY_SCENE: (
        "multi-frame computational capture must not be presented as a guaranteed "
        "dynamic-range increase in every scene"
    ),
    MOTION_AND_HIGHLIGHTS_NOT_SEPARATE: (
        "motion artifacts and retained highlight information must be measured separately"
    ),
    EXPOSURE_DIFFERENCE_MISSING: (
        "differently exposed frames are required for a computational HDR merge"
    ),
    LINEAGE_INCOMPLETE: "output lineage must name the sampled frames",
    MERGE_ARTIFACT_UNLISTED: "a reported merge artifact was omitted from the artifact list",
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


def require_int(value: object, label: str) -> int:
    require(type(value) is int and not isinstance(value, bool), label + " must be an int")
    return value


def require_number(value: object, label: str) -> int | float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number",
    )
    number = float(value)
    require(number == number and number not in (float("inf"), float("-inf")), label + " must be finite")
    return value if type(value) is int else number


def require_nonnegative(value: object, label: str) -> int | float:
    number = require_number(value, label)
    require(float(number) >= 0, label + " must be >= 0")
    return number


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def display_number(value: int | float) -> int | float:
    number = float(value)
    if number.is_integer():
        return int(number)
    return number


def motion_alignment_test_present(motion_alignment: dict | None) -> bool:
    """A motion_alignment test result is a parsed pass/fail record, never null."""
    return motion_alignment is not None


def advertises_without_motion_test(claims_extra_stops: int | float, motion_alignment_present: bool) -> bool:
    """Advertising merged dynamic range without a motion_alignment test result."""
    return float(claims_extra_stops) > 0 and not motion_alignment_present


def require_string_list(value: object, label: str, *, minimum: int) -> list[str]:
    require(isinstance(value, list), label + " must be a list")
    require(minimum <= len(value) <= MAX_LIST, label + " length is invalid")
    items = [require_text(item, f"{label}[{index}]") for index, item in enumerate(value)]
    require(len(items) == len(set(items)), label + " entries must be unique")
    return items


def require_number_list(value: object, label: str, *, minimum: int) -> list[int | float]:
    require(isinstance(value, list), label + " must be a list")
    require(minimum <= len(value) <= MAX_LIST, label + " length is invalid")
    return [require_number(item, f"{label}[{index}]") for index, item in enumerate(value)]


def parse_motion_alignment(value: object) -> dict | None:
    if value is None:
        return None
    require(isinstance(value, dict), "motionAlignment must be an object or null")
    require(set(value) == MOTION_ALIGNMENT_KEYS, "motionAlignment keys are invalid")
    status = require_text(value["status"], "motionAlignment.status")
    require(status in MOTION_STATUS, "motionAlignment.status is not a test result")
    error = require_nonnegative(value["error"], "motionAlignment.error")
    frames = require_int(value["frames"], "motionAlignment.frames")
    require(frames >= 1, "motionAlignment.frames must be >= 1")
    return {"status": status, "error": error, "frames": frames}


def parse_artifact(value: object, label: str) -> dict:
    require(isinstance(value, dict), label + " must be an object")
    require(set(value) == ARTIFACT_KEYS, label + " keys are invalid")
    reported = require_bool(value["reported"], label + ".reported")
    hidden = require_bool(value["hidden"], label + ".hidden")
    magnitude = require_nonnegative(value["magnitude"], label + ".magnitude")
    require(not (reported and hidden), label + " cannot be both reported and hidden")
    return {"reported": reported, "hidden": hidden, "magnitude": magnitude}


def parse_measurement(value: object, label: str) -> dict:
    require(isinstance(value, dict), label + " must be an object")
    require(set(value) == MEASURED_KEYS, label + " keys are invalid")
    return {
        "measured": require_bool(value["measured"], label + ".measured"),
        "value": require_nonnegative(value["value"], label + ".value"),
    }


def parse_raw_modes(value: object) -> list[dict]:
    require(isinstance(value, list), "alternativeRawModes must be a list")
    require(len(value) <= MAX_LIST, "alternativeRawModes length is invalid")
    modes = []
    for index, item in enumerate(value):
        require(isinstance(item, dict), f"alternativeRawModes[{index}] must be an object")
        require(set(item) == RAW_MODE_KEYS, f"alternativeRawModes[{index}] keys are invalid")
        measurement = item["measurementId"]
        if measurement is not None:
            measurement = require_text(measurement, f"alternativeRawModes[{index}].measurementId")
        modes.append({
            "id": require_text(item["id"], f"alternativeRawModes[{index}].id"),
            "available": require_bool(item["available"], f"alternativeRawModes[{index}].available"),
            "measurementId": measurement,
        })
    ids = [mode["id"] for mode in modes]
    require(len(ids) == len(set(ids)), "alternative RAW mode ids must be unique")
    return modes


def parse_baseline(value: object) -> dict:
    require(isinstance(value, dict), "singleExposureBaseline must be an object")
    require(set(value) == BASELINE_KEYS, "singleExposureBaseline keys are invalid")
    return {
        "evidenceId": require_text(value["evidenceId"], "singleExposureBaseline.evidenceId"),
        "retainedHighlights": require_nonnegative(
            value["retainedHighlights"],
            "singleExposureBaseline.retainedHighlights",
        ),
    }


def parse_synchronization(value: object) -> dict:
    require(isinstance(value, dict), "synchronization must be an object")
    require(set(value) == SYNC_KEYS, "synchronization keys are invalid")
    offset_measured = require_bool(value["offsetMeasured"], "synchronization.offsetMeasured")
    offset = value["offsetMs"]
    if offset is None:
        require(not offset_measured, "synchronization.offsetMs is required when offset is measured")
    else:
        offset = require_number(offset, "synchronization.offsetMs")
        require(offset_measured, "synchronization.offsetMs must be null when offset is not measured")
    return {
        "labelled": require_text(value["labelled"], "synchronization.labelled"),
        "offsetMeasured": offset_measured,
        "offsetMs": offset,
    }


def _sensor_log_claimed(claim: str, flag: bool, label: str) -> bool:
    if flag:
        return True
    if SENSOR_DERIVED_LOG_TEXT in claim or SENSOR_DERIVED_LOG_TEXT in label:
        return True
    return False


def _artifact_visible(artifact: dict) -> bool:
    return bool(artifact["reported"]) and not bool(artifact["hidden"])


def analyze_computation(
    *,
    claim: str,
    apply_mutant: bool,
    experiment_label: str,
    capture_kind: str,
    presented_as: str,
    labels_merge_explicitly: bool,
    claims_extra_stops: int | float,
    guaranteed_every_scene: bool,
    motion_alignment: dict | None,
    ghosting: dict,
    alignment_error: dict,
    motion_artifacts: dict,
    retained_highlights: dict,
    exposure_differences: list,
    merge_artifacts: list[str],
    output_lineage: list[str],
    baseline: dict,
    raw_modes: list[dict],
    synchronization: dict,
    claims_sensor_derived_log: bool,
) -> dict[str, Any]:
    faults: list[str] = []
    effective_stops = claims_extra_stops
    effective_alignment = motion_alignment
    if apply_mutant:
        if float(effective_stops) <= 0:
            effective_stops = 1
        effective_alignment = None
    alignment_present = motion_alignment_test_present(effective_alignment)
    if experiment_label != EXPERIMENT_LABEL or synchronization["labelled"] != EXPERIMENT_LABEL:
        faults.append(LABEL_NOT_EXPERIMENTAL)
    if advertises_without_motion_test(effective_stops, alignment_present):
        faults.append(MERGED_DR_WITHOUT_MOTION)
    if _sensor_log_claimed(claim, claims_sensor_derived_log, experiment_label):
        faults.append(SENSOR_DERIVED_LOG)
    if guaranteed_every_scene:
        faults.append(GUARANTEED_EVERY_SCENE)
    unmeasured_raw = [
        mode["id"] for mode in raw_modes if mode["available"] and not mode["measurementId"]
    ]
    if unmeasured_raw:
        faults.append(ALT_RAW_WITHOUT_MEASUREMENT)
    if capture_kind == "multi-frame-hdr":
        ghost_visible = _artifact_visible(ghosting)
        align_visible = _artifact_visible(alignment_error)
        if ghosting["hidden"] or alignment_error["hidden"] or not (ghost_visible or align_visible):
            faults.append(HIDDEN_MERGE_ARTIFACT)
        if presented_as == "single-unmodified-sensor-exposure":
            faults.append(PRESENTED_AS_UNMODIFIED_SENSOR)
        if not labels_merge_explicitly:
            faults.append(MERGE_NOT_LABELLED)
        separate = bool(motion_artifacts["measured"] and retained_highlights["measured"])
        if not separate:
            faults.append(MOTION_AND_HIGHLIGHTS_NOT_SEPARATE)
        if len({float(item) for item in exposure_differences}) < 2:
            faults.append(EXPOSURE_DIFFERENCE_MISSING)
        if len(output_lineage) < 2:
            faults.append(LINEAGE_INCOMPLETE)
        if ghosting["reported"] and "ghosting" not in merge_artifacts:
            faults.append(MERGE_ARTIFACT_UNLISTED)
        if alignment_error["reported"] and "alignment-error" not in merge_artifacts:
            faults.append(MERGE_ARTIFACT_UNLISTED)
    else:
        separate = bool(motion_artifacts["measured"] and retained_highlights["measured"])
    status = None if effective_alignment is None else effective_alignment["status"]
    snapshot = {
        "experimentLabel": experiment_label,
        "captureKind": capture_kind,
        "presentedAs": presented_as,
        "claimsExtraStops": display_number(effective_stops),
        "requestedClaimsExtraStops": display_number(claims_extra_stops),
        "motionAlignmentPresent": alignment_present,
        "motionAlignmentStatus": status,
        "ghostingReported": ghosting["reported"],
        "ghostingHidden": ghosting["hidden"],
        "alignmentErrorReported": alignment_error["reported"],
        "alignmentErrorHidden": alignment_error["hidden"],
        "motionArtifactsMeasured": motion_artifacts["measured"],
        "retainedHighlightsMeasured": retained_highlights["measured"],
        "measurementsSeparate": separate,
        "labelsMergeExplicitly": labels_merge_explicitly,
        "guaranteedEveryScene": guaranteed_every_scene,
        "claimsSensorDerivedLog": claims_sensor_derived_log or SENSOR_DERIVED_LOG in faults,
        "unmeasuredAvailableRawModes": unmeasured_raw,
        "baselineEvidenceId": baseline["evidenceId"],
        "baselineRetainedHighlights": display_number(baseline["retainedHighlights"]),
        "retainedHighlights": display_number(retained_highlights["value"]),
        "applyMutant": apply_mutant,
    }
    extra_reasons = [
        "motion rule: " + MOTION_RULE,
        "claims_extra_stops "
        + str(snapshot["claimsExtraStops"])
        + " motion_alignment "
        + ("present" if alignment_present else "absent"),
    ]
    if unmeasured_raw:
        extra_reasons.append(
            "alternative RAW modes without a measurement id: " + ", ".join(unmeasured_raw)
        )
    if capture_kind == "multi-frame-hdr" and separate:
        extra_reasons.append(
            "motion artifacts "
            + str(display_number(motion_artifacts["value"]))
            + " retained highlights "
            + str(snapshot["retainedHighlights"])
            + " baseline "
            + str(snapshot["baselineRetainedHighlights"])
        )
    return {
        "faults": dedupe(faults),
        "snapshot": snapshot,
        "extraReasons": extra_reasons,
    }


def _parse_core(mapping: dict) -> dict[str, Any]:
    evidence = require_text(mapping["evidenceId"], "evidenceId")
    claim = require_text(mapping["claim"], "claim")
    apply_mutant = require_bool(mapping["applyMutant"], "applyMutant")
    experiment_label = require_text(mapping["experimentLabel"], "experimentLabel")
    capture_kind = require_text(mapping["captureKind"], "captureKind")
    require(capture_kind in CAPTURE_KINDS, "captureKind is not recognized")
    presented_as = require_text(mapping["presentedAs"], "presentedAs")
    require(presented_as in PRESENTED_AS, "presentedAs is not recognized")
    analysis = analyze_computation(
        claim=claim,
        apply_mutant=apply_mutant,
        experiment_label=experiment_label,
        capture_kind=capture_kind,
        presented_as=presented_as,
        labels_merge_explicitly=require_bool(mapping["labelsMergeExplicitly"], "labelsMergeExplicitly"),
        claims_extra_stops=require_nonnegative(mapping["claimsExtraStops"], "claimsExtraStops"),
        guaranteed_every_scene=require_bool(mapping["guaranteedEveryScene"], "guaranteedEveryScene"),
        motion_alignment=parse_motion_alignment(mapping["motionAlignment"]),
        ghosting=parse_artifact(mapping["ghosting"], "ghosting"),
        alignment_error=parse_artifact(mapping["alignmentError"], "alignmentError"),
        motion_artifacts=parse_measurement(mapping["motionArtifacts"], "motionArtifacts"),
        retained_highlights=parse_measurement(mapping["retainedHighlights"], "retainedHighlights"),
        exposure_differences=require_number_list(
            mapping["exposureDifferences"],
            "exposureDifferences",
            minimum=1,
        ),
        merge_artifacts=require_string_list(mapping["mergeArtifacts"], "mergeArtifacts", minimum=0),
        output_lineage=require_string_list(mapping["outputLineage"], "outputLineage", minimum=1),
        baseline=parse_baseline(mapping["singleExposureBaseline"]),
        raw_modes=parse_raw_modes(mapping["alternativeRawModes"]),
        synchronization=parse_synchronization(mapping["synchronization"]),
        claims_sensor_derived_log=require_bool(
            mapping["claimsSensorDerivedLog"],
            "claimsSensorDerivedLog",
        ),
    )
    require_text(mapping["sourceSampling"], "sourceSampling")
    require_text(mapping["motionAssumptions"], "motionAssumptions")
    analysis["evidence"] = evidence
    analysis["claim"] = claim
    analysis["applyMutant"] = apply_mutant
    return analysis


def assemble(
    case_id: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    open_questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    ordered = dedupe(faults)
    decision = "rejected" if ordered else "recorded"
    require(decision in DECISIONS, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": ordered,
        "preservedResults": preserved,
        "openQuestions": list(open_questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(OPEN_QUESTION in result["openQuestions"], "open question missing")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(bool(result["reasons"]), "reasons must be non-empty")
    return result


def _reasons(analysis: dict[str, Any], lead: list[str], fault_text: dict[str, str] | None) -> list[str]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    reasons = list(lead)
    reasons.extend(analysis["extraReasons"])
    for token in analysis["faults"]:
        reasons.append(text.get(token, token))
    if not analysis["faults"]:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("advanced capture experiment recorded; not a physical qualification")
    if analysis["applyMutant"]:
        reasons.append("mutant rejected: " + MUTANT)
    return reasons


def _lead(full: bool) -> list[str]:
    lead = [
        "host reference only; not a physical S23 measurement",
        "physical S23 was not run",
    ]
    if full:
        lead.extend([
            "goal: " + GOAL,
            "method: " + METHOD,
        ])
    lead.extend([
        "fixture: " + FIXTURE,
        "oracle: " + ORACLE,
    ])
    return lead


def assess(document: dict) -> dict[str, Any]:
    """Record a labelled advanced-capture experiment, or reject an overclaim."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    analysis = _parse_core(document)
    reasons = _reasons(analysis, _lead(True), None)
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, list(NON_CLAIM_QUESTIONS), analysis["evidence"])


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a phase document or a core advanced-capture experiment payload."""
    require(isinstance(payload, dict), "payload must be an object")
    if (
        "schemaVersion" in payload
        or "implementationBaseRevision" in payload
        or "phase" in payload
    ):
        return assess(payload)
    require(set(payload) == CORE_KEYS, "invalid payload keys")
    analysis = _parse_core(payload)
    reasons = _reasons(analysis, _lead(False), None)
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, list(NON_CLAIM_QUESTIONS), analysis["evidence"])


def begin_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(CASE_COMMON_KEYS) | set(extra_keys), "invalid payload keys")
    repeat = require_text(payload["repeat"], "repeat")
    analysis = _parse_core(payload)
    return {
        "evidence": analysis["evidence"],
        "claim": analysis["claim"],
        "repeat": repeat,
        "faults": list(analysis["faults"]),
        "analysis": analysis,
        "snapshot": analysis["snapshot"],
    }


def finish_case(
    case: dict,
    bundle: dict,
    faults: list[str],
    extra_preserved: list,
    fault_text: dict | None = None,
) -> dict[str, Any]:
    analysis = dict(bundle["analysis"])
    analysis["faults"] = dedupe(list(faults))
    reasons = _reasons(
        analysis,
        _lead(False) + [
            case["expected"],
            "repeat " + bundle["repeat"],
        ],
        fault_text,
    )
    preserved = [bundle["evidence"], bundle["snapshot"], bundle["claim"], *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], analysis["faults"], reasons, preserved, questions, bundle["evidence"])


def _artifact(reported: bool, hidden: bool, magnitude: int | float) -> dict:
    return {"reported": reported, "hidden": hidden, "magnitude": magnitude}


def _measurement(measured: bool, value: int | float) -> dict:
    return {"measured": measured, "value": value}


def fixture_motion_alignment() -> dict:
    return {"status": "pass", "error": 0.12, "frames": 3}


def fixture_raw_modes() -> list[dict]:
    return [
        {"id": "raw-10bit", "available": False, "measurementId": None},
        {"id": "raw-14bit", "available": True, "measurementId": "meas-raw-14bit-001"},
    ]


def core_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "experimentLabel": EXPERIMENT_LABEL,
        "captureKind": "multi-frame-hdr",
        "presentedAs": "computational-merge",
        "labelsMergeExplicitly": True,
        "claimsExtraStops": 2,
        "guaranteedEveryScene": False,
        "motionAlignment": fixture_motion_alignment(),
        "ghosting": _artifact(True, False, 0.04),
        "alignmentError": _artifact(True, False, 0.12),
        "motionArtifacts": _measurement(True, 0.04),
        "retainedHighlights": _measurement(True, 0.83),
        "sourceSampling": "bracketed-sensor-frames",
        "motionAssumptions": "moving-subject-across-differently-exposed-frames",
        "exposureDifferences": [-2, 0, 2],
        "mergeArtifacts": ["ghosting", "alignment-error"],
        "outputLineage": [
            "frame-minus-2ev",
            "frame-0ev",
            "frame-plus-2ev",
            "computational-merge",
        ],
        "singleExposureBaseline": {
            "evidenceId": BASELINE_EVIDENCE_ID,
            "retainedHighlights": 0.61,
        },
        "alternativeRawModes": fixture_raw_modes(),
        "synchronization": {
            "labelled": EXPERIMENT_LABEL,
            "offsetMeasured": False,
            "offsetMs": None,
        },
        "claimsSensorDerivedLog": False,
    }
    payload.update(overrides)
    return payload


def fixture_document() -> dict[str, Any]:
    core = core_payload()
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        **core,
    }
