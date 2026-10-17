#!/usr/bin/env python3
"""P159 Explore higher-quality computational optics.

Host reference only. This module does not probe a device and does not qualify
a physical S23. A model candidate has name, benchmark_rank, baseline_error,
candidate_error, and adopted. Adopting solely because rank is better is
rejected: adopted true while candidate_error is not lower than baseline_error,
or only rank is cited. Adoption requires a measured error improvement and a
named limit. Larger model size alone is not a reason. The decision is never
qualified. Baseline product stability must be noted; if baseline_stable is
false, adoption is rejected. A larger temporal model that improves some
boundaries but causes memory pressure or unacceptable deferred rendering time
is not an automatic replacement of the stable path.

Adoption rule: a model candidate has name, benchmark_rank, baseline_error,
candidate_error, and adopted. Adopting solely because rank is better is
rejected: adopted true while candidate_error is not lower than baseline_error,
or only rank is cited. Adoption requires a measured error improvement and a
named limit. Larger model size alone is not a reason. The decision is never
qualified. Baseline product stability must be noted; if baseline_stable is
false, adoption is rejected. Memory pressure or unacceptable deferred rendering
time blocks automatic replacement even when boundary error improves.
"""

from __future__ import annotations

import math
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P159"
WORKSTREAM = 20
TITLE = "Explore higher-quality computational optics"
GOAL = (
    "Investigate richer depth, multi-view cues, or research models only after the "
    "baseline product is stable."
)
METHOD = (
    "Compare real synchronized inputs where available, improved temporal models, and "
    "calibrated geometry under explicit resource and privacy limits. Keep the original "
    "on-device workflow usable. New models require licensing, conversion, and "
    "difficult-scene validation again."
)
FIXTURE = (
    "A larger temporal model improving some boundaries but causing memory pressure and "
    "unacceptable deferred rendering time."
)
ORACLE = (
    "The decision reports the quality-cost tradeoff rather than replacing the stable "
    "path automatically."
)
MUTANT = "Adopt a larger model solely because its benchmark ranking is higher."
DELIVERABLE = "Advanced optics research comparison and adoption gate"
DEPENDENCIES = ("P158",)

ADOPTION_RULE = (
    "A model candidate has name, benchmark_rank, baseline_error, candidate_error, and "
    "adopted. Adopting solely because rank is better is rejected: adopted true while "
    "candidate_error is not lower than baseline_error, or only rank is cited. Adoption "
    "requires a measured error improvement and a named limit. Larger model size alone is "
    "not a reason. The decision is never qualified. Baseline product stability must be "
    "noted; if baseline_stable is false, adoption is rejected. A larger model that "
    "improves some boundaries but causes memory pressure or unacceptable deferred "
    "rendering time is not an automatic replacement of the stable path."
)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p159-computational-optics"
CLAIM = "higher-quality-computational-optics-host-reference"

STABLE_NOTE = "baseline product stable"
UNSTABLE_NOTE = "baseline product unstable"

RANK_ONLY_ADOPTION = "rank-only-adoption"
ONLY_RANK_CITED = "only-rank-cited"
MISSING_NAMED_LIMIT = "missing-named-limit"
SIZE_ALONE = "model-size-alone"
BASELINE_UNSTABLE = "baseline-unstable"
BASELINE_NOT_NOTED = "baseline-stability-not-noted"
COST_TRADEOFF_IGNORED = "quality-cost-tradeoff-ignored"
REVALIDATION_INCOMPLETE = "revalidation-incomplete"

FIXTURE_BASELINE_ERROR = 42
FIXTURE_CANDIDATE_ERROR = 31
FIXTURE_BASELINE_RANK = 4
FIXTURE_BENCHMARK_RANK = 1
FIXTURE_MODEL_SIZE = 8
FIXTURE_BASELINE_MODEL_SIZE = 2
FIXTURE_MEMORY_BYTES = 900
FIXTURE_MEMORY_BUDGET_BYTES = 512
FIXTURE_DEFERRED_TIME_MS = 2400
FIXTURE_DEFERRED_BUDGET_MS = 400
FIXTURE_NAMED_LIMIT = "deferred-render-ms"
FIXTURE_CANDIDATE_NAME = "larger-temporal-model"

RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = frozenset({"recorded", "rejected"})
NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]
CITED_REASON_TOKENS = frozenset({
    "benchmark_rank",
    "rank",
    "leaderboard",
    "boundary-error",
    "model-size",
    "larger-model",
    "size",
    "memory-pressure",
    "deferred-time",
    "named-limit",
    "privacy",
    "licensing",
})
RANK_CITATIONS = frozenset({"benchmark_rank", "rank", "leaderboard"})
SIZE_CITATIONS = frozenset({"model-size", "larger-model", "size"})
COST_CITATIONS = frozenset({"memory-pressure", "deferred-time", "named-limit", "privacy"})
NAMED_LIMITS = frozenset({
    "memory-bytes",
    "deferred-render-ms",
    "privacy-on-device",
    "on-device-workflow",
})
CANDIDATE_KEYS = frozenset({
    "name",
    "benchmark_rank",
    "baseline_error",
    "candidate_error",
    "adopted",
    "citedReasons",
    "namedLimit",
    "modelSize",
    "baselineModelSize",
    "memoryBytes",
    "memoryBudgetBytes",
    "deferredTimeMs",
    "deferredBudgetMs",
    "licenseDeclared",
    "converted",
    "difficultScenesValidated",
})
DOCUMENT_KEYS = frozenset({
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "baseline_stable",
    "stabilityNoted",
    "baselineRank",
    "candidates",
})
CORE_KEYS = frozenset({
    "evidenceId",
    "claim",
    "applyMutant",
    "baseline_stable",
    "stabilityNoted",
    "baselineRank",
    "candidates",
})
CASE_COMMON_KEYS = CORE_KEYS | {"repeat"}
RESULT_STATUSES = frozenset({"pass", "fail", "skip", "unavailable"})
SUMMARY_KEYS = ("pass", "fail", "skip", "unavailable")
STAGE_CAUSES = frozenset({
    "storage",
    "scheduling",
    "firmware",
    "acquisition",
    "development",
    "encoder",
    "unknown",
})
MODIFICATIONS = frozenset({"none", "firmware", "low-level", "scheduling"})
ROUTE_IDS = frozenset({"p010", "surface", "reduced-geometry", "deferred", "scheduling"})
OPERATION_KINDS = frozenset({
    "none",
    "flash",
    "bootloader",
    "security-state",
    "recovery-image",
})
RECORD_OUTCOMES = frozenset({"favorable", "failed"})
PROPRIETARY_COMPONENT = "proprietary-imaging"

