#!/usr/bin/env python3
"""P016 first physical-qualification slice, as a host fixture.

The method, fixture, oracle, and mutant below are the phase contract. This
module does not open a camera, decode a phone file, or execute TC-P016-01
through TC-P016-08. Accepting a mode after only the first decoded frame is
the deliberate mutation and is rejected.

A green result is software bookkeeping for an authored fixture. It is not a
physical S23 qualification, an endurance certificate, or cinema-camera
equivalence.
"""

from __future__ import annotations

import re
from typing import Any


PHASE_ID = "P016"
CASE_ID = "P016"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
REPORT_ID = "s23-first-physical-slice-fixture"
METHOD = (
    "Choose one actually available rear route and conservative advertised configuration. "
    "Capture a controlled sixty-second take with a visible timing event and audio when supported. "
    "Decode it fully, inspect source and output metadata, and preserve thermal and storage observations."
)
FIXTURE = (
    "A real phone take with a single missing sample near thermal escalation "
    "and an otherwise playable output."
)
ORACLE = (
    "The file is retained, playback integrity and cadence receive separate statuses, "
    "and the mode is not endurance-certified."
)
MUTANT = "Accept a mode after checking only the first decoded frame."
DELIVERABLE = "Physical qualification report for one exact configuration"

HEX40 = re.compile(r"^[0-9a-f]{40}$")
REAR_ROUTE = "rear"
CONSERVATIVE = "conservative-advertised"
CONTROLLED_SECONDS = 60
FRAMES = {"all", "first"}
PLAYBACK = {"playable", "playable-with-gap", "unplayable"}
CADENCE = {"withheld", "measured", "unmeasured"}
DECISIONS = {"rejected", "withheld", "slice_reported"}
REPORT_KEYS = {
    "schemaVersion",
    "phase",
    "reportId",
    "implementationBaseRevision",
    "hostFixture",
    "route",
    "configuration",
    "durationSec",
    "timingEventVisible",
    "audioSupported",
    "audioPresent",
    "decodedFully",
    "sourceMetadataInspected",
    "outputMetadataInspected",
    "thermalObservation",
    "storageObservation",
    "fileRetained",
    "playable",
    "missingSampleCount",
    "missingSampleNearThermalEscalation",
    "framesChecked",
    "playbackIntegrity",
    "cadenceStatus",
    "enduranceCertified",
    "firstFrameOnly",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _text(value: object, label: str) -> str:
    require(isinstance(value, str) and bool(value.strip()) and value == value.strip(),
            label + " must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def _exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def _expected_playback(playable: bool, missing: int) -> str:
    if not playable:
        return "unplayable"
    if missing == 0:
        return "playable"
    return "playable-with-gap"


def validate_report(document: dict) -> None:
    """Raise ValueError unless document is the P016 host slice report."""
    report = _exact_keys(document, REPORT_KEYS, "slice report")
    require(type(report["schemaVersion"]) is int and report["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(report["phase"] == PHASE_ID, "phase must be P016")
    require(report["reportId"] == REPORT_ID, "reportId must be " + REPORT_ID)
    revision = report["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "slice report needs the P016 implementation base revision")
    require(_bool(report["hostFixture"], "hostFixture") is True,
            "this gate only accepts an authored host fixture")
    _text(report["route"], "route")
    _text(report["configuration"], "configuration")
    duration = report["durationSec"]
    require(type(duration) is int and duration > 0, "durationSec must be a positive int")
    _bool(report["timingEventVisible"], "timingEventVisible")
    audio_supported = _bool(report["audioSupported"], "audioSupported")
    audio_present = _bool(report["audioPresent"], "audioPresent")
    require(not audio_present or audio_supported, "audio cannot be present when it is unsupported")
    decoded = _bool(report["decodedFully"], "decodedFully")
    _bool(report["sourceMetadataInspected"], "sourceMetadataInspected")
    _bool(report["outputMetadataInspected"], "outputMetadataInspected")
    _text(report["thermalObservation"], "thermalObservation")
    _text(report["storageObservation"], "storageObservation")
    _bool(report["fileRetained"], "fileRetained")
    playable = _bool(report["playable"], "playable")
    missing = report["missingSampleCount"]
    require(type(missing) is int and missing >= 0, "missingSampleCount must be a non-negative int")
    near = _bool(report["missingSampleNearThermalEscalation"], "missingSampleNearThermalEscalation")
    require(missing > 0 or near is False,
            "a thermal-escalation gap requires at least one missing sample")
    frames = report["framesChecked"]
    require(frames in FRAMES, "framesChecked must be all or first")
    first_only = _bool(report["firstFrameOnly"], "firstFrameOnly")
    require(first_only is (frames == "first"), "firstFrameOnly must match framesChecked")
    require(decoded is (frames == "all"), "decodedFully must match a full frame check")
    playback = report["playbackIntegrity"]
    require(playback in PLAYBACK, "playbackIntegrity is not a known status")
    require(playback == _expected_playback(playable, missing),
            "playbackIntegrity does not match playable and missingSampleCount")
    cadence = report["cadenceStatus"]
    require(cadence in CADENCE, "cadenceStatus is not a known status")
    require(playback != cadence, "playback integrity and cadence must be separate statuses")
    _bool(report["enduranceCertified"], "enduranceCertified")


def _preserved(report: dict) -> list[str]:
    file_token = "file-retained" if report["fileRetained"] else "file-not-retained"
    return [
        report["thermalObservation"],
        report["storageObservation"],
        "playback:" + report["playbackIntegrity"],
        "cadence:" + report["cadenceStatus"],
        file_token,
        "route:" + report["route"],
    ]


def _method_gap(report: dict) -> str | None:
    if report["route"] != REAR_ROUTE:
        return "method requires one actually available rear route"
    if report["configuration"] != CONSERVATIVE:
        return "configuration is not the conservative advertised configuration"
    if report["durationSec"] != CONTROLLED_SECONDS:
        return "take is not the controlled sixty-second slice"
    if report["timingEventVisible"] is not True:
        return "visible timing event was not recorded"
    if report["audioSupported"] and not report["audioPresent"]:
        return "audio was supported but not captured"
    if not report["sourceMetadataInspected"] or not report["outputMetadataInspected"]:
        return "source and output metadata were not both inspected"
    return None


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict[str, Any]:
    require(decision in DECISIONS, "decision must not be qualified or allowed")
    require(decision not in {"qualified", "allowed"}, "decision must not be qualified or allowed")
    require(bool(reasons), "reasons required")
    require(bool(preserved), "preservedResults must keep unaffected observations")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def assess_slice(document: dict) -> dict:
    """Apply the P016 oracle and reject the first-frame-only mutant.

    ``slice_reported`` means the authored host record met the sixty-second
    rear-route checklist. It is never ``qualified`` or ``allowed``. Playback
    integrity and cadence stay separate strings. Endurance certification is
    rejected. Checking only the first decoded frame cannot accept the mode.
    """
    validate_report(document)
    report = document
    preserved = _preserved(report)
    playback = report["playbackIntegrity"]
    cadence = report["cadenceStatus"]
    require("playback:" + playback in preserved, "playback status missing from preserved results")
    require("cadence:" + cadence in preserved, "cadence status missing from preserved results")
    require(("playback:" + playback) != ("cadence:" + cadence), "statuses collapsed")

    mutant = report["firstFrameOnly"] is True or report["framesChecked"] != "all"
    rejected: list[str] = []
    if mutant:
        rejected.append("first-frame-only")
    if not report["fileRetained"]:
        rejected.append("file-not-retained")
    if report["enduranceCertified"]:
        rejected.append("endurance-certified")
    if playback == "unplayable":
        rejected.append("playback-failed")

    reasons: list[str] = []
    if mutant:
        reasons.append("checking only the first decoded frame does not accept the mode")
        reasons.append(MUTANT)
    if not report["fileRetained"]:
        reasons.append("the file was not retained")
    if report["enduranceCertified"]:
        reasons.append("endurance certification is rejected for this slice")
    gap = _method_gap(report)
    if gap is not None:
        reasons.append(gap)
    if playback == "unplayable":
        reasons.append("output is not playable")
    if (
        report["missingSampleCount"] == 1
        and report["missingSampleNearThermalEscalation"] is True
        and report["playable"] is True
    ):
        reasons.append(
            "single missing sample near thermal escalation retained on an otherwise playable output"
        )

    hard_reject = bool(rejected)
    if hard_reject:
        decision = "rejected"
    elif gap is not None:
        decision = "withheld"
    else:
        decision = "slice_reported"
        reasons.insert(0, ORACLE)

    reasons.append(
        f"playback {playback} is separate from cadence {cadence}"
    )

    if mutant and decision != "rejected":
        raise ValueError("mutant: accepting a mode after only the first decoded frame")
    if mutant and "first-frame-only" not in rejected:
        raise ValueError("mutant claim was dropped")
    if decision == "slice_reported":
        require(report["fileRetained"] is True, "slice report requires the retained file")
        require(report["enduranceCertified"] is False, "slice report must not endurance-certify")
        require(report["firstFrameOnly"] is False, "slice report must decode more than the first frame")
        require(report["framesChecked"] == "all" and report["decodedFully"] is True,
                "slice report requires a full decode")
        require(gap is None, "slice report must meet the method checklist")
        require(playback != "unplayable", "slice report requires a playable output")

    questions = ["mode is not endurance-certified"]
    if cadence != "measured":
        questions.append("cadence withheld pending measured results")
    else:
        questions.append("measured cadence is not a fixed-cadence certificate")
    if decision == "slice_reported":
        questions.append("endurance unqualified")
    if decision == "withheld" and gap is not None:
        questions.append(gap)

    return _result(decision, reasons, rejected, preserved, questions)
