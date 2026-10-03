#!/usr/bin/env python3
"""P012 dynamic-range profile combination planner.

Query ten-bit capability and supported dynamic-range profiles. Pairwise and
set constraints decide which preview and recording outputs may share a capture
request. Additional latency is copied only when a route exposes it. HLG,
HDR10, SDR, and RAW-derived Log stay separate source and encoding categories.

The fixture is an HLG-capable route that rejects an SDR preview in the same
capture request. The planner either rejects that mixed combination or records
an explicit independent monitoring route. It does not treat HLG support as
permission for arbitrary SDR and HDR surface coexistence.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P012-01 through TC-P012-08.
"""

from __future__ import annotations

import re
from typing import Any


BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
PLANNER_ID = "s23-dynamic-range-profile-fixture"
PHASE = "P012"
METHOD = (
    "Query ten-bit capability and supported dynamic-range profiles. "
    "Evaluate pairwise or set constraints for preview and recording outputs. "
    "Record additional latency information where exposed. "
    "Keep HLG, HDR10, SDR, and RAW-derived Log as separate source and encoding categories."
)
FIXTURE = "An HLG-capable route that rejects an SDR preview in the same capture request."
ORACLE = (
    "The planner rejects the mixed combination or explicitly chooses an "
    "independently qualified monitoring route."
)
MUTANT = "Assume HLG support implies arbitrary SDR and HDR surface coexistence."

