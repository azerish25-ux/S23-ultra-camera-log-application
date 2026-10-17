"""TC-P153-07 Advanced model cost regression.

Host reference. A larger model that improves one artifact but exceeds the
memory or time budget reports that tradeoff and keeps the stable baseline
until the adoption gate passes. A leaderboard rank alone does not justify
replacement.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

GATE_NOT_PASSED = "baseline-retained-until-adoption-gate"
LEADERBOARD = "leaderboard-position-cannot-justify-replacement"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "hypotheses",
    "questions",
    "plan",
    "limiter",
    "applyMutant",
    "candidate",
    "baseline",
    "artifact_improved",
    "memory_bytes",
    "time_ms",
    "memory_budget_bytes",
    "time_budget_ms",
    "leaderboard_rank",
    "adoption_gate_passed",
    "replaced_baseline",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p153_identify_the_actual_blocked_capability.py"
    spec = importlib.util.spec_from_file_location("p153_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()
CASE = dict(_GATE.CASES[6])


def _non_negative(value: object, label: str) -> int:
    number = _GATE.require_int(value, label)
    _GATE.require(number >= 0, label + " must be >= 0")
    return number


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    candidate = _GATE.require_text(payload["candidate"], "candidate")
    baseline = _GATE.require_text(payload["baseline"], "baseline")
    improved = _GATE.require_bool(payload["artifact_improved"], "artifact_improved")
    memory = _non_negative(payload["memory_bytes"], "memory_bytes")
    time_ms = _non_negative(payload["time_ms"], "time_ms")
    memory_budget = _non_negative(payload["memory_budget_bytes"], "memory_budget_bytes")
    time_budget = _non_negative(payload["time_budget_ms"], "time_budget_ms")
    _GATE.require(memory_budget > 0 and time_budget > 0, "budgets must be > 0")
    rank = payload["leaderboard_rank"]
    if rank is not None:
        rank = _GATE.require_int(rank, "leaderboard_rank")
        _GATE.require(rank >= 1, "leaderboard_rank must be >= 1")
    gate_passed = _GATE.require_bool(payload["adoption_gate_passed"], "adoption_gate_passed")
    replaced = _GATE.require_bool(payload["replaced_baseline"], "replaced_baseline")
    over_memory = memory > memory_budget
    over_time = time_ms > time_budget
    exceeds = over_memory or over_time
    faults = list(bundle["faults"])
    if replaced and not gate_passed:
        faults.append(GATE_NOT_PASSED)
        if rank is not None:
            faults.append(LEADERBOARD)
    extra = [{
        "candidate": candidate,
        "baseline": baseline,
        "artifact_improved": improved,
        "exceedsBudget": exceeds,
        "overMemory": over_memory,
        "overTime": over_time,
        "leaderboard_rank": rank,
        "adoption_gate_passed": gate_passed,
        "replaced_baseline": replaced,
        "baselineRetained": not replaced,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            GATE_NOT_PASSED: CASE["expected"],
            LEADERBOARD: CASE["negative"],
        },
    )


def example_payload(**overrides):
    payload = _GATE.core_payload(repeat="difficult-scene-quality")
    payload.update({
        "candidate": "larger-research-model",
        "baseline": "stable-baseline",
        "artifact_improved": True,
        "memory_bytes": 9_000_000_000,
        "time_ms": 5000,
        "memory_budget_bytes": 2_000_000_000,
        "time_budget_ms": 1000,
        "leaderboard_rank": 1,
        "adoption_gate_passed": False,
        "replaced_baseline": False,
    })
    payload.update(overrides)
    return payload
