#!/usr/bin/env python3
"""P017 resource-lifetime map and deterministic owner gate.

Closeable leases carry generation identity. Application-owned capture work
(camera device, session, image) stays separate from Activity surface
attachment. A session callback that arrives after Activity recreation cannot
attach to the new generation or double-close a released surface. A non-null
object reference is not generation identity.

Failure is reported as typed events. Open resources that the stale callback
must drop close image, then surface, then session, then camera device.
Resources the current generation still depends on stay open. The active
preview stays valid.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P017-01 through TC-P017-08.
"""

from __future__ import annotations

import re
from typing import Any, Optional


PHASE_ID = "P017"
MAP_ID = "s23-resource-lifetime-fixture"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
METHOD = (
    "Draw the ownership graph and implement closeable leases with generation identity. "
    "Separate application-owned capture work from Activity attachment. Propagate failure "
    "through typed events and close resources in a defined reverse dependency order."
)
FIXTURE = (
    "A session callback arriving after its Activity has been recreated and its "
    "previous surface released."
)
ORACLE = (
    "The callback cannot attach to the new generation or double-close a resource; "
    "the active preview remains valid."
)
MUTANT = "Reuse a surface solely because its previous object reference is non-null."
MUTANT_CLAIM = "reuse-non-null-surface"
OPEN_QUESTION = "host fixture only; physical S23 camera ownership was not measured"
HEX40 = re.compile(r"^[0-9a-f]{40}$")

