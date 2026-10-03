"""TC-P009-02 camera-route inventory: advertised but unusable route.

Advertisement is historical evidence only. Configuration without samples,
a non-none failure mode, or an independent physical open is not qualification.
Missing focal length stays unknown; no lens is invented.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P009-02"
FAILURE_MODES = ("none", "session_rejected", "startup_timeout", "stream_mismatch")
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
    """Qualify a single route only from advertisement, configuration, and samples."""
    route, failure_mode = _payload(payload)
    logical = route["logicalId"]
    physical = route["physicalId"]
    identity = _route_id(route)
    claim = f"{logical}/{physical}/{failure_mode}"
    reasons: list[str] = []
    rejected: list[str] = []
    preserved: list[str] = []
    open_questions: list[str] = []

    if route["focalMm"] is None:
        open_questions.append("focal unknown")
    if physical is not None and physical not in route["publicCameraIds"]:
        reasons.append(f"{physical} addressed via {logical}")

    advertised = route["advertised"]
    configured = route["configured"]
    samples = route["samples"]
    independent = route["openPhysicalIndependently"]
    unusable = (advertised and not configured) or samples == 0 or failure_mode != "none"
    qualified = advertised and configured and samples > 0 and failure_mode == "none"

    if independent:
        decision = "rejected"
        rejected.append(identity)
        reasons.append(f"{identity} openPhysicalIndependently is rejected")
        if unusable:
            rejected.append(claim)
        if advertised:
            preserved.append(f"advertised:{logical}")
    elif qualified:
        decision = "qualified"
        preserved.append(identity)
        reasons.append(f"{identity} qualified")
    elif unusable:
        decision = "advertised_only"
        rejected.append(claim)
        preserved.append(f"advertised:{logical}")
        reasons.append(f"qualification denied for {claim}")
    else:
        decision = "rejected"
        rejected.append(identity)
        reasons.append(f"{identity} is not advertised for qualification")

    if independent or unusable:
        if decision in {"qualified", "allowed"}:
            raise ValueError("unusable or independent route must not be qualified or allowed")
    if decision != "allowed" and not reasons:
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


def _payload(payload: object) -> tuple[dict, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != {"route", "failureMode"}:
        raise ValueError("payload keys must be route and failureMode")
    failure = payload["failureMode"]
    if failure not in FAILURE_MODES:
        raise ValueError(
            "failureMode must be none, session_rejected, startup_timeout, or stream_mismatch"
        )
    route = payload["route"]
    return _route(route), failure


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
