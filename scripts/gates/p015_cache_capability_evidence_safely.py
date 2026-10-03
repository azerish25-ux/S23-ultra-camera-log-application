#!/usr/bin/env python3
"""P015 capability-cache invalidation and historical evidence viewer.

Cached probes are keyed by build fingerprint, app protocol version, route,
and codec identity. Immutable historical measurements stay inspectable and
are not the current selection cache. A stale candidate is revalidated on
selection. A previously working mode that no longer matches the environment
keeps an explicit reason and is not certified.

The deliberate fault keys the cache only by the marketing string
"Galaxy S23 Ultra". This module rejects that fault. It does not probe a
device, does not qualify a physical S23, and does not execute TC-P015-01
through TC-P015-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P015"
CASE_ID = "P015"
METHOD = (
    "Key cached probes by build fingerprint, app protocol version, route, and codec identity. "
    "Separate immutable historical measurements from the current selection cache. "
    "Revalidate stale candidates on selection and retain a reason when a previously working "
    "mode becomes unavailable."
)
FIXTURE = (
    "A firmware update with the same marketing phone name but a changed codec capability response."
)
ORACLE = (
    "The old report remains inspectable while the current planner refuses to certify "
    "the changed route from stale data."
)
MUTANT = "Key the cache only by the string Galaxy S23 Ultra."
MUTANT_KEY = "Galaxy S23 Ultra"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
CACHE_ID = "s23-capability-cache-fixture"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
KEY_FIELDS = ("buildFingerprint", "appProtocolVersion", "route", "codecIdentity")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "cacheId",
    "implementationBaseRevision",
    "marketingName",
    "historical",
    "selectionCache",
    "currentEnvironment",
}
HISTORICAL_KEYS = {
    "reportId",
    "immutable",
    "buildFingerprint",
    "appProtocolVersion",
    "route",
    "codecIdentity",
    "codecCapabilityResponse",
    "marketingName",
    "previouslyWorking",
}
SELECTION_KEYS = {
    "candidateId",
    "sourceReportId",
    "buildFingerprint",
    "appProtocolVersion",
    "route",
    "codecIdentity",
    "codecCapabilityResponse",
    "marketingName",
    "previouslyWorking",
}
CURRENT_KEYS = {
    "buildFingerprint",
    "appProtocolVersion",
    "route",
    "codecIdentity",
    "codecCapabilityResponse",
    "marketingName",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = {"withheld", "reused"}
FORBIDDEN = {"qualified", "allowed"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def _text(value: object, context: str) -> str:
    require(isinstance(value, str) and bool(value.strip()) and value == value.strip(),
            context + " must be a non-empty string")
    return value


def _bool(value: object, context: str) -> bool:
    require(type(value) is bool, context + " must be a bool")
    return value


def cache_key(record: dict) -> str:
    """Identity key. Marketing name and capability text are not key material.

    A firmware update that keeps the marketing phone name still changes this
    key when the build fingerprint changes. Codec identity and app protocol
    version are part of the key as well.
    """
    require(isinstance(record, dict), "cache record must be an object")
    parts: list[str] = []
    for field in KEY_FIELDS:
        require(field in record, "cache record missing " + field)
        parts.append(field + "=" + _text(record[field], field))
    key = "|".join(parts)
    require(MUTANT_KEY not in key, "marketing name must not be a cache key")
    return key


def mutant_key(record: dict) -> str:
    """Deliberate fault: the only key material is the string Galaxy S23 Ultra.

    assess_selection must not accept a hit from this key. It exists so tests
    can show the fault would collide while the real key does not.
    """
    require(isinstance(record, dict), "cache record must be an object")
    name = _text(record.get("marketingName"), "marketingName")
    require(name == MUTANT_KEY, "mutant key requires marketing name Galaxy S23 Ultra")
    return MUTANT_KEY


def _identity_record(record: dict, context: str, fields: set[str], marketing: str) -> dict:
    checked = exact_keys(record, fields, context)
    for field in KEY_FIELDS:
        _text(checked[field], context + " " + field)
    _text(checked["codecCapabilityResponse"], context + " codecCapabilityResponse")
    name = _text(checked["marketingName"], context + " marketingName")
    require(name == marketing, context + " marketing name must match the document")
    if "previouslyWorking" in fields:
        _bool(checked["previouslyWorking"], context + " previouslyWorking")
    if "immutable" in fields:
        require(checked["immutable"] is True, context + " must be immutable")
    return checked


def validate_cache(document: dict) -> None:
    """Raise ValueError unless document is a P015 capability-cache fixture."""
    exact_keys(document, DOCUMENT_KEYS, "capability cache")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P015")
    require(document["cacheId"] == CACHE_ID, "cacheId must be s23-capability-cache-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "capability cache needs the P015 implementation base revision")
    marketing = _text(document["marketingName"], "marketingName")
    historical = document["historical"]
    require(isinstance(historical, list) and historical, "historical must be a non-empty list")
    seen_reports: set[str] = set()
    for index, item in enumerate(historical):
        checked = _identity_record(item, f"historical[{index}]", HISTORICAL_KEYS, marketing)
        require(checked["immutable"] is True, f"historical[{index}] must be immutable")
        report_id = _text(checked["reportId"], f"historical[{index}] reportId")
        require(report_id not in seen_reports, "duplicate historical reportId: " + report_id)
        seen_reports.add(report_id)
    selection = document["selectionCache"]
    require(isinstance(selection, list), "selectionCache must be a list")
    seen_candidates: set[str] = set()
    for index, item in enumerate(selection):
        checked = _identity_record(item, f"selectionCache[{index}]", SELECTION_KEYS, marketing)
        candidate_id = _text(checked["candidateId"], f"selectionCache[{index}] candidateId")
        require(candidate_id not in seen_candidates, "duplicate candidateId: " + candidate_id)
        seen_candidates.add(candidate_id)
        source = _text(checked["sourceReportId"], f"selectionCache[{index}] sourceReportId")
        require(source in seen_reports, "selection sourceReportId is not historical: " + source)
    _identity_record(document["currentEnvironment"], "currentEnvironment", CURRENT_KEYS, marketing)


def _matches_current(record: dict, current: dict) -> bool:
    return (
        cache_key(record) == cache_key(current)
        and record["codecCapabilityResponse"] == current["codecCapabilityResponse"]
        and record["route"] == current["route"]
    )


def view_history(document: dict) -> list[dict]:
    """Return immutable historical measurements. None of them are current certification."""
    validate_cache(document)
    viewed: list[dict] = []
    for item in document["historical"]:
        viewed.append({
            "reportId": item["reportId"],
            "immutable": True,
            "cacheKey": cache_key(item),
            "route": item["route"],
            "codecCapabilityResponse": item["codecCapabilityResponse"],
            "currentCertification": False,
        })
    return viewed


def current_selection(document: dict) -> list[dict]:
    """Selection-cache entries that survive revalidation against the current environment.

    Stale candidates are omitted. Historical reports are not copied in.
    A marketing-name collision is not enough to keep an entry.
    """
    validate_cache(document)
    current = document["currentEnvironment"]
    kept: list[dict] = []
    for item in document["selectionCache"]:
        if _matches_current(item, current):
            kept.append({
                "candidateId": item["candidateId"],
                "sourceReportId": item["sourceReportId"],
                "cacheKey": cache_key(item),
                "reusable": True,
                "certified": False,
            })
    return kept


def mutant_selection(document: dict) -> list[str]:
    """What the deliberate fault would keep: previously working marketing-name hits.

    This is not the planner. assess_selection must disagree whenever this
    list contains a candidate the real key would drop.
    """
    validate_cache(document)
    kept: list[str] = []
    for item in document["selectionCache"]:
        if item["previouslyWorking"] and mutant_key(item) == MUTANT_KEY:
            kept.append(item["candidateId"])
    return kept


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict[str, Any]:
    require(decision in DECISIONS, "decision must be withheld or reused")
    require(decision not in FORBIDDEN, "decision must not be qualified or allowed")
    require(bool(reasons), "reasons required")
    require(all(isinstance(item, str) and item for item in reasons), "reasons must be non-empty strings")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def assess_selection(document: dict) -> dict:
    """Revalidate the current route. Refuse to certify it from stale data.

    Historical report ids stay in preservedResults. The decision is withheld
    when the route's evidence or selection candidate does not match the
    current build, protocol, route, codec identity, and capability response.
    A matching selection entry is reused as a host cache hit only. That is
    never qualified or allowed physical capture.
    """
    validate_cache(document)
    current = document["currentEnvironment"]
    historical = document["historical"]
    preserved = [item["reportId"] for item in historical]
    route_history = [item for item in historical if item["route"] == current["route"]]
    fresh_history = [item for item in route_history if _matches_current(item, current)]
    stale_history = [item for item in route_history if item not in fresh_history]
    route_selection = [item for item in document["selectionCache"] if item["route"] == current["route"]]
    fresh_selection = [item for item in route_selection if _matches_current(item, current)]
    stale_selection = [item for item in route_selection if item not in fresh_selection]
    marketing_collision = any(
        item["marketingName"] == current["marketingName"] == MUTANT_KEY
        and cache_key(item) != cache_key(current)
        for item in (stale_history + stale_selection)
    )

    if fresh_selection and fresh_history:
        reasons = [
            "selection cache matches build fingerprint, app protocol version, route, and codec identity",
            "capability response matches the current environment",
            "reuse is a host cache decision and is not physical S23 qualification",
            "marketing name is not the cache key",
        ]
        return _result("reused", reasons, [], preserved, [])

    reasons = [
        "old report remains inspectable as historical evidence",
        "current planner refuses to certify the changed route from stale data",
    ]
    rejected = ["stale-route-certification"]
    questions = ["requalification required before the changed route can be selected"]
    unavailable = [
        item for item in stale_selection + stale_history if item["previouslyWorking"]
    ]
    if unavailable:
        reasons.append(
            "previously working mode is unavailable under the current build, protocol, route, or codec identity"
        )
    response_changes = [
        item for item in stale_history + stale_selection
        if item["codecCapabilityResponse"] != current["codecCapabilityResponse"]
    ]
    if response_changes:
        previous = response_changes[0]["codecCapabilityResponse"]
        reasons.append(
            "codec capability response changed from "
            + previous
            + " to "
            + current["codecCapabilityResponse"]
        )
    if marketing_collision:
        rejected.append("marketing-name-cache-hit")
        reasons.append("marketing name Galaxy S23 Ultra does not bypass the changed environment")
    if not route_history:
        reasons.append("no historical measurement exists for the current route")
    return _result("withheld", reasons, rejected, preserved, questions)
