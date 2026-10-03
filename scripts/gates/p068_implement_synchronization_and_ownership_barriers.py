#!/usr/bin/env python3
"""P068 synchronization and ownership barriers.

Each resource is tied to a frame identity and a lifetime. Reuse and release
wait for a fence. In-flight work stays inside a bound. Correctness
synchronization is not a performance measurement.

The fixture is a slow GPU frame, then rapid cancellation and reuse of the
same texture pool slot. The next frame must not observe a partial write or
the previous generation, and cancellation releases only completed ownership.

The deliberate mutant — recycle a texture immediately after command
submission — is rejected. Immediate recycle does not make an incomplete
slot readable. This module does not probe a device, does not qualify a
physical S23, and does not execute TC-P068-01 through TC-P068-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P068"
CASE_ID = "P068"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-synchronization-ownership-fixture"
METHOD = (
    "Associate each resource with a frame identity and lifetime. Use "
    "backend-appropriate fences and barriers, bound in-flight work, and "
    "verify completion before reuse or release. Separate correctness "
    "synchronization from performance measurements."
)
FIXTURE = (
    "A slow GPU frame followed by rapid cancellation and reuse of the same "
    "texture pool slot."
)
ORACLE = (
    "The next frame cannot read partially written or previous-generation "
    "data and cancellation releases only completed ownership."
)
MUTANT = "Recycle a texture immediately after command submission."
DECLARED_PATH = "fenced"
MUTANT_PATH = "immediate-recycle"
PATHS = (DECLARED_PATH, MUTANT_PATH)
HOST_LIMIT = "host fixture does not qualify a physical S23 or a measured GPU fence"
KINDS = ("texture", "buffer")
LIFETIMES = ("in-flight", "completed", "released")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[a-z0-9-]+$")
COUNT = re.compile(r"[1-9][0-9]*")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "synchronization",
    "pool",
    "frames",
}
SYNC_KEYS = {"correctnessSeparated", "performanceMeasured", "inFlightBound"}
POOL_KEYS = {"slotId", "kind"}
FRAME_KEYS = {
    "frameId",
    "generation",
    "lifetime",
    "submitted",
    "fenceComplete",
    "cancelled",
    "partialWrite",
    "payload",
    "readsSlot",
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
_DECISIONS = {"rejected", "withheld", "ownership_held", "completion_verified"}


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


def _token(value: object, label: str) -> str:
    require(isinstance(value, str) and TOKEN.fullmatch(value) is not None, label + " must be a token")
    return value


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def _count(value: object, label: str) -> str:
    require(isinstance(value, str) and COUNT.fullmatch(value) is not None, label + " must be a canonical positive integer")
    return value


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is a P068 ownership fixture."""
    exact_keys(document, DOCUMENT_KEYS, "ownership fixture")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P068")
    require(document["mapId"] == MAP_ID, "mapId must be s23-synchronization-ownership-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "ownership fixture needs the P068 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    sync = exact_keys(document["synchronization"], SYNC_KEYS, "synchronization")
    _bool(sync["correctnessSeparated"], "correctnessSeparated")
    _bool(sync["performanceMeasured"], "performanceMeasured")
    _count(sync["inFlightBound"], "inFlightBound")
    pool = exact_keys(document["pool"], POOL_KEYS, "pool")
    _token(pool["slotId"], "slotId")
    require(pool["kind"] in KINDS, "kind must be texture or buffer")
    frames = document["frames"]
    require(type(frames) is list and frames, "frames must be a non-empty list")
    seen_ids: set[str] = set()
    seen_generations: set[str] = set()
    previous_generation = 0
    for index, raw in enumerate(frames):
        frame = exact_keys(raw, FRAME_KEYS, f"frame {index}")
        frame_id = _token(frame["frameId"], f"frame {index} frameId")
        require(frame_id not in seen_ids, "duplicate frame id: " + frame_id)
        seen_ids.add(frame_id)
        generation = _count(frame["generation"], f"frame {frame_id} generation")
        require(generation not in seen_generations, "duplicate generation: " + generation)
        seen_generations.add(generation)
        generation_value = int(generation)
        require(generation_value > previous_generation, f"frame {frame_id} generation must increase")
        previous_generation = generation_value
        require(frame["lifetime"] in LIFETIMES, f"frame {frame_id} lifetime is unsupported")
        submitted = _bool(frame["submitted"], f"frame {frame_id} submitted")
        fence = _bool(frame["fenceComplete"], f"frame {frame_id} fenceComplete")
        _bool(frame["cancelled"], f"frame {frame_id} cancelled")
        _bool(frame["partialWrite"], f"frame {frame_id} partialWrite")
        _bool(frame["readsSlot"], f"frame {frame_id} readsSlot")
        _token(frame["payload"], f"frame {frame_id} payload")
        require(not fence or submitted, f"frame {frame_id} fence cannot complete before submission")


def _read_faults(frame: dict, priors: list[dict]) -> list[str]:
    if not frame["readsSlot"] or not priors:
        return []
    faults: list[str] = []
    if any(prior["partialWrite"] for prior in priors):
        faults.append("partial-read")
    if any(
        prior["generation"] != frame["generation"]
        and (
            not prior["fenceComplete"]
            or prior["partialWrite"]
            or prior["payload"] == frame["payload"]
        )
        for prior in priors
    ):
        faults.append("previous-generation")
    return faults


def frame_faults(document: dict) -> list[str]:
    """Return ownership faults. The immediate-recycle mutant is not included."""
    validate_document(document)
    faults: list[str] = []

    def add(claim: str) -> None:
        if claim not in faults:
            faults.append(claim)

    sync = document["synchronization"]
    if not sync["correctnessSeparated"]:
        add("performance-substituted")
    in_flight = sum(1 for frame in document["frames"] if frame["lifetime"] == "in-flight")
    if in_flight > int(sync["inFlightBound"]):
        add("in-flight-unbounded")
    if any(
        frame["lifetime"] == "released" and (not frame["fenceComplete"] or frame["partialWrite"])
        for frame in document["frames"]
    ):
        add("incomplete-release")
    for index, frame in enumerate(document["frames"]):
        for claim in _read_faults(frame, document["frames"][:index]):
            add(claim)
    return faults


def _status(frame: dict, priors: list[dict], faults: list[str], mutant: bool) -> str:
    read_faults = _read_faults(frame, priors)
    if mutant and frame["readsSlot"] and "immediate-recycle" in faults:
        return "recycled"
    if read_faults:
        return "blocked"
    if frame["readsSlot"]:
        return "readable"
    if frame["lifetime"] == "released" and (not frame["fenceComplete"] or frame["partialWrite"]):
        return "released-early"
    if frame["cancelled"] and not frame["fenceComplete"] and frame["lifetime"] == "in-flight":
        return "held"
    if frame["lifetime"] == "released" and frame["fenceComplete"] and not frame["partialWrite"]:
        return "released"
    if frame["lifetime"] == "completed" and frame["fenceComplete"] and not frame["partialWrite"]:
        return "completed"
    return "recorded"


def _inventory(document: dict, faults: list[str], mutant: bool) -> list[str]:
    pool = document["pool"]
    sync = document["synchronization"]
    preserved = [
        f"slot:{pool['slotId']}:kind={pool['kind']}",
        "bound:" + sync["inFlightBound"],
        "correctness-separated:" + str(sync["correctnessSeparated"]).lower(),
        "performance-measured:" + str(sync["performanceMeasured"]).lower(),
    ]
    frames = document["frames"]
    for index, frame in enumerate(frames):
        status = _status(frame, frames[:index], faults, mutant)
        preserved.append(
            f"frame:{frame['frameId']}:generation={frame['generation']}:"
            f"lifetime={frame['lifetime']}:submitted={str(frame['submitted']).lower()}:"
            f"fence={str(frame['fenceComplete']).lower()}:"
            f"cancelled={str(frame['cancelled']).lower()}:"
            f"partial={str(frame['partialWrite']).lower()}:"
            f"payload={frame['payload']}:reads={str(frame['readsSlot']).lower()}:"
            f"status={status}"
        )
    return preserved


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS, "unexpected decision")
    require(decision not in _FORBIDDEN, "P068 must not decide qualified or allowed")
    require(
        bool(reasons) and all(isinstance(item, str) and item for item in reasons),
        "reasons must be a non-empty list of strings",
    )
    for items in (rejected, preserved, questions):
        require(all(isinstance(item, str) and item for item in items), "result lists must be non-empty strings")
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