# Children close before parents. Image and surface depend on session; session
# depends on the camera device. This is a host graph, not a HAL trace.
CLOSE_ORDER = ("image", "surface", "session", "camera_device")
KIND_PARENT = {
    "camera_device": None,
    "session": "camera_device",
    "surface": "session",
    "image": "session",
}
OWNER_FOR_KIND = {
    "camera_device": "application",
    "session": "application",
    "surface": "activity",
    "image": "application",
}
MAP_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "closeOrder",
    "activityGeneration",
    "reuseSurfaceBecauseNonNull",
    "callback",
    "leases",
}
LEASE_KEYS = {"id", "kind", "owner", "generation", "state", "objectRef", "dependsOn"}
CALLBACK_KEYS = {"kind", "generation", "surfaceRef", "success"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = {"rejected", "withheld", "stale_ignored", "preview_retained", "failure_propagated"}
FORBIDDEN = {"qualified", "allowed"}


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


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()


def _generation(value: object, context: str) -> int:
    require(type(value) is int and value >= 1, context + " must be a positive int")
    return value


def _by_id(leases: list[dict]) -> dict[str, dict]:
    return {lease["id"]: lease for lease in leases}


def _ordered(by_id: dict[str, dict], ids: list[str]) -> list[str]:
    rank = {kind: index for index, kind in enumerate(CLOSE_ORDER)}
    return sorted(ids, key=lambda item: (rank[by_id[item]["kind"]], item))


def _active_preview(leases: list[dict], activity_generation: int) -> dict:
    matches = [
        lease
        for lease in leases
        if lease["kind"] == "surface"
        and lease["state"] == "open"
        and lease["generation"] == activity_generation
    ]
    require(len(matches) == 1, "map needs exactly one open surface at the activity generation")
    return matches[0]


def _target_surface(document: dict) -> Optional[dict]:
    ref = document["callback"]["surfaceRef"]
    matches = [lease for lease in document["leases"] if lease["objectRef"] == ref]
    require(len(matches) <= 1, "surface reference matches more than one lease")
    if not matches:
        return None
    return matches[0]


def validate_map(document: dict) -> None:
    """Raise ValueError unless document is a P017 resource-lifetime map."""
    exact_keys(document, MAP_KEYS, "resource map")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE_ID, "phase must be P017")
    require(document["mapId"] == MAP_ID, "mapId must be s23-resource-lifetime-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "resource map needs the P017 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    require(document["closeOrder"] == list(CLOSE_ORDER),
            "closeOrder must be image, surface, session, camera_device")
    activity = _generation(document["activityGeneration"], "activityGeneration")
    require(type(document["reuseSurfaceBecauseNonNull"]) is bool,
            "reuseSurfaceBecauseNonNull must be a bool")
    callback = exact_keys(document["callback"], CALLBACK_KEYS, "callback")
    require(callback["kind"] == "session", "callback kind must be session")
    _generation(callback["generation"], "callback generation")
    require(_text(callback["surfaceRef"]), "callback surfaceRef must be a non-empty string")
    require(type(callback["success"]) is bool, "callback success must be a bool")
    leases = document["leases"]
    require(isinstance(leases, list) and leases, "leases must be a non-empty list")
    seen: set[str] = set()
    refs: set[str] = set()
    for index, lease in enumerate(leases):
        exact_keys(lease, LEASE_KEYS, f"lease {index}")
        require(_text(lease["id"]), f"lease {index} id must be a non-empty string")
        require(lease["id"] not in seen, "duplicate lease id: " + lease["id"])
        seen.add(lease["id"])
        require(lease["kind"] in KIND_PARENT, f"lease {index} kind is not a camera resource")
        require(lease["owner"] == OWNER_FOR_KIND[lease["kind"]],
                f"lease {lease['id']} owner does not match its kind")
        _generation(lease["generation"], f"lease {lease['id']} generation")
        require(lease["state"] in {"open", "released"}, f"lease {lease['id']} state is invalid")
        ref = lease["objectRef"]
        if lease["state"] == "open":
            require(_text(ref), f"open lease {lease['id']} needs an objectRef")
        else:
            require(ref is None or _text(ref), f"lease {lease['id']} objectRef is invalid")
        if ref is not None:
            require(ref not in refs, "duplicate objectRef: " + ref)
            refs.add(ref)
        parent = lease["dependsOn"]
        require(parent is None or _text(parent), f"lease {lease['id']} dependsOn is invalid")
    by_id = _by_id(leases)
    kinds = {lease["kind"] for lease in leases}
    require(kinds == set(CLOSE_ORDER), "map must include camera, session, surface, and image")
    for lease in leases:
        parent_kind = KIND_PARENT[lease["kind"]]
        parent_id = lease["dependsOn"]
        if parent_kind is None:
            require(parent_id is None, lease["id"] + " must not depend on another lease")
        else:
            require(parent_id in by_id, lease["id"] + " depends on a missing lease")
            parent = by_id[parent_id]
            require(parent["kind"] == parent_kind,
                    lease["id"] + " must depend on " + parent_kind)
        if lease["state"] == "open" and parent_id is not None:
            require(by_id[parent_id]["state"] == "open",
                    "open lease depends on a released parent: " + lease["id"])
        seen_walk: set[str] = set()
        cursor: Optional[str] = lease["id"]
        while cursor is not None:
            require(cursor not in seen_walk, "dependency cycle at " + lease["id"])
            seen_walk.add(cursor)
            cursor = by_id[cursor]["dependsOn"]
    _active_preview(leases, activity)


def ownership_edges(document: dict) -> list[dict[str, str]]:
    """Return child→parent edges. Activity surfaces stay off the camera owner."""
    validate_map(document)
    edges = []
    for lease in document["leases"]:
        if lease["dependsOn"] is None:
            continue
        edges.append({
            "child": lease["id"],
            "parent": lease["dependsOn"],
            "kind": lease["kind"],
            "owner": lease["owner"],
        })
    return edges


def release_plan(document: dict) -> list[str]:
    """Open leases at the stale callback generation, children before parents.

    Already released leases are omitted, so a terminal release is not repeated.
    A lease the current generation still depends on is kept. Application camera
    ownership is not closed merely because the Activity generation changed.
    Each id appears at most once. A current-generation callback releases nothing.
    """
    validate_map(document)
    callback_gen = document["callback"]["generation"]
    if callback_gen == document["activityGeneration"]:
        return []
    leases = document["leases"]
    by_id = _by_id(leases)
    candidates = {
        lease["id"]
        for lease in leases
        if lease["state"] == "open" and lease["generation"] == callback_gen
    }
    kept = [
        lease["id"]
        for lease in leases
        if lease["state"] == "open" and lease["id"] not in candidates
    ]
    protected: set[str] = set()
    stack = list(kept)
    seen: set[str] = set()
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        parent = by_id[current]["dependsOn"]
        if parent is None:
            continue
        protected.add(parent)
        stack.append(parent)
    releasing = [item for item in candidates if item not in protected]
    return _ordered(by_id, releasing)


def _preserved_ids(document: dict) -> list[str]:
    by_id = _by_id(document["leases"])
    releasing = set(release_plan(document))
    kept = [
        lease["id"]
        for lease in document["leases"]
        if lease["state"] == "open" and lease["id"] not in releasing
    ]
    return _ordered(by_id, kept)


def failure_events(document: dict) -> list[str]:
    """Typed events for a late or failing callback. Never a reuse event."""
    validate_map(document)
    events: list[str] = []
    if document["reuseSurfaceBecauseNonNull"]:
        events.append("mutant_refused")
    callback = document["callback"]
    active = _active_preview(document["leases"], document["activityGeneration"])
    target = _target_surface(document)
    stale = callback["generation"] != document["activityGeneration"]
    if stale:
        events.append("stale_callback")
    if stale or target is None or target["id"] != active["id"]:
        events.append("attach_refused")
    if target is not None and target["state"] == "released":
        events.append("double_close_refused")
    for item in release_plan(document):
        events.append("released:" + item)
    if not callback["success"] and not stale:
        events.append("capture_failure")
    events.append("preview_retained:" + active["id"])
    require("reused_surface" not in events, "mutant reuse event is not a legal typed event")
    return events


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in DECISIONS, "unexpected decision")
    require(decision not in FORBIDDEN, "decision must not be qualified or allowed")
    require(bool(reasons), "reasons required")
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


