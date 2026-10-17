"""TC-P158-07 Advanced model cost regression.

Host reference. A larger research model that improves one artifact but exceeds
memory or time budgets must report the quality-cost tradeoff. The stable
baseline stays in place until the adoption gate passes. A leaderboard position
alone cannot justify replacement.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P158-07",
    "phase": "P158",
    "workstream": 20,
    "name": "Advanced model cost regression",
    "intervention": (
        "Adopt a larger research model that improves one artifact but exceeds practical "
        "memory or time budgets."
    ),
    "expected": "Report the quality-cost tradeoff and retain the stable baseline until the adoption gate passes.",
    "negative": "A leaderboard position alone cannot justify replacement.",
    "repeat": "Repeat difficult-scene quality, sustained device load, and deferred job interruption.",
}

NEGATIVE_TOKEN = "leaderboard-position-alone"
TRADEOFF_UNREPORTED = "quality-cost-tradeoff-not-reported"
BASELINE_REPLACED_EARLY = "baseline-replaced-before-adoption-gate"
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
    "leaderboardRank",
    "artifactDelta",
    "memoryBytes",
    "budgetMemoryBytes",
    "timeMs",
    "budgetTimeMs",
    "tradeoffReported",
    "adoptionGatePassed",
    "replacedBaseline",
    "justifiedByLeaderboardOnly",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p158_explore_advanced_capture_research_independently.py"
    spec = importlib.util.spec_from_file_location("p158_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _cost_faults(
    memory_bytes: int,
    budget_memory: int,
    time_ms: int | float,
    budget_time: int | float,
    tradeoff_reported: bool,
    adoption_gate_passed: bool,
    replaced_baseline: bool,
    leaderboard_only: bool,
) -> list[str]:
    faults: list[str] = []
    over_budget = memory_bytes > budget_memory or float(time_ms) > float(budget_time)
    if over_budget and not tradeoff_reported:
        faults.append(TRADEOFF_UNREPORTED)
    if replaced_baseline and not adoption_gate_passed:
        faults.append(BASELINE_REPLACED_EARLY)
    if leaderboard_only:
        faults.append(NEGATIVE_TOKEN)
    return faults


def case_payload(**overrides):
    payload = _GATE.core_payload()
    payload.update({
        "repeat": "difficult-scene-quality",
        "leaderboardRank": 3,
        "artifactDelta": 0.2,
        "memoryBytes": 8_000_000_000,
        "budgetMemoryBytes": 2_000_000_000,
        "timeMs": 4000,
        "budgetTimeMs": 500,
        "tradeoffReported": True,
        "adoptionGatePassed": False,
        "replacedBaseline": False,
        "justifiedByLeaderboardOnly": False,
    })
    payload.update(overrides)
    return payload


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    rank = _GATE.require_int(payload["leaderboardRank"], "leaderboardRank")
    _GATE.require(rank >= 1, "leaderboardRank must be >= 1")
    delta = _GATE.require_number(payload["artifactDelta"], "artifactDelta")
    memory_bytes = _GATE.require_int(payload["memoryBytes"], "memoryBytes")
    budget_memory = _GATE.require_int(payload["budgetMemoryBytes"], "budgetMemoryBytes")
    _GATE.require(memory_bytes >= 0 and budget_memory >= 0, "memory budgets must be >= 0")
    time_ms = _GATE.require_nonnegative(payload["timeMs"], "timeMs")
    budget_time = _GATE.require_nonnegative(payload["budgetTimeMs"], "budgetTimeMs")
    tradeoff = _GATE.require_bool(payload["tradeoffReported"], "tradeoffReported")
    gate_passed = _GATE.require_bool(payload["adoptionGatePassed"], "adoptionGatePassed")
    replaced = _GATE.require_bool(payload["replacedBaseline"], "replacedBaseline")
    leaderboard_only = _GATE.require_bool(payload["justifiedByLeaderboardOnly"], "justifiedByLeaderboardOnly")
    faults = list(bundle["faults"])
    faults.extend(_cost_faults(
        memory_bytes,
        budget_memory,
        time_ms,
        budget_time,
        tradeoff,
        gate_passed,
        replaced,
        leaderboard_only,
    ))
    extra = [{
        "leaderboardRank": rank,
        "artifactDelta": delta,
        "memoryBytes": memory_bytes,
        "budgetMemoryBytes": budget_memory,
        "timeMs": time_ms,
        "budgetTimeMs": budget_time,
        "tradeoffReported": tradeoff,
        "adoptionGatePassed": gate_passed,
        "replacedBaseline": replaced,
        "justifiedByLeaderboardOnly": leaderboard_only,
        "overBudget": memory_bytes > budget_memory or float(time_ms) > float(budget_time),
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            TRADEOFF_UNREPORTED: CASE["expected"],
            BASELINE_REPLACED_EARLY: CASE["expected"],
        },
    )
