#!/usr/bin/env python3
"""P138 Build the first sourced recipe family.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not treat a title match as a stock or lens source.
"""

from __future__ import annotations

from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P138"
WORKSTREAM = 18
TITLE = "Build the first sourced recipe family"
GOAL = "Demonstrate the database with a small, well-supported set rather than hundreds of names."
METHOD = (
    "Use primary production accounts where available and separate daylight, low-light, "
    "monochrome, and format variants. Record the exact scope of each source. Do not extend "
    "a statement about a whole production into an unsupported claim about every shot."
)
FIXTURE = "A production account documenting several stocks used under different shooting conditions."
ORACLE = "The database creates separate supported variants and clearly marks any scene-specific reconstruction."
MUTANT = "Assign one stock and one lens to every scene because the film title matches."
DELIVERABLE = "Initial recipe family with source-to-field traceability"
DEPENDENCIES = ("P137",)

# The document sets max_entries. The declared maximum used by this phase is 12.
DECLARED_MAXIMUM = 12
TRACE_RULE = (
    "Each non-null stock or lens must have a trace {field, source_id} with a non-empty source_id. "
    "Assigning stock and lens because the title matches, with empty traces, is rejected. "
    "A family larger than the declared maximum (12 when the document sets max_entries) without "
    "sources is rejected. Unknown fields stay null rather than invented."
)

OPEN_QUESTION = "physical S23 capture was not run"
EVIDENCE_ID = "p138-recipe-family"
CLAIM = "sourced-recipe-family-host-reference"
FILM_TITLE = "North Sea Ledger"

TITLE_MATCH = "title-match-empty-traces"
UNSOURCED_STOCK = "unsourced-stock"
UNSOURCED_LENS = "unsourced-lens"
INVENTED = "invented-unknown-field"
OVERSIZE = "family-exceeds-declared-maximum-without-sources"
WHOLE_FILM = "whole-production-extended-to-every-shot"
RECON_FACT = "reconstruction-invented-production-fact"
RECON_DOC = "reconstruction-presented-as-documented-fact"
TRACE_NULL = "trace-for-null-field"

ENTRY_KEYS = {
    "recipe_id",
    "film_title",
    "stock",
    "lens",
    "traces",
    "variant",
    "scope",
    "reconstruction",
    "documented",
}
TRACE_KEYS = {"field", "source_id"}
TRACE_FIELDS = {"stock", "lens"}
VARIANTS = {"daylight", "low-light", "monochrome", "format", "scene"}
WHOLE_FILM_SCOPES = {
    "every-shot",
    "every-scene",
    "whole-film",
    "whole-production",
    "all-scenes",
    "title-match",
}
INVENTED_SENTINELS = frozenset({
    "unknown",
    "invented",
    "guess",
    "guessed",
    "tbd",
    "n/a",
    "unspecified",
    "placeholder",
})
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "max_entries",
    "family",
}
EVALUATE_KEYS = {"evidenceId", "repeat", "family", "max_entries", "applyMutant"}
COMMON_KEYS = {"evidenceId", "repeat", "family", "max_entries"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]
FAULT_TEXT = {
    TITLE_MATCH: MUTANT,
    UNSOURCED_STOCK: "a non-null stock requires a trace {field, source_id}",
    UNSOURCED_LENS: "a non-null lens requires a trace {field, source_id}",
    INVENTED: "unknown fields stay null rather than invented",
    OVERSIZE: (
        "a family larger than the declared maximum without sources is rejected"
    ),
    WHOLE_FILM: (
        "a whole-production statement must not become an unsupported claim about every shot"
    ),
    RECON_FACT: "a scene-specific reconstruction must not invent stock or lens",
    RECON_DOC: "a reconstruction must not be presented as a documented production fact",
    TRACE_NULL: "a trace must not invent a value for a null stock or lens",
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


def require_maximum(value: object) -> int:
    """Use 12 when the document sets max_entries at or above the declared maximum."""
    require(type(value) is int and value >= 1, "max_entries must be a positive integer")
    if value >= DECLARED_MAXIMUM:
        return DECLARED_MAXIMUM
    return value


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def trace(field: str, source_id: str) -> dict[str, str]:
    return {"field": field, "source_id": source_id}


def make_entry(
    recipe_id: str,
    film_title: str = FILM_TITLE,
    stock: str | None = None,
    lens: str | None = None,
    traces: list | None = None,
    variant: str = "scene",
    scope: str = "scene note",
    reconstruction: bool = False,
    documented: bool = False,
) -> dict[str, Any]:
    return {
        "recipe_id": recipe_id,
        "film_title": film_title,
        "stock": stock,
        "lens": lens,
        "traces": [] if traces is None else [dict(item) for item in traces],
        "variant": variant,
        "scope": scope,
        "reconstruction": reconstruction,
        "documented": documented,
    }


def sample_family() -> list[dict[str, Any]]:
    """Small production-account family: separate conditions, nulls where unknown."""
    return [
        make_entry(
            "daylight-5219",
            stock="5219",
            traces=[trace("stock", "prod-acct-daylight")],
            variant="daylight",
            scope="daylight exteriors",
            documented=True,
        ),
        make_entry(
            "low-light-5219",
            stock="5219",
            lens="Cooke S4 35mm",
            traces=[
                trace("stock", "prod-acct-low-light"),
                trace("lens", "prod-acct-low-light"),
            ],
            variant="low-light",
            scope="night interiors",
            documented=True,
        ),
        make_entry(
            "monochrome-5222",
            stock="5222",
            traces=[trace("stock", "prod-acct-mono")],
            variant="monochrome",
            scope="monochrome inserts",
            documented=True,
        ),
        make_entry(
            "format-5207",
            stock="5207",
            traces=[trace("stock", "prod-acct-format")],
            variant="format",
            scope="65mm plates only",
            documented=True,
        ),
        make_entry(
            "scene-12",
            variant="scene",
            scope="scene 12 only",
            reconstruction=True,
            documented=False,
        ),
    ]


def fixture_document() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "max_entries": DECLARED_MAXIMUM,
        "family": sample_family(),
    }


