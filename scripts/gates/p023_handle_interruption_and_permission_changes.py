#!/usr/bin/env python3
"""P023 interruption and permission-change policy.

Host fixture only. Visible stop-and-finalize is the response when camera or
microphone access is lost. A requested audio track is never removed in silence.
This module does not probe a device, does not qualify a physical S23, and does
not execute TC-P023-01 through TC-P023-08.
"""

from __future__ import annotations

PHASE_ID = "P023"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
POLICY_ID = "s23-interruption-permission-fixture"
POLICY = "visible-stop-and-finalize"
METHOD = (
    "Define responses to permission denial, camera preemption, screen departure, "
    "app backgrounding, and device policy restrictions. Follow the existing visible "
    "stop-and-finalize policy unless a separately qualified background design is "
    "approved. Never silently remove a requested audio track."
)
FIXTURE = (
    "Microphone permission revoked during startup while video samples are already arriving."
)
ORACLE = (
    "The take stops or fails visibly under policy, retains available media, and cannot "
    "be labelled a successful audio recording."
)
MUTANT = "Continue silently as video-only after requested microphone acquisition fails."

EVENTS = (
    "permission_denial",
    "camera_preemption",
    "screen_departure",
    "app_backgrounding",
    "device_policy",
    "microphone_revoked_during_startup",
)
OUTCOMES = ("stop", "fail", "continue")
CLAIM_SILENT = "silent-video-only"
CLAIM_NO_VISIBLE = "missing-visible-stop"
CLAIM_DROPPED = "dropped-available-media"
CLAIM_AUDIO = "successful-audio-recording"
CLAIM_BACKGROUND = "qualified-background-recording"

