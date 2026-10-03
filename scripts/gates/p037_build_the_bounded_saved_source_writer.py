#!/usr/bin/env python3
"""P037 bounded saved-source writer.

Owned copies move through a fixed-capacity pool to an independent writer.
Short writes, the flush policy, the source count, and overflow are recorded.
A full pool stops acquisition. It does not overwrite an older frame or invent
a replacement timestamp. Late writer completion cannot resume a failed take.

The mutant overwrites the oldest queued source frame to keep a green
recording indicator. assess rejects that document. This module does not probe
a device, does not qualify a physical S23, and does not execute TC-P037-01
through TC-P037-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P037"
CASE_ID = "P037"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
WRITER_ID = "s23-bounded-raw-writer-fixture"
METHOD = (
    "Transfer owned copies through a fixed-capacity pool to an independent writer. "
    "Record short writes, flush policy, source count, and overflow. A full pool stops "
    "acquisition explicitly; it must not silently overwrite an older frame or invent "
    "replacement timestamps."
)
FIXTURE = (
    "A source writer paused until the copy pool fills, then resumed after the capture "
    "controller has stopped."
)
ORACLE = (
    "All retained records remain ordered and intact, overflow is visible, and late "
    "completion cannot resume the failed take."
)
MUTANT = "Overwrite the oldest queued source frame to keep a green recording indicator."
MUTANT_POLICY = "overwrite_oldest_keep_green"
HONEST_POLICY = "stop_on_full_pool"
MUTANT_CLAIM = "overwrite-oldest-keep-green"

HEX40 = re.compile(r"^[0-9a-f]{40}$")
TS_TEXT = re.compile(r"^(0|[1-9][0-9]*)$")
DIGEST_TEXT = re.compile(r"^[0-9a-f]{4,64}$")
TOKEN_TEXT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
FLUSH_POLICIES = {"flush_on_stop", "none"}
CONTROL_OPS = {"pause_writer", "stop_controller", "resume_writer"}
RECORD_OPS = {"offer", "late_offer"}
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "writerId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "poolCapacity",
    "flushPolicy",
    "shortWriteBytes",
    "policy",
    "records",
    "script",
}
RECORD_KEYS = {"id", "timestampNs", "bytes", "digest"}
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


def _text_token(value: object, label: str) -> str:
    require(isinstance(value, str) and TOKEN_TEXT.fullmatch(value) is not None,
            label + " must be a token")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision not in _FORBIDDEN, "P037 must not decide qualified or allowed")
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


def record_token(record: dict) -> str:
    """Stable inventory token. Timestamps and digests are not rewritten."""
    return f"{record['id']}@{record['timestampNs']}:{record['digest']}"


def _owned_copy(record: dict) -> dict[str, Any]:
    return {
        "id": record["id"],
        "timestampNs": record["timestampNs"],
        "bytes": record["bytes"],
        "digest": record["digest"],
    }


def _parse_record(value: object, index: int, seen: set[str], previous: int | None) -> dict:
    item = exact_keys(value, RECORD_KEYS, f"records[{index}]")
    ident = _text_token(item["id"], f"records[{index}] id")
    require(ident not in seen, "duplicate record id " + ident)
    seen.add(ident)
    require(isinstance(item["timestampNs"], str) and TS_TEXT.fullmatch(item["timestampNs"]) is not None,
            f"records[{index}] timestampNs must be a canonical non-negative integer string")
    stamp = int(item["timestampNs"])
    require(previous is None or stamp > previous, f"records[{index}] timestamp must strictly increase")
    require(type(item["bytes"]) is int and item["bytes"] > 0, f"records[{index}] bytes must be a positive int")
    require(isinstance(item["digest"], str) and DIGEST_TEXT.fullmatch(item["digest"]) is not None,
            f"records[{index}] digest must be lowercase hex")
    return item


def _parse_records(records: object) -> list[dict]:
    require(isinstance(records, list) and records, "records must be a non-empty list")
    require(len(records) <= 32, "records exceed the harness bound")
    parsed: list[dict] = []
    seen: set[str] = set()
    previous: int | None = None
    for index, record in enumerate(records):
        item = _parse_record(record, index, seen, previous)
        previous = int(item["timestampNs"])
        parsed.append(item)
    return parsed


def _identity(document: dict) -> None:
    require(type(document.get("schemaVersion")) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document.get("phase") == PHASE, "phase must be P037")
    require(document.get("writerId") == WRITER_ID, "writerId must be s23-bounded-raw-writer-fixture")
    revision = document.get("implementationBaseRevision")
    require(revision == BASE_REVISION and isinstance(revision, str) and HEX40.fullmatch(revision) is not None,
            "writer needs the P037 implementation base revision")
    require(document.get("method") == METHOD, "method text drifted")
    require(document.get("fixture") == FIXTURE, "fixture text drifted")
    require(document.get("oracle") == ORACLE, "oracle text drifted")
    require(document.get("mutant") == MUTANT, "mutant text must name the overwrite-oldest writer")


def _parse_script(script: object, records: list[dict]) -> list[dict]:
    require(isinstance(script, list) and script, "script must be a non-empty list")
    known = {record["id"] for record in records}
    parsed: list[dict] = []
    for index, step in enumerate(script):
        require(isinstance(step, dict), f"script[{index}] must be an object")
        op = step.get("op")
        require(isinstance(op, str), f"script[{index}] op must be a string")
        if op in CONTROL_OPS:
            exact_keys(step, {"op"}, f"script[{index}]")
            parsed.append({"op": op})
        elif op in RECORD_OPS:
            exact_keys(step, {"op", "recordId"}, f"script[{index}]")
            record_id = _text_token(step["recordId"], f"script[{index}] recordId")
            require(record_id in known, f"script[{index}] unknown record {record_id}")
            parsed.append({"op": op, "recordId": record_id})
        else:
            raise ValueError(f"script[{index}] op is unknown")
    ops = [step["op"] for step in parsed]
    require(ops.count("pause_writer") == 1 and ops[0] == "pause_writer",
            "script must pause the writer first")
    require(ops.count("stop_controller") == 1, "script must stop the controller once")
    require(ops.count("resume_writer") == 1, "script must resume the writer once")
    require(ops.count("late_offer") == 1 and ops[-1] == "late_offer",
            "script must end with one late offer")
    stop_at = ops.index("stop_controller")
    resume_at = ops.index("resume_writer")
    require(resume_at == stop_at + 1, "resume must follow the controller stop with no intervening offer")
    require(all(op == "offer" for op in ops[1:stop_at]) and stop_at > 1,
            "offers must sit between the pause and the controller stop")
    script_ids = [step["recordId"] for step in parsed if "recordId" in step]
    require(script_ids == [record["id"] for record in records],
            "script record ids must match the record inventory in order")
    require(len(script_ids) == len(set(script_ids)), "script record ids must be unique")
    return parsed


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is a structurally valid P037 writer fixture.

    The overwrite-oldest policy is not a valid bounded writer. assess rejects it
    before this validator is used.
    """
    require(isinstance(document, dict), "writer document must be an object")
    require(document.get("policy") != MUTANT_POLICY, "mutant documents are not a bounded writer")
    exact_keys(document, DOCUMENT_KEYS, "writer document")
    _identity(document)
    require(document["policy"] == HONEST_POLICY, "policy must stop acquisition when the pool is full")
    require(document["flushPolicy"] in FLUSH_POLICIES, "flushPolicy is unknown")
    capacity = document["poolCapacity"]
    require(type(capacity) is int and 1 <= capacity <= 16, "poolCapacity must be an int from 1 to 16")
    short = document["shortWriteBytes"]
    require(type(short) is int and 0 <= short <= 1 << 20, "shortWriteBytes must be an int from 0 to 1048576")
    records = _parse_records(document["records"])
    _parse_script(document["script"], records)


