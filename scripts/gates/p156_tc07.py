"""TC-P156-07 Advanced model cost regression.

Host reference. A leaderboard rank does not justify replacing the stable
baseline. Replacement is rejected when the adoption gate has not passed or
the model exceeds the memory or time budget. The baseline stays retained.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P156-07",
    "phase": "P156",
    "workstream": 20,
    "name": "Advanced model cost regression",
    "intervention": "Adopt a larger research model that improves one artifact but exceeds practical memory or time budgets.",
    "expected": "Report the quality-cost tradeoff and retain the stable baseline until the adoption gate passes.",
    "negative": "A leaderboard position alone cannot justify replacement.",
    "repeat": "Repeat difficult-scene quality, sustained device load, and deferred job interruption.",
}

NEGATIVE_TOKEN = "leaderboard-alone-justifies-replacement"
BASELINE_DROPPED = "stable-baseline-not-retained"
EXTRA_KEYS = {
    "leaderboardRank",
    "qualityGain",
    "memoryBytes",
    "memoryBudget",
    "timeMs",
    "timeBudget",
    "baselineRetained",
    "replacedBaseline",
    "adoptionGatePassed",
}


def _load_gate():
    path = Path(__file__).resolve().parent / "p156_prepare_a_separate_firmware_risk_gate.py"
    spec = importlib.util.spec_from_file_location("p156_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _cost_faults(
    *,
    memory_bytes: int,
    memory_budget: int,
    time_ms: int,
    time_budget: int,
    baseline_retained: bool,
    replaced_baseline: bool,
    adoption_gate_passed: bool,
) -> tuple[list[str], bool]:
    over_budget = memory_bytes > memory_budget or time_ms > time_budget
    faults: list[str] = []
    if not baseline_retained:
        faults.append(BASELINE_DROPPED)
    if replaced_baseline and (not adoption_gate_passed or over_budget):
        faults.append(NEGATIVE_TOKEN)
    return faults, over_budget


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, EXTRA_KEYS)
    rank = _GATE.require_int(payload["leaderboardRank"], "leaderboardRank")
    _GATE.require(rank >= 1, "leaderboardRank must be >= 1")
    quality = _GATE.require_number(payload["qualityGain"], "qualityGain")
    memory_bytes = _GATE.require_int(payload["memoryBytes"], "memoryBytes")
    memory_budget = _GATE.require_int(payload["memoryBudget"], "memoryBudget")
    time_ms = _GATE.require_int(payload["timeMs"], "timeMs")
    time_budget = _GATE.require_int(payload["timeBudget"], "timeBudget")
    _GATE.require(memory_bytes >= 0 and memory_budget >= 0, "memory figures must be >= 0")
    _GATE.require(time_ms >= 0 and time_budget >= 0, "time figures must be >= 0")
    retained = _GATE.require_bool(payload["baselineRetained"], "baselineRetained")
    replaced = _GATE.require_bool(payload["replacedBaseline"], "replacedBaseline")
    adopted = _GATE.require_bool(payload["adoptionGatePassed"], "adoptionGatePassed")
    case_faults, over_budget = _cost_faults(
        memory_bytes=memory_bytes,
        memory_budget=memory_budget,
        time_ms=time_ms,
        time_budget=time_budget,
        baseline_retained=retained,
        replaced_baseline=replaced,
        adoption_gate_passed=adopted,
    )
    faults = list(bundle["faults"])
    faults.extend(case_faults)
    extra = [{
        "leaderboardRank": rank,
        "qualityGain": quality,
        "memoryBytes": memory_bytes,
        "memoryBudget": memory_budget,
        "timeMs": time_ms,
        "timeBudget": time_budget,
        "overBudget": over_budget,
        "baselineRetained": retained,
        "replacedBaseline": replaced,
        "adoptionGatePassed": adopted,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            BASELINE_DROPPED: CASE["expected"],
        },
    )