FAULT_TEXT = {
    RANK_ONLY_ADOPTION: (
        "adopted true while candidate_error is not lower than baseline_error"
    ),
    ONLY_RANK_CITED: "only rank is cited",
    MISSING_NAMED_LIMIT: "adoption requires a measured error improvement and a named limit",
    SIZE_ALONE: "Larger model size alone is not a reason",
    BASELINE_UNSTABLE: "baseline_stable is false; adoption is rejected",
    BASELINE_NOT_NOTED: "Baseline product stability must be noted",
    COST_TRADEOFF_IGNORED: ORACLE,
    REVALIDATION_INCOMPLETE: (
        "New models require licensing, conversion, and difficult-scene validation again."
    ),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_text(value: object, label: str) -> str:
    require(
        isinstance(value, str) and bool(value.strip()) and value == value.strip(),
        label + " must be a non-empty string",
    )
    return value


def require_bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def require_int(value: object, label: str) -> int:
    require(type(value) is int, label + " must be an int")
    return value


def require_number(value: object, label: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number",
    )
    number = float(value)
    require(math.isfinite(number), label + " must be finite")
    return number


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def display_number(value: float) -> int | float:
    if float(value).is_integer():
        return int(value)
    return float(value)


def expected_stability_note(baseline_stable: bool) -> str:
    return STABLE_NOTE if baseline_stable else UNSTABLE_NOTE


def stability_is_noted(baseline_stable: bool, note: str) -> bool:
    return note == expected_stability_note(baseline_stable)


def _positive_int(value: object, label: str) -> int:
    number = require_int(value, label)
    require(number > 0, label + " must be > 0")
    return number


def _non_negative_number(value: object, label: str) -> float:
    number = require_number(value, label)
    require(number >= 0, label + " must be >= 0")
    return number


def parse_named_limit(value: object, label: str) -> str | None:
    if value is None:
        return None
    text = require_text(value, label)
    require(text in NAMED_LIMITS, label + " is not a named limit")
    return text


def parse_cited_reasons(value: object, label: str) -> list[str]:
    require(isinstance(value, list) and bool(value), label + " must be a non-empty list")
    reasons: list[str] = []
    for index, item in enumerate(value):
        reason = require_text(item, f"{label}[{index}]")
        require(reason in CITED_REASON_TOKENS, f"{label}[{index}] is not a citation")
        reasons.append(reason)
    require(len(reasons) == len(set(reasons)), label + " entries must be unique")
    return reasons


def parse_candidate(value: object, index: int) -> dict[str, Any]:
    require(isinstance(value, dict), f"candidates[{index}] must be an object")
    require(set(value) == set(CANDIDATE_KEYS), f"candidates[{index}] keys are invalid")
    label = f"candidates[{index}]"
    candidate = {
        "name": require_text(value["name"], label + ".name"),
        "benchmark_rank": _positive_int(value["benchmark_rank"], label + ".benchmark_rank"),
        "baseline_error": _non_negative_number(value["baseline_error"], label + ".baseline_error"),
        "candidate_error": _non_negative_number(value["candidate_error"], label + ".candidate_error"),
        "adopted": require_bool(value["adopted"], label + ".adopted"),
        "citedReasons": parse_cited_reasons(value["citedReasons"], label + ".citedReasons"),
        "namedLimit": parse_named_limit(value["namedLimit"], label + ".namedLimit"),
        "modelSize": _positive_int(value["modelSize"], label + ".modelSize"),
        "baselineModelSize": _positive_int(value["baselineModelSize"], label + ".baselineModelSize"),
        "memoryBytes": _positive_int(value["memoryBytes"], label + ".memoryBytes"),
        "memoryBudgetBytes": _positive_int(value["memoryBudgetBytes"], label + ".memoryBudgetBytes"),
        "deferredTimeMs": _positive_int(value["deferredTimeMs"], label + ".deferredTimeMs"),
        "deferredBudgetMs": _positive_int(value["deferredBudgetMs"], label + ".deferredBudgetMs"),
        "licenseDeclared": require_bool(value["licenseDeclared"], label + ".licenseDeclared"),
        "converted": require_bool(value["converted"], label + ".converted"),
        "difficultScenesValidated": require_bool(
            value["difficultScenesValidated"], label + ".difficultScenesValidated"
        ),
    }
    return candidate


def parse_candidates(value: object) -> list[dict[str, Any]]:
    require(isinstance(value, list) and bool(value), "candidates must be a non-empty list")
    candidates = [parse_candidate(item, index) for index, item in enumerate(value)]
    names = [candidate["name"] for candidate in candidates]
    require(len(names) == len(set(names)), "candidate names must be unique")
    return candidates


def only_rank_cited(cited: list[str]) -> bool:
    return bool(cited) and all(item in RANK_CITATIONS for item in cited)


def only_size_cited(cited: list[str]) -> bool:
    return bool(cited) and all(item in SIZE_CITATIONS for item in cited)


def error_improved(candidate: dict[str, Any]) -> bool:
    return float(candidate["candidate_error"]) < float(candidate["baseline_error"])


def measure_candidate(candidate: dict[str, Any], baseline_rank: int) -> dict[str, Any]:
    """Measured quality-cost comparison for one model candidate."""
    cited = list(candidate["citedReasons"])
    improved = error_improved(candidate)
    memory_pressure = candidate["memoryBytes"] > candidate["memoryBudgetBytes"]
    deferred_bad = candidate["deferredTimeMs"] > candidate["deferredBudgetMs"]
    larger = candidate["modelSize"] > candidate["baselineModelSize"]
    revalidated = (
        candidate["licenseDeclared"] is True
        and candidate["converted"] is True
        and candidate["difficultScenesValidated"] is True
    )
    return {
        "name": candidate["name"],
        "benchmark_rank": candidate["benchmark_rank"],
        "baseline_error": display_number(candidate["baseline_error"]),
        "candidate_error": display_number(candidate["candidate_error"]),
        "adopted": candidate["adopted"],
        "errorImproved": improved,
        "rankBetter": candidate["benchmark_rank"] < baseline_rank,
        "onlyRankCited": only_rank_cited(cited),
        "onlySizeCited": only_size_cited(cited),
        "modelLarger": larger,
        "namedLimit": candidate["namedLimit"],
        "memoryBytes": candidate["memoryBytes"],
        "memoryBudgetBytes": candidate["memoryBudgetBytes"],
        "deferredTimeMs": candidate["deferredTimeMs"],
        "deferredBudgetMs": candidate["deferredBudgetMs"],
        "memoryPressure": memory_pressure,
        "deferredUnacceptable": deferred_bad,
        "costExceeded": memory_pressure or deferred_bad,
        "revalidated": revalidated,
        "citedReasons": cited,
    }


def candidate_blockers(measured: dict[str, Any]) -> list[str]:
    """Return adoption faults for one measured candidate. Empty means the row is honest."""
    blockers: list[str] = []
    adopted = measured["adopted"] is True
    improved = measured["errorImproved"] is True
    cited = measured["citedReasons"]
    if adopted and not improved:
        blockers.append(RANK_ONLY_ADOPTION)
    if measured["onlyRankCited"]:
        blockers.append(ONLY_RANK_CITED)
    if adopted and measured["namedLimit"] is None:
        blockers.append(MISSING_NAMED_LIMIT)
    size_without_error = (
        adopted
        and measured["modelLarger"]
        and not improved
        and any(item in SIZE_CITATIONS for item in cited)
        and "boundary-error" not in cited
    )
    if measured["onlySizeCited"] or size_without_error:
        blockers.append(SIZE_ALONE)
    if adopted and measured["costExceeded"]:
        blockers.append(COST_TRADEOFF_IGNORED)
    if adopted and not measured["revalidated"]:
        blockers.append(REVALIDATION_INCOMPLETE)
    return dedupe(blockers)


def tradeoff_reason(measured: dict[str, Any]) -> str:
    parts = [
        measured["name"],
        "benchmark_rank " + str(measured["benchmark_rank"]),
        "baseline_error " + str(measured["baseline_error"]),
        "candidate_error " + str(measured["candidate_error"]),
        "measured error improved" if measured["errorImproved"] else "measured error did not improve",
    ]
    if measured["rankBetter"]:
        parts.append("rank is better")
    if measured["memoryPressure"]:
        parts.append(
            "memory pressure "
            + str(measured["memoryBytes"])
            + ">"
            + str(measured["memoryBudgetBytes"])
        )
    if measured["deferredUnacceptable"]:
        parts.append(
            "unacceptable deferred rendering "
            + str(measured["deferredTimeMs"])
            + "ms>"
            + str(measured["deferredBudgetMs"])
            + "ms"
        )
    if measured["namedLimit"] is None:
        parts.append("named limit missing")
    else:
        parts.append("named limit " + measured["namedLimit"])
    if measured["modelLarger"]:
        parts.append("model size is larger")
    parts.append("adopted " + ("true" if measured["adopted"] else "false"))
    if measured["adopted"] and not measured["costExceeded"] and measured["errorImproved"]:
        parts.append("adoption gate passed")
    else:
        parts.append("stable path retained")
    return "quality-cost tradeoff: " + "; ".join(parts)


def reports_quality_cost(measured: dict[str, Any]) -> bool:
    cited = set(measured["citedReasons"])
    return "boundary-error" in cited and bool(cited & COST_CITATIONS) and measured["namedLimit"] is not None


def analyze_computation(
    *,
    baseline_stable: bool,
    stability_noted: str,
    baseline_rank: int,
    candidates: list[dict[str, Any]],
    apply_mutant: bool,
) -> dict[str, Any]:
    faults: list[str] = []
    if not stability_is_noted(baseline_stable, stability_noted):
        faults.append(BASELINE_NOT_NOTED)
    if baseline_stable is False:
        faults.append(BASELINE_UNSTABLE)
    measured_rows = [measure_candidate(candidate, baseline_rank) for candidate in candidates]
    for measured in measured_rows:
        faults.extend(candidate_blockers(measured))
    if apply_mutant:
        faults.append(RANK_ONLY_ADOPTION)
        faults.append(ONLY_RANK_CITED)
    automatic = any(
        row["adopted"] and (row["costExceeded"] or row["onlyRankCited"] or not row["errorImproved"])
        for row in measured_rows
    )
    tradeoff_reported = all(reports_quality_cost(row) for row in measured_rows) and not automatic
    snapshot = {
        "baseline_stable": baseline_stable,
        "stabilityNoted": stability_noted,
        "baselineRank": baseline_rank,
        "candidates": measured_rows,
        "qualityCostTradeoffReported": tradeoff_reported,
        "automaticReplacement": automatic,
        "adoptionRejected": baseline_stable is False or automatic or bool(dedupe(faults)),
    }
    extra_reasons = [
        "baseline product stability noted="
        + stability_noted
        + "; baseline_stable="
        + ("true" if baseline_stable else "false"),
        "adoption rule: " + ADOPTION_RULE,
    ]
    extra_reasons.extend(tradeoff_reason(row) for row in measured_rows)
    if baseline_stable is False:
        extra_reasons.append("baseline_stable is false; adoption is rejected")
    if automatic:
        extra_reasons.append("stable path was not retained; automatic replacement rejected")
    elif all(not row["adopted"] for row in measured_rows):
        extra_reasons.append("stable path retained; replacement was not automatic")
    if apply_mutant or RANK_ONLY_ADOPTION in faults or ONLY_RANK_CITED in faults:
        extra_reasons.append("mutant rejected: " + MUTANT)
    return {
        "faults": dedupe(faults),
        "snapshot": snapshot,
        "extraReasons": extra_reasons,
    }


def assemble(
    case_id: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    open_questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    ordered = dedupe(faults)
    decision = "rejected" if ordered else "recorded"
    require(decision in DECISIONS, "decision must be recorded or rejected")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": ordered,
        "preservedResults": preserved,
        "openQuestions": list(open_questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(OPEN_QUESTION in result["openQuestions"], "open question missing")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(bool(result["reasons"]), "reasons must be non-empty")
    return result


def _core_from_mapping(mapping: dict, label: str) -> dict[str, Any]:
    evidence = require_text(mapping["evidenceId"], "evidenceId")
    claim = require_text(mapping["claim"], "claim")
    apply_mutant = require_bool(mapping["applyMutant"], "applyMutant")
    baseline_stable = require_bool(mapping["baseline_stable"], "baseline_stable")
    stability_noted = require_text(mapping["stabilityNoted"], "stabilityNoted")
    baseline_rank = _positive_int(mapping["baselineRank"], "baselineRank")
    candidates = parse_candidates(mapping["candidates"])
    analysis = analyze_computation(
        baseline_stable=baseline_stable,
        stability_noted=stability_noted,
        baseline_rank=baseline_rank,
        candidates=candidates,
        apply_mutant=apply_mutant,
    )
    analysis["evidence"] = evidence
    analysis["claim"] = claim
    analysis["applyMutant"] = apply_mutant
    analysis["label"] = label
    return analysis


def _reasons(analysis: dict[str, Any], lead: list[str], fault_text: dict[str, str] | None) -> list[str]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    reasons = list(lead)
    reasons.extend(analysis["extraReasons"])
    for token in analysis["faults"]:
        reasons.append(text.get(token, token))
    if not analysis["faults"]:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("optics comparison recorded; not a physical qualification")
    return reasons


def assess(document: dict) -> dict[str, Any]:
    """Record an optics comparison, or reject an adoption that fails the gate."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    analysis = _core_from_mapping(document, "document")
    reasons = _reasons(
        analysis,
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 was not run",
            "goal: " + GOAL,
            "method: " + METHOD,
            "fixture: " + FIXTURE,
            "oracle: " + ORACLE,
        ],
        None,
    )
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a phase document or a core optics-comparison payload."""
    require(isinstance(payload, dict), "payload must be an object")
    if (
        "schemaVersion" in payload
        or "implementationBaseRevision" in payload
        or "phase" in payload
    ):
        return assess(payload)
    require(set(payload) == set(CORE_KEYS), "invalid payload keys")
    analysis = _core_from_mapping(payload, "payload")
    reasons = _reasons(
        analysis,
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 was not run",
            "oracle: " + ORACLE,
            "fixture: " + FIXTURE,
        ],
        None,
    )
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


def begin_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(CASE_COMMON_KEYS) | set(extra_keys), "invalid payload keys")
    repeat = require_text(payload["repeat"], "repeat")
    analysis = _core_from_mapping(payload, "case")
    return {
        "evidence": analysis["evidence"],
        "claim": analysis["claim"],
        "repeat": repeat,
        "faults": list(analysis["faults"]),
        "analysis": analysis,
        "snapshot": analysis["snapshot"],
    }


def finish_case(
    case: dict,
    bundle: dict,
    faults: list[str],
    extra_preserved: list,
    fault_text: dict | None = None,
) -> dict[str, Any]:
    analysis = dict(bundle["analysis"])
    analysis["faults"] = dedupe(list(faults))
    reasons = _reasons(
        analysis,
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 was not run",
            "oracle: " + ORACLE,
            case["expected"],
            "repeat " + bundle["repeat"],
        ],
        fault_text,
    )
    preserved = [bundle["evidence"], bundle["snapshot"], bundle["claim"], *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], analysis["faults"], reasons, preserved, questions, bundle["evidence"])


