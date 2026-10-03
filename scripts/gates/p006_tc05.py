#!/usr/bin/env python3
"""TC-P006-05: measurement without units or a coordinate domain.

A numeric value cannot establish comparable performance until both its unit
and domain are present. Comparing distinct domains (milliseconds versus
microseconds, display versus scene, or any other pair) is blocked.
"""

from __future__ import annotations

import math
from typing import Any

CASE_ID = "TC-P006-05"


def evaluate(payload: dict) -> dict:
    """Return the TC-P006-05 gate decision for one measurement payload."""
    measurements, compare = _parse(payload)
    incomplete = [item for item in measurements if item["unit"] is None or item["domain"] is None]
    if incomplete:
        return _clarification(measurements, incomplete)
    if compare is not None:
        left, right = compare
        if left["domain"] != right["domain"]:
            return _blocked(measurements, left, right)
    shared = None if compare is None else compare[0]["domain"]
    return _comparable(measurements, shared)


def _parse(
    payload: object,
) -> tuple[list[dict[str, Any]], tuple[dict[str, Any], dict[str, Any]] | None]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    if payload.get("caseId") != CASE_ID:
        raise ValueError(f"wrong caseId: {payload.get('caseId')!r}")
    raw_measurements = payload.get("measurements")
    if not isinstance(raw_measurements, list):
        raise ValueError("measurements must be a list")
    measurements: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_measurements):
        measurements.append(_measurement(raw, index, seen))
    compare = _compare(payload["compare"] if "compare" in payload else None, measurements)
    return measurements, compare


def _measurement(raw: object, index: int, seen: set[str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"measurements[{index}] must be an object")
    if "name" not in raw or "value" not in raw:
        raise ValueError(f"measurements[{index}] requires name and value")
    name = raw["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"measurements[{index}] name must be a non-empty string")
    if name in seen:
        raise ValueError(f"duplicate measurement name: {name}")
    seen.add(name)
    value = raw["value"]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"measurements[{index}] value must be a finite number")
    unit = _optional_label(raw["unit"] if "unit" in raw else None, f"measurements[{index}].unit")
    domain = _optional_label(raw["domain"] if "domain" in raw else None, f"measurements[{index}].domain")
    return {"name": name, "value": value, "unit": unit, "domain": domain}


def _optional_label(value: object, context: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{context} must be a string or null")
    if not value.strip():
        return None
    return value


def _compare(
    raw: object, measurements: list[dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    if raw is None:
        return None
    if (
        not isinstance(raw, list)
        or len(raw) != 2
        or not all(isinstance(item, str) and item.strip() for item in raw)
    ):
        raise ValueError("compare must be null or a list of two measurement names")
    by_name = {item["name"]: item for item in measurements}
    resolved: list[dict[str, Any]] = []
    for name in raw:
        if name not in by_name:
            raise ValueError(f"compare name not in measurements: {name}")
        resolved.append(by_name[name])
    return resolved[0], resolved[1]


def _finish(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision == "allowed":
        raise ValueError("a bare number must not decision allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty unless decision is allowed")
    for label, items in (
        ("reasons", reasons),
        ("rejectedClaims", rejected),
        ("preservedResults", preserved),
        ("openQuestions", questions),
    ):
        if not isinstance(items, list) or not all(isinstance(item, str) and item for item in items):
            raise ValueError(f"{label} must be a list of non-empty strings")
    return {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }


def _clarification(measurements: list[dict[str, Any]], incomplete: list[dict[str, Any]]) -> dict:
    rejected = [item["name"] for item in incomplete]
    rejected_names = set(rejected)
    preserved = [item["name"] for item in measurements if item["name"] not in rejected_names]
    reasons: list[str] = []
    questions = ["clarification required before evaluating the threshold"]
    for item in incomplete:
        missing: list[str] = []
        if item["unit"] is None:
            missing.append("unit")
        if item["domain"] is None:
            missing.append("domain")
        if missing == ["unit", "domain"]:
            reasons.append(f"{item['name']} has a numeric value but unit and domain are missing")
        else:
            reasons.append(f"{item['name']} has a numeric value but {missing[0]} is missing")
        questions.append(f"clarify {item['name']} before threshold evaluation")
    if any(item["unit"] is None for item in incomplete):
        reasons.append("a bare number cannot establish comparable performance")
    else:
        reasons.append("domain is required before a numeric threshold can be evaluated")
    return _finish("clarification_required", reasons, rejected, preserved, questions)


def _blocked(
    measurements: list[dict[str, Any]], left: dict[str, Any], right: dict[str, Any]
) -> dict:
    left_domain = str(left["domain"])
    right_domain = str(right["domain"])
    reasons = [
        (
            f"comparison of {left['name']} and {right['name']} is blocked because domains differ: "
            f"{left_domain} vs {right_domain}"
        ),
        "units do not make distinct domains comparable",
    ]
    rejected = [f"compare:{left['name']}:{left_domain}:{right['name']}:{right_domain}"]
    preserved = [item["name"] for item in measurements]
    return _finish("blocked", reasons, rejected, preserved, [])


def _comparable(measurements: list[dict[str, Any]], shared_domain: str | None) -> dict:
    if shared_domain is None:
        reasons = ["all measurements have unit and domain and no cross-domain comparison was requested"]
    else:
        reasons = [
            f"all measurements have unit and domain and compare shares domain {shared_domain}"
        ]
    preserved = [item["name"] for item in measurements]
    return _finish("comparable", reasons, [], preserved, [])
