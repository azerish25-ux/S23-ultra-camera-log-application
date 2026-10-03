#!/usr/bin/env python3
"""P040 saved-RAW duration boundaries on a host fixture.

Successively longer experiments are recorded only after acquisition and writer
gates pass. The fixture is a five-second successful RAW sequence and a
sixty-second run that stops under severe thermal pressure. The assessor
reports those measured duration boundaries and keeps the longer partial take.
It does not extrapolate endurance, and it does not treat a five-frame still
sequence as sustained RAW video.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P040-01 through TC-P040-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P040"
CASE_ID = "P040"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-saved-raw-qualification-fixture"
METHOD = (
    "Run successively longer conservative experiments only after acquisition and writer "
    "gates pass. Measure sample integrity, source completeness, metadata availability, "
    "storage bandwidth, thermal state, and lens behaviour. Keep maximum-resolution "
    "experiments conditional on lower-cost results."
)
FIXTURE = (
    "A five-second successful RAW sequence followed by a sixty-second run that stops "
    "under severe thermal pressure."
)
ORACLE = (
    "The app reports the measured duration boundaries and retains the longer partial "
    "take rather than extrapolating endurance."
)
MUTANT = "Treat a five-frame still sequence as proof of sustained RAW video."
HOST_LIMIT = "a host fixture does not qualify a physical S23"
MEASURED = "measured_boundaries"
MUTANT_BASIS = "five_frame_still"
BASES = (MEASURED, MUTANT_BASIS)
SHORT_REQUESTED_MS = "5000"
LONG_REQUESTED_MS = "60000"
STILL_FRAMES = "5"

HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
UINT = re.compile(r"0|[1-9][0-9]*")
POSITIVE = re.compile(r"[1-9][0-9]*")
STOPS = ("requested_bound", "severe_thermal")
INTEGRITY = ("intact", "corrupt", "unmeasured")
BANDWIDTH = ("sufficient", "constrained", "unmeasured")
THERMAL = ("nominal", "warm", "severe")
LENS = ("stable", "drifting", "unmeasured")

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "gates",
    "shortTake",
    "longTake",
    "maximumResolution",
    "stillSequence",
}
GATE_KEYS = {"acquisitionPassed", "writerPassed"}
TAKE_KEYS = {
    "id",
    "kind",
    "requestedDurationMs",
    "measuredDurationMs",
    "frameCount",
    "complete",
    "stoppedReason",
    "sampleIntegrity",
    "sourceComplete",
    "metadataAvailable",
    "storageBandwidth",
    "thermalState",
    "lensBehaviour",
    "retained",
}
MAX_KEYS = {"attempted", "conditionalOnLowerCost"}
STILL_KEYS = {"frameCount", "kind"}
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


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def _token(value: object, label: str) -> str:
    require(isinstance(value, str) and TOKEN.fullmatch(value) is not None, label + " must be a token")
    return value


def _uint(value: object, label: str) -> str:
    require(isinstance(value, str) and UINT.fullmatch(value) is not None,
            label + " must be a canonical non-negative integer string")
    return value


def _positive(value: object, label: str) -> str:
    require(isinstance(value, str) and POSITIVE.fullmatch(value) is not None,
            label + " must be a canonical positive integer string")
    return value


def _choice(value: object, options: tuple[str, ...], label: str) -> str:
    require(isinstance(value, str) and value in options, label + " is not a known value")
    return value


def _flag(value: bool) -> str:
    return "true" if value else "false"


def _gates(value: object) -> dict:
    item = exact_keys(value, GATE_KEYS, "gates")
    _bool(item["acquisitionPassed"], "acquisitionPassed")
    _bool(item["writerPassed"], "writerPassed")
    return item


def _take(value: object, role: str, requested: str) -> dict:
    item = exact_keys(value, TAKE_KEYS, role)
    _token(item["id"], role + " id")
    require(item["kind"] == "raw_sequence", role + " kind must be raw_sequence")
    require(_positive(item["requestedDurationMs"], role + " requestedDurationMs") == requested,
            role + " requested duration must be " + requested)
    measured = _uint(item["measuredDurationMs"], role + " measuredDurationMs")
    require(int(measured) <= int(requested), role + " measured duration exceeds the request")
    frames = item["frameCount"]
    if int(measured) == 0:
        require(frames == "0", role + " frameCount must be 0 when nothing was measured")
    else:
        _positive(frames, role + " frameCount")
    complete = _bool(item["complete"], role + " complete")
    stop = _choice(item["stoppedReason"], STOPS, role + " stoppedReason")
    integrity = _choice(item["sampleIntegrity"], INTEGRITY, role + " sampleIntegrity")
    source_complete = _bool(item["sourceComplete"], role + " sourceComplete")
    _bool(item["metadataAvailable"], role + " metadataAvailable")
    _choice(item["storageBandwidth"], BANDWIDTH, role + " storageBandwidth")
    thermal = _choice(item["thermalState"], THERMAL, role + " thermalState")
    _choice(item["lensBehaviour"], LENS, role + " lensBehaviour")
    _bool(item["retained"], role + " retained")
    if complete:
        require(measured == requested, role + " complete take must meet its requested duration")
        require(stop == "requested_bound", role + " complete take stops at the requested bound")
        require(source_complete is True, role + " complete take must have a complete source")
        require(thermal != "severe", role + " complete take cannot be in severe thermal state")
    else:
        require(source_complete is False, role + " partial take must not claim a complete source")
        require(int(measured) < int(requested), role + " partial take must stop before the request")
    if stop == "severe_thermal":
        require(complete is False, role + " severe thermal stop is not a completed request")
        require(thermal == "severe", role + " severe thermal stop requires thermalState severe")
    if stop == "requested_bound" and complete:
        require(measured == requested, role + " requested bound must match the measured duration")
    return item


def _maximum(value: object) -> dict:
    item = exact_keys(value, MAX_KEYS, "maximumResolution")
    _bool(item["attempted"], "maximumResolution attempted")
    conditional = _bool(item["conditionalOnLowerCost"], "conditionalOnLowerCost")
    require(conditional is True, "maximum-resolution experiments stay conditional on lower-cost results")
    return item


def _still(value: object) -> dict:
    item = exact_keys(value, STILL_KEYS, "stillSequence")
    require(item["kind"] == "still_sequence", "stillSequence kind must be still_sequence")
    require(_positive(item["frameCount"], "stillSequence frameCount") == STILL_FRAMES,
            "stillSequence is the five-frame still, not a video duration")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P040 saved-RAW fixture shape."""
    exact_keys(document, DOCUMENT_KEYS, "qualification document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P040")
    require(document["mapId"] == MAP_ID, "mapId must be s23-saved-raw-qualification-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "qualification document needs the P040 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    _gates(document["gates"])
    short = _take(document["shortTake"], "shortTake", SHORT_REQUESTED_MS)
    long = _take(document["longTake"], "longTake", LONG_REQUESTED_MS)
    require(short["id"] != long["id"], "short and long takes must have distinct ids")
    _maximum(document["maximumResolution"])
    _still(document["stillSequence"])


def take_token(take: dict) -> str:
    """Inventory token for one take. Measured duration is not the request."""
    return (
        f"take:{take['id']}:kind={take['kind']}:requested={take['requestedDurationMs']}:"
        f"measured={take['measuredDurationMs']}:frames={take['frameCount']}:"
        f"complete={_flag(take['complete'])}:stop={take['stoppedReason']}:"
        f"integrity={take['sampleIntegrity']}:source={_flag(take['sourceComplete'])}:"
        f"metadata={_flag(take['metadataAvailable'])}:bandwidth={take['storageBandwidth']}:"
        f"thermal={take['thermalState']}:lens={take['lensBehaviour']}:"
        f"retained={_flag(take['retained'])}"
    )


def still_token(still: dict) -> str:
    """Five still frames stay a still sequence. They are not sustained RAW video."""
    return f"still:frames={still['frameCount']}:kind={still['kind']}"


def _longer_token(short: dict, long: dict) -> str:
    longer_partial = (
        not long["complete"]
        and int(long["measuredDurationMs"]) > int(short["measuredDurationMs"])
        and long["retained"] is True
    )
    if longer_partial:
        return f"retained-longer:{long['id']}:measured={long['measuredDurationMs']}"
    return "retained-longer:absent"


def _preserved(document: dict) -> list[str]:
    gates = document["gates"]
    short = document["shortTake"]
    long = document["longTake"]
    maximum = document["maximumResolution"]
    return [
        f"gates:acquisition={_flag(gates['acquisitionPassed'])}:writer={_flag(gates['writerPassed'])}",
        take_token(short),
        take_token(long),
        still_token(document["stillSequence"]),
        (
            "maximum-resolution:attempted="
            + _flag(maximum["attempted"])
            + ":conditional="
            + _flag(maximum["conditionalOnLowerCost"])
        ),
        _longer_token(short, long),
    ]


def _measured(take: dict) -> bool:
    return (
        take["sampleIntegrity"] == "intact"
        and take["metadataAvailable"] is True
        and take["storageBandwidth"] != "unmeasured"
        and take["lensBehaviour"] != "unmeasured"
        and take["thermalState"] != "unmeasured"
    )


def _story(document: dict) -> bool:
    short = document["shortTake"]
    long = document["longTake"]
    maximum = document["maximumResolution"]
    return (
        short["complete"] is True
        and short["measuredDurationMs"] == SHORT_REQUESTED_MS
        and short["retained"] is True
        and short["thermalState"] != "severe"
        and _measured(short)
        and long["complete"] is False
        and long["stoppedReason"] == "severe_thermal"
        and int(long["measuredDurationMs"]) > int(short["measuredDurationMs"])
        and long["retained"] is True
        and long["thermalState"] == "severe"
        and _measured(long)
        and maximum["attempted"] is False
    )


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision not in _FORBIDDEN, "P040 must not decide qualified or allowed")
    require(decision != "sustained_raw", "five still frames are not sustained RAW video")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons),
            "reasons must be a non-empty list of strings")
    require(all(isinstance(item, str) for item in rejected), "rejectedClaims must be strings")
    require(bool(preserved) and all(isinstance(item, str) and item for item in preserved),
            "preservedResults must keep the inventory")
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


