"""TC-P157-07 Advanced model cost regression.

Host reference. A larger model that improves one artifact still has to fit
memory and time budgets. The quality-cost tradeoff is reported and the stable
baseline stays until the adoption gate passes. A leaderboard rank alone cannot
replace it.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P157-07",
    "phase": "P157",
    "workstream": 20,
    "name": "Advanced model cost regression",
    "intervention": "Adopt a larger research model that improves one artifact but exceeds practical memory or time budgets.",
    "expected": "Report the quality-cost tradeoff and retain the stable baseline until the adoption gate passes.",
    "negative": "A leaderboard position alone cannot justify replacement.",
    "repeat": "Repeat difficult-scene quality, sustained device load, and deferred job interruption.",
}

NEGATIVE_TOKEN = "leaderboard-alone-justifies-replacement"
TRADEOFF_TOKEN = "quality-cost-tradeoff-not-reported"
RETAINED_TOKEN = "baseline-not-retained"
REPLACED_TOKEN = "baseline-replaced-before-adoption-gate"
GATE_TOKEN = "adoption-gate-passed-without-budget-and-checks"
CHECK_KEYS = ("difficultSceneQuality", "sustainedDeviceLoad", "deferredJobInterruption")
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
    "baseline",
    "candidate",
    "budgets",
    "tradeoffReported",
    "adoptionGatePassed",
    "replacedBaseline",
    "checks",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p157_design_instrumented_low_level_experiments.py"
    spec = importlib.util.spec_from_file_location("p157_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _non_negative_int(value: object, label: str) -> int:
    number = _GATE.require_int(value, label)
    _GATE.require(number >= 0, label + " must be >= 0")
    return number


def _parse_model(value: object, label: str, *, ranked: bool) -> dict:
    _GATE.require(isinstance(value, dict), label + " must be an object")
    keys = {"id", "memoryBytes", "timeMs", "quality"}
    if ranked:
        keys |= {"artifactImproved", "leaderboardRank"}
    else:
        keys |= {"retained"}
    _GATE.require(set(value) == keys, label + " keys are invalid")
    parsed = {
        "id": _GATE.require_text(value["id"], label + ".id"),
        "memoryBytes": _non_negative_int(value["memoryBytes"], label + ".memoryBytes"),
        "timeMs": _non_negative_int(value["timeMs"], label + ".timeMs"),
        "quality": _quality(value["quality"], label + ".quality"),
    }
    if ranked:
        rank = value["leaderboardRank"]
        if rank is not None:
            rank = _GATE.require_int(rank, label + ".leaderboardRank")
            _GATE.require(rank >= 1, label + ".leaderboardRank must be >= 1")
        parsed["artifactImproved"] = _GATE.require_text(value["artifactImproved"], label + ".artifactImproved")
        parsed["leaderboardRank"] = rank
    else:
        parsed["retained"] = _GATE.require_bool(value["retained"], label + ".retained")
    return parsed


def _quality(value: object, label: str) -> float:
    _GATE.require(isinstance(value, (int, float)) and not isinstance(value, bool), label + " must be a number")
    number = float(value)
    _GATE.require(number == number and number != float("inf") and number != float("-inf"), label + " must be finite")
    _GATE.require(0 <= number <= 1, label + " must be between 0 and 1")
    return number


def _parse_budgets(value: object) -> dict:
    _GATE.require(isinstance(value, dict), "budgets must be an object")
    _GATE.require(set(value) == {"memoryBytes", "timeMs"}, "budgets keys are invalid")
    return {
        "memoryBytes": _non_negative_int(value["memoryBytes"], "budgets.memoryBytes"),
        "timeMs": _non_negative_int(value["timeMs"], "budgets.timeMs"),
    }


def _parse_checks(value: object) -> dict:
    _GATE.require(isinstance(value, dict), "checks must be an object")
    _GATE.require(set(value) == set(CHECK_KEYS), "checks keys are invalid")
    return {key: _GATE.require_bool(value[key], "checks." + key) for key in CHECK_KEYS}


def _cost_faults(baseline: dict, candidate: dict, budgets: dict, checks: dict, observed: dict) -> tuple[list[str], dict]:
    exceeds_memory = candidate["memoryBytes"] > budgets["memoryBytes"]
    exceeds_time = candidate["timeMs"] > budgets["timeMs"]
    exceeds = exceeds_memory or exceeds_time
    checks_pass = all(checks.values())
    faults: list[str] = []
    if not observed["tradeoffReported"]:
        faults.append(TRADEOFF_TOKEN)
    if not baseline["retained"] and not observed["adoptionGatePassed"]:
        faults.append(RETAINED_TOKEN)
    if observed["replacedBaseline"] and not observed["adoptionGatePassed"]:
        faults.append(REPLACED_TOKEN)
    if observed["adoptionGatePassed"] and (exceeds or not checks_pass):
        faults.append(GATE_TOKEN)
    rank = candidate["leaderboardRank"]
    justified = observed["tradeoffReported"] and checks_pass and not exceeds and observed["adoptionGatePassed"]
    if observed["replacedBaseline"] and rank is not None and not justified:
        faults.append(NEGATIVE_TOKEN)
    cost = {
        "exceedsMemory": exceeds_memory,
        "exceedsTime": exceeds_time,
        "exceedsBudget": exceeds,
        "checksPass": checks_pass,
        "qualityDelta": candidate["quality"] - baseline["quality"],
        "leaderboardRank": rank,
    }
    return faults, cost


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    baseline = _parse_model(payload["baseline"], "baseline", ranked=False)
    candidate = _parse_model(payload["candidate"], "candidate", ranked=True)
    budgets = _parse_budgets(payload["budgets"])
    checks = _parse_checks(payload["checks"])
    observed = {
        "tradeoffReported": _GATE.require_bool(payload["tradeoffReported"], "tradeoffReported"),
        "adoptionGatePassed": _GATE.require_bool(payload["adoptionGatePassed"], "adoptionGatePassed"),
        "replacedBaseline": _GATE.require_bool(payload["replacedBaseline"], "replacedBaseline"),
    }
    faults = list(bundle["faults"])
    cost_faults, cost = _cost_faults(baseline, candidate, budgets, checks, observed)
    faults.extend(cost_faults)
    preserved = dict(observed)
    preserved.update(cost)
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [preserved],
        {
            NEGATIVE_TOKEN: CASE["negative"],
            TRADEOFF_TOKEN: CASE["expected"],
            RETAINED_TOKEN: CASE["expected"],
            REPLACED_TOKEN: CASE["expected"],
            GATE_TOKEN: CASE["expected"],
        },
    )
