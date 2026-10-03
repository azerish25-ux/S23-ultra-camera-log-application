#!/usr/bin/env python3
"""P036 acquisition-only throughput probe.

Preallocated buffers and counters measure intervals, occupancy, copy time, and
sustained delivery for a bounded run. Acquisition-only frames are not retained.
That rate stays separate from saved-source throughput and encoded performance.

The deliberate mutant — publishing the best acquisition-only rate as the
recording capability — is rejected. This module does not probe a device, does
not qualify a physical S23, and does not execute TC-P036-01 through TC-P036-08.
"""

from __future__ import annotations

import math
import re
from typing import Any


PHASE = "P036"
CASE_ID = "P036"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-acquisition-throughput-fixture"
METHOD = (
    "Use preallocated buffers and counters to measure intervals, occupancy, copy time, "
    "and sustained delivery for a bounded run. State clearly when frames are not retained. "
    "Keep acquisition-only results separate from saved-source throughput and final encoded "
    "performance."
)
FIXTURE = (
    "A route delivering frames regularly when discarded but losing cadence when written "
    "to storage."
)
ORACLE = (
    "The report preserves the distinction and cannot claim the faster acquisition-only "
    "rate as reliable recorded RAW video."
)
MUTANT = "Publish the best acquisition-only rate as the recording capability."

STAGE_ORDER = ("acquisition_only", "saved_source", "encoded")
CADENCE = ("regular", "lost", "absent")
PUBLICATION = ("separated", "acquisition_as_recording")
MUTANT_PUBLICATION = "acquisition_as_recording"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
CANONICAL_UINT = re.compile(r"0|[1-9][0-9]*")
CANONICAL_POSITIVE = re.compile(r"[1-9][0-9]*")

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "routeId",
    "preallocatedBuffers",
    "boundFrameCount",
    "publication",
    "stages",
}
STAGE_KEYS = {
    "stage",
    "framesRetained",
    "cadence",
    "intervalsNs",
    "occupancy",
    "copyTimeNs",
    "deliveredCount",
}
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


def _text(value: object, label: str) -> str:
    require(isinstance(value, str) and bool(value) and value == value.strip(),
            label + " must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def _positive_int(value: object, label: str) -> int:
    require(type(value) is int and value > 0, label + " must be a positive int")
    return value


def _uint(value: object, label: str) -> str:
    require(isinstance(value, str) and CANONICAL_UINT.fullmatch(value) is not None,
            label + " must be a canonical non-negative integer string")
    return value


def _positive_uint(value: object, label: str) -> str:
    require(isinstance(value, str) and CANONICAL_POSITIVE.fullmatch(value) is not None,
            label + " must be a canonical positive integer string")
    return value


def sustained_rate(intervals_ns: list[str]) -> str:
    """Sustained deliveries per second as a reduced numerator/denominator.

    Each interval is one delivered frame period. An empty counter is absent,
    not a zero rate and not a recording capability.
    """
    if not intervals_ns:
        return "absent"
    total = sum(int(item) for item in intervals_ns)
    require(total > 0, "intervals must be positive")
    numerator = len(intervals_ns) * 1_000_000_000
    divisor = math.gcd(numerator, total)
    return f"{numerator // divisor}/{total // divisor}"


def measured_cadence(intervals_ns: list[str]) -> str:
    """Regular when every measured interval matches; lost when they differ."""
    if not intervals_ns:
        return "absent"
    if all(item == intervals_ns[0] for item in intervals_ns):
        return "regular"
    return "lost"


def _parse_rate(rate: str) -> tuple[int, int] | None:
    if rate == "absent":
        return None
    numerator, slash, denominator = rate.partition("/")
    require(slash == "/" and numerator.isdigit() and denominator.isdigit() and int(denominator) > 0,
            "rate must be a reduced fraction")
    return int(numerator), int(denominator)


def _faster(left: str, right: str) -> bool:
    parsed_left = _parse_rate(left)
    parsed_right = _parse_rate(right)
    if parsed_left is None:
        return False
    if parsed_right is None:
        return True
    left_num, left_den = parsed_left
    right_num, right_den = parsed_right
    return left_num * right_den > right_num * left_den


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision not in _FORBIDDEN, "P036 must not decide qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons),
            "reasons must be a non-empty list of strings")
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


def _counters(stage: dict, index: int, preallocated: int, bound: int) -> None:
    label = f"stage {index}"
    intervals = stage["intervalsNs"]
    occupancy = stage["occupancy"]
    copies = stage["copyTimeNs"]
    require(isinstance(intervals, list), label + " intervalsNs must be a list")
    require(isinstance(occupancy, list), label + " occupancy must be a list")
    require(isinstance(copies, list), label + " copyTimeNs must be a list")
    require(len(intervals) == len(occupancy) == len(copies),
            label + " counters must be the same length")
    for item in intervals:
        _positive_uint(item, label + " interval")
    for item in occupancy:
        text = _uint(item, label + " occupancy")
        require(int(text) <= preallocated, label + " occupancy exceeds preallocated buffers")
    for item in copies:
        _uint(item, label + " copy time")
    delivered = _uint(stage["deliveredCount"], label + " deliveredCount")
    require(delivered == str(len(intervals)), label + " deliveredCount must match intervals")
    require(int(delivered) <= bound, label + " deliveredCount exceeds the bounded run")
    cadence = _text(stage["cadence"], label + " cadence")
    require(cadence in CADENCE, label + " cadence is unknown")
    require(cadence == measured_cadence(intervals), label + " cadence does not match intervals")
    retained = _bool(stage["framesRetained"], label + " framesRetained")
    if not intervals:
        require(not retained, label + " cannot retain frames without deliveries")