_PAYLOAD_KEYS = (
    "event",
    "audioRequested",
    "videoSamples",
    "audioSamples",
    "visibleOutcome",
    "availableMediaRetained",
    "labelledSuccessfulAudio",
    "silentVideoOnlyContinuation",
    "backgroundDesignApproved",
    "takeId",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FIXTURE_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "policyId",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "backgroundDesignApproved",
    "policy",
    "scenario",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _bool(value: object, name: str) -> bool:
    _require(type(value) is bool, f"{name} must be a bool")
    return value


def _count(value: object, name: str) -> int:
    _require(type(value) is int and value >= 0, f"{name} must be a non-negative int")
    return value


def _token(value: object, name: str) -> str:
    _require(
        isinstance(value, str) and bool(value) and value == value.strip() and " " not in value,
        f"{name} must be a non-empty token",
    )
    return value


def _payload(payload: object) -> dict:
    _require(isinstance(payload, dict), "payload must be a dict")
    _require(set(payload) == set(_PAYLOAD_KEYS), "invalid payload keys")
    event = payload["event"]
    _require(event in EVENTS, "event is not a P023 interruption")
    outcome = payload["visibleOutcome"]
    _require(outcome in OUTCOMES, "visibleOutcome must be stop, fail, or continue")
    audio_requested = _bool(payload["audioRequested"], "audioRequested")
    silent = _bool(payload["silentVideoOnlyContinuation"], "silentVideoOnlyContinuation")
    video_samples = _count(payload["videoSamples"], "videoSamples")
    audio_samples = _count(payload["audioSamples"], "audioSamples")
    if event == "microphone_revoked_during_startup":
        _require(audio_requested, "startup microphone revocation requires requested audio")
        _require(video_samples >= 1, "startup microphone revocation requires arrived video samples")
    if silent:
        _require(audio_requested, "silent video-only continuation requires requested audio")
        _require(outcome == "continue", "silent video-only continuation is not a visible stop or failure")
    normalized = {
        "event": event,
        "audioRequested": audio_requested,
        "videoSamples": video_samples,
        "audioSamples": audio_samples,
        "visibleOutcome": outcome,
        "availableMediaRetained": _bool(payload["availableMediaRetained"], "availableMediaRetained"),
        "labelledSuccessfulAudio": _bool(payload["labelledSuccessfulAudio"], "labelledSuccessfulAudio"),
        "silentVideoOnlyContinuation": silent,
        "backgroundDesignApproved": _bool(payload["backgroundDesignApproved"], "backgroundDesignApproved"),
        "takeId": _token(payload["takeId"], "takeId"),
    }
    return normalized


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict:
    _require(decision not in {"qualified", "allowed"}, "P023 must not yield qualified or allowed")
    _require(bool(reasons), "reasons must be non-empty")
    _require(all(isinstance(item, str) and item for item in reasons), "reasons must be non-empty strings")
    for bucket in (rejected, preserved, open_questions):
        _require(all(isinstance(item, str) for item in bucket), "result lists must contain strings")
    result = {
        "caseId": PHASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(open_questions),
    }
    _require(tuple(result) == _RESULT_KEYS, "invalid result keys")
    return result


def evaluate(payload: dict) -> dict:
    """Apply visible stop-and-finalize. Reject the silent video-only mutant.

    A requested microphone that fails does not become a successful audio
    recording and does not continue as unannounced video-only. Arrived sample
    counts stay in preservedResults even when the decision is rejected.
    backgroundDesignApproved is never treated as a qualified background design.
    """
    fields = _payload(payload)
    silent = fields["silentVideoOnlyContinuation"]
    continued = fields["visibleOutcome"] == "continue"
    retained = fields["availableMediaRetained"]
    labelled = fields["labelledSuccessfulAudio"]
    approved = fields["backgroundDesignApproved"]
    audio_requested = fields["audioRequested"]

    reasons = [f"event {fields['event']} under {POLICY}"]
    rejected: list[str] = []
    open_questions: list[str] = []

    if silent:
        rejected.append(CLAIM_SILENT)
        reasons.append(
            "silent video-only continuation after requested microphone acquisition fails is rejected"
        )
        reasons.append("mutant: " + MUTANT)
    if continued:
        rejected.append(CLAIM_NO_VISIBLE)
        reasons.append("interruption without a visible stop or failure is rejected")
    if not retained:
        rejected.append(CLAIM_DROPPED)
        reasons.append("available media must be retained when the take stops or fails")
    if labelled or audio_requested:
        rejected.append(CLAIM_AUDIO)
        if labelled:
            reasons.append("the take was labelled a successful audio recording")
        else:
            reasons.append("requested audio cannot be labelled a successful audio recording")
    if approved:
        rejected.append(CLAIM_BACKGROUND)
        open_questions.append(
            "separately qualified background design is not established by this host fixture"
        )
        reasons.append("a claimed background-design approval is not qualification")
    if audio_requested and fields["audioSamples"] == 0:
        open_questions.append("requested audio was not acquired before the interruption")

    hard_breach = silent or continued or (not retained) or labelled
    if hard_breach:
        decision = "rejected"
        reasons.append("visible stop-and-finalize policy was not met")
    elif fields["visibleOutcome"] == "stop":
        decision = "stopped"
        reasons.append(
            "visible stop retains available media and does not label a successful audio recording"
        )
    else:
        decision = "failed_visible"
        reasons.append(
            "visible failure retains available media and does not label a successful audio recording"
        )
    if audio_requested and not silent:
        reasons.append("requested audio track was not silently removed")

    preserved = [
        fields["takeId"],
        f"video-samples:{fields['videoSamples']}",
        f"audio-samples:{fields['audioSamples']}",
    ]
    return _result(decision, reasons, rejected, preserved, open_questions)


def validate_fixture(document: object) -> dict:
    """Raise ValueError unless document is the P023 interruption fixture."""
    _require(isinstance(document, dict), "fixture must be an object")
    _require(set(document) == _FIXTURE_KEYS, "invalid fixture keys")
    _require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
             "schemaVersion must be 1")
    _require(document["phase"] == PHASE_ID, "phase must be P023")
    _require(document["implementationBaseRevision"] == BASE_REVISION,
             "fixture needs the P023 implementation base revision")
    _require(document["policyId"] == POLICY_ID, "policyId must be s23-interruption-permission-fixture")
    _require(document["method"] == METHOD, "method text drifted")
    _require(document["fixture"] == FIXTURE, "fixture text drifted")
    _require(document["oracle"] == ORACLE, "oracle text drifted")
    _require(document["mutant"] == MUTANT, "mutant text drifted")
    _require(document["backgroundDesignApproved"] is False,
             "fixture must not approve a background design")
    _require(document["policy"] == POLICY, "policy must be visible-stop-and-finalize")
    scenario = _payload(document["scenario"])
    _require(scenario["event"] == "microphone_revoked_during_startup",
             "fixture scenario must revoke the microphone during startup")
    _require(scenario["silentVideoOnlyContinuation"] is False, "fixture scenario must not be the mutant")
    _require(scenario["labelledSuccessfulAudio"] is False,
             "fixture scenario must not label a successful audio recording")
    _require(scenario["availableMediaRetained"] is True, "fixture scenario must retain available media")
    _require(scenario["visibleOutcome"] in {"stop", "fail"},
             "fixture scenario must stop or fail visibly")
    _require(scenario["backgroundDesignApproved"] is False,
             "fixture scenario must not approve a background design")
    return scenario


def assess_fixture(document: dict) -> dict:
    """Assess the authored fixture. Decision is stopped or failed_visible, never qualified."""
    return evaluate(validate_fixture(document))


def mutant_payload(payload: dict) -> dict:
    """Return the rejected mutant: continue silently as video-only.

    Implementing that mutant would make evaluate() accept this payload as a
    stopped or successful audio take. The host gate rejects it instead.
    """
    fields = _payload(payload)
    _require(fields["audioRequested"], "mutant requires requested audio")
    cloned = dict(fields)
    cloned["silentVideoOnlyContinuation"] = True
    cloned["visibleOutcome"] = "continue"
    cloned["labelledSuccessfulAudio"] = False
    return cloned