def _inventory(document: dict) -> list[str]:
    records = _parse_records(document.get("records"))
    return [record_token(record) for record in records]


def _reject_mutant(document: dict) -> dict[str, Any]:
    require(isinstance(document, dict), "writer document must be an object")
    _identity(document)
    preserved = _inventory(document)
    return _result(
        "rejected",
        [
            MUTANT,
            "overwriting the oldest queued frame to keep a green indicator hides overflow",
            "the mutant does not stop acquisition and invents no honest gap",
            ORACLE,
        ],
        [MUTANT_CLAIM, "green-recording-indicator"],
        preserved,
        [
            "host fixture only; physical S23 capture was not measured",
            "rejecting the mutant does not qualify a device writer",
        ],
    )


def mutant_overwrite(records: list[dict], capacity: int) -> dict[str, Any]:
    """Deliberate mutation: drop the oldest queued frame and stay green.

    assess must not treat this outcome as overflow_visible. A test fails if the
    oldest frame disappears from the assessor inventory or the decision turns
    into a green success.
    """
    require(type(capacity) is int and capacity > 0, "capacity must be a positive int")
    require(isinstance(records, list) and records, "records must be a non-empty list")
    pool: list[dict] = []
    overwritten: list[dict] = []
    for record in records:
        require(isinstance(record, dict) and "id" in record, "record must have an id")
        if len(pool) >= capacity:
            overwritten.append(pool.pop(0))
        pool.append(dict(record))
    return {
        "indicator": "green",
        "acquisitionStopped": False,
        "overflow": [],
        "retained": pool,
        "overwritten": overwritten,
    }


