#!/usr/bin/env python3
"""P149 Establish thermal and endurance acceptance.

Host reference only. This module does not probe a device and does not qualify
a physical S23. Thermal status is one of none, moderate, severe, critical, or
unknown. Severe or critical must set continue_capture false or a controlled
stop. Ignoring severe thermal to keep an advertised fps (continue_capture true
and advertised_fps claimed) is rejected. An envelope is recorded only with
measured_on_device true; otherwise it is not a physical pass and the decision
stays recorded only if the document says unavailable. Do not claim a
frame-rate guarantee from a short sample. The decision is never qualified.

Thermal rule: severe or critical must set continue_capture false or a
controlled stop. continue_capture true together with an advertised fps claim
under severe or critical thermal status is rejected. A configuration envelope
is a physical pass only when measured_on_device is true and the document
records it; an unmeasured document stays recorded only when envelope status
is unavailable. A frame-rate guarantee from a sample shorter than the
sustained-sample floor is rejected.
"""

from __future__ import annotations

import math
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P149"
WORKSTREAM = 19
TITLE = "Establish thermal and endurance acceptance"
GOAL = "Use conservative safety policies and measured operating envelopes."
METHOD = (
    "Run controlled sustained tests across relevant source and render configurations, "
    "record ambient conditions and device state, and observe thermal callbacks. Reduce "
    "optional preview work first. Severe pressure triggers a controlled stop that preserves "
    "footage; do not bypass protections."
)
FIXTURE = "A prolonged high-resolution take followed by deferred depth rendering while the phone is already warm."
ORACLE = "The app follows its documented limits, retains media, and does not claim unlimited performance from a short cold run."
MUTANT = "Ignore severe thermal status to maintain an advertised frame-rate claim."
DELIVERABLE = "Endurance protocol and configuration-specific operating envelope"
DEPENDENCIES = ("P148",)

THERMAL_RULE = (
    "Thermal status is one of none, moderate, severe, critical, or unknown. "
    "Severe or critical must set continue_capture false or a controlled stop. "
    "Ignoring severe thermal to keep an advertised fps "
    "(continue_capture true and advertised_fps claimed) is rejected. "
    "An envelope is recorded only with measured_on_device true; otherwise it is not a physical pass "
    "and the decision stays recorded only if the document says unavailable. "
    "Do not claim a frame-rate guarantee from a short sample. "
    "The decision is never qualified."
)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p149-thermal-endurance"
CLAIM = "thermal-and-endurance-acceptance-host-reference"
CONFIGURATION = "high-resolution-deferred-depth"
SHORT_SAMPLE_SECONDS = 30
PROLONGED_SAMPLE_SECONDS = 180
AMBIENT_CELSIUS = 28
HIGH_COVERAGE = 0.8
MAX_DIMENSION = 8192
MAX_LENGTH = 8_000_000
MAX_ALLOCATION = 8_000_000

THERMAL_STATUSES = frozenset({"none", "moderate", "severe", "critical", "unknown"})
PRESSURE_STATUSES = frozenset({"severe", "critical"})
WARMTH_STATUSES = frozenset({"moderate", "severe", "critical"})
ENVELOPE_STATUSES = frozenset({"recorded", "unavailable"})

ADVERTISED_FPS_IGNORED_SEVERE = "protection-bypassed-for-advertised-rate"
SEVERE_OR_CRITICAL_CONTINUED = "severe-or-critical-capture-continued"
FOOTAGE_NOT_PRESERVED = "footage-not-preserved-under-thermal-pressure"
OPTIONAL_PREVIEW_NOT_REDUCED = "optional-preview-not-reduced"
ENVELOPE_WITHOUT_MEASUREMENT = "envelope-recorded-without-device-measurement"
FRAME_RATE_FROM_SHORT_SAMPLE = "frame-rate-guarantee-from-short-sample"
FRAME_RATE_WITHOUT_MEASURED_ENVELOPE = "frame-rate-guarantee-without-measured-envelope"
MUTANT_NOT_DETECTED = "critical-thermal-mutant-not-detected"

RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = frozenset({"recorded", "rejected"})
NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "thermalStatus",
    "continueCapture",
    "controlledStop",
    "advertisedFpsClaimed",
    "optionalPreviewReduced",
    "footagePreserved",
    "sampleDurationSeconds",
    "frameRateGuaranteeClaimed",
    "measuredOnDevice",
    "envelopeStatus",
    "configuration",
    "ambientCelsius",
    "deviceState",
}
CORE_KEYS = {
    "evidenceId",
    "claim",
    "applyMutant",
    "thermalStatus",
    "continueCapture",
    "controlledStop",
    "advertisedFpsClaimed",
    "optionalPreviewReduced",
    "footagePreserved",
    "sampleDurationSeconds",
    "frameRateGuaranteeClaimed",
    "measuredOnDevice",
    "envelopeStatus",
    "configuration",
    "ambientCelsius",
    "deviceState",
}
CASE_COMMON_KEYS = CORE_KEYS | {"repeat"}
RESULT_STATUSES = frozenset({"pass", "fail", "skip", "unavailable"})
SUMMARY_KEYS = ("pass", "fail", "skip", "unavailable")
FORBIDDEN_RELEASE_SCOPES = frozenset({"native-resolution", "camera-equivalence"})
FEATURE_STATES = frozenset({"implemented", "experimental", "physically-qualified"})
MIGRATIONS = frozenset({"explicit", "refused", "silent-uninstall", "none"})
PRIVATE_TRANSMISSIONS = frozenset({"frames", "depth", "audio", "metadata", "private-metadata"})
TRANSMISSION_KINDS = PRIVATE_TRANSMISSIONS | {"thumbnail", "none"}