HEX40 = re.compile(r"^[0-9a-f]{40}$")
CATEGORIES = ("HLG", "HDR10", "SDR", "RAW_LOG")
CATEGORY_LABELS = {
    "HLG": "HLG",
    "HDR10": "HDR10",
    "SDR": "SDR",
    "RAW_LOG": "RAW-derived Log",
}
ROLES = {"recording", "preview", "monitoring"}
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "plannerId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "tenBitCapable",
    "failedProperties",
    "routes",
    "constraints",
}
ROUTE_KEYS = {
    "routeId",
    "role",
    "profile",
    "category",
    "tenBit",
    "supported",
    "width",
    "height",
    "format",
    "queryError",
    "additionalLatencyNs",
}
CONSTRAINT_KEYS = {"constraintId", "kind", "members", "reason"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = {"rejected", "withheld", "candidate", "independent_monitor"}
SEPARATE_CATEGORIES = "HLG, HDR10, SDR, and RAW-derived Log remain separate categories"
MUTANT_REJECTION = "HLG support does not imply arbitrary SDR and HDR surface coexistence"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def _text(value: object, context: str) -> str:
    require(
        isinstance(value, str) and bool(value.strip()) and value == value.strip(),
        context + " must be a non-empty string",
    )
    return value


def _bool(value: object, context: str) -> bool:
    require(type(value) is bool, context + " must be a bool")
    return value


def _positive_int(value: object, context: str) -> int:
    require(type(value) is int and value > 0, context + " must be a positive int")
    return value


def _identity(route: dict) -> str:
    return f"{route['width']}x{route['height']}:{route['profile']}@{route['routeId']}"


def _check_route(route: object, index: int, seen: set[str]) -> dict:
    context = f"route {index}"
    parsed = _exact_keys(route, ROUTE_KEYS, context)
    route_id = _text(parsed["routeId"], context + " routeId")
    require(route_id not in seen, "duplicate routeId: " + route_id)
    seen.add(route_id)
    require(parsed["role"] in ROLES, context + " role must be recording, preview, or monitoring")
    require(parsed["profile"] in CATEGORIES, context + " profile must be HLG, HDR10, SDR, or RAW_LOG")
    require(parsed["category"] == parsed["profile"], context + " category must match profile")
    _bool(parsed["tenBit"], context + " tenBit")
    _bool(parsed["supported"], context + " supported")
    _positive_int(parsed["width"], context + " width")
    _positive_int(parsed["height"], context + " height")
    _text(parsed["format"], context + " format")
    query = parsed["queryError"]
    require(query is None or (isinstance(query, str) and bool(query.strip()) and query == query.strip()),
            context + " queryError must be a non-empty string or null")
    latency = parsed["additionalLatencyNs"]
    if latency is not None:
        require(type(latency) is int and latency >= 0,
                context + " additionalLatencyNs must be a non-negative int or null")
    return parsed


def _check_constraint(constraint: object, index: int, route_ids: set[str], seen: set[str]) -> dict:
    context = f"constraint {index}"
    parsed = _exact_keys(constraint, CONSTRAINT_KEYS, context)
    constraint_id = _text(parsed["constraintId"], context + " constraintId")
    require(constraint_id not in seen, "duplicate constraintId: " + constraint_id)
    seen.add(constraint_id)
    require(parsed["kind"] == "same_request_rejected",
            context + " kind must be same_request_rejected")
    members = parsed["members"]
    require(isinstance(members, list) and len(members) >= 2, context + " members must list at least two routes")
    checked: list[str] = []
    for member in members:
        require(isinstance(member, str) and member in route_ids, context + " member is not a known route")
        checked.append(member)
    require(len(checked) == len(set(checked)), context + " members must be unique")
    _text(parsed["reason"], context + " reason")
    return parsed


def validate_planner(document: dict) -> None:
    """Raise ValueError unless document is a P012 profile planner fixture."""
    parsed = _exact_keys(document, DOCUMENT_KEYS, "profile planner")
    require(type(parsed["schemaVersion"]) is int and parsed["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(parsed["phase"] == PHASE, "phase must be P012")
    require(parsed["plannerId"] == PLANNER_ID, "plannerId must be s23-dynamic-range-profile-fixture")
    revision = parsed["implementationBaseRevision"]
    require(revision == BASE_REVISION and isinstance(revision, str) and HEX40.fullmatch(revision) is not None,
            "profile planner needs the P012 implementation base revision")
    require(parsed["method"] == METHOD, "method does not match the P012 profile planner")
    require(parsed["fixture"] == FIXTURE, "fixture does not match the P012 profile planner")
    require(parsed["oracle"] == ORACLE, "oracle does not match the P012 profile planner")
    require(parsed["mutant"] == MUTANT, "mutant does not match the P012 profile planner")
    _bool(parsed["tenBitCapable"], "tenBitCapable")
    failed = parsed["failedProperties"]
    require(isinstance(failed, list) and all(isinstance(item, str) and bool(item.strip()) and item == item.strip()
                                             for item in failed),
            "failedProperties must be a list of non-empty strings")
    require(len(failed) == len(set(failed)), "failedProperties must be unique")
    routes = parsed["routes"]
    require(isinstance(routes, list) and routes, "routes must be a non-empty list")
    seen_routes: set[str] = set()
    for index, route in enumerate(routes):
        _check_route(route, index, seen_routes)
    constraints = parsed["constraints"]
    require(isinstance(constraints, list), "constraints must be a list")
    seen_constraints: set[str] = set()
    for index, constraint in enumerate(constraints):
        _check_constraint(constraint, index, seen_routes, seen_constraints)


def inventory(document: dict) -> list[dict]:
    """Return every route. A failed property or query does not drop the others.

    additionalLatencyNs is copied when exposed and left null when it is not.
    Category labels keep HLG, HDR10, SDR, and RAW-derived Log distinct.
    """
    validate_planner(document)
    rows: list[dict] = []
    for route in document["routes"]:
        rows.append({
            "identity": _identity(route),
            "routeId": route["routeId"],
            "role": route["role"],
            "profile": route["profile"],
            "category": route["category"],
            "categoryLabel": CATEGORY_LABELS[route["category"]],
            "tenBit": route["tenBit"],
            "supported": route["supported"],
            "queryError": route["queryError"],
            "additionalLatencyNs": route["additionalLatencyNs"],
            "format": route["format"],
            "width": route["width"],
            "height": route["height"],
        })
    return rows


def _preserved(document: dict) -> list[str]:
    preserved = [_identity(route) for route in document["routes"]]
    for route in document["routes"]:
        latency = route["additionalLatencyNs"]
        if latency is not None:
            preserved.append(f"latency:{route['routeId']}:{latency}")
    return preserved


def _questions(document: dict) -> list[str]:
    questions: list[str] = []
    for prop in document["failedProperties"]:
        questions.append(prop + " query failed; unrelated routes were retained")
    for route in document["routes"]:
        if route["queryError"] is not None:
            questions.append(
                f"route {route['routeId']} query error retained: {route['queryError']}"
            )
    for route in document["routes"]:
        if route["additionalLatencyNs"] is None:
            questions.append(f"additional latency not exposed for {route['routeId']}")
    if document["tenBitCapable"] is False:
        questions.append("ten-bit capability query is false; ten-bit fidelity is not claimed")
    if any(route["profile"] == "RAW_LOG" for route in document["routes"]):
        questions.append("sensor-derived Log is not established by a RAW-derived Log label")
    return questions


def _usable(route: dict, ten_bit_capable: bool) -> bool:
    if route["queryError"] is not None:
        return False
    if route["supported"] is not True:
        return False
    if route["tenBit"] is True and ten_bit_capable is not True:
        return False
    return True


def _unusable_reason(route: dict, ten_bit_capable: bool) -> str:
    if route["queryError"] is not None:
        return f"{route['routeId']} query error {route['queryError']} blocks selection"
    if route["supported"] is not True:
        return f"{route['routeId']} is not supported"
    if route["tenBit"] is True and ten_bit_capable is not True:
        return f"{route['routeId']} requires ten-bit capability that was not queried as true"
    raise ValueError("usable route has no unusable reason")


def _capture_ids(capture_request: object, by_id: dict[str, dict]) -> list[str]:
    require(isinstance(capture_request, list) and capture_request,
            "capture request must be a non-empty list")
    ids: list[str] = []
    for item in capture_request:
        require(isinstance(item, str) and bool(item.strip()) and item == item.strip(),
                "capture request ids must be non-empty strings")
        require(item in by_id, "unknown route: " + item)
        ids.append(item)
    require(len(ids) == len(set(ids)), "capture request ids must be unique")
    return ids


def _monitoring_id(monitoring_route: object, by_id: dict[str, dict], capture_ids: list[str]) -> str | None:
    if monitoring_route is None:
        return None
    require(isinstance(monitoring_route, str) and bool(monitoring_route.strip())
            and monitoring_route == monitoring_route.strip(),
            "monitoring route must be a non-empty string or null")
    require(monitoring_route in by_id, "unknown monitoring route: " + monitoring_route)
    require(by_id[monitoring_route]["role"] == "monitoring",
            "monitoring route must have role monitoring")
    require(monitoring_route not in capture_ids,
            "monitoring route must not be inside the capture request")
    return monitoring_route


def _violations(document: dict, capture_ids: list[str]) -> list[dict]:
    selected = set(capture_ids)
    found: list[dict] = []
    for constraint in document["constraints"]:
        if set(constraint["members"]) <= selected:
            found.append(constraint)
    return found


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict[str, Any]:
    require(decision in DECISIONS, "decision must not be qualified or allowed")
    require(decision not in {"qualified", "allowed"}, "decision must not be qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons), "reasons required")
    require(all(isinstance(item, str) for item in rejected), "rejectedClaims must be strings")
    require(preserved and all(isinstance(item, str) and item for item in preserved),
            "preservedResults must keep the inventory")
    require(all(isinstance(item, str) for item in questions), "openQuestions must be strings")
    result = {
        "caseId": PHASE,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def _selection_reasons(selected: list[dict], profile: str) -> list[str]:
    reasons = [
        f"capture request uses profile {profile}",
        "candidate is a host software label, not physical S23 qualification",
    ]
    if profile == "RAW_LOG":
        reasons.append("RAW-derived Log is not HLG, HDR10, SDR, or sensor-derived Log")
    for route in selected:
        latency = route["additionalLatencyNs"]
        if latency is not None:
            reasons.append(f"additional latency {latency} ns recorded for {route['routeId']}")
    if any(route["tenBit"] is True for route in selected):
        reasons.append(
            "ten-bit capability query is true on this host fixture; ten-bit fidelity is not claimed"
        )
    return reasons


def assess(document: dict, capture_request: list, monitoring_route: str | None = None) -> dict:
    """Plan one capture request without assuming HLG support implies coexistence.

    A cross-category request, or a request covered by a same_request_rejected
    constraint, is rejected. If monitoring_route is a usable route with role
    monitoring and it is not inside the capture request, the decision is
    independent_monitor instead: the mix stays rejected and the monitor is
    not pulled into the request. A single usable category is candidate.
    Unusable selections are withheld. The decision is never qualified or allowed.
    preservedResults always lists every route identity, plus latency tokens
    only where additionalLatencyNs was exposed.
    """
    inventory(document)
    by_id = {route["routeId"]: route for route in document["routes"]}
    capture_ids = _capture_ids(capture_request, by_id)
    monitor_id = _monitoring_id(monitoring_route, by_id, capture_ids)
    selected = [by_id[item] for item in capture_ids]
    profile_set = {route["profile"] for route in selected}
    violations = _violations(document, capture_ids)
    cross = len(profile_set) > 1
    questions = _questions(document)
    preserved = _preserved(document)
    ten_bit = document["tenBitCapable"]
    monitor_route = by_id[monitor_id] if monitor_id is not None else None
    monitor_ok = monitor_route is not None and _usable(monitor_route, ten_bit)

    if cross or violations:
        rejected = [_identity(route) for route in selected]
        reasons: list[str] = []
        if cross:
            rejected.append("cross-category-coexistence")
            reasons.append("mixed dynamic-range combination rejected")
            reasons.append(SEPARATE_CATEGORIES)
        if "HLG" in profile_set and ("SDR" in profile_set or "HDR10" in profile_set):
            rejected.append("hlg-implies-sdr-hdr-coexistence")
            reasons.append(MUTANT_REJECTION)
        if violations:
            reasons.append("declared same-request constraint rejects this combination")
        reasons.append("individual support does not prove same-request coexistence")
        for constraint in violations:
            span = "pairwise" if len(constraint["members"]) == 2 else "set"
            reasons.append(
                f"{span} constraint {constraint['constraintId']} rejects this capture request"
            )
            reasons.append(constraint["reason"])
            rejected.append("constraint:" + constraint["constraintId"])
        for route in selected:
            if not _usable(route, ten_bit):
                reasons.append(_unusable_reason(route, ten_bit))
        if monitor_ok:
            reasons.append(f"independent monitoring route {monitor_id} is not in the capture request")
            reasons.append(
                "choosing that monitoring route does not authorize SDR and HDR surfaces inside the capture request"
            )
            decision = "independent_monitor"
        else:
            if monitor_id is not None:
                reasons.append(f"monitoring route {monitor_id} is not usable and was not chosen")
            else:
                reasons.append("no independent monitoring route was chosen")
            decision = "rejected"
        return _result(decision, reasons, rejected, preserved, questions)

    unusable = [route for route in selected if not _usable(route, ten_bit)]
    if unusable or (monitor_id is not None and not monitor_ok):
        rejected = [_identity(route) for route in unusable]
        reasons = [_unusable_reason(route, ten_bit) for route in unusable]
        if monitor_id is not None and not monitor_ok:
            rejected.append(_identity(monitor_route))
            reasons.append(f"monitoring route {monitor_id} is not usable and was not chosen")
        reasons.append("selection withheld pending usable profile evidence")
        if any(route["tenBit"] is True and ten_bit is not True for route in unusable):
            reasons.append("ten-bit fidelity is not claimed")
        return _result("withheld", reasons, rejected, preserved, questions)

    profile = selected[0]["profile"]
    reasons = _selection_reasons(selected, profile)
    if monitor_ok:
        reasons.append(f"independent monitoring route {monitor_id} was chosen explicitly")
        reasons.append("the monitoring route is outside the capture request and is not coexistence")
        return _result("independent_monitor", reasons, [], preserved, questions)
    return _result("candidate", reasons, [], preserved, questions)