def fixture_candidate(**overrides: Any) -> dict[str, Any]:
    candidate: dict[str, Any] = {
        "name": FIXTURE_CANDIDATE_NAME,
        "benchmark_rank": FIXTURE_BENCHMARK_RANK,
        "baseline_error": FIXTURE_BASELINE_ERROR,
        "candidate_error": FIXTURE_CANDIDATE_ERROR,
        "adopted": False,
        "citedReasons": ["boundary-error", "memory-pressure", "deferred-time"],
        "namedLimit": FIXTURE_NAMED_LIMIT,
        "modelSize": FIXTURE_MODEL_SIZE,
        "baselineModelSize": FIXTURE_BASELINE_MODEL_SIZE,
        "memoryBytes": FIXTURE_MEMORY_BYTES,
        "memoryBudgetBytes": FIXTURE_MEMORY_BUDGET_BYTES,
        "deferredTimeMs": FIXTURE_DEFERRED_TIME_MS,
        "deferredBudgetMs": FIXTURE_DEFERRED_BUDGET_MS,
        "licenseDeclared": False,
        "converted": False,
        "difficultScenesValidated": False,
    }
    candidate.update(overrides)
    return candidate


def fixture_candidates() -> list[dict[str, Any]]:
    return [fixture_candidate()]