FAULT_TEXT = {
    ADVERTISED_FPS_IGNORED_SEVERE: MUTANT,
    SEVERE_OR_CRITICAL_CONTINUED: (
        "severe or critical thermal status continued capture without a controlled stop"
    ),
    FOOTAGE_NOT_PRESERVED: (
        "thermal pressure or a controlled stop did not preserve footage"
    ),
    OPTIONAL_PREVIEW_NOT_REDUCED: (
        "optional preview work was not reduced before continued capture under warmth"
    ),
    ENVELOPE_WITHOUT_MEASUREMENT: (
        "envelope recorded without measured_on_device; not a physical pass"
    ),
    FRAME_RATE_FROM_SHORT_SAMPLE: (
        "frame-rate guarantee claimed from a short sample"
    ),
    FRAME_RATE_WITHOUT_MEASURED_ENVELOPE: (
        "frame-rate guarantee claimed without a measured recorded envelope"
    ),
    MUTANT_NOT_DETECTED: (
        "critical thermal mutant was not detected"
    ),
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
    require(type(value) is int, label + " must be an int")
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


def display_number(value: float) -> int | float:
    if float(value).is_integer():
        return int(value)
    return float(value)


def is_short_sample(duration_seconds: float) -> bool:
    """A sample shorter than the sustained floor cannot support a frame-rate guarantee."""
    return float(duration_seconds) < float(SHORT_SAMPLE_SECONDS)


def capture_held(continue_capture: bool, controlled_stop: bool) -> bool:
    """True when capture is still running and no controlled stop was taken."""
    return continue_capture is True and controlled_stop is False


def pressure_resolved(continue_capture: bool, controlled_stop: bool) -> bool:
    """Severe or critical must set continue_capture false or a controlled stop."""
    return continue_capture is False or controlled_stop is True


def envelope_recorded(measured_on_device: bool, envelope_status: str) -> bool:
    """An envelope is recorded only with measured_on_device true."""
    return measured_on_device is True and envelope_status == "recorded"


def ignored_severe_for_advertised_fps(
    thermal_status: str,
    continue_capture: bool,
    advertised_fps_claimed: bool,
    apply_mutant: bool,
) -> bool:
    """Ignoring severe or critical thermal status to keep an advertised fps."""
    if apply_mutant:
        return True
    return (
        thermal_status in PRESSURE_STATUSES
        and continue_capture is True
        and advertised_fps_claimed is True
    )


def analyze_computation(
    *,
    thermal_status: str,
    continue_capture: bool,
    controlled_stop: bool,
    advertised_fps_claimed: bool,
    optional_preview_reduced: bool,
    footage_preserved: bool,
    sample_duration_seconds: float,
    frame_rate_guarantee_claimed: bool,
    measured_on_device: bool,
    envelope_status: str,
    configuration: str,
    ambient_celsius: float,
    device_state: str,
    apply_mutant: bool,
) -> dict[str, Any]:
    faults: list[str] = []
    short = is_short_sample(sample_duration_seconds)
    recorded = envelope_recorded(measured_on_device, envelope_status)
    ignored = ignored_severe_for_advertised_fps(
        thermal_status,
        continue_capture,
        advertised_fps_claimed,
        apply_mutant,
    )
    if thermal_status in PRESSURE_STATUSES and not pressure_resolved(continue_capture, controlled_stop):
        faults.append(SEVERE_OR_CRITICAL_CONTINUED)
    if ignored:
        faults.append(ADVERTISED_FPS_IGNORED_SEVERE)
    if (thermal_status in PRESSURE_STATUSES or controlled_stop) and not footage_preserved:
        faults.append(FOOTAGE_NOT_PRESERVED)
    if (
        thermal_status in WARMTH_STATUSES
        and capture_held(continue_capture, controlled_stop)
        and not optional_preview_reduced
    ):
        faults.append(OPTIONAL_PREVIEW_NOT_REDUCED)
    if not measured_on_device and envelope_status != "unavailable":
        faults.append(ENVELOPE_WITHOUT_MEASUREMENT)
    if frame_rate_guarantee_claimed and short:
        faults.append(FRAME_RATE_FROM_SHORT_SAMPLE)
    if frame_rate_guarantee_claimed and not recorded:
        faults.append(FRAME_RATE_WITHOUT_MEASURED_ENVELOPE)
    snapshot: dict[str, Any] = {
        "thermalStatus": thermal_status,
        "continueCapture": continue_capture,
        "controlledStop": controlled_stop,
        "advertisedFpsClaimed": advertised_fps_claimed,
        "optionalPreviewReduced": optional_preview_reduced,
        "footagePreserved": footage_preserved,
        "sampleDurationSeconds": display_number(sample_duration_seconds),
        "shortSample": short,
        "frameRateGuaranteeClaimed": frame_rate_guarantee_claimed,
        "measuredOnDevice": measured_on_device,
        "envelopeStatus": envelope_status,
        "envelopeRecorded": recorded,
        "physicalPass": recorded,
        "configuration": configuration,
        "ambientCelsius": display_number(ambient_celsius),
        "deviceState": device_state,
        "pressureResolved": pressure_resolved(continue_capture, controlled_stop)
        if thermal_status in PRESSURE_STATUSES
        else True,
        "ignoredSevereForAdvertisedFps": ignored,
        "mutantApplied": apply_mutant,
        "envelope": None,
    }
    if recorded:
        snapshot["envelope"] = {
            "configuration": configuration,
            "ambientCelsius": display_number(ambient_celsius),
            "deviceState": device_state,
            "measuredOnDevice": True,
            "sampleDurationSeconds": display_number(sample_duration_seconds),
            "thermalStatus": thermal_status,
        }
    extra_reasons = [
        "thermal status " + thermal_status,
        "continue_capture " + str(continue_capture).lower(),
        "controlled_stop " + str(controlled_stop).lower(),
        "thermal rule: " + THERMAL_RULE,
    ]
    if recorded:
        extra_reasons.append(
            "envelope recorded for " + configuration + " because measured_on_device is true"
        )
    elif envelope_status == "unavailable":
        extra_reasons.append(
            "document says unavailable; not a physical pass; decision stays recorded only without other faults"
        )
    else:
        extra_reasons.append(
            "document does not say unavailable and measured_on_device is false; not a physical pass"
        )
    if short:
        extra_reasons.append(
            "short sample " + str(snapshot["sampleDurationSeconds"]) + "s; no frame-rate guarantee is accepted"
        )
    else:
        extra_reasons.append(
            "sample duration " + str(snapshot["sampleDurationSeconds"]) + "s is not a short sample"
        )
    if ignored:
        extra_reasons.append("ignored severe thermal status while an advertised fps was claimed")
    return {
        "faults": dedupe(faults),
        "snapshot": snapshot,
        "extraReasons": extra_reasons,
    }


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


def _parse_core(mapping: dict) -> dict[str, Any]:
    evidence = require_text(mapping["evidenceId"], "evidenceId")
    claim = require_text(mapping["claim"], "claim")
    apply_mutant = require_bool(mapping["applyMutant"], "applyMutant")
    thermal_status = require_text(mapping["thermalStatus"], "thermalStatus")
    require(thermal_status in THERMAL_STATUSES, "thermalStatus is not recognized")
    continue_capture = require_bool(mapping["continueCapture"], "continueCapture")
    controlled_stop = require_bool(mapping["controlledStop"], "controlledStop")
    advertised = require_bool(mapping["advertisedFpsClaimed"], "advertisedFpsClaimed")
    preview = require_bool(mapping["optionalPreviewReduced"], "optionalPreviewReduced")
    footage = require_bool(mapping["footagePreserved"], "footagePreserved")
    duration = require_number(mapping["sampleDurationSeconds"], "sampleDurationSeconds")
    require(duration > 0, "sampleDurationSeconds must be > 0")
    guarantee = require_bool(mapping["frameRateGuaranteeClaimed"], "frameRateGuaranteeClaimed")
    measured = require_bool(mapping["measuredOnDevice"], "measuredOnDevice")
    envelope_status = require_text(mapping["envelopeStatus"], "envelopeStatus")
    require(envelope_status in ENVELOPE_STATUSES, "envelopeStatus is not recognized")
    configuration = require_text(mapping["configuration"], "configuration")
    ambient = require_number(mapping["ambientCelsius"], "ambientCelsius")
    device_state = require_text(mapping["deviceState"], "deviceState")
    analysis = analyze_computation(
        thermal_status=thermal_status,
        continue_capture=continue_capture,
        controlled_stop=controlled_stop,
        advertised_fps_claimed=advertised,
        optional_preview_reduced=preview,
        footage_preserved=footage,
        sample_duration_seconds=duration,
        frame_rate_guarantee_claimed=guarantee,
        measured_on_device=measured,
        envelope_status=envelope_status,
        configuration=configuration,
        ambient_celsius=ambient,
        device_state=device_state,
        apply_mutant=apply_mutant,
    )
    analysis["evidence"] = evidence
    analysis["claim"] = claim
    analysis["applyMutant"] = apply_mutant
    return analysis


def _reasons(analysis: dict[str, Any], lead: list[str], fault_text: dict[str, str] | None) -> list[str]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    reasons = list(lead)
    reasons.extend(analysis["extraReasons"])
    for token in analysis["faults"]:
        reasons.append(text.get(token, token))
    if ADVERTISED_FPS_IGNORED_SEVERE in analysis["faults"]:
        reasons.append("mutant rejected: " + MUTANT)
    if not analysis["faults"]:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("endurance protocol recorded; not a physical qualification")
    return reasons


def _lead(full: bool) -> list[str]:
    rows = [
        "host reference only; not a physical S23 measurement",
        "physical S23 was not run",
    ]
    if full:
        rows.extend([
            "goal: " + GOAL,
            "method: " + METHOD,
            "fixture: " + FIXTURE,
            "oracle: " + ORACLE,
        ])
    else:
        rows.extend([
            "oracle: " + ORACLE,
            "fixture: " + FIXTURE,
        ])
    return rows


def assess(document: dict) -> dict[str, Any]:
    """Record an endurance protocol, or reject a thermal or envelope breach."""
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
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a phase document or a core thermal-and-endurance payload."""
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
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


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
        "applyMutant": analysis["applyMutant"],
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
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 was not run",
            "oracle: " + ORACLE,
            case["expected"],
            "repeat " + bundle["repeat"],
        ],
        fault_text,
    )
    preserved = [bundle["evidence"], bundle["snapshot"], bundle["claim"], *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], analysis["faults"], reasons, preserved, questions, bundle["evidence"])


def core_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "thermalStatus": "moderate",
        "continueCapture": True,
        "controlledStop": False,
        "advertisedFpsClaimed": False,
        "optionalPreviewReduced": True,
        "footagePreserved": True,
        "sampleDurationSeconds": PROLONGED_SAMPLE_SECONDS,
        "frameRateGuaranteeClaimed": False,
        "measuredOnDevice": False,
        "envelopeStatus": "unavailable",
        "configuration": CONFIGURATION,
        "ambientCelsius": AMBIENT_CELSIUS,
        "deviceState": "warm-unmeasured",
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


def canonical_severe_mutant(**overrides: Any) -> dict[str, Any]:
    """The phase mutant: keep capturing an advertised fps under severe thermal status."""
    payload = core_payload(
        thermalStatus="severe",
        continueCapture=True,
        controlledStop=False,
        advertisedFpsClaimed=True,
        optionalPreviewReduced=False,
        footagePreserved=True,
    )
    payload.update(overrides)
    return payload


def canonical_critical_stop(**overrides: Any) -> dict[str, Any]:
    """Critical thermal status resolved by stopping capture and preserving footage."""
    payload = core_payload(
        thermalStatus="critical",
        continueCapture=False,
        controlledStop=True,
        advertisedFpsClaimed=False,
        optionalPreviewReduced=True,
        footagePreserved=True,
    )
    payload.update(overrides)
    return payload
