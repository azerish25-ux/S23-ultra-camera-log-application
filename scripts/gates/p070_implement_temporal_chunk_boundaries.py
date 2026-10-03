#!/usr/bin/env python3
"""P070 temporal chunk boundaries for deferred video processing.

Each temporal node declares history and lookahead, checkpoints the state a
resume must reload, and names overlap frames that are read but not emitted
again. Caches are bound to source, model, graph, and algorithm identities.
A scene cut must invalidate history; a cut that keeps history is rejected.
Overlap that shows up twice in the final frame list is rejected.

The deliberate mutant — restart the temporal model from an empty state at
every export chunk — is rejected. Empty history does not preserve temporal
continuity. This module does not probe a device, does not qualify a physical
S23, and does not execute TC-P070-01 through TC-P070-08.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


PHASE = "P070"
CASE_ID = "P070"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-temporal-chunk-boundaries-fixture"
METHOD = (
    "Declare history and lookahead per temporal node, checkpoint relevant state, "
    "and include overlap frames that are not duplicated in final output. Bind caches "
    "to source, model, graph, and algorithm identities. Scene cuts invalidate appropriate history."
)
FIXTURE = (
    "A subject crossing a chunk boundary during a focus pull with a process restart at the boundary."
)
ORACLE = (
    "The resumed output preserves temporal continuity within the declared tolerance and exact frame count."
)
MUTANT = "Restart the temporal model from an empty state at every export chunk."
DECLARED_PATH = "checkpointed"
MUTANT_PATH = "empty-restart"
PATHS = (DECLARED_PATH, MUTANT_PATH)
HOST_LIMIT = "host fixture does not qualify a physical S23 or a resumed export"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[a-z0-9-]+$")
INT = re.compile(r"0|[1-9][0-9]*")
POS = re.compile(r"[1-9][0-9]*")
DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "subject",
    "focusPull",
    "boundaryCrossed",
    "sourceId",
    "modelId",
    "graphId",
    "algorithmId",
    "tolerance",
    "expectedFrameCount",
    "nodes",
    "chunks",
    "uninterrupted",
    "resumed",
}
NODE_KEYS = {"id", "history", "lookahead", "checkpoint", "cacheBound", "cache"}
CACHE_KEYS = {"sourceId", "modelId", "graphId", "algorithmId"}
CHUNK_KEYS = {
    "id",
    "startFrame",
    "endFrame",
    "overlapIn",
    "overlapOut",
    "sceneCut",
    "historyInvalidated",
    "emittedFrames",
    "overlapFrames",
    "continuityDelta",
}
RUN_KEYS = {
    "frameCount",
    "continuityDelta",
    "duplicateFrames",
    "checkpointLoaded",
    "emptyState",
}
RESUMED_KEYS = RUN_KEYS | {"restartAtBoundary"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "withheld", "continuity_preserved"}
_DISCARD = "empty-state restart at every export chunk discards checkpointed history"


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


def _int(value: object, label: str) -> str:
    require(isinstance(value, str) and INT.fullmatch(value) is not None, label + " must be a canonical integer")
    return value


def _pos(value: object, label: str) -> str:
    require(
        isinstance(value, str) and POS.fullmatch(value) is not None,
        label + " must be a canonical positive integer",
    )
    return value


def _decimal(value: object, label: str, positive: bool) -> str:
    require(
        isinstance(value, str) and DECIMAL.fullmatch(value) is not None,
        label + " must be a canonical decimal",
    )
    if positive and Decimal(value) <= 0:
        raise ValueError(label + " must be positive")
    return value


def _frames(value: object, label: str, allow_empty: bool) -> list[str]:
    require(type(value) is list, label + " must be a list")
    if not allow_empty:
        require(bool(value), label + " must be non-empty")
    frames: list[str] = []
    last = -1
    for item in value:
        token = _int(item, label)
        number = int(token)
        require(number > last, label + " must be strictly increasing")
        last = number
        frames.append(token)
    return frames


def _cache(value: object, label: str) -> dict:
    cache = exact_keys(value, CACHE_KEYS, label)
    for key in ("sourceId", "modelId", "graphId", "algorithmId"):
        _token(cache[key], label + " " + key)
    return cache


def _run(value: object, label: str, resumed: bool) -> dict:
    run = exact_keys(value, RESUMED_KEYS if resumed else RUN_KEYS, label)
    _pos(run["frameCount"], label + " frameCount")
    _decimal(run["continuityDelta"], label + " continuityDelta", False)
    _frames(run["duplicateFrames"], label + " duplicateFrames", True)
    _bool(run["checkpointLoaded"], label + " checkpointLoaded")
    _bool(run["emptyState"], label + " emptyState")
    if resumed:
        _bool(run["restartAtBoundary"], label + " restartAtBoundary")
    return run


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is a P070 temporal-chunk fixture."""
    exact_keys(document, DOCUMENT_KEYS, "temporal chunk contract")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P070")
    require(document["mapId"] == MAP_ID, "mapId must be s23-temporal-chunk-boundaries-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "temporal chunk contract needs the P070 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    _token(document["subject"], "subject")
    _bool(document["focusPull"], "focusPull")
    _bool(document["boundaryCrossed"], "boundaryCrossed")
    for key in ("sourceId", "modelId", "graphId", "algorithmId"):
        _token(document[key], key)
    _decimal(document["tolerance"], "tolerance", True)
    _pos(document["expectedFrameCount"], "expectedFrameCount")
    nodes = document["nodes"]
    require(type(nodes) is list and nodes, "nodes must be a non-empty list")
    seen_nodes: set[str] = set()
    for index, raw in enumerate(nodes):
        node = exact_keys(raw, NODE_KEYS, f"node {index}")
        node_id = _token(node["id"], f"node {index} id")
        require(node_id not in seen_nodes, "duplicate node id: " + node_id)
        seen_nodes.add(node_id)
        _int(node["history"], f"node {node_id} history")
        _int(node["lookahead"], f"node {node_id} lookahead")
        _bool(node["checkpoint"], f"node {node_id} checkpoint")
        _bool(node["cacheBound"], f"node {node_id} cacheBound")
        _cache(node["cache"], f"node {node_id} cache")
    chunks = document["chunks"]
    require(type(chunks) is list and chunks, "chunks must be a non-empty list")
    seen_chunks: set[str] = set()
    for index, raw in enumerate(chunks):
        chunk = exact_keys(raw, CHUNK_KEYS, f"chunk {index}")
        chunk_id = _token(chunk["id"], f"chunk {index} id")
        require(chunk_id not in seen_chunks, "duplicate chunk id: " + chunk_id)
        seen_chunks.add(chunk_id)
        start = _int(chunk["startFrame"], f"chunk {chunk_id} startFrame")
        end = _int(chunk["endFrame"], f"chunk {chunk_id} endFrame")
        require(int(end) > int(start), f"chunk {chunk_id} endFrame must be greater than startFrame")
        overlap_in = _int(chunk["overlapIn"], f"chunk {chunk_id} overlapIn")
        overlap_out = _int(chunk["overlapOut"], f"chunk {chunk_id} overlapOut")
        _bool(chunk["sceneCut"], f"chunk {chunk_id} sceneCut")
        _bool(chunk["historyInvalidated"], f"chunk {chunk_id} historyInvalidated")
        emitted = _frames(chunk["emittedFrames"], f"chunk {chunk_id} emittedFrames", False)
        overlap = _frames(chunk["overlapFrames"], f"chunk {chunk_id} overlapFrames", True)
        require(
            len(overlap) == int(overlap_in) + int(overlap_out),
            f"chunk {chunk_id} overlapFrames must match overlapIn plus overlapOut",
        )
        require(len(emitted) == len(set(emitted)), f"chunk {chunk_id} emittedFrames must be unique")
        _decimal(chunk["continuityDelta"], f"chunk {chunk_id} continuityDelta", False)
    _run(document["uninterrupted"], "uninterrupted", False)
    _run(document["resumed"], "resumed", True)


def _add(faults: list[tuple[str, str]], claim: str, reason: str) -> None:
    if claim not in {item for item, _ in faults}:
        faults.append((claim, reason))


def _faults(document: dict) -> list[tuple[str, str]]:
    faults: list[tuple[str, str]] = []
    tolerance = document["tolerance"]
    expected = document["expectedFrameCount"]
    identities = (
        document["sourceId"],
        document["modelId"],
        document["graphId"],
        document["algorithmId"],
    )
    for node in document["nodes"]:
        node_id = node["id"]
        if int(node["history"]) == 0 and int(node["lookahead"]) == 0:
            _add(faults, "empty-temporal-window", f"node {node_id} declared neither history nor lookahead")
        if not node["checkpoint"]:
            _add(faults, "missing-checkpoint", f"node {node_id} did not checkpoint relevant state")
        cache = node["cache"]
        cached = (cache["sourceId"], cache["modelId"], cache["graphId"], cache["algorithmId"])
        if not node["cacheBound"]:
            _add(
                faults,
                "unbound-cache",
                f"node {node_id} cache is not bound to source, model, graph, and algorithm identities",
            )
        if cached != identities:
            _add(
                faults,
                "cache-identity-mismatch",
                f"node {node_id} cache identity does not match the document source, model, graph, and algorithm",
            )
    for chunk in document["chunks"]:
        chunk_id = chunk["id"]
        if chunk["sceneCut"] and not chunk["historyInvalidated"]:
            _add(faults, "scene-cut-history-kept", f"chunk {chunk_id} scene cut did not invalidate history")
        if chunk["historyInvalidated"] and not chunk["sceneCut"]:
            _add(faults, "history-cleared-without-cut", f"chunk {chunk_id} invalidated history without a scene cut")
        if set(chunk["overlapFrames"]) & set(chunk["emittedFrames"]):
            _add(faults, "overlap-emitted", f"chunk {chunk_id} duplicated overlap frames in emitted output")
        start = int(chunk["startFrame"])
        end = int(chunk["endFrame"])
        if any(not (start <= int(frame) < end) for frame in chunk["emittedFrames"]):
            _add(faults, "emitted-outside-owned-range", f"chunk {chunk_id} emitted a frame outside its owned range")
        if Decimal(chunk["continuityDelta"]) > Decimal(tolerance):
            _add(
                faults,
                "chunk-continuity",
                f"chunk {chunk_id} continuity {chunk['continuityDelta']} exceeds tolerance {tolerance}",
            )
        if any(int(node["history"]) < int(chunk["overlapIn"]) for node in document["nodes"]):
            _add(
                faults,
                "history-short",
                f"declared history does not cover chunk {chunk_id} overlap-in {chunk['overlapIn']}",
            )
        if any(int(node["lookahead"]) < int(chunk["overlapOut"]) for node in document["nodes"]):
            _add(
                faults,
                "lookahead-short",
                f"declared lookahead does not cover chunk {chunk_id} overlap-out {chunk['overlapOut']}",
            )
    assembled: list[str] = []
    for chunk in document["chunks"]:
        assembled.extend(chunk["emittedFrames"])
    expected_seq = [str(index) for index in range(int(expected))]
    if len(assembled) != len(set(assembled)):
        _add(faults, "duplicate-output-frame", "final output duplicated an overlap or owned frame")
    if assembled != expected_seq:
        _add(faults, "frame-count-mismatch", f"assembled output is not the expected {expected} frames in order")
    _run_faults(faults, document["uninterrupted"], "uninterrupted", tolerance, expected)
    _run_faults(faults, document["resumed"], "resumed", tolerance, expected)
    resumed = document["resumed"]
    if resumed["emptyState"]:
        _add(faults, "empty-state-restart", "resumed run restarted the temporal model from an empty state")
    if not resumed["checkpointLoaded"]:
        _add(faults, "checkpoint-not-loaded", "resumed run did not load the checkpoint")
    return faults


def _run_faults(
    faults: list[tuple[str, str]],
    run: dict,
    name: str,
    tolerance: str,
    expected: str,
) -> None:
    if run["frameCount"] != expected:
        _add(faults, f"{name}-frame-count", f"{name} frame count {run['frameCount']} is not {expected}")
    if Decimal(run["continuityDelta"]) > Decimal(tolerance):
        _add(
            faults,
            f"{name}-continuity",
            f"{name} continuity {run['continuityDelta']} exceeds tolerance {tolerance}",
        )
    if run["duplicateFrames"]:
        _add(faults, f"{name}-duplicates", f"{name} output listed duplicate frames")
    if name == "uninterrupted" and run["emptyState"]:
        _add(faults, "uninterrupted-empty-state", "uninterrupted run restarted from an empty state")


def _inventory(document: dict) -> list[str]:
    preserved = [
        (
            f"subject:{document['subject']}:focus-pull={str(document['focusPull']).lower()}:"
            f"boundary-crossed={str(document['boundaryCrossed']).lower()}"
        ),
        (
            f"identity:source={document['sourceId']}:model={document['modelId']}:"
            f"graph={document['graphId']}:algorithm={document['algorithmId']}"
        ),
        "tolerance:" + document["tolerance"],
        "expected-frame-count:" + document["expectedFrameCount"],
    ]
    for node in document["nodes"]:
        cache = node["cache"]
        preserved.append(
            f"node:{node['id']}:history={node['history']}:lookahead={node['lookahead']}:"
            f"checkpoint={str(node['checkpoint']).lower()}:cache-bound={str(node['cacheBound']).lower()}:"
            f"source={cache['sourceId']}:model={cache['modelId']}:graph={cache['graphId']}:"
            f"algorithm={cache['algorithmId']}"
        )
    for chunk in document["chunks"]:
        overlap = ",".join(chunk["overlapFrames"]) if chunk["overlapFrames"] else "none"
        preserved.append(
            f"chunk:{chunk['id']}:start={chunk['startFrame']}:end={chunk['endFrame']}:"
            f"overlap-in={chunk['overlapIn']}:overlap-out={chunk['overlapOut']}:"
            f"scene-cut={str(chunk['sceneCut']).lower()}:"
            f"history-invalidated={str(chunk['historyInvalidated']).lower()}:"
            f"emitted={','.join(chunk['emittedFrames'])}:overlap={overlap}:delta={chunk['continuityDelta']}"
        )
    for name in ("uninterrupted", "resumed"):
        run = document[name]
        duplicates = ",".join(run["duplicateFrames"]) if run["duplicateFrames"] else "none"
        line = (
            f"run:{name}:frames={run['frameCount']}:delta={run['continuityDelta']}:"
            f"duplicates={duplicates}:checkpoint={str(run['checkpointLoaded']).lower()}:"
            f"empty={str(run['emptyState']).lower()}"
        )
        if name == "resumed":
            line += f":restart={str(run['restartAtBoundary']).lower()}"
        preserved.append(line)
    return preserved


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS, "unexpected decision")
    require(decision not in _FORBIDDEN, "P070 must not decide qualified or allowed")
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
    """Compare uninterrupted and resumed chunks, and reject an empty restart.

    ``path`` ``empty-restart`` is the deliberate mutant. It restarts every
    export chunk from an empty temporal state even when the fixture loaded a
    checkpoint. That path stays ``rejected`` and does not erase the chunk,
    frame, or identity inventory. The decision is never ``qualified`` or
    ``allowed``. ``continuity_preserved`` is only a host-fixture comparison.
    """
    validate_document(document)
    require(path in PATHS, "path must be checkpointed or empty-restart")
    faults = _faults(document)
    mutant = path == MUTANT_PATH
    if mutant:
        _add(faults, "empty-state-restart", _DISCARD)
    reasons = [ORACLE]
    reasons.extend(reason for _, reason in faults)
    scenario = (
        document["focusPull"] and document["boundaryCrossed"] and document["resumed"]["restartAtBoundary"]
    )
    if mutant:
        reasons.append(MUTANT)
        if _DISCARD not in reasons:
            reasons.append(_DISCARD)
    elif not faults and scenario:
        resumed = document["resumed"]
        reasons.append(
            f"resumed continuity {resumed['continuityDelta']} is within tolerance {document['tolerance']}"
        )
        reasons.append(
            f"resumed frame count {resumed['frameCount']} matches expected {document['expectedFrameCount']}"
        )
        reasons.append("overlap frames were not duplicated in the final output")
    elif not faults:
        reasons.append(
            "focus pull, boundary crossing, and a process restart at the boundary were not all recorded"
        )
    reasons.append(HOST_LIMIT)
    questions = [
        "host fixture is not a physical S23 measurement",
        HOST_LIMIT,
        "continuity_preserved is not physical S23 qualification",
    ]
    if mutant:
        questions.append("mutant empty-state restart was rejected")
    if not document["focusPull"]:
        questions.append("focus pull was not recorded")
    if not document["boundaryCrossed"]:
        questions.append("chunk boundary crossing was not recorded")
    if not document["resumed"]["restartAtBoundary"]:
        questions.append("process restart at the boundary was not recorded")
    preserved = _inventory(document)
    rejected = [claim for claim, _ in faults]
    if rejected:
        return _result("rejected", reasons, rejected, preserved, questions)
    if not scenario:
        return _result("withheld", reasons, rejected, preserved, questions)
    return _result("continuity_preserved", reasons, rejected, preserved, questions)