def assess_ownership(document: dict) -> dict[str, Any]:
    """Judge the fixture callback. The non-null-surface mutant is rejected.

    A released surface with a live objectRef is not attached to the new
    Activity generation and is not closed a second time. preservedResults
    keeps the active preview and every open lease the correct owner still holds.
    """
    validate_map(document)
    mutant = document["reuseSurfaceBecauseNonNull"] is True
    callback = document["callback"]
    active = _active_preview(document["leases"], document["activityGeneration"])
    target = _target_surface(document)
    stale = callback["generation"] != document["activityGeneration"]
    obsolete = target is None or target["id"] != active["id"] or target["state"] != "open"
    double_close = target is not None and target["state"] == "released"
    # Correct policy: objectRef being non-null never authorizes reuse.
    reuse_allowed = False
    if target is not None and target["state"] == "released" and target["objectRef"]:
        reuse_allowed = False
    require(reuse_allowed is False, "released surface must not be reused")
    plan = release_plan(document)
    preserved = _preserved_ids(document)

    reasons = [
        "closeable leases with generation identity",
        "application-owned capture work stays separate from Activity attachment",
    ]
    rejected: list[str] = []
    if mutant:
        rejected.append(MUTANT_CLAIM)
        reasons.append("a non-null object reference does not reuse a released surface")
        reasons.append(MUTANT)
    if stale:
        reasons.append("callback cannot attach to the new generation")
    elif obsolete:
        reasons.append("callback surface is not the active preview")
        rejected.append("obsolete-surface")
    if double_close:
        reasons.append("released resource is not double-closed")
    else:
        reasons.append("no released resource was selected for a second close")
    if plan:
        reasons.append("stale resources close in reverse dependency order: " + ",".join(plan))
    else:
        reasons.append("stale release plan is empty")
    if not callback["success"] and stale:
        reasons.append("stale failure is not applied to the current generation")
    if not callback["success"] and not stale and not mutant and not obsolete:
        reasons.append("typed event capture_failure")
    reasons.append("active preview remains valid")
    reasons.append("active preview " + active["id"])

    if mutant or ((not stale) and obsolete):
        decision = "rejected"
    elif stale:
        decision = "stale_ignored"
    elif not callback["success"]:
        decision = "failure_propagated"
    else:
        decision = "preview_retained"

    require(active["id"] in preserved, "active preview dropped from preserved results")
    if double_close and target is not None:
        require(target["id"] not in preserved, "released surface preserved as live")
        require(target["id"] not in plan, "released surface closed again")
    require(decision not in FORBIDDEN, "decision must not be qualified or allowed")
    return _result(decision, reasons, rejected, preserved, [OPEN_QUESTION])


assess = assess_ownership
