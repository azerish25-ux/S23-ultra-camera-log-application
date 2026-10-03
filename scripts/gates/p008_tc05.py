"""TC-P008-05. Measurement without units.

A number without a unit or coordinate domain cannot establish comparable
performance. Milliseconds are not microseconds, and display values are not
scene values. P008 never marks the phase complete from a local build: the
remote commit is preserved and a pending physical-device gate stays open.
"""

from __future__ import annotations

import math
from typing import Any

CASE_ID = "TC-P008-05"
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

# Canonical identity only. Different scales stay distinct so ms cannot pass as us.
_UNIT_ALIASES = {
    "ms": "ms",
    "msec": "ms",
    "millisecond": "ms",
    "milliseconds": "ms",
    "us": "us",
    "usec": "us",
    "µs": "us",
    "μs": "us",
    "microsecond": "us",
    "microseconds": "us",
    "ns": "ns",
    "nsec": "ns",
    "nanosecond": "ns",
    "nanoseconds": "ns",
    "s": "s",
    "sec": "s",
    "second": "s",
    "seconds": "s",
}


def evaluate(payload: Any) -> dict[str, Any]:
    """Judge measurement comparability. Never returns allowed or complete."""
    measurements, compare, remote_commit, local_build = _parse(payload)
    by_name = {item["name"]: item for item in measurements}
    incomplete = [item["name"] for item in measurements if item["unit"] is None or item["domain"] is None]
    complete = [item["name"] for item in measurements if item["name"] not in incomplete]
    questions = ["physical-device gate pending"]
    reasons = [
        "Physical-device gate is pending, so the phase is not complete.",
        f"Remote commit {remote_commit} is preserved.",
    ]
    if local_build:
        reasons.append("Local build success does not mark the phase complete.")
    else:
        reasons.append("A local build failure is not rewritten into phase completion.")

    if incomplete:
        for name in incomplete:
            reasons.append(
                f"Measurement {name} is missing a unit or coordinate domain; "
                "a number alone cannot establish comparable performance."
            )
            questions.append(f"unit or domain missing for {name}")
        return _result(
            "clarification_required",
            reasons,
            incomplete,
            [*complete, remote_commit],
            questions,
        )

    if compare is not None:
        left = by_name[compare[0]]
        right = by_name[compare[1]]
        unit_mismatch = _unit_key(left["unit"]) != _unit_key(right["unit"])
        domain_mismatch = _domain_key(left["domain"]) != _domain_key(right["domain"])
        if unit_mismatch or domain_mismatch:
            if unit_mismatch:
                reasons.append(
                    f"Unit mismatch: {left['name']} is {left['unit']} but {right['name']} is {right['unit']}."
                )
            if domain_mismatch:
                reasons.append(
                    f"Domain mismatch: {left['name']} is {left['domain']} but {right['name']} is {right['domain']}."
                )
            reasons.append(
                "Cross-domain comparison is blocked; milliseconds are not microseconds "
                "and display values are not scene values."
            )
            claim = f"{left['name']} vs {right['name']}"
            rejected = [left["name"]]
            if right["name"] != left["name"]:
                rejected.append(right["name"])
            rejected.append(claim)
            preserved = [item["name"] for item in measurements]
            preserved.append(remote_commit)
            return _result("blocked", reasons, rejected, preserved, questions)

    names = [item["name"] for item in measurements]
    reasons.append(
        "Measurements that share a unit and coordinate domain are comparable only; "
        "comparability is not phase completion."
    )
    return _result("comparable", reasons, [], [*names, remote_commit], questions)


def _parse(payload: Any) -> tuple[list[dict[str, Any]], tuple[str, str] | None, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    for key in ("measurements", "compare", "remoteCommit", "localBuildSucceeded"):
        if key not in payload:
            raise ValueError(f"payload missing {key}")
    raw_measurements = payload["measurements"]
    if not isinstance(raw_measurements, list) or not raw_measurements:
        raise ValueError("measurements must be a non-empty list")
    measurements: list[dict[str, Any]] = []
    index_by_name: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw_measurements):
        parsed = _measurement(item, index)
        if parsed["name"] in index_by_name:
            raise ValueError(f"duplicate measurement name: {parsed['name']}")
        measurements.append(parsed)
        index_by_name[parsed["name"]] = parsed
    compare = _compare(payload["compare"], index_by_name)
    remote_commit = payload["remoteCommit"]
    if not isinstance(remote_commit, str) or not remote_commit.strip():
        raise ValueError("remoteCommit must be a non-empty string")
    local_build = payload["localBuildSucceeded"]
    if type(local_build) is not bool:
        raise ValueError("localBuildSucceeded must be a boolean")
    return measurements, compare, remote_commit, local_build


def _measurement(item: Any, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError(f"measurements[{index}] must be an object")
    if "name" not in item or "value" not in item:
        raise ValueError(f"measurements[{index}] requires name and value")
    name = item["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"measurements[{index}].name must be a non-empty string")
    value = item["value"]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"measurements[{index}].value must be a finite number")
    unit = _optional_text(item.get("unit"), f"measurements[{index}].unit")
    domain = _optional_text(item.get("domain"), f"measurements[{index}].domain")
    return {"name": name.strip(), "value": value, "unit": unit, "domain": domain}


def _optional_text(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string or null")
    stripped = value.strip()
    return stripped or None


def _compare(value: Any, measurements: dict[str, dict[str, Any]]) -> tuple[str, str] | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("compare must be null or a pair of measurement names")
    left, right = value
    if not isinstance(left, str) or not isinstance(right, str) or not left.strip() or not right.strip():
        raise ValueError("compare names must be non-empty strings")
    left, right = left.strip(), right.strip()
    if left not in measurements or right not in measurements:
        raise ValueError("compare references an unknown measurement")
    return left, right


def _unit_key(unit: str) -> str:
    key = unit.strip().lower()
    return _UNIT_ALIASES.get(key, key)


def _domain_key(domain: str) -> str:
    return domain.strip().lower()


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    if decision in {"allowed", "complete"}:
        raise ValueError("P008 must not mark the phase allowed or complete")
    if not reasons:
        raise ValueError("reasons must be non-empty unless decision is allowed")
    body = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    if tuple(body) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    return body
