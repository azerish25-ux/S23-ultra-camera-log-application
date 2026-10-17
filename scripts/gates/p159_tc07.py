"""TC-P159-07 Advanced model cost regression.

Host reference. A larger research model that improves one artifact but exceeds
memory or time budgets does not replace the stable baseline. The quality-cost
tradeoff is reported. A leaderboard position alone cannot justify replacement.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P159-07",
    "phase": "P159",
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

NEGATIVE_TOKEN = "leaderboard-position-justifies-replacement"
TRADEOFF_NOT_REPORTED = "quality-cost-tradeoff-not-reported"
BASELINE_NOT_RETAINED = "stable-baseline-not-retained"
ADOPTION_CONTRADICTS_BASELINE = "adoption-contradicts-retained-baseline"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "baseline_stable",
    "stabilityNoted",
    "baselineRank",
    "candidates",
    "retainedBaseline",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p159_explore_higher_quality_computational_optics.py"
    spec = importlib.util.spec_from_file_location("p159_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _regression_faults(candidates: list[dict], retained_baseline: bool) -> list[str]:
    faults: list[str] = []
    cost_exceeded = any(
        candidate["memoryBytes"] > candidate["memoryBudgetBytes"]
        or candidate["deferredTimeMs"] > candidate["deferredBudgetMs"]
        for candidate in candidates
    )
    adopted_any = any(candidate["adopted"] is True for candidate in candidates)
    only_rank = any(candidate["citedReasons"] == ["benchmark_rank"] or _GATE.only_rank_cited(candidate["citedReasons"])
                    for candidate in candidates)
    reports_tradeoff = all(
        "boundary-error" in candidate["citedReasons"]
        and bool(set(candidate["citedReasons"]) & _GATE.COST_CITATIONS)
        and candidate["namedLimit"] is not None
        for candidate in candidates
    )
    if not reports_tradeoff:
        faults.append(TRADEOFF_NOT_REPORTED)
    if only_rank:
        faults.append(NEGATIVE_TOKEN)
    if cost_exceeded and (not retained_baseline or adopted_any):
        faults.append(BASELINE_NOT_RETAINED)
    if adopted_any and retained_baseline:
        faults.append(ADOPTION_CONTRADICTS_BASELINE)
    return _GATE.dedupe(faults)


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    retained = _GATE.require_bool(payload["retainedBaseline"], "retainedBaseline")
    faults = list(bundle["faults"])
    faults.extend(_regression_faults(payload["candidates"], retained))
    measured = bundle["snapshot"]["candidates"]
    extra = [{
        "retainedBaseline": retained,
        "adopted": [row["adopted"] for row in measured],
        "costExceeded": [row["costExceeded"] for row in measured],
        "qualityCostTradeoffReported": bundle["snapshot"]["qualityCostTradeoffReported"],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            TRADEOFF_NOT_REPORTED: CASE["expected"],
            BASELINE_NOT_RETAINED: CASE["expected"],
            ADOPTION_CONTRADICTS_BASELINE: CASE["expected"],
        },
    )