def parse_trace(raw: object, label: str) -> dict[str, str]:
    require(isinstance(raw, dict), label + " must be an object")
    require(set(raw) == TRACE_KEYS, label + " keys must be field and source_id")
    field = raw["field"]
    require(field in TRACE_FIELDS, label + " field must be stock or lens")
    source_id = raw["source_id"]
    require(
        isinstance(source_id, str) and bool(source_id.strip()) and source_id == source_id.strip(),
        label + " source_id must be non-empty",
    )
    return {"field": field, "source_id": source_id}


def parse_optional_name(value: object, label: str) -> str | None:
    if value is None:
        return None
    return require_text(value, label)


def parse_entry(raw: object, index: int) -> dict[str, Any]:
    label = f"family[{index}]"
    require(isinstance(raw, dict), label + " must be an object")
    require(set(raw) == ENTRY_KEYS, label + " keys are invalid")
    recipe_id = require_text(raw["recipe_id"], label + " recipe_id")
    film_title = require_text(raw["film_title"], label + " film_title")
    stock = parse_optional_name(raw["stock"], label + " stock")
    lens = parse_optional_name(raw["lens"], label + " lens")
    require(isinstance(raw["traces"], list), label + " traces must be a list")
    traces = [parse_trace(item, f"{label} traces[{trace_index}]") for trace_index, item in enumerate(raw["traces"])]
    variant = require_text(raw["variant"], label + " variant")
    require(variant in VARIANTS, label + " variant is not a supported condition")
    scope = require_text(raw["scope"], label + " scope")
    reconstruction = require_bool(raw["reconstruction"], label + " reconstruction")
    documented = require_bool(raw["documented"], label + " documented")
    return {
        "recipe_id": recipe_id,
        "film_title": film_title,
        "stock": stock,
        "lens": lens,
        "traces": traces,
        "variant": variant,
        "scope": scope,
        "reconstruction": reconstruction,
        "documented": documented,
    }


def has_trace(entry: dict, field: str) -> bool:
    return any(item["field"] == field for item in entry["traces"])


def entry_faults(entry: dict) -> list[str]:
    faults: list[str] = []
    for field, token in (("stock", UNSOURCED_STOCK), ("lens", UNSOURCED_LENS)):
        value = entry[field]
        if isinstance(value, str) and value.casefold() in INVENTED_SENTINELS:
            faults.append(INVENTED)
        if value is not None and not has_trace(entry, field):
            faults.append(token)
        if value is None and has_trace(entry, field):
            faults.append(TRACE_NULL)
    if entry["scope"].casefold() in WHOLE_FILM_SCOPES and (
        entry["stock"] is not None or entry["lens"] is not None
    ):
        faults.append(WHOLE_FILM)
    if entry["reconstruction"] and entry["documented"]:
        faults.append(RECON_DOC)
    if entry["reconstruction"] and (entry["stock"] is not None or entry["lens"] is not None):
        faults.append(RECON_FACT)
    return faults


def title_match_assignment(entries: list[dict]) -> bool:
    """Stock and lens assigned together, with empty traces, are a title match."""
    for entry in entries:
        if entry["stock"] is not None and entry["lens"] is not None and not entry["traces"]:
            return True
    return False


def analyze_family(family: object, maximum: int) -> dict[str, Any]:
    require(isinstance(family, list) and len(family) >= 1, "family must be a non-empty list")
    require(type(maximum) is int and maximum >= 1, "maximum must be a positive integer")
    entries: list[dict] = []
    seen: set[str] = set()
    faults: list[str] = []
    for index, raw in enumerate(family):
        entry = parse_entry(raw, index)
        require(entry["recipe_id"] not in seen, "duplicate recipe_id " + entry["recipe_id"])
        seen.add(entry["recipe_id"])
        faults.extend(entry_faults(entry))
        entries.append(entry)
    if title_match_assignment(entries):
        faults.append(TITLE_MATCH)
    without_sources = not any(entry["traces"] for entry in entries)
    if len(entries) > maximum and without_sources:
        faults.append(OVERSIZE)
    return {
        "entries": entries,
        "faults": dedupe(faults),
        "maximum": maximum,
        "withoutSources": without_sources,
        "reconstructions": [entry["recipe_id"] for entry in entries if entry["reconstruction"]],
        "variants": [entry["variant"] for entry in entries],
    }


