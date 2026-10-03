#!/usr/bin/env python3
"""P065 typed render graph and static compatibility validator.

Every node declares input and output descriptors, a precision requirement,
a spatial halo, temporal context, and deterministic parameters. Edges are
checked before allocation. A film-density output must not feed an encoded
YUV surface, and a display overlay must not feed clean-master export.

The deliberate mutant — untyped texture handles for every intermediate —
is rejected. Untyped handles do not make those connections legal. This
module does not probe a device, does not qualify a physical S23, and does
not execute TC-P065-01 through TC-P065-08.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


PHASE = "P065"
CASE_ID = "P065"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-typed-render-graph-fixture"
METHOD = (
    "Give every node declared input and output descriptors, precision requirements, "
    "spatial halo, temporal context, and deterministic parameters. Validate graph "
    "edges before allocation. Nodes report whether they alter geometry, exposure, "
    "color, texture, or time."
)
FIXTURE = (
    "A film-density node connected directly to an encoded YUV surface and a "
    "display overlay connected to clean-master export."
)
ORACLE = "The graph validator rejects both invalid connections before processing frames."
MUTANT = "Represent all intermediate images as untyped texture handles."
DECLARED_PATH = "typed"
MUTANT_PATH = "untyped-handles"
PATHS = (DECLARED_PATH, MUTANT_PATH)
STAGE = "before-allocation"
HOST_LIMIT = "host fixture does not qualify a physical S23 or a measured render graph"
DOMAINS = (
    "film-density",
    "encoded-yuv",
    "display-overlay",
    "clean-master",
    "scene-linear",
    "untyped",
)
PRECISIONS = ("rgba32f", "rgba16f", "rgba8", "yuv420", "untyped")
GEOMETRIES = ("image-plane", "overlay-plane", "export-plane")
TEMPORALS = ("none", "history", "chunk")
ALTERS = ("geometry", "exposure", "color", "texture", "time")
TYPED_DOMAINS = tuple(item for item in DOMAINS if item != "untyped")
TYPED_PRECISIONS = tuple(item for item in PRECISIONS if item != "untyped")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[a-z0-9-]+$")
HALO = re.compile(r"0|[1-9][0-9]*")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "validation",
    "nodes",
    "edges",
}
VALIDATION_KEYS = {"stage", "framesProcessed", "allocated"}
NODE_KEYS = {
    "id",
    "inputs",
    "outputs",
    "precisionRequirement",
    "halo",
    "temporal",
    "deterministic",
    "parameters",
    "alters",
}
PORT_KEYS = {"name", "domain", "precision", "geometry"}
EDGE_KEYS = {"id", "fromNode", "fromPort", "toNode", "toPort"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "withheld", "edges_validated"}
_INVALID_EDGES = ("density-to-yuv", "overlay-to-master")


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


def _halo(value: object, label: str) -> str:
    require(isinstance(value, str) and HALO.fullmatch(value) is not None, label + " must be a canonical halo")
    return value


def _choice(value: object, allowed: tuple[str, ...], label: str) -> str:
    require(isinstance(value, str) and value in allowed, label + " is unsupported")
    return value


def _unique_tokens(value: object, allowed: tuple[str, ...] | None, label: str) -> list[str]:
    require(type(value) is list, label + " must be a list")
    seen: set[str] = set()
    items: list[str] = []
    for item in value:
        token = _token(item, label)
        if allowed is not None:
            require(token in allowed, label + " has an unsupported token")
        require(token not in seen, label + " has a duplicate")
        seen.add(token)
        items.append(token)
    return items


def _port(value: object, label: str) -> dict:
    port = exact_keys(value, PORT_KEYS, label)
    _token(port["name"], label + " name")
    _choice(port["domain"], DOMAINS, label + " domain")
    _choice(port["precision"], PRECISIONS, label + " precision")
    _choice(port["geometry"], GEOMETRIES, label + " geometry")
    return port


def _ports(value: object, label: str) -> list[dict]:
    require(type(value) is list, label + " must be a list")
    ports = [_port(item, label) for item in value]
    names = [item["name"] for item in ports]
    require(len(names) == len(set(names)), label + " port names must be unique")
    return ports


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is a P065 typed render-graph fixture."""
    exact_keys(document, DOCUMENT_KEYS, "render graph")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P065")
    require(document["mapId"] == MAP_ID, "mapId must be s23-typed-render-graph-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "render graph needs the P065 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    validation = exact_keys(document["validation"], VALIDATION_KEYS, "validation")
    require(validation["stage"] == STAGE, "validation stage must be before-allocation")
    _bool(validation["framesProcessed"], "framesProcessed")
    _bool(validation["allocated"], "allocated")
    nodes = document["nodes"]
    require(type(nodes) is list and nodes, "nodes must be a non-empty list")
    seen_nodes: set[str] = set()
    for index, raw in enumerate(nodes):
        node = exact_keys(raw, NODE_KEYS, f"node {index}")
        node_id = _token(node["id"], f"node {index} id")
        require(node_id not in seen_nodes, "duplicate node id: " + node_id)
        seen_nodes.add(node_id)
        inputs = _ports(node["inputs"], f"node {node_id} inputs")
        outputs = _ports(node["outputs"], f"node {node_id} outputs")
        names = [item["name"] for item in inputs] + [item["name"] for item in outputs]
        require(len(names) == len(set(names)), f"node {node_id} port names overlap")
        require(names, f"node {node_id} needs at least one port")
        precision = _choice(node["precisionRequirement"], PRECISIONS, f"node {node_id} precision")
        for port in inputs + outputs:
            require(
                port["precision"] == precision,
                f"node {node_id} port {port['name']} precision must match the requirement",
            )
        _halo(node["halo"], f"node {node_id} halo")
        _choice(node["temporal"], TEMPORALS, f"node {node_id} temporal")
        deterministic = _bool(node["deterministic"], f"node {node_id} deterministic")
        parameters = _unique_tokens(node["parameters"], None, f"node {node_id} parameters")
        if deterministic:
            require(parameters, f"node {node_id} deterministic parameters must be non-empty")
        _unique_tokens(node["alters"], ALTERS, f"node {node_id} alters")
    edges = document["edges"]
    require(type(edges) is list, "edges must be a list")
    seen_edges: set[str] = set()
    index_by_id = {node["id"]: node for node in nodes}
    for index, raw in enumerate(edges):
        edge = exact_keys(raw, EDGE_KEYS, f"edge {index}")
        edge_id = _token(edge["id"], f"edge {index} id")
        require(edge_id not in seen_edges, "duplicate edge id: " + edge_id)
        seen_edges.add(edge_id)
        _bind_port(index_by_id, edge["fromNode"], edge["fromPort"], "outputs", edge_id)
        _bind_port(index_by_id, edge["toNode"], edge["toPort"], "inputs", edge_id)


def _bind_port(nodes: dict, node_id: object, port_name: object, side: str, edge_id: str) -> dict:
    require(isinstance(node_id, str) and node_id in nodes, f"edge {edge_id} references an unknown node")
    require(isinstance(port_name, str) and port_name, f"edge {edge_id} port must be a string")
    ports = nodes[node_id][side]
    match = [item for item in ports if item["name"] == port_name]
    require(len(match) == 1, f"edge {edge_id} {side[:-1]} {node_id}.{port_name} is missing")
    return match[0]


def _node(document: dict, node_id: str) -> dict:
    return next(item for item in document["nodes"] if item["id"] == node_id)


def _endpoint(document: dict, node_id: str, port_name: str, side: str) -> dict:
    return _bind_port({node["id"]: node for node in document["nodes"]}, node_id, port_name, side, "lookup")


def edge_faults(document: dict, edge: dict) -> list[str]:
    """Return typed compatibility faults for one edge. Untyped is never a match."""
    source = _endpoint(document, edge["fromNode"], edge["fromPort"], "outputs")
    sink = _endpoint(document, edge["toNode"], edge["toPort"], "inputs")
    producer = _node(document, edge["fromNode"])
    consumer = _node(document, edge["toNode"])
    faults: list[str] = []
    untyped = (
        source["domain"] == "untyped"
        or sink["domain"] == "untyped"
        or source["precision"] == "untyped"
        or sink["precision"] == "untyped"
        or producer["precisionRequirement"] == "untyped"
        or consumer["precisionRequirement"] == "untyped"
    )
    if untyped:
        faults.append("untyped-port")
    if source["domain"] != sink["domain"] or source["domain"] not in TYPED_DOMAINS:
        faults.append("domain-mismatch")
    if source["precision"] != sink["precision"] or source["precision"] not in TYPED_PRECISIONS:
        faults.append("precision-mismatch")
    if source["geometry"] != sink["geometry"]:
        faults.append("geometry-mismatch")
    if Decimal(producer["halo"]) < Decimal(consumer["halo"]):
        faults.append("halo-short")
    if producer["temporal"] != consumer["temporal"]:
        faults.append("temporal-mismatch")
    if not producer["deterministic"] or not consumer["deterministic"]:
        faults.append("nondeterministic")
    return faults


def _inventory(document: dict, statuses: dict[str, str]) -> list[str]:
    preserved: list[str] = []
    for node in document["nodes"]:
        alters = ",".join(node["alters"]) if node["alters"] else "none"
        parameters = ",".join(node["parameters"]) if node["parameters"] else "none"
        preserved.append(
            f"node:{node['id']}:precision={node['precisionRequirement']}:halo={node['halo']}:"
            f"temporal={node['temporal']}:deterministic={str(node['deterministic']).lower()}:"
            f"parameters={parameters}:alters={alters}"
        )
        for side in ("inputs", "outputs"):
            for port in node[side]:
                preserved.append(
                    f"port:{node['id']}:{port['name']}:domain={port['domain']}:"
                    f"precision={port['precision']}:geometry={port['geometry']}"
                )
    for edge in document["edges"]:
        status = statuses[edge["id"]]
        preserved.append(
            f"edge:{edge['id']}:{edge['fromNode']}.{edge['fromPort']}->"
            f"{edge['toNode']}.{edge['toPort']}:status={status}"
        )
    validation = document["validation"]
    preserved.append("stage:" + validation["stage"])
    preserved.append("frames-processed:" + str(validation["framesProcessed"]).lower())
    preserved.append("allocated:" + str(validation["allocated"]).lower())
    return preserved


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS, "unexpected decision")
    require(decision not in _FORBIDDEN, "P065 must not decide qualified or allowed")
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
    """Reject incompatible typed edges before allocation, and reject the mutant.

    ``path`` ``untyped-handles`` is the deliberate mutant. It does not erase
    domain, precision, or geometry checks. Both fixture failures stay rejected
    and the node inventory stays in ``preservedResults``. The decision is never
    ``qualified`` or ``allowed``.
    """
    validate_document(document)
    require(path in PATHS, "path must be typed or untyped-handles")
    reasons = [ORACLE, "precision and domain descriptors are checked before allocation"]
    questions = [
        "host fixture is not a physical S23 measurement",
        HOST_LIMIT,
        "validation stage is before-allocation",
    ]
    statuses: dict[str, str] = {}
    rejected: list[str] = []
    for edge in document["edges"]:
        faults = edge_faults(document, edge)
        if faults:
            statuses[edge["id"]] = "rejected"
            rejected.append(edge["id"])
            reasons.append(f"{edge['id']} rejected: " + ", ".join(faults))
        else:
            statuses[edge["id"]] = "compatible"
            reasons.append(f"{edge['id']} is a typed compatible edge")
    if set(_INVALID_EDGES).issubset(set(rejected)):
        reasons.append("both invalid connections were rejected before processing frames")
    mutant = path == MUTANT_PATH
    if mutant:
        rejected.append("untyped-texture-handles")
        reasons.append(MUTANT)
        reasons.append("untyped texture handles do not make incompatible domains connect")
        questions.append("mutant untyped handles were rejected before allocation")
    validation = document["validation"]
    if validation["framesProcessed"] or validation["allocated"]:
        rejected.append("processed-before-validation")
        reasons.append("frames or allocation were marked before edge validation")
    else:
        reasons.append("no frames were processed and no resources were allocated")
    reasons.append(HOST_LIMIT)
    preserved = _inventory(document, statuses)
    if rejected:
        return _result("rejected", reasons, rejected, preserved, questions)
    if not document["edges"]:
        questions.append("graph has nodes but no edges to validate")
        return _result("withheld", reasons, rejected, preserved, questions)
    reasons.append("typed edges are compatible and were checked before allocation")
    return _result("edges_validated", reasons, rejected, preserved, questions)