def simulate(document: dict) -> dict[str, Any]:
    """Transfer owned copies. Refuse the overwrite mutant.

    The writer stays paused until after the controller stops. Frames that do
    not fit are overflow, not replacements. Resume drains only the retained
    copies and does not clear the failed take.
    """
    validate_document(document)
    by_id = {record["id"]: record for record in document["records"]}
    capacity = document["poolCapacity"]
    pool: list[dict] = []
    written: list[dict] = []
    overflow: list[dict] = []
    late: list[dict] = []
    paused = False
    controller_stopped = False
    acquisition_stopped = False
    take_failed = False
    indicator = "idle"
    offers = 0
    short_writes: list[dict[str, Any]] = []

    for step in document["script"]:
        op = step["op"]
        if op == "pause_writer":
            paused = True
            indicator = "recording"
        elif op == "offer":
            record = _owned_copy(by_id[step["recordId"]])
            offers += 1
            if not paused:
                late.append(record)
                continue
            if acquisition_stopped or len(pool) >= capacity:
                acquisition_stopped = True
                take_failed = True
                indicator = "stopped"
                overflow.append(record)
            else:
                pool.append(record)
        elif op == "stop_controller":
            controller_stopped = True
            acquisition_stopped = True
            take_failed = True
            indicator = "stopped"
        elif op == "resume_writer":
            require(controller_stopped, "writer resumed before the controller stopped")
            paused = False
            while pool:
                written.append(pool.pop(0))
            if document["flushPolicy"] == "flush_on_stop":
                short_writes.append({
                    "bytes": document["shortWriteBytes"],
                    "policy": document["flushPolicy"],
                })
            indicator = "stopped"
        elif op == "late_offer":
            late.append(_owned_copy(by_id[step["recordId"]]))
            indicator = "stopped"
        else:
            raise ValueError("unknown script op")

    return {
        "written": written,
        "overflow": overflow,
        "late": late,
        "sourceCount": len(written),
        "offers": offers,
        "indicator": indicator,
        "takeFailed": take_failed,
        "acquisitionStopped": acquisition_stopped,
        "controllerStopped": controller_stopped,
        "shortWrites": short_writes,
        "flushPolicy": document["flushPolicy"],
        "poolResidual": pool,
    }


def _intact(observed: list[dict], expected_ids: list[str], by_id: dict[str, dict]) -> bool:
    if [item["id"] for item in observed] != expected_ids:
        return False
    for item in observed:
        source = by_id[item["id"]]
        if (
            item["timestampNs"] != source["timestampNs"]
            or item["digest"] != source["digest"]
            or item["bytes"] != source["bytes"]
        ):
            return False
    return True


