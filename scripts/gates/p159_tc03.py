"""TC-P159-03 Unexplored reversible alternative.

Host reference. One failed codec or camera interface does not block the
broader capture goal while another public route is still untested. A failed
P010 route does not prove that every ten-bit encoding is impossible.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P159-03",
    "phase": "P159",
    "workstream": 20,
    "name": "Unexplored reversible alternative",
    "intervention": "Fail one codec or camera interface while another public route remains untested.",
    "expected": "Evaluate plausible reversible alternatives before declaring the broader capture goal blocked.",
    "negative": "One failed P010 route must not prove all ten-bit encoding impossible.",
    "repeat": "Repeat surface input, reduced geometry, deferred processing, and scheduling changes.",
}

NEGATIVE_TOKEN = "failed-p010-proves-ten-bit-impossible"
ALTERNATIVES_NOT_EVALUATED = "reversible-alternatives-not-evaluated"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "baseline_stable",
    "stabilityNoted",
    "baselineRank",
    "candidates",
    "routes",
    "declaredBlocked",
    "alternativesEvaluated",
)
ROUTE_KEYS = {"id", "public", "tested", "failed"}


def _load_gate():
    path = Path(__file__).resolve().parent / "p159_explore_higher_quality_computational_optics.py"
    spec = importlib.util.spec_from_file_location("p159_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_routes(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list) and bool(value), "routes must be a non-empty list")
    routes = []
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict), f"routes[{index}] must be an object")
        _GATE.require(set(item) == ROUTE_KEYS, f"routes[{index}] keys are invalid")
        route_id = _GATE.require_text(item["id"], f"routes[{index}].id")
        _GATE.require(route_id in _GATE.ROUTE_IDS, f"routes[{index}].id is not recognized")
        tested = _GATE.require_bool(item["tested"], f"routes[{index}].tested")
        failed = _GATE.require_bool(item["failed"], f"routes[{index}].failed")
        _GATE.require(not failed or tested, f"routes[{index}] cannot fail before it is tested")
        routes.append({
            "id": route_id,
            "public": _GATE.require_bool(item["public"], f"routes[{index}].public"),
            "tested": tested,
            "failed": failed,
        })
    ids = [route["id"] for route in routes]
    _GATE.require(len(ids) == len(set(ids)), "route ids must be unique")
    return routes


def _route_faults(routes: list[dict], declared_blocked: bool, alternatives_evaluated: bool) -> list[str]:
    faults: list[str] = []
    untested_public = [route for route in routes if route["public"] and not route["tested"]]
    p010_failed = any(route["id"] == "p010" and route["failed"] for route in routes)
    if declared_blocked and (not alternatives_evaluated or bool(untested_public)):
        faults.append(ALTERNATIVES_NOT_EVALUATED)
    if p010_failed and declared_blocked and (bool(untested_public) or not alternatives_evaluated):
        faults.append(NEGATIVE_TOKEN)
    return _GATE.dedupe(faults)


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    routes = _parse_routes(payload["routes"])
    declared = _GATE.require_bool(payload["declaredBlocked"], "declaredBlocked")
    evaluated = _GATE.require_bool(payload["alternativesEvaluated"], "alternativesEvaluated")
    faults = list(bundle["faults"])
    faults.extend(_route_faults(routes, declared, evaluated))
    extra = [{
        "declaredBlocked": declared,
        "alternativesEvaluated": evaluated,
        "routeIds": [route["id"] for route in routes],
        "untestedPublic": [route["id"] for route in routes if route["public"] and not route["tested"]],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            ALTERNATIVES_NOT_EVALUATED: CASE["expected"],
        },
    )
