#!/usr/bin/env python3
"""P027 microphone acquisition contract.

Host fixture only. A stereo request routed to a mono source must report the
actual channel count. A blocked encoder is encoder delay, not missing
microphone data. Bounded PCM queues, clipping, silencing, permission, and
route policy stay in the result.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P027-01 through TC-P027-08.
"""

from __future__ import annotations

import re


PHASE_ID = "P027"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
CONTRACT_ID = "s23-microphone-acquisition-fixture"
METHOD = (
    "Use bounded PCM transfer, report actual format and route, preserve clipping and "
    "silencing evidence, and separate acquisition from AAC callbacks. Microphone route "
    "changes are events with an explicit continue or stop policy, never invisible "
    "configuration drift."
)
FIXTURE = (
    "A stereo request routed to a mono source and a deliberate encoder stall while "
    "microphone acquisition continues."
)
ORACLE = (
    "The output describes actual channels, queue limits hold, and acquisition timing "
    "distinguishes encoder delay from missing microphone data."
)
MUTANT = "Report requested stereo when only one source channel exists."
MUTANT_CLAIM = "requested-stereo-as-actual"
HOST_LIMIT = "physical S23 microphone acquisition was not measured"

ROUTE_POLICIES = ("continue", "stop", "invisible-drift")
PERMISSIONS = ("granted", "denied")
_TOKEN = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
_DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "contractId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "queueLimitFrames",
    "sampleRateHz",
    "pcmFormat",
    "observations",
}
_OBS_KEYS = {
    "id",
    "requestedChannels",
    "sourceChannels",
    "reportedChannels",
    "pcmFormat",
    "sampleRateHz",
    "route",
    "routeChanged",
    "routePolicy",
    "microphonePermission",
    "queueLimitFrames",
    "queuedFrames",
    "encoderStalled",
    "acquisitionContinuing",
    "encoderDelayMs",
    "missingMicrophoneMs",
    "timingSeparated",
    "clippedSamples",
    "silencedSamples",
    "clippingPreserved",
    "silencingPreserved",
    "aacSeparated",
}
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _exact_keys(value: object, required: set[str], context: str) -> dict:
    _require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    _require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    _require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def _bool(value: object, name: str) -> bool:
    _require(type(value) is bool, f"{name} must be a bool")
    return value


def _int(value: object, name: str, low: int, high: int) -> int:
    _require(type(value) is int and low <= value <= high, f"{name} must be an int in {low}..{high}")
    return value


def _token(value: object, name: str) -> str:
    _require(isinstance(value, str) and _TOKEN.fullmatch(value) is not None, f"{name} must be a token")
    return value


def _observation(payload: object) -> dict:
    raw = _exact_keys(payload, _OBS_KEYS, "observation")
    policy = raw["routePolicy"]
    permission = raw["microphonePermission"]
    _require(policy in ROUTE_POLICIES, "routePolicy must be continue, stop, or invisible-drift")
    _require(permission in PERMISSIONS, "microphonePermission must be granted or denied")
    return {
        "id": _token(raw["id"], "id"),
        "requestedChannels": _int(raw["requestedChannels"], "requestedChannels", 1, 8),
        "sourceChannels": _int(raw["sourceChannels"], "sourceChannels", 1, 8),
        "reportedChannels": _int(raw["reportedChannels"], "reportedChannels", 1, 8),
        "pcmFormat": _token(raw["pcmFormat"], "pcmFormat"),
        "sampleRateHz": _int(raw["sampleRateHz"], "sampleRateHz", 1, 384000),
        "route": _token(raw["route"], "route"),
        "routeChanged": _bool(raw["routeChanged"], "routeChanged"),
        "routePolicy": policy,
        "microphonePermission": permission,
        "queueLimitFrames": _int(raw["queueLimitFrames"], "queueLimitFrames", 1, 256),
        "queuedFrames": _int(raw["queuedFrames"], "queuedFrames", 0, 100000),
        "encoderStalled": _bool(raw["encoderStalled"], "encoderStalled"),
        "acquisitionContinuing": _bool(raw["acquisitionContinuing"], "acquisitionContinuing"),
        "encoderDelayMs": _int(raw["encoderDelayMs"], "encoderDelayMs", 0, 3600000),
        "missingMicrophoneMs": _int(raw["missingMicrophoneMs"], "missingMicrophoneMs", 0, 3600000),
        "timingSeparated": _bool(raw["timingSeparated"], "timingSeparated"),
        "clippedSamples": _int(raw["clippedSamples"], "clippedSamples", 0, 10000000),
        "silencedSamples": _int(raw["silencedSamples"], "silencedSamples", 0, 10000000),
        "clippingPreserved": _bool(raw["clippingPreserved"], "clippingPreserved"),
        "silencingPreserved": _bool(raw["silencingPreserved"], "silencingPreserved"),
        "aacSeparated": _bool(raw["aacSeparated"], "aacSeparated"),
    }