def assess(document: dict) -> dict[str, Any]:
    """Judge the host fixture. The overwrite-oldest writer is rejected.

    Retained records stay ordered and intact. Overflow stays visible. A late
    offer after the controller has stopped cannot resume the failed take.
    Decision is never qualified or allowed.
    """
    require(isinstance(document, dict), "writer document must be an object")
    if document.get("policy") == MUTANT_POLICY:
        return _reject_mutant(document)
    validate_document(document)
    preserved = [record_token(record) for record in document["records"]]
    questions = ["host fixture only; physical S23 capture was not measured"]
    if document["flushPolicy"] != "flush_on_stop":
        return _result(
            "rejected",
            [
                "flush policy was not recorded as flush_on_stop",
                "missing flush policy does not erase the source inventory",
                ORACLE,
            ],
            ["missing-flush-policy"],
            preserved,
            questions,
        )
    observed = simulate(document)
    by_id = {record["id"]: record for record in document["records"]}
    offer_ids = [step["recordId"] for step in document["script"] if step["op"] == "offer"]
    late_ids = [step["recordId"] for step in document["script"] if step["op"] == "late_offer"]
    capacity = document["poolCapacity"]
    filled = len(offer_ids) > capacity
    expected_written = offer_ids[:capacity] if filled else offer_ids
    expected_overflow = offer_ids[capacity:] if filled else []
    written_ok = _intact(observed["written"], expected_written, by_id)
    overflow_ok = _intact(observed["overflow"], expected_overflow, by_id)
    late_ok = _intact(observed["late"], late_ids, by_id)
    late_ids_written = {item["id"] for item in observed["written"]} & set(late_ids)
    if (
        not written_ok
        or not overflow_ok
        or not late_ok
        or observed["poolResidual"]
        or observed["indicator"] == "green"
        or late_ids_written
    ):
        return _result(
            "rejected",
            [
                "retained records were reordered, replaced, or given invented timestamps",
                ORACLE,
            ],
            ["invented-timestamps"],
            preserved,
            questions,
        )
    accounting = [
        f"sourceCount:{observed['sourceCount']}",
        f"flush:{observed['flushPolicy']}",
        f"shortWrite:{document['shortWriteBytes']}",
        f"indicator:{observed['indicator']}",
    ]
    if not filled or not observed["overflow"]:
        return _result(
            "withheld",
            [
                "the paused writer did not fill the copy pool, so overflow is not visible",
                f"source count {observed['sourceCount']}",
                f"flush policy {document['flushPolicy']}",
                ORACLE,
            ],
            [],
            preserved + accounting,
            questions + ["pool did not overflow; the failed-take oracle was not exercised"],
        )
    short_ok = observed["shortWrites"] == [
        {"bytes": document["shortWriteBytes"], "policy": "flush_on_stop"}
    ]
    resumed_blocked = (
        observed["takeFailed"] is True
        and observed["acquisitionStopped"] is True
        and observed["controllerStopped"] is True
        and observed["indicator"] == "stopped"
        and observed["sourceCount"] == capacity
        and not late_ids_written
        and short_ok
    )
    overflow_claims = [f"overflow:{record_token(item)}" for item in observed["overflow"]]
    late_claims = [f"late:{record_token(item)}" for item in observed["late"]]
    if not resumed_blocked:
        return _result(
            "rejected",
            [
                "late completion resumed the failed take or dropped the stop",
                ORACLE,
            ],
            ["resumed-failed-take"],
            preserved + accounting,
            questions,
        )
    reasons = [
        METHOD,
        f"source count {observed['sourceCount']}",
        f"flush policy {document['flushPolicy']}",
        f"short write {document['shortWriteBytes']}",
        "retained records stayed ordered and intact",
        "overflow visible: " + ", ".join(overflow_claims),
        "late completion cannot resume the failed take",
        ORACLE,
    ]
    return _result(
        "overflow_visible",
        reasons,
        overflow_claims + late_claims,
        preserved + accounting,
        questions + [
            "late writer completion did not resume the failed take",
            "overflow is visible and was not overwritten",
        ],
    )
