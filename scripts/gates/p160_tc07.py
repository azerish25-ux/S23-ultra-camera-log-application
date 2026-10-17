"""TC-P160-07 Advanced model cost regression.

Host reference. A larger model that improves one artifact but exceeds memory
or time must report the quality-cost tradeoff and keep the stable baseline
until the adoption gate passes. A leaderboard position alone cannot justify
replacement.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P160-07",
    "phase": "P160",
    "workstream": 20,
    "name": "Advanced model cost regression",
    "intervention": "Adopt a larger research model that improves one artifact but exceeds practical memory or time budgets.",
    "expected": "Report the quality-cost tradeoff and retain the stable baseline until the adoption gate passes.",
    "negative": "A leaderboard position alone cannot justify replacement.",
    "repeat": "Repeat difficult-scene quality, sustained device load, and deferred job interruption.",
}

NEGATIVE_TOKEN = "leaderboard-alone-justifies-replacement"
BASELINE_DROPPED = "stable-baseline-not-retained"
TRADEOFF_OMITTED = "quality-cost-tradeoff-not-reported"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "records",
    "maintenanceNote",
    "only_passes",
    "largerModel",
    "artifactImproved",
    "exceedsMemory",
    "exceedsTime",
    "tradeoffReported",
    "baselineRetained",
    "adoptionGatePassed",
    "leaderboardAlone",
    "replaced",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p160_close_the_programme_with_a_reproducible_evidence_archive.py"
    spec = importlib.util.spec_from_file_location("p160_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _cost_faults(payload: dict) -> dict:
    larger = _GATE.require_bool(payload["largerModel"], "largerModel")
    improved = _GATE.require_bool(payload["artifactImproved"], "artifactImproved")
    memory = _GATE.require_bool(payload["exceedsMemory"], "exceedsMemory")
    time_budget = _GATE.require_bool(payload["exceedsTime"], "exceedsTime")
    tradeoff = _GATE.require_bool(payload["tradeoffReported"], "tradeoffReported")
    baseline = _GATE.require_bool(payload["baselineRetained"], "baselineRetained")
    gate_passed = _GATE.require_bool(payload["adoptionGatePassed"], "adoptionGatePassed")
    leaderboard = _GATE.require_bool(payload["leaderboardAlone"], "leaderboardAlone")
    replaced = _GATE.require_bool(payload["replaced"], "replaced")
    faults: list[str] = []
    over_budget = memory or time_budget
    if larger and over_budget and not tradeoff:
        faults.append(TRADEOFF_OMITTED)
    if larger and not gate_passed and not baseline:
        faults.append(BASELINE_DROPPED)
    if larger and leaderboard and (replaced or not baseline):
        faults.append(NEGATIVE_TOKEN)
    if larger and replaced and not gate_passed:
        faults.append(BASELINE_DROPPED)
    return {
        "faults": faults,
        "observed": {
            "largerModel": larger,
            "artifactImproved": improved,
            "exceedsMemory": memory,
            "exceedsTime": time_budget,
            "overBudget": over_budget,
            "tradeoffReported": tradeoff,
            "baselineRetained": baseline,
            "adoptionGatePassed": gate_passed,
            "leaderboardAlone": leaderboard,
            "replaced": replaced,
        },
    }


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    judged = _cost_faults(payload)
    faults = list(bundle["faults"])
    faults.extend(judged["faults"])
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [judged["observed"]],
        {
            NEGATIVE_TOKEN: CASE["negative"],
            BASELINE_DROPPED: CASE["expected"],
            TRADEOFF_OMITTED: CASE["expected"],
        },
    )
