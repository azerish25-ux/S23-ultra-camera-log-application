#!/usr/bin/env python3
"""P009 camera-route inventory and routing contract.

Route identity is the logical owner plus any requested physical target.
A physical member that is not a public camera id is not opened on its own.
Null focal metadata stays "unknown". Per-property query errors are kept.
This host module does not open a physical Galaxy S23.
"""

from __future__ import annotations

import math
from typing import Any


IMPLEMENTATION_BASE = "fffd5c9a63cb732e103052acae29ae0c251585cc"
INVENTORY_ID = "s23-route-inventory-fixture"
PUBLIC_CAMERA_IDS = ["0", "1"]
INVENTORY_KEYS = {
    "schemaVersion",
    "phase",
    "inventoryId",
    "implementationBaseRevision",
    "publicCameraIds",
    "routes",
}
ROUTE_KEYS = {
    "logicalId",
    "physicalId",
    "role",
    "focalMm",
    "orientation",
    "queryErrors",
    "openMode",
    "advertised",
}
ROLES = {"logical_rear", "physical_member", "logical_front"}
ORIENTATIONS = {0, 90, 180, 270}
PLAN_KEYS = ("logicalId", "physicalId", "openId", "focal", "errors")
ASSESS_KEYS = (
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
INDEPENDENT_CLAIM = "independent-physical-open"

# Oracle routes that the fixture must contain. Extra routes may follow the
# same field rules; these three may not be dropped or rewritten.
_REQUIRED_ROUTES = (
    {
        "logicalId": "0",
        "physicalId": None,
        "role": "logical_rear",
        "focalMm": 6.7,
        "orientation": 90,
        "queryErrors": {},
        "openMode": "logical_owner",
        "advertised": True,
    },
    {
        "logicalId": "0",
        "physicalId": "2",
        "role": "physical_member",
        "focalMm": None,
        "orientation": None,
        "queryErrors": {},
        "openMode": "logical_owner",
        "advertised": True,
    },
    {
        "logicalId": "1",
        "physicalId": None,
        "role": "logical_front",
        "focalMm": None,
        "orientation": None,
        "queryErrors": {"focal": "missing"},
        "openMode": "logical_owner",
        "advertised": True,
    },
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _exact_keys(value: dict, required: set[str], context: str) -> None:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))


def _finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float) and not math.isfinite(value):
        return False
    return True


def _query_errors(value: object, context: str) -> dict[str, str]:
    require(isinstance(value, dict), context + " queryErrors must be an object")
    errors: dict[str, str] = {}
    for key, detail in value.items():
        require(isinstance(key, str) and bool(key), context + " queryErrors keys must be non-empty strings")
        require(
            isinstance(detail, str) and bool(detail),
            context + " queryErrors values must be non-empty strings",
        )
        errors[key] = detail
    return errors


def _check_route(route: object, index: int, public_ids: list[str]) -> dict[str, Any]:
    context = f"routes[{index}]"
    require(isinstance(route, dict), context + " must be an object")
    _exact_keys(route, ROUTE_KEYS, context)
    logical = route["logicalId"]
    require(isinstance(logical, str) and bool(logical), context + " logicalId must be a non-empty string")
    require(logical in public_ids, context + " logicalId must be a public camera id")
    physical = route["physicalId"]
    if physical is not None:
        require(
            isinstance(physical, str) and bool(physical),
            context + " physicalId must be a non-empty string or null",
        )
    role = route["role"]
    require(role in ROLES, context + " role is not a known route role")
    if role == "physical_member":
        require(physical is not None, context + " physical_member requires physicalId")
    else:
        require(physical is None, context + " logical route must not set physicalId")
    focal = route["focalMm"]
    require(focal is None or _finite_number(focal), context + " focalMm must be a finite number or null")
    orientation = route["orientation"]
    require(
        orientation is None or (type(orientation) is int and orientation in ORIENTATIONS),
        context + " orientation must be null or 0, 90, 180, or 270",
    )
    errors = _query_errors(route["queryErrors"], context)
    require(route["openMode"] == "logical_owner", context + " openMode must be logical_owner")
    require(type(route["advertised"]) is bool and route["advertised"] is True, context + " advertised must be true")
    checked = dict(route)
    checked["queryErrors"] = errors
    return checked


def _same_route(route: dict, expected: dict) -> bool:
    if route["logicalId"] != expected["logicalId"]:
        return False
    if route["physicalId"] != expected["physicalId"]:
        return False
    if route["role"] != expected["role"]:
        return False
    if route["focalMm"] != expected["focalMm"]:
        return False
    if route["orientation"] != expected["orientation"]:
        return False
    if route["queryErrors"] != expected["queryErrors"]:
        return False
    if route["openMode"] != expected["openMode"]:
        return False
    if route["advertised"] is not expected["advertised"]:
        return False
    return True