def assess(document: dict, path: str = DECLARED_PATH) -> dict:
    """Hold the slot until the fence completes, and reject immediate recycle.

    ``path`` ``immediate-recycle`` is the deliberate mutant. It does not erase
    partial-read or previous-generation checks, and it does not release a
    cancelled frame that is still in flight. The decision is never
    ``qualified`` or ``allowed``.
    """
    validate_document(document)
    require(path in PATHS, "path must be fenced or immediate-recycle")
    slot = document["pool"]["slotId"]
    reasons = [
        ORACLE,
        "fences and barriers are checked before reuse or release",
        "correctness synchronization is separate from performance measurements",
    ]
    questions = [
        "host fixture is not a physical S23 measurement",
        HOST_LIMIT,
        "performance measurements do not authorize reuse",
    ]
    rejected = frame_faults(document)
    mutant = path == MUTANT_PATH
    if mutant and any(frame["submitted"] for frame in document["frames"]):
        if "immediate-recycle" not in rejected:
            rejected.append("immediate-recycle")
        reasons.append(MUTANT)
        reasons.append("recycling immediately after command submission was rejected")
        questions.append("mutant immediate recycle was rejected before reuse")
    for index, frame in enumerate(document["frames"]):
        read_faults = _read_faults(frame, document["frames"][:index])
        if read_faults:
            reasons.append(
                f"{frame['frameId']} blocked on {slot}: " + ", ".join(read_faults)
            )
        if (
            frame["cancelled"]
            and not frame["fenceComplete"]
            and frame["lifetime"] == "in-flight"
        ):
            reasons.append(
                f"cancellation of {frame['frameId']} did not release incomplete ownership"
            )
        if (
            frame["cancelled"]
            and frame["lifetime"] == "released"
            and frame["fenceComplete"]
            and not frame["partialWrite"]
        ):
            reasons.append(f"cancellation of {frame['frameId']} released completed ownership")
        if frame["lifetime"] == "released" and (not frame["fenceComplete"] or frame["partialWrite"]):
            reasons.append(f"cancellation or release of {frame['frameId']} was not a completed ownership")
    if "in-flight-unbounded" in rejected:
        reasons.append("in-flight work exceeded the declared bound")
    if "performance-substituted" in rejected:
        reasons.append("a performance measurement was substituted for a fence")
    reasons.append(HOST_LIMIT)
    preserved = _inventory(document, rejected, mutant)
    if rejected:
        return _result("rejected", reasons, rejected, preserved, questions)
    if not any(frame["submitted"] for frame in document["frames"]):
        questions.append("no command was submitted, so completion was not verified")
        return _result("withheld", reasons, rejected, preserved, questions)
    held = any(
        frame["cancelled"] and not frame["fenceComplete"] and frame["lifetime"] == "in-flight"
        for frame in document["frames"]
    )
    if held and not any(frame["readsSlot"] for frame in document["frames"]):
        reasons.append(f"ownership of {slot} stayed with the in-flight frame")
        return _result("ownership_held", reasons, rejected, preserved, questions)
    reasons.append(f"reuse of {slot} waited until completion")
    return _result("completion_verified", reasons, rejected, preserved, questions)
