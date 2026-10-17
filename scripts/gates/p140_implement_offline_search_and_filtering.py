#!/usr/bin/env python3
"""P140 Implement offline search and filtering.

Host reference only. This module does not probe a device and does not qualify
a physical S23. Catalogue lookup is a local token index:

Retrieval rule: build a local token index from each catalogue record's id and
text fields. Query tokens are lowercase words. Results are the ids whose index
contains every query token, sorted deterministically. The same query twice
returns the same ids. A filter on a field is applied locally and must not drop
the query tokens. An empty query performs no remote call and returns an
explicit empty result, not a recommendation list. remote_model true or
network_used true is rejected.

Typo tolerance is off unless a non-negative ``typoTolerance`` is supplied.
Private user recipes are withheld from the index. Popularity is never a rank
and never a certification.
"""

from __future__ import annotations

import copy
import re
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P140"
WORKSTREAM = 18
TITLE = "Implement offline search and filtering"
GOAL = "Make the catalogue useful without network dependence or opaque recommendation behavior."
METHOD = (
    "Index titles, alternate titles, stock names, formats, scene families, and evidence quality. "
    "Support typo-tolerant discovery with explicit matching behavior. Keep local user recipes "
    "private and allow sorting by relevant technical criteria rather than invented popularity."
)
FIXTURE = (
    "A search for a misspelled film title while the phone is offline and a filter for "
    "monochrome large-format recipes."
)
ORACLE = (
    "The correct local candidates appear with their evidence status and no network request "
    "is required."
)
MUTANT = "Call a remote language model for every catalogue search."
DELIVERABLE = "Offline search index and deterministic retrieval tests"
DEPENDENCIES = ("P139",)
RETRIEVAL_RULE = (
    "Build a local token index from each catalogue record id and text fields. "
    "Query tokens are lowercase words. Results are ids containing every query token, "
    "sorted deterministically. The same query twice returns the same ids. "
    "A filter on a field is applied locally and must not drop the query tokens. "
    "An empty query returns no remote call and an explicit empty result, not a recommendation list. "
    "remote_model true or network_used true is rejected."
)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p140-offline-search"
CLAIM = "offline-search-and-filtering-host-reference"
MIN_TYPO_LENGTH = 4
WORD = re.compile(r"[a-z0-9]+")
EVIDENCE_RANK = {
    "documented": 0,
    "partial": 1,
    "unknown": 2,
    "user-reconstruction": 3,
    "preference": 4,
}
SORTS = frozenset({"id", "evidenceQuality", "popularity"})
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DOCUMENT_KEYS = frozenset({
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "remote_model",
    "network_used",
    "catalogue",
    "query",
    "filters",
    "typoTolerance",
    "sort",
})
EVAL_KEYS = frozenset({
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "remote_model",
    "network_used",
    "catalogue",
    "query",
    "filters",
    "typoTolerance",
    "sort",
    "dropQueryTokens",
    "recommendationIds",
})
NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]
REMOTE_MODEL = "remote-model-catalogue-search"
NETWORK_USED = "network-used-for-catalogue-search"
POPULARITY_SORT = "invented-popularity-sort"
DROPPED_TOKENS = "filter-dropped-query-tokens"
EMPTY_RECOMMENDATION = "empty-query-recommendation-list"
OPAQUE_RECOMMENDATION = "opaque-recommendation-list"
NONDETERMINISTIC = "nondeterministic-retrieval"