def validate_inventory(inv: dict) -> None:
    """Raise ValueError unless inv is the P009 route-inventory fixture.

    Physical member "2" stays off publicCameraIds. Null focal and per-property
    query errors are retained. openMode is logical_owner only.
    """
    _exact_keys(inv, INVENTORY_KEYS, "inventory")
    require(type(inv["schemaVersion"]) is int and inv["schemaVersion"] == 1, "Unsupported inventory schema")
    require(inv["phase"] == "P009", "Inventory phase must be P009")
    require(inv["inventoryId"] == INVENTORY_ID, "Unexpected inventory id")
    require(inv["implementationBaseRevision"] == IMPLEMENTATION_BASE, "Unexpected implementation base revision")
    public = inv["publicCameraIds"]
    require(public == PUBLIC_CAMERA_IDS, "publicCameraIds must be [\"0\", \"1\"]")
    require("2" not in public, "physical member 2 is not a public camera id")
    routes = inv["routes"]
    require(isinstance(routes, list) and len(routes) >= 3, "routes must list at least 3 entries")
    checked: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None]] = set()
    for index, route in enumerate(routes):
        item = _check_route(route, index, public)
        identity = (item["logicalId"], item["physicalId"])
        require(identity not in seen, "duplicate route identity " + repr(identity))
        seen.add(identity)
        checked.append(item)
    for expected in _REQUIRED_ROUTES:
        require(
            any(_same_route(item, expected) for item in checked),
            "inventory is missing required route "
            + expected["role"]
            + " logical "
            + expected["logicalId"],
        )
    member = next(item for item in checked if item["physicalId"] == "2")
    require(member["logicalId"] == "0", "physical member 2 must keep logical owner 0")
    require(member["focalMm"] is None, "physical member 2 focal metadata must stay null")


def plan(inv: dict) -> list[dict]:
    """Plan every route. openId is the logical owner, never the physical id.

    focalMm null becomes focal "unknown". A numeric focalMm is copied.
    queryErrors are copied onto errors. A route with errors is not dropped,
    and its error does not drop any other route.
    """
    validate_inventory(inv)
    planned: list[dict] = []
    for route in inv["routes"]:
        focal_mm = route["focalMm"]
        focal: object = "unknown" if focal_mm is None else focal_mm
        planned.append(
            {
                "logicalId": route["logicalId"],
                "physicalId": route["physicalId"],
                "openId": route["logicalId"],
                "focal": focal,
                "errors": dict(route["queryErrors"]),
            }
        )
    require(len(planned) == len(inv["routes"]), "plan dropped a route")
    for item in planned:
        require(tuple(item) == PLAN_KEYS, "plan result keys drifted")
        require(item["openId"] == item["logicalId"], "openId must equal logicalId")
        require(item["focal"] == "unknown" or _finite_number(item["focal"]), "focal must be a number or unknown")
    return planned


def _unknown_focal(route: dict) -> bool:
    """True when this route has no numeric focal to display."""
    if "focalMm" in route:
        return route["focalMm"] is None
    if route.get("focal") == "unknown":
        return True
    errors = route.get("queryErrors")
    if not isinstance(errors, dict):
        errors = route.get("errors")
    return isinstance(errors, dict) and "focal" in errors


def assess_open_mode(route: dict) -> dict:
    """Reject opening a physical member as its own camera.

    ``openMode`` ``independent_physical``, or a truthy ``openPhysicalIndependently``
    flag, yields decision ``rejected`` and rejectedClaims
    ``["independent-physical-open"]``. Otherwise decision is ``logical_owner``
    and preservedResults is ``[logicalId]``. Null focal stays an open question
    and is not replaced with a number.
    """
    require(isinstance(route, dict), "route must be an object")
    logical_id = route["logicalId"]
    require(isinstance(logical_id, str) and bool(logical_id), "logicalId must be a non-empty string")
    independent = route["openMode"] == "independent_physical" or bool(route.get("openPhysicalIndependently"))
    open_questions = ["focal unknown"] if _unknown_focal(route) else []
    preserved = [logical_id]
    if independent:
        result = {
            "decision": "rejected",
            "reasons": ["independent physical open is rejected; use the logical owner"],
            "rejectedClaims": [INDEPENDENT_CLAIM],
            "preservedResults": preserved,
            "openQuestions": open_questions,
        }
    else:
        physical = route.get("physicalId")
        if isinstance(physical, str) and physical:
            reason = f"{physical} addressed via {logical_id}"
        else:
            reason = f"open through logical owner {logical_id}"
        result = {
            "decision": "logical_owner",
            "reasons": [reason],
            "rejectedClaims": [],
            "preservedResults": preserved,
            "openQuestions": open_questions,
        }
    require(tuple(result) == ASSESS_KEYS, "assess result keys drifted")
    return result
