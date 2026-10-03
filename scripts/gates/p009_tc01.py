"""TC-P009-01 camera-route inventory: partial characteristic failure.

A query error on one route must not erase readable routes. Physical members
that are not public camera ids are addressed through their logical owner.
Missing focal length stays unknown; no lens is invented.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P009-01"
FAILED_PROPERTIES = ("metadata", "timing", "dynamic_range", "codec")
_ROUTE_FIELDS = (
    "logicalId",
    "physicalId",
    "publicCameraIds",
    "focalMm",
    "queryError",
    "advertised",
    "configured",
    "samples",
    "openPhysicalIndependently",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Inventory routes. One failed property or route does not clear the rest."""
    routes, failed_property = _payload(payload)
    reasons: list[str] = []
    rejected: list[str] = [failed_property]
    preserved: list[str] = []
    open_questions: list[str] = []
    saw_error = False
    saw_unknown_focal = False

    for route in routes:
        identity = _route_id(route)
        if route["focalMm"] is None:
            saw_unknown_focal = True
        physical = route["physicalId"]
        if physical is not None and physical not in route["publicCameraIds"]:
            reasons.append(f"{physical} addressed via {route['logicalId']}")
        if route["queryError"] is not None:
            saw_error = True
            _append(rejected, identity)
        else:
            preserved.append(identity)
        if route["openPhysicalIndependently"]:
            # Mutant: opening the physical member as its own camera is rejected.
            _append(rejected, identity)
            reasons.append(f"{identity} openPhysicalIndependently is rejected")

    if saw_unknown_focal:
        open_questions.append("focal unknown")

    decision = "partial" if saw_error else "inventoried"
    if decision == "partial":
        reasons.append(
            f"failed property {failed_property} reported without clearing readable routes"
        )
    else:
        reasons.append("camera routes inventoried")
    if decision == "allowed":
        raise ValueError("TC-P009-01 must not decide allowed")
    if not reasons:
        raise ValueError("reasons required")

    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": open_questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result


def _payload(payload: object) -> tuple[list[dict], str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != {"routes", "failedProperty"}:
        raise ValueError("payload keys must be routes and failedProperty")
    failed = payload["failedProperty"]
    if failed not in FAILED_PROPERTIES:
        raise ValueError("failedProperty must be metadata, timing, dynamic_range, or codec")
    routes = payload["routes"]
    if not isinstance(routes, list):
        raise ValueError("routes must be a list")
    return [_route(item) for item in routes], failed


def _route(route: object) -> dict:
    if not isinstance(route, dict):
        raise ValueError("route must be a dict")
    if set(route) != set(_ROUTE_FIELDS):
        raise ValueError("invalid route fields")
    logical = route["logicalId"]
    if not isinstance(logical, str) or not logical:
        raise ValueError("logicalId must be a non-empty string")
    physical = route["physicalId"]
    if physical is not None and (not isinstance(physical, str) or not physical):
        raise ValueError("physicalId must be a non-empty string or null")
    public = route["publicCameraIds"]
    if not isinstance(public, list) or any(not isinstance(item, str) for item in public):
        raise ValueError("publicCameraIds must be a list of strings")
    focal = route["focalMm"]
    if focal is not None and not _number(focal):
        raise ValueError("focalMm must be a finite number or null")
    query = route["queryError"]
    if query is not None and (not isinstance(query, str) or not query):
        raise ValueError("queryError must be a non-empty string or null")
    for key in ("advertised", "configured", "openPhysicalIndependently"):
        if not isinstance(route[key], bool):
            raise ValueError(f"{key} must be a bool")
    samples = route["samples"]
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 0:
        raise ValueError("samples must be a non-negative int")
    return route


def _number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return isinstance(value, int) or math.isfinite(value)


def _route_id(route: dict) -> str:
    physical = route["physicalId"] if route["physicalId"] is not None else "logical"
    return f"{route['logicalId']}:{physical}"


def _append(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)