def is_requested_stereo_mutant(observation: dict) -> bool:
    """True when requested stereo is reported for a one-channel source.

    Implementing the mutant would make this true and still return actual_channels.
    The host gate rejects that report instead.
    """
    _require(isinstance(observation, dict), "observation must be an object")
    return (
        observation.get("sourceChannels") == 1
        and observation.get("requestedChannels") == 2
        and observation.get("reportedChannels") == 2
    )


def _preserved(data: dict) -> list[str]:
    return [
        data["id"],
        f"source-channels:{data['sourceChannels']}",
        f"requested-channels:{data['requestedChannels']}",
        f"reported-channels:{data['reportedChannels']}",
        data["pcmFormat"],
        data["route"],
        f"route-policy:{data['routePolicy']}",
        f"permission:{data['microphonePermission']}",
        f"queued-frames:{data['queuedFrames']}/{data['queueLimitFrames']}",
        f"encoder-delay-ms:{data['encoderDelayMs']}",
        f"missing-microphone-ms:{data['missingMicrophoneMs']}",
        f"clipped-samples:{data['clippedSamples']}",
        f"silenced-samples:{data['silencedSamples']}",
    ]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    _require(decision not in {"qualified", "allowed"}, "P027 must not yield qualified or allowed")
    _require(bool(reasons), "reasons must be non-empty")
    _require(all(isinstance(item, str) and item for item in reasons), "reasons must be non-empty strings")
    for bucket in (rejected, preserved, questions):
        _require(all(isinstance(item, str) for item in bucket), "result lists must contain strings")
    result = {
        "caseId": PHASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    _require(tuple(result) == _RESULT_KEYS, "invalid result keys")
    return result


def evaluate(payload: dict) -> dict:
    """Report actual channels and keep encoder delay distinct from microphone gaps.

    The mutant — reporting requested stereo when only one source channel exists —
    is rejected. Clipping, silencing, queue occupancy, and both timing figures
    stay in preservedResults.
    """
    data = _observation(payload)
    reasons = [
        f"observation {data['id']}",
        (
            f"requested {data['requestedChannels']} source {data['sourceChannels']} "
            f"reported {data['reportedChannels']}"
        ),
        f"route {data['route']} policy {data['routePolicy']}",
        f"pcm {data['pcmFormat']} at {data['sampleRateHz']}",
    ]
    rejected: list[str] = []
    questions = [HOST_LIMIT]
    if data["encoderStalled"]:
        questions.append("encoder stall does not prove microphone samples were missing")

    if is_requested_stereo_mutant(data):
        rejected.append(MUTANT_CLAIM)
        reasons.append("mutant: " + MUTANT)
    if data["reportedChannels"] != data["sourceChannels"]:
        rejected.append("actual-channels-not-reported")
        reasons.append("output must describe actual source channels")
    if data["queuedFrames"] > data["queueLimitFrames"]:
        rejected.append("queue-limit-exceeded")
        reasons.append("PCM queue limit did not hold")
    if not data["timingSeparated"]:
        rejected.append("timing-not-distinguished")
        reasons.append("encoder delay was not distinguished from missing microphone data")
    if data["encoderStalled"] and not data["acquisitionContinuing"]:
        rejected.append("stall-treated-as-missing-microphone")
        reasons.append("encoder stall stopped acquisition as if microphone data were missing")
    if data["routePolicy"] == "invisible-drift":
        rejected.append("invisible-route-drift")
        reasons.append("microphone route change must use an explicit continue or stop policy")
    elif data["routeChanged"] and data["routePolicy"] not in {"continue", "stop"}:
        rejected.append("invisible-route-drift")
        reasons.append("microphone route change must use an explicit continue or stop policy")
    if data["clippedSamples"] > 0 and not data["clippingPreserved"]:
        rejected.append("clipping-erased")
        reasons.append("clipping evidence was not preserved")
    if data["silencedSamples"] > 0 and not data["silencingPreserved"]:
        rejected.append("silencing-erased")
        reasons.append("silencing evidence was not preserved")
    if not data["aacSeparated"]:
        rejected.append("aac-callback-merged")
        reasons.append("microphone acquisition was not separated from AAC callbacks")
    if data["microphonePermission"] == "denied" and data["acquisitionContinuing"]:
        rejected.append("acquisition-without-permission")
        reasons.append("microphone acquisition continued without permission")
    if data["microphonePermission"] == "denied" and data["routePolicy"] != "stop":
        rejected.append("permission-without-stop")
        reasons.append("permission loss requires an explicit stop policy")

    if rejected:
        decision = "rejected"
    elif data["microphonePermission"] == "denied":
        decision = "stopped"
        reasons.append("microphone permission denied and acquisition stopped under an explicit policy")
    else:
        decision = "actual_channels"
        reasons.append(
            f"actual channels {data['sourceChannels']} described; "
            f"queue {data['queuedFrames']} within {data['queueLimitFrames']}"
        )
        reasons.append("acquisition is separate from AAC callbacks")
        if data["encoderStalled"] and data["acquisitionContinuing"]:
            reasons.append(
                f"encoder delay {data['encoderDelayMs']} ms is distinct from "
                f"missing microphone data {data['missingMicrophoneMs']} ms"
            )
        if data["clippedSamples"] or data["silencedSamples"]:
            reasons.append("clipping and silencing evidence preserved")
    return _result(decision, reasons, rejected, _preserved(data), questions)


def validate_fixture(document: object) -> None:
    """Raise ValueError unless document is a P027 acquisition fixture."""
    raw = _exact_keys(document, _DOCUMENT_KEYS, "fixture")
    _require(type(raw["schemaVersion"]) is int and raw["schemaVersion"] == 1, "schemaVersion must be 1")
    _require(raw["phase"] == PHASE_ID, "phase must be P027")
    _require(raw["contractId"] == CONTRACT_ID, "contractId must be s23-microphone-acquisition-fixture")
    _require(raw["implementationBaseRevision"] == BASE_REVISION, "fixture needs the P027 implementation base revision")
    _require(raw["method"] == METHOD, "method text drifted")
    _require(raw["fixture"] == FIXTURE, "fixture text drifted")
    _require(raw["oracle"] == ORACLE, "oracle text drifted")
    _require(raw["mutant"] == MUTANT, "mutant text drifted")
    limit = _int(raw["queueLimitFrames"], "queueLimitFrames", 1, 256)
    rate = _int(raw["sampleRateHz"], "sampleRateHz", 1, 384000)
    pcm = _token(raw["pcmFormat"], "pcmFormat")
    observations = raw["observations"]
    _require(isinstance(observations, list) and observations, "observations must be a non-empty list")
    seen: set[str] = set()
    for index, item in enumerate(observations):
        data = _observation(item)
        _require(data["id"] not in seen, "duplicate observation id: " + data["id"])
        seen.add(data["id"])
        _require(data["queueLimitFrames"] == limit, f"observation {index} queue limit drifted from the fixture")
        _require(data["sampleRateHz"] == rate, f"observation {index} sample rate drifted from the fixture")
        _require(data["pcmFormat"] == pcm, f"observation {index} pcm format drifted from the fixture")


def assess_acquisition(document: dict) -> dict:
    """Assess every observation. The stereo-as-actual mutant is rejected.

    preservedResults keeps channel counts, queue occupancy, clipping, silencing,
    encoder delay, and missing-microphone time even when the decision is rejected.
    """
    validate_fixture(document)
    parts = [evaluate(item) for item in document["observations"]]
    rejected: list[str] = []
    preserved: list[str] = []
    reasons: list[str] = []
    questions: list[str] = []
    decisions: list[str] = []
    for part in parts:
        decisions.append(part["decision"])
        reasons.extend(part["reasons"])
        preserved.extend(part["preservedResults"])
        for claim in part["rejectedClaims"]:
            if claim not in rejected:
                rejected.append(claim)
        for question in part["openQuestions"]:
            if question not in questions:
                questions.append(question)
    stalled = any(item["encoderStalled"] for item in document["observations"])
    if any(item == "rejected" for item in decisions):
        decision = "rejected"
        reasons.append("microphone acquisition contract rejected")
    elif decisions and all(item == "actual_channels" for item in decisions):
        decision = "actual_channels"
        reasons.append("queue limits hold")
        if stalled:
            reasons.append("acquisition timing distinguishes encoder delay from missing microphone data")
    elif decisions and all(item == "stopped" for item in decisions):
        decision = "stopped"
        reasons.append("acquisition stopped under an explicit permission policy")
    else:
        decision = "withheld"
        reasons.append("microphone acquisition outcome withheld")
    return _result(decision, reasons, rejected, preserved, questions)
