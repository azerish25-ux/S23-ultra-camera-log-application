#!/usr/bin/env python3
"""P026 host gate for video encoder startup.

Format changes, codec-config buffers, keyframe requests, and startup timeouts
are separate events. Bit depth is read from the emitted SPS, not from the
MediaFormat that configure accepted. A Main10 request that yields an eight-bit
SPS fails the ten-bit route and is not relabelled as acceptable Log.

The deliberate mutant — validating codec depth from the requested MediaFormat
rather than the emitted stream — is rejected. This module does not probe a
device, does not qualify a physical S23, and does not execute TC-P026-01
through TC-P026-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE_ID = "P026"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
CONTRACT_ID = "s23-encoder-startup-fixture"
METHOD = (
    "Handle format changes, codec-config buffers, keyframe requests, and startup "
    "timeouts separately. Inspect the actual output profile and bit depth. Retain "
    "diagnostic reasons for an advertised codec that fails configuration or produces "
    "the wrong signal."
)
FIXTURE = "A Main10 request that yields an eight-bit SPS after a successful configure call."
ORACLE = (
    "The output fails the ten-bit route gate and is not silently relabelled as acceptable Log."
)
MUTANT = "Validate codec depth from the requested MediaFormat rather than the emitted stream."
EMITTED_STREAM = "emitted-stream"
REQUESTED_MEDIAFORMAT = "requested-mediaformat"
DEPTH_SOURCES = (EMITTED_STREAM, REQUESTED_MEDIAFORMAT)
HOST_LIMIT = "host fixture does not qualify a physical S23"
TEN_BIT_CLAIM = "ten-bit-route-failed"
LOG_CLAIM = "silent-acceptable-log"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
PROFILES = ("Main", "Main10")
DEPTHS = (8, 10)
TRANSFERS = ("unspecified", "bt709", "hlg", "pq")
RANGES = ("limited", "full")
EVENT_ORDER = (
    "format_change",
    "codec_config",
    "keyframe_request",
    "startup_timeout",
    "output_sample",
)
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "contractId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "request",
    "configure",
    "events",
    "emitted",
    "advertisedCodec",
    "inventory",
}
REQUEST_KEYS = {
    "codec",
    "profile",
    "bitDepth",
    "width",
    "height",
    "transfer",
    "colorRange",
    "logLabel",
}
CONFIGURE_KEYS = {"succeeded", "mediaFormatBitDepth", "mediaFormatProfile"}
EMITTED_KEYS = {
    "profile",
    "bitDepth",
    "spsBitDepth",
    "width",
    "height",
    "transfer",
    "colorRange",
    "relabelledAsAcceptableLog",
}
CODEC_KEYS = {"name", "configFailureReason"}
FORMAT_KEYS = {"kind", "id", "width", "height", "handledSeparately"}
CONFIG_BUFFER_KEYS = {"kind", "id", "bufferRole", "spsBitDepth", "handledSeparately"}
KEYFRAME_KEYS = {"kind", "id", "requested", "handledSeparately"}
TIMEOUT_KEYS = {"kind", "id", "fired", "boundMs", "elapsedMs", "handledSeparately"}
SAMPLE_KEYS = {"kind", "id", "usable", "handledSeparately"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def _text(value: object, context: str) -> str:
    require(isinstance(value, str) and bool(value) and value == value.strip(),
            context + " must be a non-empty string")
    return value


def _bool(value: object, context: str) -> bool:
    require(type(value) is bool, context + " must be a bool")
    return value


def _depth(value: object, context: str) -> int:
    require(type(value) is int and value in DEPTHS, context + " must be 8 or 10")
    return value


def _profile(value: object, context: str) -> str:
    text = _text(value, context)
    require(text in PROFILES, context + " must be Main or Main10")
    return text


def _size(value: object, context: str) -> int:
    require(type(value) is int and value > 0, context + " must be a positive int")
    return value


def _choice(value: object, allowed: tuple[str, ...], context: str) -> str:
    text = _text(value, context)
    require(text in allowed, context + " is not in the fixture vocabulary")
    return text


def _event_map(document: dict) -> dict[str, dict]:
    return {event["kind"]: event for event in document["events"]}


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision not in _FORBIDDEN, "P026 must not decide qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons),
            "reasons must be a non-empty list of strings")
    result = {
        "caseId": PHASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def _parse_event(value: object, index: int, seen: set[str]) -> dict:
    require(isinstance(value, dict) and value.get("kind") in EVENT_ORDER,
            f"event {index} kind must be one of the startup events")
    kind = value["kind"]
    if kind == "format_change":
        item = exact_keys(value, FORMAT_KEYS, f"event {index}")
        _size(item["width"], f"event {index} width")
        _size(item["height"], f"event {index} height")
    elif kind == "codec_config":
        item = exact_keys(value, CONFIG_BUFFER_KEYS, f"event {index}")
        require(item["bufferRole"] == "codec-config", f"event {index} bufferRole must be codec-config")
        _depth(item["spsBitDepth"], f"event {index} spsBitDepth")
    elif kind == "keyframe_request":
        item = exact_keys(value, KEYFRAME_KEYS, f"event {index}")
        _bool(item["requested"], f"event {index} requested")
    elif kind == "startup_timeout":
        item = exact_keys(value, TIMEOUT_KEYS, f"event {index}")
        _bool(item["fired"], f"event {index} fired")
        require(type(item["boundMs"]) is int and item["boundMs"] > 0,
                f"event {index} boundMs must be a positive int")
        require(type(item["elapsedMs"]) is int and item["elapsedMs"] >= 0,
                f"event {index} elapsedMs must be a non-negative int")
    else:
        item = exact_keys(value, SAMPLE_KEYS, f"event {index}")
        _bool(item["usable"], f"event {index} usable")
    ident = _text(item["id"], f"event {index} id")
    require(ident not in seen, "duplicate event id: " + ident)
    seen.add(ident)
    _bool(item["handledSeparately"], f"event {index} handledSeparately")
    return item


def validate_fixture(document: dict) -> None:
    """Raise ValueError unless document is the P026 encoder-startup fixture."""
    exact_keys(document, DOCUMENT_KEYS, "encoder startup")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE_ID, "phase must be P026")
    require(document["contractId"] == CONTRACT_ID, "contractId must be s23-encoder-startup-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "encoder startup needs the P026 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")

    request = exact_keys(document["request"], REQUEST_KEYS, "request")
    _text(request["codec"], "request codec")
    _profile(request["profile"], "request profile")
    _depth(request["bitDepth"], "request bitDepth")
    _size(request["width"], "request width")
    _size(request["height"], "request height")
    _choice(request["transfer"], TRANSFERS, "request transfer")
    _choice(request["colorRange"], RANGES, "request colorRange")
    require(request["logLabel"] == "none", "request logLabel must be none")
    if request["profile"] == "Main10":
        require(request["bitDepth"] == 10, "Main10 request must ask for ten-bit depth")
    if request["profile"] == "Main":
        require(request["bitDepth"] == 8, "Main request must ask for eight-bit depth")

    configure = exact_keys(document["configure"], CONFIGURE_KEYS, "configure")
    _bool(configure["succeeded"], "configure succeeded")
    _depth(configure["mediaFormatBitDepth"], "configure mediaFormatBitDepth")
    _profile(configure["mediaFormatProfile"], "configure mediaFormatProfile")

    events = document["events"]
    require(isinstance(events, list) and len(events) == len(EVENT_ORDER),
            "events must list each startup event once")
    seen: set[str] = set()
    parsed = [_parse_event(item, index, seen) for index, item in enumerate(events)]
    kinds = [item["kind"] for item in parsed]
    require(sorted(kinds) == sorted(EVENT_ORDER), "events must cover format, config, keyframe, timeout, and sample")

    emitted = exact_keys(document["emitted"], EMITTED_KEYS, "emitted")
    _profile(emitted["profile"], "emitted profile")
    _depth(emitted["bitDepth"], "emitted bitDepth")
    _depth(emitted["spsBitDepth"], "emitted spsBitDepth")
    require(emitted["bitDepth"] == emitted["spsBitDepth"],
            "emitted bitDepth must match the emitted SPS")
    _size(emitted["width"], "emitted width")
    _size(emitted["height"], "emitted height")
    _choice(emitted["transfer"], TRANSFERS, "emitted transfer")
    _choice(emitted["colorRange"], RANGES, "emitted colorRange")
    _bool(emitted["relabelledAsAcceptableLog"], "emitted relabelledAsAcceptableLog")

    codec = exact_keys(document["advertisedCodec"], CODEC_KEYS, "advertisedCodec")
    _text(codec["name"], "advertisedCodec name")
    reason = codec["configFailureReason"]
    require(reason is None or (isinstance(reason, str) and bool(reason) and reason == reason.strip()),
            "configFailureReason must be a non-empty string or null")
    if reason is None:
        require(configure["succeeded"] is True, "a null config failure requires configure success")
    else:
        require(configure["succeeded"] is False, "a config failure cannot claim configure succeeded")

    mapped = {item["kind"]: item for item in parsed}
    require(mapped["format_change"]["width"] == emitted["width"]
            and mapped["format_change"]["height"] == emitted["height"],
            "format_change size must match the emitted stream")
    require(mapped["codec_config"]["spsBitDepth"] == emitted["spsBitDepth"],
            "codec-config SPS depth must match the emitted stream")

    inventory = document["inventory"]
    require(isinstance(inventory, list) and inventory, "inventory must be a non-empty list")
    require(all(isinstance(item, str) and item and item == item.strip() for item in inventory),
            "inventory items must be non-empty strings")
    require(len(inventory) == len(set(inventory)), "inventory items must be unique")


def bit_depth(document: dict, source: str) -> int:
    """Return a bit depth from one named source.

    assess_startup calls this with emitted-stream only. requested-mediaformat is
    the mutant: it reports the MediaFormat depth even when the SPS is eight-bit.
    """
    validate_fixture(document)
    require(source in DEPTH_SOURCES, "unknown bit-depth source")
    if source == EMITTED_STREAM:
        return document["emitted"]["spsBitDepth"]
    return document["configure"]["mediaFormatBitDepth"]


def _preconditions(document: dict) -> bool:
    mapped = _event_map(document)
    if document["advertisedCodec"]["configFailureReason"] is not None:
        return False
    if document["configure"]["succeeded"] is not True:
        return False
    if mapped["startup_timeout"]["fired"] is True:
        return False
    if mapped["keyframe_request"]["requested"] is not True:
        return False
    if mapped["output_sample"]["usable"] is not True:
        return False
    if any(event["handledSeparately"] is not True for event in document["events"]):
        return False
    return True


def ten_bit_route_ok(document: dict, source: str) -> bool:
    """True only when that depth source supports a Main10 ten-bit route.

    The requested-mediaformat source false-passes the fixture. The emitted-stream
    source does not. Callers that decide startup must use emitted-stream.
    """
    validate_fixture(document)
    require(source in DEPTH_SOURCES, "unknown bit-depth source")
    request = document["request"]
    emitted = document["emitted"]
    shape = (
        request["bitDepth"] == 10
        and request["profile"] == "Main10"
        and emitted["profile"] == request["profile"]
        and emitted["width"] == request["width"]
        and emitted["height"] == request["height"]
        and emitted["transfer"] == request["transfer"]
        and emitted["colorRange"] == request["colorRange"]
        and emitted["relabelledAsAcceptableLog"] is False
        and _preconditions(document)
    )
    if not shape:
        return False
    if source == REQUESTED_MEDIAFORMAT:
        configure = document["configure"]
        return configure["mediaFormatBitDepth"] == 10 and configure["mediaFormatProfile"] == "Main10"
    return emitted["spsBitDepth"] == 10 and emitted["bitDepth"] == 10


def _signal_matches_emitted(document: dict) -> bool:
    request = document["request"]
    emitted = document["emitted"]
    return (
        emitted["spsBitDepth"] == request["bitDepth"]
        and emitted["bitDepth"] == request["bitDepth"]
        and emitted["profile"] == request["profile"]
        and emitted["width"] == request["width"]
        and emitted["height"] == request["height"]
        and emitted["transfer"] == request["transfer"]
        and emitted["colorRange"] == request["colorRange"]
        and emitted["relabelledAsAcceptableLog"] is False
    )


def _preserved(document: dict) -> list[str]:
    preserved = list(document["inventory"])
    name = document["advertisedCodec"]["name"]
    if name not in preserved:
        preserved.append(name)
    token = "sps-bit-depth:" + str(document["emitted"]["spsBitDepth"])
    if token not in preserved:
        preserved.append(token)
    return preserved


def assess_startup(document: dict) -> dict:
    """Judge encoder startup from the emitted stream.

    decision is startup_ready only when the emitted SPS, profile, size, transfer,
    and color range match the request and the four startup events were handled
    separately. decision is rejected when the ten-bit route fails, the output
    was relabelled as acceptable Log, configure failed, or an event was folded
    together. The requested MediaFormat depth is never the gate. preservedResults
    keep the inventory either way. decision is never qualified or allowed.
    """
    validate_fixture(document)
    request = document["request"]
    emitted = document["emitted"]
    codec = document["advertisedCodec"]
    mapped = _event_map(document)
    rejected: list[str] = []
    reasons: list[str] = [
        "format changes, codec-config buffers, keyframe requests, and startup timeouts are separate events",
    ]

    observed = bit_depth(document, EMITTED_STREAM)
    require(observed == emitted["spsBitDepth"], "startup depth must be the emitted SPS")
    mutant_would_pass = ten_bit_route_ok(document, REQUESTED_MEDIAFORMAT)
    honest_ten_bit = ten_bit_route_ok(document, EMITTED_STREAM)
    if mutant_would_pass and not honest_ten_bit:
        rejected.append(TEN_BIT_CLAIM)
        reasons.append(
            "emitted SPS bit depth "
            + str(observed)
            + " disagrees with requested MediaFormat bit depth "
            + str(document["configure"]["mediaFormatBitDepth"])
        )
        reasons.append(ORACLE)
        reasons.append(MUTANT + " was not applied")
    elif request["bitDepth"] == 10 and observed != 10:
        rejected.append(TEN_BIT_CLAIM)
        reasons.append(ORACLE)

    if emitted["relabelledAsAcceptableLog"] is True:
        rejected.append(LOG_CLAIM)
        reasons.append("output must not be silently relabelled as acceptable Log")
    if emitted["profile"] != request["profile"]:
        rejected.append("output-profile")
        reasons.append("emitted profile " + emitted["profile"] + " contradicts the request")
    if (emitted["width"], emitted["height"]) != (request["width"], request["height"]):
        rejected.append("output-dimensions")
        reasons.append("emitted dimensions contradict the request")
    if emitted["transfer"] != request["transfer"]:
        rejected.append("output-transfer")
        reasons.append("emitted transfer tag contradicts the request")
    if emitted["colorRange"] != request["colorRange"]:
        rejected.append("output-color-range")
        reasons.append("emitted color range contradicts the request")

    if codec["configFailureReason"] is not None:
        rejected.append("advertised-codec-config-failed")
        reasons.append(codec["name"] + " failed configuration: " + codec["configFailureReason"])
    elif not _signal_matches_emitted(document):
        reasons.append(codec["name"] + " produced the wrong signal")

    for kind in EVENT_ORDER:
        if mapped[kind]["handledSeparately"] is not True:
            rejected.append(kind + "-not-separate")
            reasons.append(kind + " must be handled separately")
    if mapped["startup_timeout"]["fired"] is True:
        rejected.append("startup-timeout")
        reasons.append(
            "startup timeout fired at "
            + str(mapped["startup_timeout"]["elapsedMs"])
            + "ms within bound "
            + str(mapped["startup_timeout"]["boundMs"])
            + "ms"
        )
    if mapped["keyframe_request"]["requested"] is not True:
        rejected.append("keyframe-not-requested")
        reasons.append("keyframe request was not issued")

    questions = [
        HOST_LIMIT,
        "ten-bit fidelity is not established by a Main10 request",
        "sensor-derived Log is not claimed",
    ]
    preserved = _preserved(document)
    usable = mapped["output_sample"]["usable"] is True
    if rejected:
        decision = "rejected"
    elif not usable:
        decision = "withheld"
        reasons.append("no usable output sample was emitted")
        questions.append("startup remains withheld without a usable sample")
    elif _signal_matches_emitted(document) and _preconditions(document):
        decision = "startup_ready"
        reasons.append("emitted stream matches the requested signal contract")
        reasons.append("startup_ready is a host-fixture label, not physical qualification")
        if request["bitDepth"] != 10:
            reasons.append("an eight-bit match is not a ten-bit route")
    else:
        decision = "withheld"
        reasons.append("startup signal is not ready")

    require(decision != "startup_ready" or observed == request["bitDepth"],
            "startup_ready cannot ignore the emitted SPS")
    require(not (decision == "startup_ready" and mutant_would_pass and not honest_ten_bit),
            "the MediaFormat mutant must not pass the ten-bit route")
    return _result(decision, reasons, rejected, preserved, questions)
