"""TC-P160-03 Unexplored reversible alternative.

Host reference. One failed codec or camera interface does not block the
broader capture goal while a reversible public route is still untested.
One failed P010 route does not prove that all ten-bit encoding is impossible.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P160-03",
    "phase": "P160",
    "workstream": 20,
    "name": "Unexplored reversible alternative",
    "intervention": "Fail one codec or camera interface while another public route remains untested.",
    "expected": "Evaluate plausible reversible alternatives before declaring the broader capture goal blocked.",
    "negative": "One failed P010 route must not prove all ten-bit encoding impossible.",
    "repeat": "Repeat surface input, reduced geometry, deferred processing, and scheduling changes.",
}

NEGATIVE_TOKEN = "failed-p010-proves-all-ten-bit-impossible"
ALTERNATIVE_UNEVALUATED = "reversible-alternative-not-evaluated"
ALTERNATIVE_KEYS = {"id", "reversible", "tested"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "records",
    "maintenanceNote",
    "only_passes",
    "failedRoute",
    "alternatives",
    "captureGoalBlocked",
    "claimsAllTenBitImpossible",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p160_close_the_programme_with_a_reproducible_evidence_archive.py"
    spec = importlib.util.spec_from_file_location("p160_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _is_p010(route: str) -> bool:
    return "p010" in route.casefold()


def _parse_alternatives(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list), "alternatives must be a list")
    rows = []
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict), f"alternatives[{index}] must be an object")
        _GATE.require(set(item) == ALTERNATIVE_KEYS, f"alternatives[{index}] keys are invalid")
        rows.append({
            "id": _GATE.require_text(item["id"], f"alternatives[{index}].id"),
            "reversible": _GATE.require_bool(item["reversible"], f"alternatives[{index}].reversible"),
            "tested": _GATE.require_bool(item["tested"], f"alternatives[{index}].tested"),
        })
    ids = [row["id"] for row in rows]
    _GATE.require(len(ids) == len(set(ids)), "alternative ids must be unique")
    return rows


def _route_faults(payload: dict) -> dict:
    failed = _GATE.require_text(payload["failedRoute"], "failedRoute")
    alternatives = _parse_alternatives(payload["alternatives"])
    blocked = _GATE.require_bool(payload["captureGoalBlocked"], "captureGoalBlocked")
    claims_impossible = _GATE.require_bool(payload["claimsAllTenBitImpossible"], "claimsAllTenBitImpossible")
    faults: list[str] = []
    reversible = [row for row in alternatives if row["reversible"]]
    untested = [row["id"] for row in reversible if not row["tested"]]
    if _is_p010(failed) and claims_impossible:
        faults.append(NEGATIVE_TOKEN)
    if blocked and (not reversible or untested):
        faults.append(ALTERNATIVE_UNEVALUATED)
    return {
        "faults": faults,
        "observed": {
            "failedRoute": failed,
            "p010": _is_p010(failed),
            "untestedReversible": untested,
            "captureGoalBlocked": blocked,
            "claimsAllTenBitImpossible": claims_impossible,
        },
    }


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    judged = _route_faults(payload)
    faults = list(bundle["faults"])
    faults.extend(judged["faults"])
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [judged["observed"]],
        {
            NEGATIVE_TOKEN: CASE["negative"],
            ALTERNATIVE_UNEVALUATED: CASE["expected"],
        },
    )