def adopting_candidate(**overrides: Any) -> dict[str, Any]:
    """A candidate the adoption gate can accept: lower error, named limit, inside budget."""
    candidate = fixture_candidate(
        name="calibrated-temporal",
        benchmark_rank=2,
        baseline_error=40,
        candidate_error=22,
        adopted=True,
        citedReasons=["boundary-error", "named-limit", "privacy"],
        namedLimit="privacy-on-device",
        modelSize=3,
        baselineModelSize=2,
        memoryBytes=400,
        memoryBudgetBytes=512,
        deferredTimeMs=300,
        deferredBudgetMs=400,
        licenseDeclared=True,
        converted=True,
        difficultScenesValidated=True,
    )
    candidate.update(overrides)
    return candidate


def core_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "baseline_stable": True,
        "stabilityNoted": STABLE_NOTE,
        "baselineRank": FIXTURE_BASELINE_RANK,
        "candidates": fixture_candidates(),
    }
    payload.update(overrides)
    return payload


def fixture_document() -> dict[str, Any]:
    core = core_payload()
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": core["evidenceId"],
        "claim": core["claim"],
        "applyMutant": core["applyMutant"],
        "baseline_stable": core["baseline_stable"],
        "stabilityNoted": core["stabilityNoted"],
        "baselineRank": core["baselineRank"],
        "candidates": core["candidates"],
    }
