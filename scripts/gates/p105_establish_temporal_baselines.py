#!/usr/bin/env python3
"""P105 Establish temporal baselines.

Host reference only. This module does not probe a device and does not qualify
a physical S23. Frame timestamps in milliseconds and optional luma means become
a mean interval, a max gap relative to the nominal frame period, and flicker
as the sample standard deviation of luma first differences. A gap above 1.5
frame periods stays a cadence_break. It is not smoothed away.
"""

from __future__ import annotations

import math
import statistics
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P105"
GOAL = "Measure frame-independent depth and a simple stabilized baseline before adding a complex temporal model."
METHOD = "Render the same sequences with no stabilization, a documented confidence-aware baseline, and candidate temporal methods. Quantify scale drift, focus pumping, edge flicker, and lag separately. Preserve per-frame depth outputs for diagnosis."
FIXTURE = "A stationary scene followed by a moving subject and a sudden camera cut."
ORACLE = "The benchmark exposes both flicker reduction and temporal lag instead of rewarding smoothness alone."
MUTANT = "Average depth heavily and ignore the resulting delay behind moving subjects."
DELIVERABLE = "Temporal baseline suite and artifact taxonomy"

OPEN_QUESTION = "physical S23 measurement was not run"
MIN_BASELINE_FRAMES = 8
GAP_PERIOD_LIMIT = 1.5
MUTANT_TOKEN = "heavy-average-ignores-subject-delay"

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "nominalFramePeriodMs",
    "frameTimestampsMs",
    "lumaMeans",
    "hideGap",
    "useKeyframeAsBaseline",
    "keyframeScore",
    "applyMutant",
}
COMMON_KEYS = {
    "evidenceId",
    "repeat",
    "nominalFramePeriodMs",
    "frameTimestampsMs",
    "lumaMeans",
    "hideGap",
    "useKeyframeAsBaseline",
    "keyframeScore",
}
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
FAULT_TEXT = {
    "single-still-frame": "a single still frame cannot establish a temporal baseline",
    "fewer-than-eight-frames": "a temporal baseline requires at least 8 frames",
    "non-finite-temporal-metrics": "temporal metrics must be finite before a baseline is recorded",
    "hidden-cadence-gap": "hiding a cadence gap is rejected; the gap stays a cadence_break",
    "pretty-keyframe-score-as-sequence-baseline": "one pretty keyframe score is not the sequence baseline",
    "heavy-average-ignores-subject-delay": MUTANT,
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_number(value: object, label: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number",
    )
    number = float(value)
    require(math.isfinite(number), label + " must be finite")
    return number


def require_bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def require_text(value: object, label: str) -> str:
    require(
        isinstance(value, str) and bool(value.strip()) and value == value.strip(),
        label + " must be a non-empty string",
    )
    return value


def require_count(value: object, label: str) -> int:
    require(type(value) is int and value >= 0, label + " must be a non-negative integer")
    return value


def _fmt(value: object) -> str:
    if value is None:
        return "none"
    return format(float(value), ".10g")


def temporal_metrics(
    frame_timestamps_ms: list,
    nominal_frame_period_ms: float,
    luma_means: list | None = None,
) -> dict[str, Any]:
    """Mean interval, max gap over the nominal period, and luma flicker.

    Intervals longer than 1.5 nominal periods are cadence_break records.
    They are not replaced by the mean interval. Flicker is statistics.stdev
    of the first differences of luma and needs at least two differences.
    """
    require(
        isinstance(frame_timestamps_ms, list) and len(frame_timestamps_ms) >= 1,
        "frameTimestampsMs must be a non-empty list",
    )
    stamps = [
        require_number(item, f"frameTimestampsMs[{index}]")
        for index, item in enumerate(frame_timestamps_ms)
    ]
    for index in range(1, len(stamps)):
        require(stamps[index] > stamps[index - 1], "frame timestamps must be strictly increasing")
    nominal = require_number(nominal_frame_period_ms, "nominalFramePeriodMs")
    require(nominal > 0, "nominalFramePeriodMs must be positive")
    luma_provided = luma_means is not None
    luma: list[float] | None = None
    if luma_provided:
        require(isinstance(luma_means, list), "lumaMeans must be a list or null")
        require(len(luma_means) == len(stamps), "lumaMeans length must match frame timestamps")
        luma = [
            require_number(item, f"lumaMeans[{index}]")
            for index, item in enumerate(luma_means)
        ]
    intervals = [stamps[index] - stamps[index - 1] for index in range(1, len(stamps))]
    mean_interval = statistics.mean(intervals) if intervals else None
    max_gap = max(intervals) if intervals else None
    max_relative = (max_gap / nominal) if max_gap is not None else None
    breaks = []
    for index, interval in enumerate(intervals):
        relative = interval / nominal
        if relative > GAP_PERIOD_LIMIT:
            breaks.append(
                {
                    "kind": "cadence_break",
                    "intervalIndex": index,
                    "intervalMs": interval,
                    "relativeToNominal": relative,
                }
            )
    flicker = None
    if luma is not None:
        differences = [luma[index] - luma[index - 1] for index in range(1, len(luma))]
        if len(differences) >= 2:
            flicker = statistics.stdev(differences)
    return {
        "frameCount": len(stamps),
        "meanIntervalMs": mean_interval,
        "maxGapMs": max_gap,
        "maxGapRelativeToNominal": max_relative,
        "flicker": flicker,
        "intervalsMs": intervals,
        "cadenceBreaks": breaks,
        "lumaProvided": luma_provided,
    }


def baseline_faults(metrics: dict, hide_gap: bool, use_keyframe_as_baseline: bool) -> list[str]:
    faults: list[str] = []
    count = metrics["frameCount"]
    if count < 2:
        faults.append("single-still-frame")
    elif count < MIN_BASELINE_FRAMES:
        faults.append("fewer-than-eight-frames")
    if count >= MIN_BASELINE_FRAMES:
        mean = metrics["meanIntervalMs"]
        relative = metrics["maxGapRelativeToNominal"]
        finite = (
            mean is not None
            and relative is not None
            and math.isfinite(mean)
            and math.isfinite(relative)
        )
        if metrics["lumaProvided"]:
            flicker = metrics["flicker"]
            finite = finite and flicker is not None and math.isfinite(flicker)
        if not finite:
            faults.append("non-finite-temporal-metrics")
    if hide_gap:
        faults.append("hidden-cadence-gap")
    if use_keyframe_as_baseline:
        faults.append("pretty-keyframe-score-as-sequence-baseline")
    return faults


def metric_reason(metrics: dict) -> str:
    return (
        "meanIntervalMs="
        + _fmt(metrics["meanIntervalMs"])
        + "; maxGapRelativeToNominal="
        + _fmt(metrics["maxGapRelativeToNominal"])
        + "; flicker="
        + _fmt(metrics["flicker"])
        + "; frames="
        + str(metrics["frameCount"])
    )


def cadence_reason(metrics: dict) -> str:
    breaks = metrics["cadenceBreaks"]
    if not breaks:
        return "no cadence_break; no interval exceeds 1.5 frame periods"
    return (
        "cadence_break recorded for "
        + str(len(breaks))
        + " interval(s); the gap was not smoothed"
    )


def public_metrics(metrics: dict) -> dict[str, Any]:
    return {
        "frameCount": metrics["frameCount"],
        "meanIntervalMs": metrics["meanIntervalMs"],
        "maxGapMs": metrics["maxGapMs"],
        "maxGapRelativeToNominal": metrics["maxGapRelativeToNominal"],
        "flicker": metrics["flicker"],
        "intervalsMs": list(metrics["intervalsMs"]),
        "cadenceBreaks": list(metrics["cadenceBreaks"]),
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
        "rejectedClaims": list(faults),
        "preservedResults": preserved,
        "openQuestions": list(open_questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(OPEN_QUESTION in result["openQuestions"], "open question missing")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    return result


def _keyframe_score(value: object) -> float | None:
    if value is None:
        return None
    return require_number(value, "keyframeScore")


def begin_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    expected = set(COMMON_KEYS) | set(extra_keys)
    require(set(payload) == expected, "invalid payload keys")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    repeat = require_text(payload["repeat"], "repeat")
    metrics = temporal_metrics(
        payload["frameTimestampsMs"],
        payload["nominalFramePeriodMs"],
        payload["lumaMeans"],
    )
    hide_gap = require_bool(payload["hideGap"], "hideGap")
    use_keyframe = require_bool(payload["useKeyframeAsBaseline"], "useKeyframeAsBaseline")
    _keyframe_score(payload["keyframeScore"])
    faults = baseline_faults(metrics, hide_gap, use_keyframe)
    return {
        "evidence": evidence,
        "repeat": repeat,
        "metrics": metrics,
        "faults": faults,
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
        "host reference only; not a physical S23 measurement",
        metric_reason(bundle["metrics"]),
        cadence_reason(bundle["metrics"]),
        case["expected"],
        "repeat " + bundle["repeat"],
    ]
    for token in faults:
        reasons.append(text.get(token, token))
    if not faults:
        reasons.append("baseline recorded; not qualified as physical temporal performance")
    preserved = [bundle["evidence"], public_metrics(bundle["metrics"]), *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], faults, reasons, preserved, questions, bundle["evidence"])


def assess(document: dict) -> dict[str, Any]:
    """Record a host temporal baseline or reject one that cannot be kept.

    A single still frame, fewer than eight frames, a hidden cadence gap, a
    pretty keyframe used as the sequence baseline, non-finite metrics, and
    the directive mutant are rejected. Eight finite frames are recorded,
    including any cadence_break, and are never qualified.
    """
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
    hide_gap = require_bool(document["hideGap"], "hideGap")
    use_keyframe = require_bool(document["useKeyframeAsBaseline"], "useKeyframeAsBaseline")
    apply_mutant = require_bool(document["applyMutant"], "applyMutant")
    _keyframe_score(document["keyframeScore"])
    metrics = temporal_metrics(
        document["frameTimestampsMs"],
        document["nominalFramePeriodMs"],
        document["lumaMeans"],
    )
    faults = baseline_faults(metrics, hide_gap, use_keyframe)
    if apply_mutant:
        faults.append(MUTANT_TOKEN)
    reasons = [
        "host reference only; not a physical S23 measurement",
        "goal: " + GOAL,
        "method: " + METHOD,
        "fixture: " + FIXTURE,
        "oracle: " + ORACLE,
        metric_reason(metrics),
        cadence_reason(metrics),
    ]
    for token in faults:
        reasons.append(FAULT_TEXT[token])
    if not faults:
        reasons.append("baseline recorded; not qualified as physical temporal performance")
    if use_keyframe:
        reasons.append("keyframe score was not accepted as the sequence baseline")
    elif document["keyframeScore"] is not None:
        reasons.append("keyframe score was ignored; the sequence metrics are the baseline")
    preserved = [evidence, public_metrics(metrics), claim]
    return assemble(PHASE, faults, reasons, preserved, NON_CLAIM_QUESTIONS, evidence)
