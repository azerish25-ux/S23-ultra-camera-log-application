"""TC-P007-02 conflicting source-revision gate.

Distinct sha256 values stay distinct even when display names match. A current
revision that differs from the inspected revision is not treated as already
inspected: without an incremental review the inspection is invalidated and
unrelated evidence is kept; with an incremental review the change scope is
named. Equal revisions leave the inspection unchanged.
"""

from __future__ import annotations

CASE_ID = "TC-P007-02"
_SCOPES = frozenset({"documentation", "capture_interface", "none"})
_KEYS = (
    "caseId",
    "inspectionRevision",
    "currentRevision",
    "incrementalReview",
    "changeScope",
    "unrelatedEvidence",
    "profiles",
)


def evaluate(payload: dict) -> dict:
    """Return the TC-P007-02 disposition for a revision payload."""
    data = _validate(payload)
    preserved: list[str] = []
    reasons: list[str] = []

    seen: list[str] = []
    by_name: dict[str, list[str]] = {}
    for profile in data["profiles"]:
        digest = profile["sha256"]
        name = profile["displayName"]
        if digest not in seen:
            seen.append(digest)
            preserved.append(digest)
        hashes = by_name.setdefault(name, [])
        if digest not in hashes:
            hashes.append(digest)

    collided = [name for name, hashes in by_name.items() if len(hashes) > 1]
    if collided:
        listed = "; ".join(
            f"{name} -> {', '.join(by_name[name])}" for name in collided
        )
        reasons.append(
            "profiles with the same display name and different sha256 stay distinct "
            f"versions and are not keyed only by display name: {listed}"
        )
    else:
        reasons.append(
            "profile identity is the sha256 content hash, not the display name"
        )

    for item in data["unrelatedEvidence"]:
        preserved.append(item)
    if data["unrelatedEvidence"]:
        reasons.append("unrelated verified evidence is retained")
    else:
        reasons.append("no unrelated evidence was supplied to discard")

    inspection = data["inspectionRevision"]
    current = data["currentRevision"]
    scope = data["changeScope"]
    if inspection != current and not data["incrementalReview"]:
        reasons.append(
            "current revision differs from the inspection revision without incremental "
            "review; affected inspection assumptions are invalidated; the new revision "
            "is not treated as already inspected"
        )
        decision = "invalidated"
    elif inspection != current and data["incrementalReview"]:
        reasons.append(_scope_reason(scope))
        reasons.append(
            "current revision differs from the inspection revision and was incrementally "
            "reviewed; it is not treated as already inspected"
        )
        decision = "reviewed"
    else:
        reasons.append(
            "inspection revision matches the current revision; inspection assumptions "
            "are unchanged"
        )
        decision = "unchanged"

    if decision == "allowed":
        raise ValueError("decision must not be allowed")

    return _finish(decision, reasons, preserved)


def _scope_reason(scope: str) -> str:
    if scope == "documentation":
        return "incremental review covers documentation change scope documentation"
    if scope == "capture_interface":
        return (
            "incremental review covers capture interface change scope capture_interface"
        )
    return "incremental review covers change scope none"


def _validate(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    missing = [key for key in _KEYS if key not in payload]
    if missing:
        raise ValueError(f"bad payload: missing {', '.join(missing)}")
    if payload["caseId"] != CASE_ID:
        raise ValueError(f"wrong caseId: {payload['caseId']!r}")
    scope = payload["changeScope"]
    if scope not in _SCOPES:
        raise ValueError(f"bad changeScope: {scope!r}")
    evidence = payload["unrelatedEvidence"]
    if not isinstance(evidence, list):
        raise ValueError("unrelatedEvidence must be a list")
    copied: list[str] = []
    for index, item in enumerate(evidence):
        if not isinstance(item, str) or item == "":
            raise ValueError(f"unrelatedEvidence[{index}] must be a non-empty string")
        copied.append(item)
    return {
        "inspectionRevision": _text(payload["inspectionRevision"], "inspectionRevision"),
        "currentRevision": _text(payload["currentRevision"], "currentRevision"),
        "incrementalReview": _flag(payload["incrementalReview"], "incrementalReview"),
        "changeScope": scope,
        "unrelatedEvidence": copied,
        "profiles": _profiles(payload["profiles"]),
    }


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


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _flag(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _finish(decision: str, reasons: list[str], preserved: list[str]) -> dict:
    rejected: list[str] = []
    questions: list[str] = []
    lists = {
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    for label, items in lists.items():
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            raise ValueError(f"{label} must be a list of strings")
    if decision != "allowed" and not reasons:
        raise ValueError("reasons must be non-empty unless decision is allowed")
    return {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