def _stage(value: object, index: int, preallocated: int, bound: int) -> dict:
    item = exact_keys(value, STAGE_KEYS, f"stage {index}")
    name = _text(item["stage"], f"stage {index} stage")
    require(name == STAGE_ORDER[index], f"stage {index} must be {STAGE_ORDER[index]}")
    _counters(item, index, preallocated, bound)
    if name == "acquisition_only":
        require(item["intervalsNs"], "acquisition_only must measure at least one interval")
        require(item["framesRetained"] is False, "acquisition_only frames are not retained")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P036 throughput fixture shape."""
    exact_keys(document, DOCUMENT_KEYS, "throughput document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P036")
    require(document["mapId"] == MAP_ID, "mapId must be s23-acquisition-throughput-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "throughput document needs the P036 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    _text(document["routeId"], "routeId")
    preallocated = _positive_int(document["preallocatedBuffers"], "preallocatedBuffers")
    bound = _positive_int(document["boundFrameCount"], "boundFrameCount")
    publication = _text(document["publication"], "publication")
    require(publication in PUBLICATION, "publication must be separated or acquisition_as_recording")
    stages = document["stages"]
    require(isinstance(stages, list) and len(stages) == len(STAGE_ORDER),
            "stages must list acquisition_only, saved_source, and encoded")
    for index, stage in enumerate(stages):
        _stage(stage, index, preallocated, bound)


def stage_token(stage: dict) -> str:
    """Inventory token. Rates are computed; frames-not-retained stays visible."""
    rate = sustained_rate(stage["intervalsNs"])
    intervals = ",".join(stage["intervalsNs"]) if stage["intervalsNs"] else "-"
    occupancy = ",".join(stage["occupancy"]) if stage["occupancy"] else "-"
    copies = ",".join(stage["copyTimeNs"]) if stage["copyTimeNs"] else "-"
    retained = "true" if stage["framesRetained"] else "false"
    return (
        f"{stage['stage']}:retained={retained}:cadence={stage['cadence']}:rate={rate}:"
        f"delivered={stage['deliveredCount']}:intervals={intervals}:occupancy={occupancy}:"
        f"copy={copies}"
    )


def recording_rate(document: dict) -> str:
    """Recording capability is never the acquisition-only rate.

    A separated report may name saved-source throughput only when that stage
    retained frames on a regular cadence. The mutant publication still returns
    withheld rather than the faster discard rate.
    """
    validate_document(document)
    if document["publication"] == MUTANT_PUBLICATION:
        return "withheld"
    saved = document["stages"][1]
    rate = sustained_rate(saved["intervalsNs"])
    if saved["framesRetained"] and saved["cadence"] == "regular" and rate != "absent":
        return "saved_source:" + rate
    return "withheld"


def assess(document: dict) -> dict:
    """Keep stage counters distinct and refuse the acquisition-as-recording mutant.

    Preserved results include every stage token and a recording-capability token
    that is withheld or names saved-source only. Decision is never qualified
    or allowed. Faster discard delivery is not reliable recorded RAW video.
    """
    validate_document(document)
    stages = document["stages"]
    rates = [sustained_rate(stage["intervalsNs"]) for stage in stages]
    acquisition, saved, encoded = stages
    acq_rate, saved_rate, encoded_rate = rates
    capability = recording_rate(document)
    preserved = [f"route:{document['routeId']}"]
    preserved.extend(stage_token(stage) for stage in stages)
    preserved.append("recordingCapability:" + capability)

    rejected: list[str] = []
    if document["publication"] == MUTANT_PUBLICATION:
        rejected.append("acquisition-as-recording")
    if _faster(acq_rate, saved_rate):
        rejected.append("acquisition-rate-as-recorded-raw")

    saved_ok = saved["framesRetained"] and saved["cadence"] == "regular" and saved_rate != "absent"
    if document["publication"] == MUTANT_PUBLICATION:
        decision = "rejected"
    elif saved_ok and acquisition["framesRetained"] is False:
        decision = "stage_separated"
    else:
        decision = "withheld"

    questions = ["acquisition_only frames are not retained"]
    if saved["cadence"] == "lost":
        questions.append("saved_source cadence lost when written to storage")
    if encoded_rate == "absent":
        questions.append("encoded performance absent")
    questions.append("not a physical S23 qualification")

    reasons = [
        ORACLE,
        (
            f"preallocated buffers {document['preallocatedBuffers']}; "
            f"bound {document['boundFrameCount']}"
        ),
        "acquisition_only frames are not retained",
        f"acquisition_only sustained {acq_rate}; cadence {acquisition['cadence']}",
        f"saved_source sustained {saved_rate}; cadence {saved['cadence']}",
        f"encoded sustained {encoded_rate}",
        "stage rates stay separate from recording capability",
    ]
    if "acquisition-as-recording" in rejected:
        reasons.append(MUTANT)
        reasons.append("refusing to publish the acquisition-only rate as recording capability")
    if decision == "stage_separated":
        reasons.append("saved-source throughput is not the acquisition-only rate")
        reasons.append("stage_separated is not physical qualification or recorded-RAW certification")
    if decision == "withheld":
        reasons.append("the faster acquisition-only rate is not recording capability")
    require(
        capability == "withheld"
        or (capability.startswith("saved_source:") and capability.split(":", 1)[1] == saved_rate),
        "recording capability must not be the acquisition-only rate",
    )
    return _result(decision, reasons, rejected, preserved, questions)