def published_name(value: str | None) -> str | None:
    if isinstance(value, str) and value.casefold() in INVENTED_SENTINELS:
        return None
    return value


def public_family(analysis: dict) -> dict[str, Any]:
    return {
        "maximum": analysis["maximum"],
        "withoutSources": analysis["withoutSources"],
        "entries": [
            {
                "recipe_id": entry["recipe_id"],
                "film_title": entry["film_title"],
                "stock": published_name(entry["stock"]),
                "lens": published_name(entry["lens"]),
                "traces": [dict(item) for item in entry["traces"]],
                "variant": entry["variant"],
                "scope": entry["scope"],
                "reconstruction": entry["reconstruction"],
                "documented": entry["documented"],
            }
            for entry in analysis["entries"]
        ],
    }


def family_reasons(analysis: dict) -> list[str]:
    reasons = ["trace rule: " + TRACE_RULE]
    supported = [variant for variant in analysis["variants"] if variant != "scene"]
    if supported:
        reasons.append("separate supported variants: " + ", ".join(supported))
    if analysis["reconstructions"]:
        reasons.append(
            "scene-specific reconstruction marked: " + ", ".join(analysis["reconstructions"])
        )
    if analysis["withoutSources"]:
        reasons.append("family has no sources")
    else:
        reasons.append("source-to-field traces retained")
    reasons.append("declared maximum " + str(analysis["maximum"]))
    return reasons


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
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
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
    return result


def begin_family_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(COMMON_KEYS) | set(extra_keys), "invalid payload keys")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    repeat = require_text(payload["repeat"], "repeat")
    maximum = require_maximum(payload["max_entries"])
    analysis = analyze_family(payload["family"], maximum)
    return {
        "evidence": evidence,
        "repeat": repeat,
        "maximum": maximum,
        "analysis": analysis,
        "faults": list(analysis["faults"]),
    }


def finish_case(
    case: dict,
    bundle: dict,
    faults: list[str],
    extra_preserved: list | None = None,
    fault_text: dict | None = None,
) -> dict[str, Any]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        case["expected"],
        "repeat " + bundle["repeat"],
    ]
    reasons.extend(family_reasons(bundle["analysis"]))
    ordered = dedupe(faults)
    for token in ordered:
        reasons.append(text.get(token, token))
    if TITLE_MATCH in ordered:
        reasons.append("mutant rejected: " + MUTANT)
    if not ordered:
        reasons.append("recipe family recorded; not a physical qualification")
    preserved = [bundle["evidence"], public_family(bundle["analysis"]), *(extra_preserved or [])]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], ordered, reasons, preserved, questions, bundle["evidence"])


def _decision_reasons(analysis: dict, faults: list[str], *, include_phase: bool) -> list[str]:
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "goal: " + GOAL,
        "method: " + METHOD,
        "fixture: " + FIXTURE,
        "oracle: " + ORACLE,
    ]
    if include_phase:
        reasons.extend(family_reasons(analysis))
    ordered = dedupe(faults)
    for token in ordered:
        reasons.append(FAULT_TEXT.get(token, token))
    if TITLE_MATCH in ordered:
        reasons.append("mutant rejected: " + MUTANT)
    if not ordered:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("recipe family recorded; not a physical qualification")
    return reasons


def assess(document: dict) -> dict[str, Any]:
    """Record a sourced recipe family or reject unsourced title-match claims."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = require_text(document["evidenceId"], "evidenceId")
    claim = require_text(document["claim"], "claim")
    apply_mutant = require_bool(document["applyMutant"], "applyMutant")
    maximum = require_maximum(document["max_entries"])
    analysis = analyze_family(document["family"], maximum)
    faults = list(analysis["faults"])
    if apply_mutant and TITLE_MATCH not in faults:
        faults.append(TITLE_MATCH)
    reasons = _decision_reasons(analysis, faults, include_phase=True)
    preserved = [evidence, public_family(analysis), claim]
    return assemble(PHASE, faults, reasons, preserved, NON_CLAIM_QUESTIONS, evidence)


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate one family payload. Same result contract as assess."""
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == EVALUATE_KEYS, "invalid payload keys")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    require_text(payload["repeat"], "repeat")
    apply_mutant = require_bool(payload["applyMutant"], "applyMutant")
    maximum = require_maximum(payload["max_entries"])
    analysis = analyze_family(payload["family"], maximum)
    faults = list(analysis["faults"])
    if apply_mutant and TITLE_MATCH not in faults:
        faults.append(TITLE_MATCH)
    reasons = _decision_reasons(analysis, faults, include_phase=True)
    preserved = [evidence, public_family(analysis)]
    return assemble(PHASE, faults, reasons, preserved, NON_CLAIM_QUESTIONS, evidence)
