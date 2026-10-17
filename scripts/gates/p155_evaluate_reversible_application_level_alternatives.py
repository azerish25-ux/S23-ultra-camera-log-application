#!/usr/bin/env python3
"""P155 Evaluate reversible application-level alternatives.

Host reference only. This module does not probe a device and does not qualify
a physical S23. alternatives is a list of {name, tried, result} where result is
available, unavailable, or untested. One codec interface failing must not mark
every ten-bit path unavailable. If any alternative is untested, a conclusion
that all ten-bit paths are unavailable is rejected. A comparative decision is
recorded only when each listed path has been tried or explicitly left untested
and the conclusion matches. The decision is never qualified or allowed.
"""

from __future__ import annotations

from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P155"
WORKSTREAM = 20
TITLE = "Evaluate reversible application-level alternatives"
GOAL = "Exhaust useful normal-app approaches before escalating risk."
METHOD = (
    "Compare alternate stream combinations, smaller source sizes, different codec "
    "interfaces, deferred development, CPU-GPU scheduling, and retained RAW workflows. "
    "Measure the information and quality tradeoffs. Keep each alternative honestly "
    "labelled by source lineage."
)
FIXTURE = (
    "A surface-only ten-bit encoder that could support a qualified GPU route even "
    "though the P010 Image developer is unavailable."
)
ORACLE = "The plan explores that interface before declaring the sensor-to-Log goal impossible."
MUTANT = "Treat failure of one codec input interface as proof that every ten-bit path is unavailable."
DELIVERABLE = "Alternative-path experiments and comparative decision"
DEPENDENCIES = ("P154",)
SLUG = "evaluate_reversible_application_level_alternatives"

COMPARATIVE_RULE = (
    "An alternative is a record with name, tried, and result, and result is available, "
    "unavailable, or untested. A path has been tried only when tried is true and result "
    "is available or unavailable. A path is explicitly left untested only when tried is "
    "false and result is untested. Any other combination is not comparable. Failure of "
    "one codec interface does not mark every other ten-bit path unavailable; each path "
    "keeps its own result. If any alternative is untested, a conclusion that all ten-bit "
    "paths are unavailable is rejected. A comparative decision is recorded only when "
    "every listed path has been tried or explicitly left untested and the conclusion "
    "matches those results. The decision is never qualified or allowed."
)

OPEN_QUESTION = "physical S23 not run"
EVIDENCE_ID = "p155-reversible-alternatives"
CLAIM = "reversible-application-level-alternatives-host-reference"

ALL_TEN_BIT_UNAVAILABLE = "all-ten-bit-paths-unavailable"
TEN_BIT_PATH_AVAILABLE = "ten-bit-path-available"
UNTESTED_REMAIN = "untested-alternatives-remain"
NOT_IMPOSSIBLE = "sensor-to-log-not-impossible"
CONCLUSIONS = frozenset({
    ALL_TEN_BIT_UNAVAILABLE,
    TEN_BIT_PATH_AVAILABLE,
    UNTESTED_REMAIN,
    NOT_IMPOSSIBLE,
})
RESULTS = frozenset({"available", "unavailable", "untested"})
ALTERNATIVE_KEYS = frozenset({"name", "tried", "result"})
CODEC_MARKERS = ("p010", "codec", "hevc", "encoder")

PATH_NOT_LABELLED = "path-not-tried-or-explicitly-untested"
UNTESTED_BLOCKS_ALL_UNAVAILABLE = "untested-alternative-blocks-all-ten-bit-unavailable"
ONE_CODEC_MARKS_ALL = "one-codec-interface-marks-every-ten-bit-path-unavailable"
CONCLUSION_MISMATCH = "conclusion-does-not-match-alternatives"

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
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "alternatives",
    "conclusion",
}
CORE_KEYS = {
    "evidenceId",
    "claim",
    "applyMutant",
    "alternatives",
    "conclusion",
}
CASE_COMMON_KEYS = CORE_KEYS | {"repeat"}

FIXTURE_ROWS = (
    ("alternate-stream-combinations", True, "available"),
    ("smaller-source-sizes", False, "untested"),
    ("p010-image", True, "unavailable"),
    ("surface-ten-bit-encoder", True, "available"),
    ("deferred-development", True, "available"),
    ("cpu-gpu-scheduling", False, "untested"),
    ("retained-raw-workflows", True, "available"),
)