def assess(document: dict, basis: str = MEASURED) -> dict:
    """Report measured duration boundaries. Reject the five-frame still mutant.

    basis "five_frame_still" is the mutant. It is rejected even when the
    five-second sequence succeeded. The sixty-second partial take stays in
    preservedResults. Decision is never qualified or allowed.
    """
    validate_document(document)
    require(basis in BASES, "basis must be measured_boundaries or five_frame_still")
    short = document["shortTake"]
    long = document["longTake"]
    gates = document["gates"]
    maximum = document["maximumResolution"]
    preserved = _preserved(document)
    require(not any("sustained-raw-video" in item for item in preserved),
            "still frames must not be labeled sustained RAW video")
    require("measured=" + long["requestedDurationMs"] not in take_token(long)
            or long["measuredDurationMs"] == long["requestedDurationMs"],
            "unmeasured endurance must not be written as the long take duration")

    rejected: list[str] = []
    questions = [
        "host fixture is not a physical S23 measurement",
        "a five-frame still sequence is not sustained RAW video",
        "maximum-resolution experiments remain conditional",
    ]
    reasons = [
        ORACLE,
        (
            f"measured boundary {short['id']} {short['measuredDurationMs']}ms "
            f"of {short['requestedDurationMs']}ms"
        ),
        (
            f"measured boundary {long['id']} {long['measuredDurationMs']}ms "
            f"of {long['requestedDurationMs']}ms"
        ),
        (
            f"sample integrity short {short['sampleIntegrity']} long {long['sampleIntegrity']}; "
            f"source short {_flag(short['sourceComplete'])} long {_flag(long['sourceComplete'])}; "
            f"metadata short {_flag(short['metadataAvailable'])} long {_flag(long['metadataAvailable'])}; "
            f"bandwidth short {short['storageBandwidth']} long {long['storageBandwidth']}; "
            f"thermal short {short['thermalState']} long {long['thermalState']}; "
            f"lens short {short['lensBehaviour']} long {long['lensBehaviour']}"
        ),
    ]
    if int(long["measuredDurationMs"]) < int(long["requestedDurationMs"]):
        rejected.append("endurance-extrapolation")
        reasons.append(
            "endurance was not extrapolated to " + long["requestedDurationMs"] + "ms"
        )
    else:
        reasons.append("a completed requested bound is not an endurance extrapolation")

    gates_ok = gates["acquisitionPassed"] is True and gates["writerPassed"] is True
    if not gates_ok:
        questions.append("acquisition and writer gates have not both passed")
    if maximum["attempted"] is True:
        rejected.append("maximum-resolution-before-lower-cost")
        reasons.append("maximum-resolution was attempted before lower-cost results allowed it")
    if long["complete"] is False and long["retained"] is not True:
        rejected.append("discarded-partial-take")
        reasons.append("the longer partial take was not retained")
    elif _longer_token(short, long) != "retained-longer:absent":
        reasons.append(
            f"longer partial take {long['id']} retained at measured "
            f"{long['measuredDurationMs']}ms"
        )
    if short["sampleIntegrity"] != "intact" or long["sampleIntegrity"] != "intact":
        rejected.append("sample-integrity")
        questions.append("sample integrity is not intact")
    if short["metadataAvailable"] is False or long["metadataAvailable"] is False:
        questions.append("metadata unavailable")
    if short["storageBandwidth"] == "unmeasured" or long["storageBandwidth"] == "unmeasured":
        questions.append("storage bandwidth unmeasured")
    if short["lensBehaviour"] == "unmeasured" or long["lensBehaviour"] == "unmeasured":
        questions.append("lens behaviour unmeasured")
    if long["stoppedReason"] == "severe_thermal":
        questions.append("severe thermal stop is a measured bound, not an endurance certificate")

    story = _story(document) and gates_ok
    if basis == MUTANT_BASIS:
        decision = "rejected"
        rejected.insert(0, "five-frame-still-as-sustained-raw-video")
        reasons.append(MUTANT)
        reasons.append("five still frames are not a sustained RAW video duration boundary")
        questions.append("five-frame still was not accepted as sustained RAW video")
    elif not gates_ok:
        decision = "withheld"
        reasons.append("longer experiments require acquisition and writer gates")
    elif "maximum-resolution-before-lower-cost" in rejected or "discarded-partial-take" in rejected:
        decision = "rejected"
        reasons.append("duration boundaries were not accepted")
    elif story:
        decision = "boundaries_reported"
        reasons.append("boundaries_reported is not physical S23 qualification")
        reasons.append("maximum-resolution stays conditional on the lower-cost thermal stop")
    else:
        decision = "withheld"
        reasons.append("measured records do not form the five-second then thermal-stop boundary")
        reasons.append("withheld is not a sustained RAW video certificate")

    reasons.append(HOST_LIMIT)
    require(decision != "boundaries_reported" or basis != MUTANT_BASIS,
            "the five-frame mutant must not report duration boundaries")
    require("five-frame-still-as-sustained-raw-video" not in rejected or decision == "rejected",
            "mutant claim cannot pass")
    return _result(decision, reasons, rejected, preserved, questions)
