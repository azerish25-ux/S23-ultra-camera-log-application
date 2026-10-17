"""TC-P154-07 Advanced model cost regression.

Host reference. A larger model that improves one artifact but exceeds memory
or time budgets does not replace the stable baseline. The quality-cost
tradeoff is reported. A leaderboard position alone cannot justify replacement.
The adoption gate must pass before the baseline is dropped.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P154-07",
    "phase": "P154",
    "workstream": 20,
    "name": "Advanced model cost regression",
    "intervention": "Adopt a larger research model that improves one artifact but exceeds practical memory or time budgets.",
    "expected": "Report the quality-cost tradeoff and retain the stable baseline until the adoption gate passes.",
    "negative": "A leaderboard position alone cannot justify replacement.",
    "repeat": "Repeat difficult-scene quality, sustained device load, and deferred job interruption.",
}

NEGATIVE_TOKEN = "leaderboard-alone-justifies-replacement"
GATE_NOT_PASSED = "baseline-replaced-before-adoption-gate"
TRADEOFF_MISSING = "quality-cost-tradeoff-unreported"
GATES = frozenset({"pass", "fail", "not-run"})
JUSTIFICATIONS = frozenset({"leaderboard", "tradeoff-and-gate", "none"})
CASE_FIELDS = {
    "candidateImprovesArtifact",
    "candidateMemoryBytes",
    "candidateTimeMs",
    "memoryBudgetBytes",
    "timeBudgetMs",
    "leaderboardRank",
    "tradeoffReported",
    "adoptionGate",
    "baselineRetained",
    "replacedBaseline",
    "justifiedBy",
}


def _load_gate():
    path = Path(__file__).resolve().parent / "p154_survey_public_firmware_and_hal_information.py"
    spec = importlib.util.spec_from_file_location("p154_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _require_non_negative(value: object, label: str) -> int:
    _GATE.require(type(value) is int and value >= 0, label + " must be an int >= 0")
    return value


def _cost_faults(
    *,
    tradeoff_reported: bool,
    adoption_gate: str,
    baseline_retained: bool,
    replaced_baseline: bool,
    justified_by: str,
) -> list[str]:
    faults: list[str] = []
    if not tradeoff_reported:
        faults.append(TRADEOFF_MISSING)
    if (replaced_baseline or not baseline_retained) and adoption_gate != "pass":
        faults.append(GATE_NOT_PASSED)
    if justified_by == "leaderboard":
        faults.append(NEGATIVE_TOKEN)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, CASE_FIELDS)
    artifact = _GATE.require_text(payload["candidateImprovesArtifact"], "candidateImprovesArtifact")
    memory = _require_non_negative(payload["candidateMemoryBytes"], "candidateMemoryBytes")
    time_ms = _require_non_negative(payload["candidateTimeMs"], "candidateTimeMs")
    memory_budget = _require_non_negative(payload["memoryBudgetBytes"], "memoryBudgetBytes")
    time_budget = _require_non_negative(payload["timeBudgetMs"], "timeBudgetMs")
    rank = payload["leaderboardRank"]
    _GATE.require(type(rank) is int and rank >= 1, "leaderboardRank must be an int >= 1")
    tradeoff = _GATE.require_bool(payload["tradeoffReported"], "tradeoffReported")
    gate = _GATE.require_text(payload["adoptionGate"], "adoptionGate")
    _GATE.require(gate in GATES, "adoptionGate is not recognized")
    retained = _GATE.require_bool(payload["baselineRetained"], "baselineRetained")
    replaced = _GATE.require_bool(payload["replacedBaseline"], "replacedBaseline")
    justified = _GATE.require_text(payload["justifiedBy"], "justifiedBy")
    _GATE.require(justified in JUSTIFICATIONS, "justifiedBy is not recognized")
    exceeds = memory > memory_budget or time_ms > time_budget
    faults = list(bundle["faults"])
    faults.extend(_cost_faults(
        tradeoff_reported=tradeoff,
        adoption_gate=gate,
        baseline_retained=retained,
        replaced_baseline=replaced,
        justified_by=justified,
    ))
    extra = [{
        "candidateImprovesArtifact": artifact,
        "exceedsBudget": exceeds,
        "leaderboardRank": rank,
        "tradeoffReported": tradeoff,
        "adoptionGate": gate,
        "baselineRetained": retained,
        "replacedBaseline": replaced,
        "justifiedBy": justified,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            GATE_NOT_PASSED: CASE["expected"],
            TRADEOFF_MISSING: "the quality-cost tradeoff must be reported",
        },
    )
