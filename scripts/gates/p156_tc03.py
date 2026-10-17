"""TC-P156-03 Unexplored reversible alternative.

Host reference. One failed P010 route does not prove every ten-bit path
impossible. Declaring the broader capture goal blocked while another public
route is still untested, or while a tested route has not failed, is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P156-03",
    "phase": "P156",
    "workstream": 20,
    "name": "Unexplored reversible alternative",
    "intervention": "Fail one codec or camera interface while another public route remains untested.",
    "expected": "Evaluate plausible reversible alternatives before declaring the broader capture goal blocked.",
    "negative": "One failed P010 route must not prove all ten-bit encoding impossible.",
    "repeat": "Repeat surface input, reduced geometry, deferred processing, and scheduling changes.",
}

NEGATIVE_TOKEN = "failed-p010-proves-all-ten-bit-impossible"
GOAL_BLOCKED_EARLY = "goal-blocked-before-alternatives-evaluated"
ROUTE_KEYS = {"id", "kind", "tested", "failed"}
EXTRA_KEYS = {"routes", "goalDeclaredBlocked"}


def _load_gate():
    path = Path(__file__).resolve().parent / "p156_prepare_a_separate_firmware_risk_gate.py"
    spec = importlib.util.spec_from_file_location("p156_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_routes(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list) and bool(value), "routes must be a non-empty list")
    rows = []
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict), f"routes[{index}] must be an object")
        _GATE.require(set(item) == ROUTE_KEYS, f"routes[{index}] keys are invalid")
        tested = _GATE.require_bool(item["tested"], f"routes[{index}].tested")
        failed = _GATE.require_bool(item["failed"], f"routes[{index}].failed")
        _GATE.require(not (failed and not tested), f"routes[{index}] cannot fail before it is tested")
        rows.append({
            "id": _GATE.require_text(item["id"], f"routes[{index}].id"),
            "kind": _GATE.require_text(item["kind"], f"routes[{index}].kind"),
            "tested": tested,
            "failed": failed,
        })
    ids = [row["id"] for row in rows]
    _GATE.require(len(ids) == len(set(ids)), "route ids must be unique")
    return rows


def _route_faults(routes: list[dict], goal_declared_blocked: bool) -> list[str]:
    faults: list[str] = []
    if not goal_declared_blocked:
        return faults
    open_routes = [route for route in routes if not route["tested"] or not route["failed"]]
    if open_routes:
        faults.append(GOAL_BLOCKED_EARLY)
    p010_failed = any(route["kind"] == "p010" and route["tested"] and route["failed"] for route in routes)
    other_untested = any(route["kind"] != "p010" and not route["tested"] for route in routes)
    if p010_failed and other_untested:
        faults.append(NEGATIVE_TOKEN)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, EXTRA_KEYS)
    routes = _parse_routes(payload["routes"])
    blocked = _GATE.require_bool(payload["goalDeclaredBlocked"], "goalDeclaredBlocked")
    faults = list(bundle["faults"])
    faults.extend(_route_faults(routes, blocked))
    extra = [{
        "routeIds": [route["id"] for route in routes],
        "goalDeclaredBlocked": blocked,
        "untested": [route["id"] for route in routes if not route["tested"]],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            GOAL_BLOCKED_EARLY: CASE["expected"],
        },
    )