FIXTURE_CATALOGUE = [
    {
        "id": "night-hunter-lf",
        "title": "The Night Hunter",
        "alternateTitles": ["Night Hunter"],
        "stockNames": ["Eastman Double-X"],
        "formats": ["large-format"],
        "sceneFamilies": ["night exterior"],
        "evidenceQuality": "partial",
        "evidenceStatus": "partial",
        "monochrome": True,
        "privateRecipe": False,
        "popularity": 3,
    },
    {
        "id": "night-hunter-35",
        "title": "The Night Hunter",
        "alternateTitles": ["Hunter"],
        "stockNames": ["Kodak Vision3 250D"],
        "formats": ["35mm"],
        "sceneFamilies": ["day interior"],
        "evidenceQuality": "documented",
        "evidenceStatus": "documented",
        "monochrome": False,
        "privateRecipe": False,
        "popularity": 80,
    },
    {
        "id": "river-day-lf",
        "title": "River Day",
        "alternateTitles": ["Le Fleuve"],
        "stockNames": ["Eastman Double-X"],
        "formats": ["large-format"],
        "sceneFamilies": ["day exterior"],
        "evidenceQuality": "unknown",
        "evidenceStatus": "unknown",
        "monochrome": True,
        "privateRecipe": False,
        "popularity": 100,
    },
    {
        "id": "user-night-grade",
        "title": "The Night Hunter",
        "alternateTitles": ["Night Hunter user grade"],
        "stockNames": ["Eastman Double-X"],
        "formats": ["large-format"],
        "sceneFamilies": ["night exterior"],
        "evidenceQuality": "preference",
        "evidenceStatus": "user-reconstruction",
        "monochrome": True,
        "privateRecipe": True,
        "popularity": 1000,
    },
]


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


def require_number(value: object, label: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number",
    )
    number = float(value)
    require(number == number and number not in (float("inf"), float("-inf")), label + " must be finite")
    return number


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def query_tokens(text: str) -> list[str]:
    """Lowercase words in first-seen order, without duplicates."""
    require(isinstance(text, str), "query must be a string")
    tokens: list[str] = []
    for token in WORD.findall(text.casefold()):
        if token not in tokens:
            tokens.append(token)
    return tokens


