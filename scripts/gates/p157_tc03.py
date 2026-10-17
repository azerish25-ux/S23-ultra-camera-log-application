"""TC-P157-03 Unexplored reversible alternative.

Host reference. One failed codec or camera interface does not block the
broader capture goal while a reversible public route is still untested.
One failed P010 route does not prove every ten-bit encoding impossible.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P157-03",
    "phase": "P157",
    "workstream": 20,
    "name": "Unexplored reversible alternative",
    "intervention": "Fail one codec or camera interface while another public route remains untested.",
    "expected": "Evaluate plausible reversible alternatives before declaring the broader capture goal blocked.",
    "negative": "One failed P010 route must not prove all ten-bit encoding impossible.",
    "repeat": "Repeat surface input, reduced geometry, deferred processing, and scheduling changes.",
}

NEGATIVE_TOKEN = "one-p010-failure-blocks-all-ten-bit"
UNTESTED_TOKEN = "reversible-alternative-not-evaluated"
OPEN_ALTERNATIVE_TOKEN = "broader-goal-blocked-despite-open-alternative"
ROUTE_IDS = ("p010", "surface-input", "reduced-geometry", "deferred-processing", "scheduling")
ROUTE_KEYS = {"id", "tested", "failed", "reversible", "tenBit"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "protocolKind",
    "deviceExperimentCompleted",
    "baselinePreserved",
    "checksum",
    "logId",
    "failureTriggers",
    "thermalSafeguardDisabled",
    "capabilityMetadataFalsified",
    "experiments",
    "routes",
    "broaderCaptureGoalBlocked",
    "tenBitDeclaredImpossible",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p157_design_instrumented_low_level_experiments.py"
    spec = importlib.util.spec_from_file_location("p157_gate_for_tc03", path)
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
        route_id = _GATE.require_text(item["id"], f"routes[{index}].id")
        _GATE.require(route_id in ROUTE_IDS, f"routes[{index}].id is not recognized")
        tested = _GATE.require_bool(item["tested"], f"routes[{index}].tested")
        failed = _GATE.require_bool(item["failed"], f"routes[{index}].failed")
        _GATE.require(not failed or tested, f"routes[{index}] cannot fail before it is tested")
        rows.append({
            "id": route_id,
            "tested": tested,
            "failed": failed,
            "reversible": _GATE.require_bool(item["reversible"], f"routes[{index}].reversible"),
            "tenBit": _GATE.require_bool(item["tenBit"], f"routes[{index}].tenBit"),
        })
    ids = [row["id"] for row in rows]
    _GATE.require(len(ids) == len(set(ids)), "route ids must be unique")
    _GATE.require(set(ids) == set(ROUTE_IDS), "routes must include every public alternative")
    return rows


def _route_faults(routes: list[dict], goal_blocked: bool, ten_bit_impossible: bool) -> list[str]:
    faults: list[str] = []
    untested_reversible = [row for row in routes if row["reversible"] and not row["tested"]]
    open_success = [row for row in routes if row["reversible"] and row["tested"] and not row["failed"]]
    if goal_blocked and untested_reversible:
        faults.append(UNTESTED_TOKEN)
    if goal_blocked and open_success:
        faults.append(OPEN_ALTERNATIVE_TOKEN)
    failed_ten_bit = [row for row in routes if row["tenBit"] and row["tested"] and row["failed"]]
    untested_ten_bit = [row for row in routes if row["tenBit"] and not row["tested"]]
    if ten_bit_impossible and (len(failed_ten_bit) < 2 or untested_ten_bit):
        faults.append(NEGATIVE_TOKEN)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    routes = _parse_routes(payload["routes"])
    goal_blocked = _GATE.require_bool(payload["broaderCaptureGoalBlocked"], "broaderCaptureGoalBlocked")
    ten_bit_impossible = _GATE.require_bool(payload["tenBitDeclaredImpossible"], "tenBitDeclaredImpossible")
    faults = list(bundle["faults"])
    faults.extend(_route_faults(routes, goal_blocked, ten_bit_impossible))
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [{
            "broaderCaptureGoalBlocked": goal_blocked,
            "tenBitDeclaredImpossible": ten_bit_impossible,
            "failedRoutes": [row["id"] for row in routes if row["failed"]],
            "untestedRoutes": [row["id"] for row in routes if not row["tested"]],
        }],
        {
            NEGATIVE_TOKEN: CASE["negative"],
            UNTESTED_TOKEN: CASE["expected"],
            OPEN_ALTERNATIVE_TOKEN: CASE["expected"],
        },
    )
