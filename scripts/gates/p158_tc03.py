"""TC-P158-03 Unexplored reversible alternative.

Host reference. One failed P010 route does not prove every ten-bit encoding
impossible. The broader capture goal stays open while a reversible public
route is still untested.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P158-03",
    "phase": "P158",
    "workstream": 20,
    "name": "Unexplored reversible alternative",
    "intervention": "Fail one codec or camera interface while another public route remains untested.",
    "expected": "Evaluate plausible reversible alternatives before declaring the broader capture goal blocked.",
    "negative": "One failed P010 route must not prove all ten-bit encoding impossible.",
    "repeat": "Repeat surface input, reduced geometry, deferred processing, and scheduling changes.",
}

NEGATIVE_TOKEN = "failed-p010-does-not-prove-ten-bit-impossible"
UNTESTED_REVERSIBLE = "untested-reversible-alternative"
ROUTE_KEYS = frozenset({"id", "tested", "failed", "reversible", "tenBit"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "experimentLabel",
    "captureKind",
    "presentedAs",
    "labelsMergeExplicitly",
    "claimsExtraStops",
    "guaranteedEveryScene",
    "motionAlignment",
    "ghosting",
    "alignmentError",
    "motionArtifacts",
    "retainedHighlights",
    "sourceSampling",
    "motionAssumptions",
    "exposureDifferences",
    "mergeArtifacts",
    "outputLineage",
    "singleExposureBaseline",
    "alternativeRawModes",
    "synchronization",
    "claimsSensorDerivedLog",
    "routes",
    "goalBlocked",
    "tenBitDeclaredImpossible",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p158_explore_advanced_capture_research_independently.py"
    spec = importlib.util.spec_from_file_location("p158_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _routes(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list) and bool(value), "routes must be a non-empty list")
    _GATE.require(len(value) <= _GATE.MAX_LIST, "routes length is invalid")
    routes = []
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict), f"routes[{index}] must be an object")
        _GATE.require(set(item) == ROUTE_KEYS, f"routes[{index}] keys are invalid")
        tested = _GATE.require_bool(item["tested"], f"routes[{index}].tested")
        failed = _GATE.require_bool(item["failed"], f"routes[{index}].failed")
        _GATE.require(not failed or tested, f"routes[{index}] cannot fail before it is tested")
        routes.append({
            "id": _GATE.require_text(item["id"], f"routes[{index}].id"),
            "tested": tested,
            "failed": failed,
            "reversible": _GATE.require_bool(item["reversible"], f"routes[{index}].reversible"),
            "tenBit": _GATE.require_bool(item["tenBit"], f"routes[{index}].tenBit"),
        })
    ids = [route["id"] for route in routes]
    _GATE.require(len(ids) == len(set(ids)), "route ids must be unique")
    return routes


def _route_faults(routes: list[dict], goal_blocked: bool, ten_bit_impossible: bool) -> list[str]:
    faults: list[str] = []
    p010_failed = any(route["id"].lower() == "p010" and route["failed"] for route in routes)
    if p010_failed and ten_bit_impossible:
        faults.append(NEGATIVE_TOKEN)
    if goal_blocked and any(route["reversible"] and not route["tested"] for route in routes):
        faults.append(UNTESTED_REVERSIBLE)
    return faults


def case_payload(**overrides):
    payload = _GATE.core_payload()
    payload.update({
        "repeat": "surface-input",
        "routes": [
            {"id": "p010", "tested": True, "failed": True, "reversible": True, "tenBit": True},
            {"id": "surface-input", "tested": True, "failed": False, "reversible": True, "tenBit": True},
        ],
        "goalBlocked": False,
        "tenBitDeclaredImpossible": False,
    })
    payload.update(overrides)
    return payload


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    routes = _routes(payload["routes"])
    goal_blocked = _GATE.require_bool(payload["goalBlocked"], "goalBlocked")
    ten_bit_impossible = _GATE.require_bool(payload["tenBitDeclaredImpossible"], "tenBitDeclaredImpossible")
    faults = list(bundle["faults"])
    faults.extend(_route_faults(routes, goal_blocked, ten_bit_impossible))
    extra = [{
        "routeIds": [route["id"] for route in routes],
        "goalBlocked": goal_blocked,
        "tenBitDeclaredImpossible": ten_bit_impossible,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            UNTESTED_REVERSIBLE: CASE["expected"],
        },
    )