def _walk_text(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.extend(WORD.findall(value.casefold()))
    elif isinstance(value, list):
        for item in value:
            found.extend(_walk_text(item))
    elif isinstance(value, dict):
        for item in value.values():
            found.extend(_walk_text(item))
    return found


def _check_json(value: Any, label: str) -> None:
    if value is None or type(value) is bool or isinstance(value, str):
        return
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        require(value == value and value not in (float("inf"), float("-inf")), label + " must be finite")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_json(item, f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            require(isinstance(key, str) and key.strip() and key == key.strip(), label + " keys must be non-empty strings")
            _check_json(item, label + "." + key)
        return
    raise ValueError(label + " must be JSON-compatible")


def _evidence_status(record: dict) -> str:
    status = record.get("evidenceStatus", record.get("evidenceQuality", "unknown"))
    if not isinstance(status, str) or not status.strip():
        return "unknown"
    return status


def _evidence_rank(record: dict) -> int:
    quality = record.get("evidenceQuality", record.get("evidenceStatus", "unknown"))
    if not isinstance(quality, str):
        return 50
    return EVIDENCE_RANK.get(quality, 50)


def build_token_index(records: list) -> dict[str, Any]:
    """Index id plus text fields. Private user recipes are withheld."""
    require(isinstance(records, list), "catalogue must be a list")
    by_id: dict[str, dict[str, Any]] = {}
    private_ids: list[str] = []
    for index, record in enumerate(records):
        require(isinstance(record, dict), f"catalogue[{index}] must be an object")
        _check_json(record, f"catalogue[{index}]")
        record_id = require_text(record.get("id"), f"catalogue[{index}].id")
        require(record_id not in by_id and record_id not in private_ids, "duplicate catalogue id " + record_id)
        private = record.get("privateRecipe", False)
        require(type(private) is bool, f"catalogue[{index}].privateRecipe must be a bool")
        if private:
            private_ids.append(record_id)
            continue
        stored = copy.deepcopy(record)
        tokens = set(query_tokens(record_id))
        for key, value in stored.items():
            if key == "id":
                continue
            tokens.update(_walk_text(value))
        by_id[record_id] = {
            "id": record_id,
            "tokens": tuple(sorted(tokens)),
            "record": stored,
            "evidenceStatus": _evidence_status(stored),
        }
    return {
        "by_id": by_id,
        "private_ids": tuple(sorted(private_ids)),
    }


def levenshtein(left: str, right: str, limit: int) -> int:
    if left == right:
        return 0
    if abs(len(left) - len(right)) > limit:
        return limit + 1
    previous = list(range(len(right) + 1))
    for i, ca in enumerate(left, 1):
        current = [i]
        row_min = i
        for j, cb in enumerate(right, 1):
            best = min(current[j - 1] + 1, previous[j] + 1, previous[j - 1] + (ca != cb))
            current.append(best)
            if best < row_min:
                row_min = best
        if row_min > limit:
            return limit + 1
        previous = current
    return previous[-1]


def _match_token(token: str, indexed: tuple[str, ...], tolerance: int) -> tuple[str, int] | None:
    exact_only = tolerance <= 0 or len(token) < MIN_TYPO_LENGTH
    if exact_only:
        if token in indexed:
            return token, 0
        return None
    best: tuple[str, int] | None = None
    for candidate in indexed:
        if candidate != token and len(candidate) < MIN_TYPO_LENGTH:
            continue
        if abs(len(candidate) - len(token)) > tolerance:
            continue
        distance = 0 if candidate == token else levenshtein(token, candidate, tolerance)
        if distance > tolerance:
            continue
        if best is None or distance < best[1] or (distance == best[1] and candidate < best[0]):
            best = (candidate, distance)
    return best


def explain_tokens(tokens: list[str], indexed: tuple[str, ...], tolerance: int) -> list[dict[str, Any]] | None:
    matched: list[dict[str, Any]] = []
    for token in tokens:
        found = _match_token(token, indexed, tolerance)
        if found is None:
            return None
        matched.append({"query": token, "indexed": found[0], "distance": found[1]})
    return matched


def _scalar_equal(actual: Any, expected: Any) -> bool:
    if isinstance(actual, str) and isinstance(expected, str):
        return actual.casefold() == expected.casefold()
    if type(actual) is bool or type(expected) is bool:
        return type(actual) is bool and type(expected) is bool and actual is expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return actual == expected
    return False


def _field_matches(record: dict, field: str, expected: Any) -> bool:
    if field not in record:
        return False
    actual = record[field]
    if isinstance(actual, list):
        return any(_scalar_equal(item, expected) for item in actual)
    return _scalar_equal(actual, expected)


def normalize_filters(filters: dict) -> dict[str, Any]:
    require(isinstance(filters, dict), "filters must be an object")
    normalized: dict[str, Any] = {}
    for key in sorted(filters):
        require(isinstance(key, str) and key.strip() and key == key.strip(), "filter field must be a non-empty string")
        value = filters[key]
        if isinstance(value, str):
            require(value.strip() and value == value.strip(), "filter string must be non-empty")
        elif type(value) is bool:
            pass
        elif isinstance(value, (int, float)):
            require_number(value, "filter " + key)
        else:
            raise ValueError("filter " + key + " must be a string, bool, or number")
        normalized[key] = value
    return normalized


def _filters_match(record: dict, filters: dict[str, Any]) -> bool:
    return all(_field_matches(record, field, expected) for field, expected in filters.items())


def _sort_hits(hits: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    if sort == "evidenceQuality":
        return sorted(hits, key=lambda item: (_evidence_rank(item["record"]), item["id"]))
    return sorted(hits, key=lambda item: item["id"])


def _collect(
    index: dict[str, Any],
    tokens: list[str],
    filters: dict[str, Any],
    tolerance: int,
    sort: str,
    apply_tokens: bool,
) -> list[dict[str, Any]]:
    if apply_tokens and not tokens:
        return []
    hits: list[dict[str, Any]] = []
    for entry in index["by_id"].values():
        matched = None
        if apply_tokens:
            matched = explain_tokens(tokens, entry["tokens"], tolerance)
            if matched is None:
                continue
        if not _filters_match(entry["record"], filters):
            continue
        hits.append({
            "id": entry["id"],
            "record": entry["record"],
            "evidenceStatus": entry["evidenceStatus"],
            "matchedTokens": matched if matched is not None else [],
        })
    return _sort_hits(hits, sort)


def retrieve(
    index: dict[str, Any],
    query: str,
    filters: dict | None = None,
    typo_tolerance: int = 0,
    sort: str = "id",
) -> list[str]:
    """Ids containing every query token, sorted deterministically.

    An empty query returns an explicit empty list. It does not browse the
    catalogue and it does not rank by popularity.
    """
    require(isinstance(index, dict) and "by_id" in index, "index is invalid")
    require(type(typo_tolerance) is int and typo_tolerance >= 0, "typo_tolerance must be a non-negative int")
    require(sort in {"id", "evidenceQuality"}, "sort is not a local technical order")
    tokens = query_tokens(query)
    applied = {} if filters is None else normalize_filters(filters)
    hits = _collect(index, tokens, applied, typo_tolerance, sort, True)
    return [hit["id"] for hit in hits]


def retrieval_trace(
    catalogue: list,
    query: str,
    filters: dict,
    typo_tolerance: int,
    sort: str,
) -> dict[str, Any]:
    require(type(typo_tolerance) is int and typo_tolerance >= 0, "typoTolerance must be a non-negative int")
    require(sort in SORTS, "sort is not recognized")
    applied_sort = "id" if sort == "popularity" else sort
    tokens = query_tokens(query)
    applied = normalize_filters(filters)
    index = build_token_index(catalogue)
    explicit_empty = not tokens
    first = _collect(index, tokens, applied, typo_tolerance, applied_sort, True)
    second = _collect(index, tokens, applied, typo_tolerance, applied_sort, True)
    filter_only = [] if explicit_empty else _collect(index, tokens, applied, typo_tolerance, applied_sort, False)
    ids = [hit["id"] for hit in first]
    repeated = [hit["id"] for hit in second]
    matches = [
        {
            "id": hit["id"],
            "evidenceStatus": hit["evidenceStatus"],
            "matchedTokens": hit["matchedTokens"],
        }
        for hit in first
    ]
    return {
        "ids": ids,
        "repeatedIds": repeated,
        "queryTokens": tokens,
        "filters": applied,
        "matches": matches,
        "remoteCall": False,
        "networkUsed": False,
        "explicitEmpty": explicit_empty,
        "recommendationList": False,
        "sortedBy": applied_sort,
        "queryTokensPreserved": True,
        "privateExcluded": list(index["private_ids"]),
        "filterOnlyIds": [hit["id"] for hit in filter_only],
    }


def judge_search(
    *,
    catalogue: list,
    query: str,
    filters: dict,
    typo_tolerance: int,
    sort: str,
    remote_model: bool,
    network_used: bool,
    apply_mutant: bool,
    drop_query_tokens: bool,
    recommendation_ids: list,
) -> tuple[list[str], dict[str, Any]]:
    require(isinstance(recommendation_ids, list), "recommendationIds must be a list")
    for index, item in enumerate(recommendation_ids):
        require_text(item, f"recommendationIds[{index}]")
    trace = retrieval_trace(catalogue, query, filters, typo_tolerance, sort)
    faults: list[str] = []
    if apply_mutant or remote_model:
        faults.append(MUTANT)
    if remote_model:
        faults.append(REMOTE_MODEL)
    if network_used:
        faults.append(NETWORK_USED)
    if sort == "popularity":
        faults.append(POPULARITY_SORT)
    if drop_query_tokens:
        faults.append(DROPPED_TOKENS)
    if recommendation_ids and trace["explicitEmpty"]:
        faults.append(EMPTY_RECOMMENDATION)
    elif recommendation_ids:
        faults.append(OPAQUE_RECOMMENDATION)
    if trace["ids"] != trace["repeatedIds"]:
        faults.append(NONDETERMINISTIC)
    if trace["explicitEmpty"] and trace["ids"]:
        faults.append(EMPTY_RECOMMENDATION)
    return dedupe(faults), trace


def _reasons_for(trace: dict[str, Any], faults: list[str], extras: list[str]) -> list[str]:
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "retrieval: " + RETRIEVAL_RULE,
        "goal: " + GOAL,
        "method: " + METHOD,
        "fixture: " + FIXTURE,
    ]
    reasons.extend(extras)
    reasons.append("queryTokens=" + ",".join(trace["queryTokens"]))
    reasons.append("sortedBy=" + trace["sortedBy"])
    reasons.append("remoteCall=false")
    reasons.append("networkUsed=false")
    if trace["explicitEmpty"]:
        reasons.append("explicit empty result; no recommendation list; no remote call")
    for match in trace["matches"]:
        rendered = ",".join(
            f"{item['query']}->{item['indexed']}:{item['distance']}" for item in match["matchedTokens"]
        )
        reasons.append(
            f"candidate {match['id']} evidenceStatus={match['evidenceStatus']} match={rendered}"
        )
    for token in faults:
        if token == MUTANT:
            reasons.append("mutant rejected: " + MUTANT)
        else:
            reasons.append("rejected: " + token)
    if not faults:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("local catalogue retrieval recorded; not a physical qualification")
    return reasons


def finish_result(
    case_id: str,
    evidence: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    extra_questions: list[str] | None = None,
) -> dict[str, Any]:
    evidence = require_text(evidence, "evidenceId")
    ordered = dedupe(faults)
    decision = "rejected" if ordered else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    if evidence not in preserved:
        preserved = [evidence, *preserved]
    questions = list(NON_CLAIM_QUESTIONS)
    if extra_questions:
        questions.extend(extra_questions)
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": ordered,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(all(isinstance(item, str) and item.strip() for item in result["reasons"]), "reasons must be text")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(OPEN_QUESTION in result["openQuestions"], "open question missing")
    return result


def _assemble(case_id: str, evidence: str, claim: str, faults: list[str], trace: dict[str, Any], extras: list[str], questions: list[str]) -> dict[str, Any]:
    reasons = _reasons_for(trace, faults, extras)
    preserved = [evidence, copy.deepcopy(trace), claim]
    return finish_result(case_id, evidence, faults, reasons, preserved, questions)


def fixture_catalogue() -> list[dict[str, Any]]:
    return copy.deepcopy(FIXTURE_CATALOGUE)


def fixture_document() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "remote_model": False,
        "network_used": False,
        "catalogue": fixture_catalogue(),
        "query": "nigt hunter",
        "filters": {"formats": "large-format", "monochrome": True},
        "typoTolerance": 1,
        "sort": "id",
    }


def assess(document: dict) -> dict[str, Any]:
    """Record a local offline retrieval or reject a remote-model catalogue search."""
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
    remote_model = require_bool(document["remote_model"], "remote_model")
    network_used = require_bool(document["network_used"], "network_used")
    require(isinstance(document["query"], str), "query must be a string")
    faults, trace = judge_search(
        catalogue=document["catalogue"],
        query=document["query"],
        filters=document["filters"],
        typo_tolerance=document["typoTolerance"],
        sort=document["sort"],
        remote_model=remote_model,
        network_used=network_used,
        apply_mutant=apply_mutant,
        drop_query_tokens=False,
        recommendation_ids=[],
    )
    return _assemble(PHASE, evidence, claim, faults, trace, [], [])


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate one offline query. Same result contract as assess."""
    require(isinstance(payload, dict), "payload must be an object")
    missing = EVAL_KEYS - set(payload)
    extra = set(payload) - EVAL_KEYS
    require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))
    evidence = require_text(payload["evidenceId"], "evidenceId")
    repeat = require_text(payload["repeat"], "repeat")
    claim = require_text(payload["claim"], "claim")
    faults, trace = judge_search(
        catalogue=payload["catalogue"],
        query=payload["query"],
        filters=payload["filters"],
        typo_tolerance=payload["typoTolerance"],
        sort=payload["sort"],
        remote_model=require_bool(payload["remote_model"], "remote_model"),
        network_used=require_bool(payload["network_used"], "network_used"),
        apply_mutant=require_bool(payload["applyMutant"], "applyMutant"),
        drop_query_tokens=require_bool(payload["dropQueryTokens"], "dropQueryTokens"),
        recommendation_ids=payload["recommendationIds"],
    )
    return _assemble(PHASE, evidence, claim, faults, trace, ["repeat " + repeat], [repeat])
