"""TC-P007-05 measurement-without-units gate.

A numeric measurement with no unit or coordinate domain cannot be evaluated.
Bare numbers are not an allowed result. Comparing different units or domains
(milliseconds with microseconds, display values with scene values) is blocked.
Complete measurements and distinct profile sha256 identities are preserved.
Identical display names do not merge profiles.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P007-05"
_DECISIONS = frozenset({"clarification_required", "blocked", "comparable"})
_KEYS = ("caseId", "measurements", "compare", "profiles")


def evaluate(payload: dict) -> dict:
    """Return the TC-P007-05 disposition for a measurement payload."""
    data = _validate(payload)
    measurements = data["measurements"]
    compare = data["compare"]
    profiles = data["profiles"]
    incomplete = [item for item in measurements if item["unit"] is None or item["domain"] is None]
    complete = [item for item in measurements if item["unit"] is not None and item["domain"] is not None]
    preserved = [item["name"] for item in complete]
    preserved.extend(_distinct_hashes(profiles))
    profile_reason = _profile_reason(profiles)

    if incomplete:
        names = [item["name"] for item in incomplete]
        reasons = [
            f"Measurement {name!r} is missing a unit or coordinate domain; "
            "a bare number cannot establish comparable performance."
            for name in names
        ]
        reasons.append(profile_reason)
        questions = [f"What unit and coordinate domain apply to {name!r}?" for name in names]
        return _finish("clarification_required", reasons, names, preserved, questions)

    if compare is not None:
        by_name = {item["name"]: item for item in measurements}
        left = by_name[compare[0]]
        right = by_name[compare[1]]
        if left["unit"] != right["unit"] or left["domain"] != right["domain"]:
            reasons = _cross_reasons(left, right)
            reasons.append(profile_reason)
            questions = [
                "Which shared unit and coordinate domain should be used to compare "
                f"{left['name']!r} and {right['name']!r}?"
            ]
            return _finish("blocked", reasons, [], preserved, questions)
        reasons = [
            f"Measurements {left['name']!r} and {right['name']!r} share unit "
            f"{left['unit']!r} and domain {left['domain']!r}."
        ]
    else:
        reasons = ["All measurements are complete and no cross-domain comparison was requested."]
    reasons.append(profile_reason)
    return _finish("comparable", reasons, [], preserved, [])


def _cross_reasons(left: dict, right: dict) -> list[str]:
    reasons = [
        f"Comparison of {left['name']!r} ({left['unit']}, {left['domain']}) with "
        f"{right['name']!r} ({right['unit']}, {right['domain']}) crosses domains and is blocked."
    ]
    units = {left["unit"], right["unit"]}
    domains = {left["domain"], right["domain"]}
    if units == {"ms", "us"} or units == {"milliseconds", "microseconds"}:
        reasons.append("Comparing milliseconds with microseconds is not comparable performance.")
    if domains == {"display", "scene"}:
        reasons.append("Comparing display values with scene values is not comparable performance.")
    if len(reasons) == 1:
        reasons.append("Measurements in different units or coordinate domains are not comparable.")
    return reasons


def _validate(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    missing = [key for key in _KEYS if key not in payload]
    if missing:
        raise ValueError(f"bad payload: missing {', '.join(missing)}")
    if payload["caseId"] != CASE_ID:
        raise ValueError(f"wrong caseId: {payload['caseId']!r}")
    measurements = _measurements(payload["measurements"])
    names = {item["name"] for item in measurements}
    return {
        "measurements": measurements,
        "compare": _compare(payload["compare"], names),
        "profiles": _profiles(payload["profiles"]),
    }


def _measurements(value: object) -> list[dict]:
    if not isinstance(value, list):
        raise ValueError("measurements must be a list")
    measurements: list[dict] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"measurements[{index}] must be a dict")
        for key in ("name", "value", "unit", "domain"):
            if key not in item:
                raise ValueError(f"measurements[{index}] missing {key}")
        name = _text(item["name"], f"measurements[{index}].name")
        if name in seen:
            raise ValueError(f"duplicate measurement name: {name}")
        seen.add(name)
        measurements.append(
            {
                "name": name,
                "value": _number(item["value"], f"measurements[{index}].value"),
                "unit": _optional_text(item["unit"], f"measurements[{index}].unit"),
                "domain": _optional_text(item["domain"], f"measurements[{index}].domain"),
            }
        )
    return measurements


def _compare(value: object, names: set[str]) -> tuple[str, str] | None:
    if value is None:
        return None
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(isinstance(item, str) and item != "" for item in value)
    ):
        raise ValueError("compare must be null or two measurement names")
    if value[0] not in names or value[1] not in names:
        raise ValueError("compare refers to an unknown measurement")
    return value[0], value[1]


def _profiles(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError("profiles must be a list")
    profiles: list[dict[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"profiles[{index}] must be a dict")
        for key in ("displayName", "sha256"):
            if key not in item:
                raise ValueError(f"profiles[{index}] missing {key}")
        profiles.append(
            {
                "displayName": _text(item["displayName"], f"profiles[{index}].displayName"),
                "sha256": _text(item["sha256"], f"profiles[{index}].sha256"),
            }
        )
    return profiles


def _distinct_hashes(profiles: list[dict[str, str]]) -> list[str]:
    seen: list[str] = []
    for profile in profiles:
        digest = profile["sha256"]
        if digest not in seen:
            seen.append(digest)
    return seen


def _profile_reason(profiles: list[dict[str, str]]) -> str:
    by_name: dict[str, list[str]] = {}
    for profile in profiles:
        hashes = by_name.setdefault(profile["displayName"], [])
        if profile["sha256"] not in hashes:
            hashes.append(profile["sha256"])
    collided = [name for name, hashes in by_name.items() if len(hashes) > 1]
    if collided:
        listed = "; ".join(f"{name} -> {', '.join(by_name[name])}" for name in collided)
        return (
            "profiles with the same display name and different sha256 stay distinct "
            f"versions and are not keyed only by display name: {listed}"
        )
    return "profile identity is the sha256 content hash, not the display name"


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _text(value, label)


def _number(value: object, label: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return value


def _finish(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision == "allowed":
        raise ValueError(f"unexpected decision: {decision}")
    lists = {
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    for label, items in lists.items():
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            raise ValueError(f"{label} must be a list of strings")
    if not reasons:
        raise ValueError("reasons must be non-empty unless decision is allowed")
    return {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
