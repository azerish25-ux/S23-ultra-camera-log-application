#!/usr/bin/env python3
"""TC-P007-03 missing-provenance gate.

Identical display names with different content hashes are distinct fixtures.
Unknown or denied redistribution rights exclude a fixture from the public
bundle. A visual result never becomes a reproducibility decision.
"""
from __future__ import annotations

from typing import Any

CASE_ID = "TC-P007-03"
KINDS = {"model", "stock_profile", "movie_reference", "generated_screenshot"}
RIGHTS = {"unknown", "permitted", "denied"}
PAYLOAD_KEYS = {"caseId", "fixtures"}
FIXTURE_KEYS = {"id", "kind", "displayName", "sha256", "provenance", "visualResult", "rights"}
PROVENANCE_KEYS = {"origin", "owner", "acquiredAt", "permittedUse"}
RESULT_KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _exact_keys(value: dict, required: set[str], context: str) -> None:
    missing = required - set(value)
    extra = set(value) - required
    _require(not missing, "bad payload: " + context + " missing fields: " + ", ".join(sorted(missing)))
    _require(not extra, "bad payload: " + context + " unexpected fields: " + ", ".join(sorted(extra)))


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[dict], questions: list[str]) -> dict:
    _require(decision != "reproducible", "visual result cannot produce decision reproducible")
    _require(decision == "allowed" or bool(reasons), "reasons must be non-empty unless decision is allowed")
    value = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    _require(tuple(value) == RESULT_KEYS, "result keys drifted")
    return value


def _validate_provenance(value: object, context: str) -> None:
    _require(isinstance(value, dict), "bad payload: " + context + " provenance must be an object or null")
    _exact_keys(value, PROVENANCE_KEYS, context + " provenance")
    for key in ("origin", "owner", "acquiredAt", "permittedUse"):
        _require(_text(value[key]), "bad payload: " + context + " provenance." + key + " must be non-empty text")


def _validate(payload: Any) -> list[dict]:
    _require(isinstance(payload, dict), "bad payload")
    _exact_keys(payload, PAYLOAD_KEYS, "payload")
    _require(payload.get("caseId") == CASE_ID, "wrong caseId: " + repr(payload.get("caseId")))
    fixtures = payload["fixtures"]
    _require(isinstance(fixtures, list) and fixtures, "bad payload: fixtures must be a non-empty list")
    seen: set[str] = set()
    for index, fixture in enumerate(fixtures):
        context = "fixtures[" + str(index) + "]"
        _require(isinstance(fixture, dict), "bad payload: " + context + " must be an object")
        _exact_keys(fixture, FIXTURE_KEYS, context)
        _require(_text(fixture["id"]), "bad payload: " + context + ".id must be non-empty text")
        _require(fixture["id"] not in seen, "bad payload: duplicate fixture id: " + fixture["id"])
        seen.add(fixture["id"])
        _require(fixture["kind"] in KINDS, "bad payload: " + context + ".kind is not a P007 fixture kind")
        _require(_text(fixture["displayName"]), "bad payload: " + context + ".displayName must be non-empty text")
        _require(_text(fixture["sha256"]), "bad payload: " + context + ".sha256 must be non-empty text")
        _require("visualResult" in fixture, "bad payload: " + context + " missing visualResult")
        _require(fixture["rights"] in RIGHTS, "bad payload: " + context + ".rights is not unknown, permitted, or denied")
        if fixture["provenance"] is None:
            continue
        _validate_provenance(fixture["provenance"], context)
    return fixtures


def _same_name_distinct_hash(records: list[dict]) -> bool:
    grouped: dict[str, set[str]] = {}
    for record in records:
        grouped.setdefault(record["displayName"], set()).add(record["sha256"])
    return any(len(hashes) > 1 for hashes in grouped.values())


def evaluate(payload: Any) -> dict:
    """Return the TC-P007-03 ledger decision for one payload.

    Valid fixtures (complete provenance and rights permitted) are retained in
    preservedResults even when they share a display name, as long as their
    content hashes differ. Missing provenance, unknown rights, and denied
    rights put that fixture id in rejectedClaims and keep it out of the public
    bundle. Decision is accepted only when every fixture is valid; otherwise
    it is excluded. It is never reproducible.
    """
    fixtures = _validate(payload)
    rejected: list[str] = []
    preserved: list[dict] = []
    questions: list[str] = []
    missing = False
    unknown = False
    denied = False
    for fixture in fixtures:
        fixture_id = fixture["id"]
        lacks_provenance = fixture["provenance"] is None
        if lacks_provenance:
            missing = True
            questions.append(fixture_id + ": source and permitted use are not established")
        if fixture["rights"] == "unknown":
            unknown = True
            questions.append(fixture_id + ": redistribution rights are unknown")
        elif fixture["rights"] == "denied":
            denied = True
        if lacks_provenance or fixture["rights"] != "permitted":
            rejected.append(fixture_id)
            continue
        preserved.append({
            "id": fixture_id,
            "kind": fixture["kind"],
            "displayName": fixture["displayName"],
            "sha256": fixture["sha256"],
        })
    decision = "accepted" if not rejected else "excluded"
    reasons: list[str] = []
    if decision == "accepted":
        reasons.append("Every fixture has provenance and permitted redistribution rights.")
    else:
        reasons.append("Fixtures missing provenance or redistribution permission are excluded from provenance-backed claims.")
    if missing:
        reasons.append("A visual result does not make a fixture reproducible when provenance is missing.")
    if unknown:
        reasons.append("Unknown redistribution rights exclude a fixture from the public bundle.")
    if denied:
        reasons.append("Denied redistribution rights exclude a fixture from the public bundle.")
    if preserved and decision == "excluded":
        reasons.append("Unrelated valid fixtures remain preserved.")
    if _same_name_distinct_hash(preserved):
        reasons.append("Identical display names with different content hashes are distinct versions.")
    return _result(decision, reasons, rejected, preserved, questions)