FAULT_TEXT = {
    PATH_NOT_LABELLED: "a listed path was neither tried nor explicitly left untested",
    UNTESTED_BLOCKS_ALL_UNAVAILABLE: (
        "an untested alternative rejects the conclusion that all ten-bit paths are unavailable"
    ),
    ONE_CODEC_MARKS_ALL: MUTANT,
    CONCLUSION_MISMATCH: "the conclusion does not match the tried and explicitly untested alternatives",
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


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def alternative(name: str, tried: bool, result: str) -> dict[str, Any]:
    return {"name": name, "tried": tried, "result": result}


def is_codec_interface(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in CODEC_MARKERS)


def labelling_of(tried: bool, result: str) -> str:
    """tried with a measured result, or explicitly untested. Anything else is invalid."""
    if tried and result in {"available", "unavailable"}:
        return "tried"
    if not tried and result == "untested":
        return "explicitly-untested"
    return "invalid"


def measure_tradeoff(result: str) -> dict[str, str]:
    """Untested paths stay unknown. A closed path is not given another path's quality."""
    if result == "available":
        return {"information": "retained", "quality": "open"}
    if result == "unavailable":
        return {"information": "not-delivered", "quality": "closed"}
    return {"information": "unknown", "quality": "unknown"}


def spread_one_codec_failure(alternatives: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Forbidden mutant: one unavailable codec interface marks every ten-bit path unavailable."""
    codec_failed = any(
        is_codec_interface(item["name"]) and item["result"] == "unavailable" for item in alternatives
    )
    if not codec_failed:
        return [dict(item) for item in alternatives]
    return [
        {"name": item["name"], "tried": True, "result": "unavailable"}
        for item in alternatives
    ]


def parse_alternative(value: object, index: int) -> dict[str, Any]:
    require(isinstance(value, dict), f"alternatives[{index}] must be an object")
    require(set(value) == ALTERNATIVE_KEYS, f"alternatives[{index}] keys are invalid")
    name = require_text(value["name"], f"alternatives[{index}].name")
    tried = require_bool(value["tried"], f"alternatives[{index}].tried")
    result = require_text(value["result"], f"alternatives[{index}].result")
    require(result in RESULTS, f"alternatives[{index}].result is not recognized")
    return alternative(name, tried, result)


def parse_alternatives(value: object) -> list[dict[str, Any]]:
    require(isinstance(value, list) and bool(value), "alternatives must be a non-empty list")
    rows = [parse_alternative(item, index) for index, item in enumerate(value)]
    names = [row["name"] for row in rows]
    require(len(names) == len(set(names)), "alternative names must be unique")
    return rows


def _counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"available": 0, "unavailable": 0, "untested": 0}
    for row in rows:
        counts[row["result"]] += 1
    return counts


def paths_comparable(rows: list[dict[str, Any]]) -> bool:
    return all(labelling_of(row["tried"], row["result"]) != "invalid" for row in rows)


def honestly_all_unavailable(rows: list[dict[str, Any]]) -> bool:
    """Every listed path was tried and is unavailable. One failure is not enough."""
    if len(rows) < 2 or not paths_comparable(rows):
        return False
    return all(row["tried"] is True and row["result"] == "unavailable" for row in rows)


def conclusion_matches(rows: list[dict[str, Any]], conclusion: str) -> bool:
    if conclusion not in CONCLUSIONS or not paths_comparable(rows):
        return False
    counts = _counts(rows)
    if conclusion == ALL_TEN_BIT_UNAVAILABLE:
        return honestly_all_unavailable(rows) and counts["untested"] == 0 and counts["available"] == 0
    if conclusion == TEN_BIT_PATH_AVAILABLE:
        return counts["available"] >= 1
    if conclusion == UNTESTED_REMAIN:
        return counts["untested"] >= 1
    if conclusion == NOT_IMPOSSIBLE:
        return not honestly_all_unavailable(rows)
    return False


def overclaims_every_path(rows: list[dict[str, Any]], conclusion: str) -> bool:
    """True when all-unavailable is asserted without every path independently unavailable."""
    if conclusion != ALL_TEN_BIT_UNAVAILABLE:
        return False
    return not honestly_all_unavailable(rows)


def analyze_computation(
    *,
    alternatives: list[dict[str, Any]],
    conclusion: str,
    claim: str,
    apply_mutant: bool,
) -> dict[str, Any]:
    faults: list[str] = []
    counts = _counts(alternatives)
    comparable = paths_comparable(alternatives)
    if not comparable:
        faults.append(PATH_NOT_LABELLED)
    if conclusion == ALL_TEN_BIT_UNAVAILABLE and counts["untested"] >= 1:
        faults.append(UNTESTED_BLOCKS_ALL_UNAVAILABLE)
    if overclaims_every_path(alternatives, conclusion):
        faults.append(ONE_CODEC_MARKS_ALL)
    matches = conclusion_matches(alternatives, conclusion)
    if not matches:
        faults.append(CONCLUSION_MISMATCH)
    if apply_mutant:
        faults.append(ONE_CODEC_MARKS_ALL)
    # The snapshot keeps each path's own result. The spread mutant is not applied.
    published = []
    for row in alternatives:
        tradeoff = measure_tradeoff(row["result"])
        published.append({
            "name": row["name"],
            "tried": row["tried"],
            "result": row["result"],
            "labelling": labelling_of(row["tried"], row["result"]),
            "sourceLineage": row["name"],
            "information": tradeoff["information"],
            "quality": tradeoff["quality"],
        })
    snapshot = {
        "alternatives": published,
        "conclusion": conclusion,
        "conclusionMatches": matches,
        "comparable": comparable,
        "availableCount": counts["available"],
        "unavailableCount": counts["unavailable"],
        "untestedCount": counts["untested"],
        "codecFailureCount": sum(
            1 for row in alternatives if is_codec_interface(row["name"]) and row["result"] == "unavailable"
        ),
        "spreadApplied": False,
        "allTenBitPathsUnavailable": honestly_all_unavailable(alternatives),
        "claim": claim,
    }
    extra_reasons = [
        "comparative rule: " + COMPARATIVE_RULE,
        "available "
        + str(counts["available"])
        + " unavailable "
        + str(counts["unavailable"])
        + " untested "
        + str(counts["untested"]),
    ]
    if snapshot["codecFailureCount"] and counts["available"]:
        extra_reasons.append(
            "one codec interface is unavailable and another ten-bit path stays "
            + published[[row["result"] for row in published].index("available")]["result"]
        )
    if counts["untested"]:
        extra_reasons.append("untested alternatives stay unknown; they are not marked unavailable")
    if matches:
        extra_reasons.append("conclusion matches: " + conclusion)
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
    require(OPEN_QUESTION in result["openQuestions"], "physical S23 not run must be noted")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(bool(result["reasons"]), "reasons must be non-empty")
    return result


def _core_from_mapping(mapping: dict) -> dict[str, Any]:
    evidence = require_text(mapping["evidenceId"], "evidenceId")
    claim = require_text(mapping["claim"], "claim")
    apply_mutant = require_bool(mapping["applyMutant"], "applyMutant")
    rows = parse_alternatives(mapping["alternatives"])
    conclusion = require_text(mapping["conclusion"], "conclusion")
    analysis = analyze_computation(
        alternatives=rows,
        conclusion=conclusion,
        claim=claim,
        apply_mutant=apply_mutant,
    )
    analysis["evidence"] = evidence
    analysis["claim"] = claim
    analysis["applyMutant"] = apply_mutant
    return analysis


def _reasons(analysis: dict[str, Any], lead: list[str], fault_text: dict[str, str] | None) -> list[str]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    reasons = list(lead)
    reasons.extend(analysis["extraReasons"])
    for token in analysis["faults"]:
        reasons.append(text.get(token, token))
    if ONE_CODEC_MARKS_ALL in analysis["faults"]:
        reasons.append("mutant rejected: " + MUTANT)
    if not analysis["faults"]:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("comparative decision recorded; not a physical qualification")
    return reasons


def assess(document: dict) -> dict[str, Any]:
    """Record a comparative alternative decision, or reject a mismatched conclusion."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    analysis = _core_from_mapping(document)
    reasons = _reasons(
        analysis,
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 not run",
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
    """Evaluate a phase document or a core alternative-path payload."""
    require(isinstance(payload, dict), "payload must be an object")
    if (
        "schemaVersion" in payload
        or "implementationBaseRevision" in payload
        or "phase" in payload
    ):
        return assess(payload)
    require(set(payload) == CORE_KEYS, "invalid payload keys")
    analysis = _core_from_mapping(payload)
    reasons = _reasons(
        analysis,
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 not run",
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
    analysis = _core_from_mapping(payload)
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
            "physical S23 not run",
            "oracle: " + ORACLE,
            case["expected"],
            "repeat " + bundle["repeat"],
        ],
        fault_text,
    )
    preserved = [bundle["evidence"], bundle["snapshot"], bundle["claim"], *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], analysis["faults"], reasons, preserved, questions, bundle["evidence"])


def fixture_alternatives() -> list[dict[str, Any]]:
    return [alternative(name, tried, result) for name, tried, result in FIXTURE_ROWS]


def core_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "alternatives": fixture_alternatives(),
        "conclusion": NOT_IMPOSSIBLE,
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
        "applyMutant": False,
        "alternatives": core["alternatives"],
        "conclusion": core["conclusion"],
    }
