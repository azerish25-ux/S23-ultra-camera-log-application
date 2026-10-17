"""TC-P155-07 Advanced model cost regression.

Host reference. A larger model that improves one artifact but exceeds memory
or time budgets does not replace the stable baseline. The quality-cost
tradeoff is reported. A leaderboard position alone does not justify replacement.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P155-07",
    "phase": "P155",
    "workstream": 20,
    "name": "Advanced model cost regression",
    "intervention": "Adopt a larger research model that improves one artifact but exceeds practical memory or time budgets.",
    "expected": "Report the quality-cost tradeoff and retain the stable baseline until the adoption gate passes.",
    "negative": "A leaderboard position alone cannot justify replacement.",
    "repeat": "Repeat difficult-scene quality, sustained device load, and deferred job interruption.",
}

NEGATIVE_TOKEN = "leaderboard-justifies-replacement"
TRADEOFF_OMITTED = "quality-cost-tradeoff-omitted"
BASELINE_DROPPED = "baseline-not-retained"
GATE_FAILED_OPEN = "adoption-gate-passed-over-budget"
ADOPTION_KEYS = frozenset({
    "improvesOneArtifact",
    "leaderboardAhead",
    "memoryWithinBudget",
    "timeWithinBudget",
    "tradeoffReported",
    "baselineRetained",
    "adoptionGatePassed",
})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "alternatives",
    "conclusion",
    "adoption",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p155_evaluate_reversible_application_level_alternatives.py"
    spec = importlib.util.spec_from_file_location("p155_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_adoption(value: object) -> dict:
    _GATE.require(isinstance(value, dict), "adoption must be an object")
    _GATE.require(set(value) == ADOPTION_KEYS, "adoption keys are invalid")
    parsed = {}
    for key in ADOPTION_KEYS:
        parsed[key] = _GATE.require_bool(value[key], "adoption." + key)
    return parsed


def _adoption_faults(adoption: dict) -> list[str]:
    faults: list[str] = []
    over_budget = not adoption["memoryWithinBudget"] or not adoption["timeWithinBudget"]
    replaced = not adoption["baselineRetained"]
    justified = (
        adoption["memoryWithinBudget"]
        and adoption["timeWithinBudget"]
        and adoption["tradeoffReported"]
        and adoption["improvesOneArtifact"]
    )
    if over_budget and not adoption["tradeoffReported"]:
        faults.append(TRADEOFF_OMITTED)
    if over_budget and replaced:
        faults.append(BASELINE_DROPPED)
    if adoption["adoptionGatePassed"] and (over_budget or not adoption["tradeoffReported"]):
        faults.append(GATE_FAILED_OPEN)
    if adoption["leaderboardAhead"] and replaced and not justified:
        faults.append(NEGATIVE_TOKEN)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    adoption = _parse_adoption(payload["adoption"])
    faults = list(bundle["faults"])
    faults.extend(_adoption_faults(adoption))
    extra = [dict(adoption)]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            TRADEOFF_OMITTED: CASE["expected"],
            BASELINE_DROPPED: CASE["expected"],
            GATE_FAILED_OPEN: CASE["expected"],
        },
    )
