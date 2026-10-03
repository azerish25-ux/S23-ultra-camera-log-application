#!/usr/bin/env python3
"""P033 host gate for a bounded RAW sequence container.

The container names file magic, schema version, route identity, source
geometry, CFA, packing, a calibration snapshot id, and per-frame lengths,
timestamps, integrity, and an explicit end state. Impossible lengths are
rejected before any payload allocation. An explicit recovery mode reports a
complete prefix and the corruption separately and does not rewrite the source.

The deliberate mutant — allocating an arbitrary declared payload length before
checking bounds — is not used. This module does not probe a device, does not
qualify a physical S23, and does not execute TC-P033-01 through TC-P033-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P033"
CASE_ID = "P033"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
CONTRACT_ID = "s23-raw-sequence-container-fixture"
METHOD = (
    "Include file magic, schema version, route identity, source geometry, CFA, packing, "
    "calibration snapshot, and per-frame metadata. Frame records need lengths, timestamps, "
    "integrity checks, and explicit end state. Readers must reject impossible lengths before "
    "allocation."
)
FIXTURE = (
    "A valid three-frame source followed by an oversized length field and a truncated final record."
)
ORACLE = (
    "The reader reports the complete prefix and corruption separately under an explicit "
    "recovery mode without rewriting the original."
)
MUTANT = "Allocate an arbitrary declared payload length before checking bounds."
MAGIC = "S23RAW01"
RECOVERY = "explicit-complete-prefix"
STRICT = "strict"
ALLOCATION_BASIS = "bounds-checked"
MUTANT_BASIS = "declared-length"
HOST_LIMIT = "host fixture does not qualify a physical S23"
CFAS = ("RGGB", "GRBG", "GBRG", "BGGR")
PACKING = "uint16le-tight"
INTEGRITY = ("crc32-ok", "absent")
END_STATES = ("complete", "truncated")
CONTAINER_END = ("closed", "interrupted")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
UINT = re.compile(r"0|[1-9][0-9]*")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "contractId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "container",
    "frames",
    "recoveryMode",
    "originalRewritten",
}
CONTAINER_KEYS = {
    "magic",
    "schemaVersion",
    "routeIdentity",
    "width",
    "height",
    "cfa",
    "packing",
    "calibrationSnapshotId",
    "maxPayloadBytes",
    "maxDimension",
    "endState",
}
FRAME_KEYS = {
    "index",
    "declaredPayloadLength",
    "timestampNs",
    "integrity",
    "endState",
    "bytesPresent",
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


def _text(value: object, context: str) -> str:
    require(isinstance(value, str) and bool(value) and value == value.strip(),
            context + " must be a non-empty string")
    return value


def _bool(value: object, context: str) -> bool:
    require(type(value) is bool, context + " must be a bool")
    return value


def _uint(value: object, context: str) -> int:
    require(type(value) is int and value >= 0, context + " must be a non-negative int")
    return value


def _positive(value: object, context: str) -> int:
    require(type(value) is int and value > 0, context + " must be a positive int")
    return value


def _choice(value: object, allowed: tuple[str, ...], context: str) -> str:
    text = _text(value, context)
    require(text in allowed, context + " is not in the fixture vocabulary")
    return text


def _timestamp(value: object, context: str) -> str:
    require(isinstance(value, str) and UINT.fullmatch(value) is not None,
            context + " must be a canonical non-negative integer string")
    return value


def _tight_bytes(width: int, height: int) -> int:
    return width * height * 2


def _frame_ok(frame: dict, container: dict) -> bool:
    length = frame["declaredPayloadLength"]
    expected = _tight_bytes(container["width"], container["height"])
    return (
        frame["endState"] == "complete"
        and frame["integrity"] == "crc32-ok"
        and length == expected
        and length == frame["bytesPresent"]
        and 0 < length <= container["maxPayloadBytes"]
    )


def _corruption_codes(frame: dict, container: dict) -> list[str]:
    codes: list[str] = []
    length = frame["declaredPayloadLength"]
    if length > container["maxPayloadBytes"]:
        codes.append("oversized-length")
    if frame["endState"] == "truncated" or length != frame["bytesPresent"]:
        codes.append("truncated-record")
    return codes


def _split(document: dict) -> tuple[list[dict], list[dict], list[str]]:
    container = document["container"]
    prefix: list[dict] = []
    tail: list[dict] = []
    seen_bad = False
    for frame in document["frames"]:
        if not seen_bad and _frame_ok(frame, container):
            prefix.append(frame)
        else:
            seen_bad = True
            tail.append(frame)
    codes: list[str] = []
    for frame in tail:
        for code in _corruption_codes(frame, container):
            if code not in codes:
                codes.append(code)
    return prefix, tail, codes


def validate_fixture(document: dict) -> None:
    """Raise ValueError unless document is a P033 RAW sequence fixture."""
    exact_keys(document, DOCUMENT_KEYS, "raw sequence")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P033")
    require(document["contractId"] == CONTRACT_ID, "contractId drifted")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "raw sequence needs the P033 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    require(document["recoveryMode"] in {RECOVERY, STRICT}, "recoveryMode is not explicit or strict")
    _bool(document["originalRewritten"], "originalRewritten")

    container = exact_keys(document["container"], CONTAINER_KEYS, "container")
    require(container["magic"] == MAGIC, "file magic must be S23RAW01")
    require(type(container["schemaVersion"]) is int and container["schemaVersion"] == 1,
            "container schemaVersion must be 1")
    _text(container["routeIdentity"], "routeIdentity")
    width = _positive(container["width"], "width")
    height = _positive(container["height"], "height")
    require(width % 2 == 0 and height % 2 == 0, "source geometry must keep Bayer parity")
    _choice(container["cfa"], CFAS, "cfa")
    require(container["packing"] == PACKING, "packing must be uint16le-tight")
    _text(container["calibrationSnapshotId"], "calibrationSnapshotId")
    max_payload = _positive(container["maxPayloadBytes"], "maxPayloadBytes")
    max_dimension = _positive(container["maxDimension"], "maxDimension")
    require(width <= max_dimension and height <= max_dimension, "geometry exceeds maxDimension")
    require(_tight_bytes(width, height) <= max_payload, "tight frame exceeds maxPayloadBytes")
    end_state = _choice(container["endState"], CONTAINER_END, "container endState")

    frames = document["frames"]
    require(isinstance(frames, list) and frames, "frames must be a non-empty list")
    previous = -1
    parsed: list[dict] = []
    for index, value in enumerate(frames):
        frame = exact_keys(value, FRAME_KEYS, f"frame {index}")
        require(type(frame["index"]) is int and frame["index"] == index, f"frame {index} index must be {index}")
        _uint(frame["declaredPayloadLength"], f"frame {index} declaredPayloadLength")
        stamp = _timestamp(frame["timestampNs"], f"frame {index} timestampNs")
        require(int(stamp) > previous, f"frame {index} timestamp must increase")
        previous = int(stamp)
        _choice(frame["integrity"], INTEGRITY, f"frame {index} integrity")
        state = _choice(frame["endState"], END_STATES, f"frame {index} endState")
        _uint(frame["bytesPresent"], f"frame {index} bytesPresent")
        if state == "complete":
            require(_frame_ok(frame, container), f"frame {index} is not a bounded complete record")
        else:
            require(frame["integrity"] == "absent", f"frame {index} truncated record has no checksum")
            length = frame["declaredPayloadLength"]
            require(
                length > container["maxPayloadBytes"] or frame["bytesPresent"] < length,
                f"frame {index} truncated record is not short or oversized",
            )
        parsed.append(frame)
    interrupted = any(frame["endState"] != "complete" for frame in parsed)
    if interrupted:
        require(end_state == "interrupted", "a truncated record requires end state interrupted")
    else:
        require(end_state == "closed", "complete records require end state closed")


def bounds_checked_reserve(document: dict) -> int:
    """Bytes reserved after rejecting impossible lengths.

    Only complete prefix records are summed. The oversized declared length is
    not added and no buffer is allocated from it.
    """
    validate_fixture(document)
    prefix, _tail, _codes = _split(document)
    return sum(frame["declaredPayloadLength"] for frame in prefix)


def mutant_declared_reserve(document: dict) -> int:
    """What the mutant would reserve: every declared length, bounds ignored.

    assess_source must not use this value. It exists so a test can show the
    arbitrary declared length is larger than the bounds-checked reserve.
    """
    validate_fixture(document)
    return sum(frame["declaredPayloadLength"] for frame in document["frames"])


def _preserved(document: dict, prefix: list[dict], tail: list[dict], reserved: int) -> list[str]:
    container = document["container"]
    preserved = [
        "magic:" + container["magic"],
        "schema:" + str(container["schemaVersion"]),
        "route:" + container["routeIdentity"],
        "geometry:" + str(container["width"]) + "x" + str(container["height"]),
        "cfa:" + container["cfa"],
        "packing:" + container["packing"],
        "calibration:" + container["calibrationSnapshotId"],
        "end-state:" + container["endState"],
        "allocation:" + ALLOCATION_BASIS,
        "reserved:" + str(reserved),
        "recovery:" + document["recoveryMode"],
    ]
    for frame in prefix:
        preserved.append("prefix:" + str(frame["index"]))
        preserved.append("timestamp:" + frame["timestampNs"])
        preserved.append("integrity:" + frame["integrity"])
    for frame in tail:
        preserved.append("tail:" + str(frame["index"]))
        preserved.append("tail-declared:" + str(frame["declaredPayloadLength"]))
        preserved.append("tail-present:" + str(frame["bytesPresent"]))
        preserved.append("tail-end-state:" + frame["endState"])
    if document["originalRewritten"]:
        preserved.append("rewrite:refused")
    else:
        preserved.append("original:unmodified")
    return preserved


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision not in _FORBIDDEN, "P033 must not decide qualified or allowed")
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


def assess_source(document: dict) -> dict:
    """Report a complete prefix and corruption without rewriting the source.

    decision is prefix_recovered only for an explicit recovery mode that leaves
    the original unmodified. Strict mode on a corrupt tail is
    development_rejected. A rewrite request is rejected. The reserved byte
    count is bounds_checked_reserve, never mutant_declared_reserve. decision
    is never qualified or allowed.
    """
    validate_fixture(document)
    prefix, tail, codes = _split(document)
    reserved = bounds_checked_reserve(document)
    unsafe = mutant_declared_reserve(document)
    if tail:
        require(reserved != unsafe, "corrupt tail must not be reserved at the declared length")
    require(reserved == sum(frame["declaredPayloadLength"] for frame in prefix),
            "reserve drifted from the complete prefix")

    rejected: list[str] = list(codes)
    reasons = [
        "bounds were checked before allocation",
        MUTANT + " was not applied",
        "reserved " + str(reserved) + " bytes from the complete prefix",
    ]
    if tail:
        reasons.append(
            "complete prefix has "
            + str(len(prefix))
            + " frame(s); corruption is reported separately"
        )
    else:
        reasons.append("every frame is a bounded complete record")

    if document["originalRewritten"]:
        decision = "rejected"
        rejected = ["original-rewritten"] + rejected
        reasons.append("the original must not be rewritten")
        reasons.append(ORACLE)
    elif tail and document["recoveryMode"] == RECOVERY:
        decision = "prefix_recovered"
        reasons.append(ORACLE)
        reasons.append("prefix_recovered is a host-fixture label, not physical qualification")
    elif tail:
        decision = "development_rejected"
        reasons.append(
            "strict development rejection is distinct from explicit complete-prefix recovery"
        )
        reasons.append("development_rejected does not rewrite the original")
    else:
        decision = "source_intact"
        reasons.append("source_intact is a host-fixture label, not physical qualification")

    questions = [
        HOST_LIMIT,
        "fixed cadence without measured evidence is not claimed",
        "sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
        "the calibration snapshot id is not a measured colour certificate",
    ]
    preserved = _preserved(document, prefix, tail, reserved)
    require("allocation:" + MUTANT_BASIS not in preserved, "mutant allocation basis leaked")
    require("reserved:" + str(unsafe) not in preserved or not tail,
            "mutant reserve must not be recorded for a corrupt tail")
    require(decision not in _FORBIDDEN, "P033 must not decide qualified or allowed")
    return _result(decision, reasons, rejected, preserved, questions)
