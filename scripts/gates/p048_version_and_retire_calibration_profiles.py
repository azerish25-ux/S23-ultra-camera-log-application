#!/usr/bin/env python3
"""P048 profile lifecycle manager.

Compatibility keys are exact: firmware, lens route, and version identifier.
Historical sources keep their original profile references. Installing a newer
profile appends a development version. It never overwrites an earlier export.
Rollback and comparison stay available.

The deliberate mutant — replace all profile files in place while keeping the
old version identifier — is rejected. This module does not probe a device,
does not qualify a physical S23, and does not execute TC-P048-01 through
TC-P048-08.
"""

from __future__ import annotations

import copy
import hashlib
import re
from typing import Any


PHASE = "P048"
CASE_ID = "P048"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-profile-lifecycle-fixture"
METHOD = (
    "Use exact compatibility keys and explicit migration policies. Historical sources "
    "retain their original profile references. A newer profile can create a new "
    "development version but never overwrite the provenance of an earlier export. "
    "Provide rollback and comparison."
)
FIXTURE = "A user installs a newly measured profile and reopens a previously rendered take."
ORACLE = (
    "The earlier result remains reproducible while a new revision may be rendered and compared."
)
MUTANT = "Replace all profile files in place while keeping the old version identifier."
MIGRATION_POLICY = "new-development-version"
HOST_LIMIT = "this host record does not qualify a physical S23"
STATUSES = ("approved", "retired", "candidate")

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9-]{0,63}$")

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "migrationPolicy",
    "profiles",
    "sources",
    "exports",
}
PROFILE_KEYS = {"versionId", "contentHash", "firmware", "lensRoute", "status", "bytesLabel"}
SOURCE_KEYS = {"id", "profileRef", "contentHash"}
EXPORT_KEYS = {"id", "sourceId", "profileRef", "contentHash", "recipeId"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld", "reproducible"}
_FORBIDDEN = {"qualified", "allowed"}
_MAX_ROWS = 8


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


def _token(value: object, label: str) -> str:
    require(isinstance(value, str) and TOKEN.fullmatch(value) is not None, label + " must be a token")
    return value


def _hash(value: object, label: str) -> str:
    require(isinstance(value, str) and HEX64.fullmatch(value) is not None,
            label + " must be 64 lowercase hex characters")
    return value


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def content_digest(bytes_label: str) -> str:
    """SHA-256 of the profile byte label. Host stand-in for profile bytes."""
    _token(bytes_label, "bytesLabel")
    return hashlib.sha256(bytes_label.encode("utf-8")).hexdigest()


def compatibility_key(profile: dict) -> str:
    """Exact key. A firmware or lens change is not the same profile version."""
    return f"{profile['firmware']}|{profile['lensRoute']}|{profile['versionId']}"


def _bounded(value: object, label: str) -> list:
    require(isinstance(value, list) and 1 <= len(value) <= _MAX_ROWS,
            label + " must be a list of 1 to 8")
    return value


def _profile(value: object, index: int, seen: set[str]) -> dict:
    item = exact_keys(value, PROFILE_KEYS, f"profiles[{index}]")
    ident = _token(item["versionId"], f"profiles[{index}] versionId")
    require(ident not in seen, "duplicate profile version " + ident)
    seen.add(ident)
    _token(item["firmware"], f"profiles[{index}] firmware")
    _token(item["lensRoute"], f"profiles[{index}] lensRoute")
    _token(item["bytesLabel"], f"profiles[{index}] bytesLabel")
    require(item["status"] in STATUSES, f"profiles[{index}] status is unknown")
    digest = _hash(item["contentHash"], f"profiles[{index}] contentHash")
    require(digest == content_digest(item["bytesLabel"]),
            f"profiles[{index}] contentHash does not match bytesLabel")
    return item


def _source(value: object, index: int, seen: set[str], profiles: set[str]) -> dict:
    item = exact_keys(value, SOURCE_KEYS, f"sources[{index}]")
    ident = _token(item["id"], f"sources[{index}] id")
    require(ident not in seen, "duplicate source id " + ident)
    seen.add(ident)
    ref = _token(item["profileRef"], f"sources[{index}] profileRef")
    require(ref in profiles, f"sources[{index}] profileRef is unknown")
    _hash(item["contentHash"], f"sources[{index}] contentHash")
    return item


def _export(value: object, index: int, seen_ids: set[str], seen_recipes: set[str],
            profiles: set[str], sources: set[str]) -> dict:
    item = exact_keys(value, EXPORT_KEYS, f"exports[{index}]")
    ident = _token(item["id"], f"exports[{index}] id")
    require(ident not in seen_ids, "duplicate export id " + ident)
    seen_ids.add(ident)
    recipe = _token(item["recipeId"], f"exports[{index}] recipeId")
    require(recipe not in seen_recipes, "duplicate recipe id " + recipe)
    seen_recipes.add(recipe)
    source = _token(item["sourceId"], f"exports[{index}] sourceId")
    require(source in sources, f"exports[{index}] sourceId is unknown")
    ref = _token(item["profileRef"], f"exports[{index}] profileRef")
    require(ref in profiles, f"exports[{index}] profileRef is unknown")
    _hash(item["contentHash"], f"exports[{index}] contentHash")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P048 lifecycle fixture shape."""
    exact_keys(document, DOCUMENT_KEYS, "profile lifecycle")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P048")
    require(document["mapId"] == MAP_ID, "mapId must be s23-profile-lifecycle-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and isinstance(revision, str) and HEX40.fullmatch(revision) is not None,
            "profile lifecycle needs the P048 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    require(document["migrationPolicy"] == MIGRATION_POLICY,
            "migrationPolicy must be new-development-version")
    profiles = _bounded(document["profiles"], "profiles")
    seen: set[str] = set()
    for index, profile in enumerate(profiles):
        _profile(profile, index, seen)
    sources = _bounded(document["sources"], "sources")
    seen_sources: set[str] = set()
    for index, source in enumerate(sources):
        _source(source, index, seen_sources, seen)
    exports = _bounded(document["exports"], "exports")
    seen_exports: set[str] = set()
    seen_recipes: set[str] = set()
    for index, export in enumerate(exports):
        _export(export, index, seen_exports, seen_recipes, seen, seen_sources)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS and decision not in _FORBIDDEN,
            "P048 must not decide qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons),
            "reasons must be a non-empty list of strings")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": _dedupe(rejected),
        "preservedResults": list(preserved),
        "openQuestions": _dedupe(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def _index(document: dict) -> dict[str, dict]:
    return {profile["versionId"]: profile for profile in document["profiles"]}


def assess(document: dict, replace_in_place: bool = False) -> dict:
    """Reopen historical bindings. Reject in-place replacement of profile bytes.

    replace_in_place True is the mutant. It is rejected even when the catalog
    still parses. Export recipes and recorded hashes stay in preservedResults.
    A newer version may be compared. It does not retarget an older source.
    """
    validate_document(document)
    require(type(replace_in_place) is bool, "replace_in_place must be a bool")
    profiles = _index(document)
    preserved = [f"policy:{document['migrationPolicy']}"]
    rejected: list[str] = []
    questions = [
        "host fixture is not physical S23 qualification",
        "a newer profile does not overwrite an earlier export",
    ]
    reasons = [ORACLE, "historical sources retain their original profile references"]

    for profile in document["profiles"]:
        key = compatibility_key(profile)
        preserved.append(
            f"profile:{profile['versionId']}|status={profile['status']}|key={key}|hash={profile['contentHash']}"
        )
        preserved.append(f"key:{key}")

    for source in document["sources"]:
        profile = profiles[source["profileRef"]]
        preserved.append(
            f"source:{source['id']}:ref={source['profileRef']}:hash={source['contentHash']}"
        )
        preserved.append(f"selected:{source['id']}:{compatibility_key(profile)}")
        if source["contentHash"] != profile["contentHash"]:
            rejected.append(f"source-hash-drift:{source['id']}")
            reasons.append(
                f"{source['id']} keeps hash {source['contentHash']} which no longer matches "
                f"{source['profileRef']}"
            )

    for export in document["exports"]:
        profile = profiles[export["profileRef"]]
        preserved.append(f"recipe:{export['id']}:{export['recipeId']}")
        preserved.append(f"export-hash:{export['id']}:{export['contentHash']}")
        preserved.append(f"export-ref:{export['id']}:{export['profileRef']}")
        if export["contentHash"] != profile["contentHash"]:
            rejected.append(f"same-identifier-byte-replacement:{export['profileRef']}")
            reasons.append(
                f"{export['id']} still records {export['contentHash']} under {export['profileRef']}"
            )

    version_ids = [profile["versionId"] for profile in document["profiles"]]
    if len(version_ids) >= 2:
        left, right = version_ids[0], version_ids[1]
        preserved.append(f"comparison:{left}:{right}")
        reasons.append(
            f"new revision {right} may be compared with {left} without rewriting earlier provenance"
        )
    else:
        questions.append("no second revision is available to compare")

    historical = document["sources"][0]
    historical_profile = profiles[historical["profileRef"]]
    for profile in document["profiles"]:
        if profile["versionId"] == historical_profile["versionId"]:
            continue
        if (
            profile["firmware"] != historical_profile["firmware"]
            or profile["lensRoute"] != historical_profile["lensRoute"]
        ):
            reasons.append(
                f"{profile['versionId']} compatibility key differs and does not retarget "
                f"{historical['id']}"
            )
            questions.append(
                f"{profile['versionId']} is a new development version, not an in-place replacement"
            )

    if replace_in_place:
        rejected.insert(0, "in-place-version-identifier")
        reasons.append(MUTANT)
        reasons.append("profile bytes were not replaced under the old version identifier")
        questions.append("in-place replacement was rejected")

    if replace_in_place or rejected:
        decision = "rejected"
    elif len(version_ids) >= 2:
        decision = "reproducible"
        reasons.append("the earlier result remains reproducible")
    else:
        decision = "withheld"
        reasons.append("earlier binding is intact but no new revision was compared")
    reasons.append(HOST_LIMIT)
    return _result(decision, reasons, rejected, preserved, questions)


def install_revision(document: dict, profile: dict) -> dict:
    """Append a development version. Historical sources and exports stay put."""
    validate_document(document)
    seen = {item["versionId"] for item in document["profiles"]}
    _profile(profile, len(document["profiles"]), seen)
    revised = copy.deepcopy(document)
    revised["profiles"].append(copy.deepcopy(profile))
    validate_document(revised)
    require(revised["sources"] == document["sources"], "install rewrote a historical source")
    require(revised["exports"] == document["exports"], "install rewrote an earlier export")
    return revised


def rollback(document: dict, version_id: str) -> dict:
    """Approve one retained version. Do not rewrite sources or exports."""
    validate_document(document)
    _token(version_id, "version_id")
    known = {profile["versionId"] for profile in document["profiles"]}
    require(version_id in known, "unknown profile version " + version_id)
    revised = copy.deepcopy(document)
    for profile in revised["profiles"]:
        if profile["versionId"] == version_id:
            profile["status"] = "approved"
        elif profile["status"] == "approved":
            profile["status"] = "retired"
    require(revised["sources"] == document["sources"], "rollback rewrote a historical source")
    require(revised["exports"] == document["exports"], "rollback rewrote an earlier export")
    validate_document(revised)
    return revised


def compare(document: dict, left_id: str, right_id: str) -> dict[str, Any]:
    """Compare two retained versions without mutating provenance."""
    validate_document(document)
    _token(left_id, "left_id")
    _token(right_id, "right_id")
    require(left_id != right_id, "comparison needs two version identifiers")
    profiles = _index(document)
    require(left_id in profiles and right_id in profiles, "unknown profile version")
    left = profiles[left_id]
    right = profiles[right_id]
    return {
        "leftVersion": left_id,
        "rightVersion": right_id,
        "leftHash": left["contentHash"],
        "rightHash": right["contentHash"],
        "bytesDiffer": left["bytesLabel"] != right["bytesLabel"],
        "firmwareDiffers": left["firmware"] != right["firmware"],
        "lensRouteDiffers": left["lensRoute"] != right["lensRoute"],
    }
