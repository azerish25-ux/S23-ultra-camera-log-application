"""TC-P154-03 Unexplored reversible alternative.

Host reference. One failed P010 route does not prove that every ten-bit path
is impossible while another public route is untested or still passing. The
broader capture goal stays open until reversible alternatives are evaluated.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P154-03",
    "phase": "P154",
    "workstream": 20,
    "name": "Unexplored reversible alternative",
    "intervention": "Fail one codec or camera interface while another public route remains untested.",
    "expected": "Evaluate plausible reversible alternatives before declaring the broader capture goal blocked.",
    "negative": "One failed P010 route must not prove all ten-bit encoding impossible.",
    "repeat": "Repeat surface input, reduced geometry, deferred processing, and scheduling changes.",
}

NEGATIVE_TOKEN = "one-failed-p010-proves-all-ten-bit-impossible"
UNTESTED_ALTERNATIVE = "reversible-alternative-untested"
ROUTE_KEYS = {"id", "tested", "passed", "reversible", "tenBit"}
CASE_FIELDS = {
    "routes",
    "claimsAllTenBitImpossible",
    "declaresCaptureGoalBlocked",
}


def _load_gate():
    path = Path(__file__).resolve().parent / "p154_survey_public_firmware_and_hal_information.py"
    spec = importlib.util.spec_from_file_location("p154_gate_for_tc03", path)
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
        tested = _GATE.require_bool(item["tested"], f"routes[{index}].tested")
        passed = _GATE.require_bool(item["passed"], f"routes[{index}].passed")
        _GATE.require(not (passed and not tested), f"routes[{index}] cannot pass while untested")
        routes.append({
            "id": _GATE.require_text(item["id"], f"routes[{index}].id"),
            "tested": tested,
            "passed": passed,
            "reversible": _GATE.require_bool(item["reversible"], f"routes[{index}].reversible"),
            "tenBit": _GATE.require_bool(item["tenBit"], f"routes[{index}].tenBit"),
        })
    ids = [route["id"] for route in routes]
    _GATE.require(len(ids) == len(set(ids)), "route ids must be unique")
    return routes


def _route_faults(routes: list[dict], claims_impossible: bool, declares_blocked: bool) -> list[str]:
    faults: list[str] = []
    ten_bit = [route for route in routes if route["tenBit"]]
    all_ten_bit_failed = bool(ten_bit) and all(route["tested"] and not route["passed"] for route in ten_bit)
    if claims_impossible and not all_ten_bit_failed:
        faults.append(NEGATIVE_TOKEN)
    if declares_blocked and any(route["reversible"] and not route["tested"] for route in routes):
        faults.append(UNTESTED_ALTERNATIVE)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, CASE_FIELDS)
    routes = _parse_routes(payload["routes"])
    claims_impossible = _GATE.require_bool(payload["claimsAllTenBitImpossible"], "claimsAllTenBitImpossible")
    declares_blocked = _GATE.require_bool(payload["declaresCaptureGoalBlocked"], "declaresCaptureGoalBlocked")
    faults = list(bundle["faults"])
    faults.extend(_route_faults(routes, claims_impossible, declares_blocked))
    extra = [{
        "routes": routes,
        "claimsAllTenBitImpossible": claims_impossible,
        "declaresCaptureGoalBlocked": declares_blocked,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            UNTESTED_ALTERNATIVE: CASE["expected"],
        },
    )
