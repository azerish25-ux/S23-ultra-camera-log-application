#!/usr/bin/env python3
"""P122 Create non-destructive recipe versions.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P122-01 through TC-P122-08 modules.

A recipe version is immutable. Its version_sha256 is the SHA-256 of the UTF-8
canonical JSON object {"params", "parent", "source"}:

    json.dumps(
        {"params": parameters, "parent": parent_id, "source": source_sha256},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )

Editing parameters allocates a new id and a new hash. The parent object stays
byte-identical under that same canonical encoding. An in-place mutation (same
id, or the caller setting mutatedInPlace) is rejected. source_sha256 is an
unchanged lowercase hex digest. A later version whose parent_id is absent from
the list is rejected. Declared hashes are recomputed and rejected on mismatch.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P122"
WORKSTREAM = 16
TITLE = "Create non-destructive recipe versions"
GOAL = "Make every creative edit reproducible without rewriting the source or previous result."
METHOD = (
    "Store immutable source references and versioned graph parameters. Separate autosaved drafts "
    "from renderable snapshots. A render consumes one frozen recipe even if the user continues "
    "editing; changes create another version."
)
FIXTURE = "A user adjusts grain and focus while an earlier export is already running."
ORACLE = (
    "The running export remains bound to its original recipe and the new edit receives a distinct identity."
)
MUTANT = "Read live UI slider values during each frame of an export."
DELIVERABLE = "Recipe snapshot store and concurrent-edit tests"
DEPENDENCIES = ("P121",)

SOURCE_MATERIAL = "s23-imported-clip-a"
PARENT_ID = "rv-1"
CHILD_ID = "rv-2"
PARENT_PARAMETERS = {"focus": 0.4, "grain": 0.15}
CHILD_PARAMETERS = {"focus": 0.72, "grain": 0.33}

IN_PLACE = "in-place-recipe-mutation"
SOURCE_CHANGED = "source-sha256-changed"
SOURCE_MISMATCH = "source-sha256-mismatch"
MISSING_PARENT = "missing-parent-version"
HASH_MISMATCH = "version-sha256-mismatch"
EXPORT_UNBOUND = "export-unbound-from-frozen-recipe"
EXPORT_FOLLOWED = "export-followed-live-edit"
EDIT_IDENTITY = "edit-lacks-distinct-identity"

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "mutatedInPlace",
    "sourceMaterial",
    "versions",
    "runningExportRecipeId",
    "liveParameters",
}
VERSION_KEYS = {"id", "parent_id", "source_sha256", "parameters", "version_sha256"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DIGEST = re.compile(r"^[0-9a-f]{64}$")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _add(claims: list[str], claim: str) -> None:
    if claim not in claims:
        claims.append(claim)


def require_text(value: Any, label: str) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(),
            f"{label} must be a non-empty string")
    require(not any(character.isspace() for character in value), f"{label} must not contain whitespace")
    return value


def require_digest(value: Any, label: str) -> str:
    require(isinstance(value, str) and DIGEST.fullmatch(value) is not None,
            f"{label} must be 64 lowercase hex characters")
    return value


def validate_json_value(value: Any, label: str) -> None:
    if value is None or type(value) is bool or type(value) is str or type(value) is int:
        return
    if type(value) is float:
        require(value == value and value not in (float("inf"), float("-inf")), f"{label} must be finite")
        return
    if type(value) is list:
        for index, item in enumerate(value):
            validate_json_value(item, f"{label}[{index}]")
        return
    if type(value) is dict:
        for key, item in value.items():
            require(type(key) is str, f"{label} keys must be strings")
            validate_json_value(item, f"{label}.{key}")
        return
    raise ValueError(f"{label} is not JSON-compatible")


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("value is not canonical JSON") from exc


def object_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def canonical_preimage(parent_id: str | None, source_sha256: str, parameters: dict) -> str:
    """Exact hash preimage for version_sha256. Not the full version object."""
    if parent_id is not None:
        require_text(parent_id, "parent")
    require_digest(source_sha256, "source")
    require(type(parameters) is dict, "params must be an object")
    validate_json_value(parameters, "params")
    return canonical_json({"parent": parent_id, "source": source_sha256, "params": parameters})


def compute_version_sha256(parent_id: str | None, source_sha256: str, parameters: dict) -> str:
    preimage = canonical_preimage(parent_id, source_sha256, parameters)
    return hashlib.sha256(preimage.encode("utf-8")).hexdigest()


def source_digest(material: str = SOURCE_MATERIAL) -> str:
    require(isinstance(material, str) and material != "", "source material must be a non-empty string")
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def make_version(version_id: str, parent_id: str | None, source_sha256: str, parameters: dict) -> dict:
    version_id = require_text(version_id, "id")
    if parent_id is not None:
        parent_id = require_text(parent_id, "parent_id")
    source_sha256 = require_digest(source_sha256, "source_sha256")
    require(type(parameters) is dict, "parameters must be an object")
    params = copy.deepcopy(parameters)
    return {
        "id": version_id,
        "parent_id": parent_id,
        "source_sha256": source_sha256,
        "parameters": params,
        "version_sha256": compute_version_sha256(parent_id, source_sha256, params),
    }


def fork_version(parent: dict, new_id: str, parameters: dict) -> dict:
    """Create a new version. The parent object stays byte-identical."""
    require(type(parent) is dict and set(parent) == VERSION_KEYS, "parent version keys are invalid")
    before = object_bytes(parent)
    new_id = require_text(new_id, "id")
    require(new_id != parent["id"], "edit must create a new version id")
    child = make_version(new_id, parent["id"], parent["source_sha256"], parameters)
    require(object_bytes(parent) == before, "parent version mutated")
    return child


def sample_versions() -> list[dict]:
    source = source_digest(SOURCE_MATERIAL)
    parent = make_version(PARENT_ID, None, source, dict(PARENT_PARAMETERS))
    child = fork_version(parent, CHILD_ID, dict(CHILD_PARAMETERS))
    return [parent, child]


def parse_version(item: Any, index: int) -> dict:
    require(type(item) is dict, f"versions[{index}] must be an object")
    require(set(item) == VERSION_KEYS, f"versions[{index}] keys must be id, parent_id, source_sha256, parameters, version_sha256")
    parent_id = item["parent_id"]
    if parent_id is not None:
        parent_id = require_text(parent_id, f"versions[{index}].parent_id")
    parameters = item["parameters"]
    require(type(parameters) is dict, f"versions[{index}].parameters must be an object")
    validate_json_value(parameters, f"versions[{index}].parameters")
    return {
        "id": require_text(item["id"], f"versions[{index}].id"),
        "parent_id": parent_id,
        "source_sha256": require_digest(item["source_sha256"], f"versions[{index}].source_sha256"),
        "parameters": copy.deepcopy(parameters),
        "version_sha256": require_digest(item["version_sha256"], f"versions[{index}].version_sha256"),
    }


def parse_versions(versions: Any) -> list[dict]:
    require(isinstance(versions, list) and len(versions) > 0, "versions must be a non-empty list")
    return [parse_version(item, index) for index, item in enumerate(versions)]


def review_versions(versions: Any, *, mutated_in_place: bool) -> dict[str, Any]:
    """Recompute every version hash without mutating the caller's objects."""
    require(type(mutated_in_place) is bool, "mutatedInPlace must be a bool")
    require(isinstance(versions, list), "versions must be a list")
    before = []
    for index, item in enumerate(versions):
        require(type(item) is dict, f"versions[{index}] must be an object")
        before.append(object_bytes(item))
    parsed = parse_versions(versions)
    reviewed = evaluate_chain(parsed, mutated_in_place=mutated_in_place)
    after = [object_bytes(item) for item in versions]
    require(before == after, "recipe versions were mutated")
    return reviewed


def evaluate_chain(parsed: list[dict], *, mutated_in_place: bool) -> dict[str, Any]:
    rejected: list[str] = []
    reasons: list[str] = []
    preserved: list[str] = []
    first_index: dict[str, int] = {}
    id_list = [version["id"] for version in parsed]
    root_source = parsed[0]["source_sha256"]

    if mutated_in_place:
        _add(rejected, IN_PLACE)
        reasons.append("caller reported an in-place parameter mutation")

    for index, version in enumerate(parsed):
        preimage = canonical_preimage(version["parent_id"], version["source_sha256"], version["parameters"])
        recomputed = hashlib.sha256(preimage.encode("utf-8")).hexdigest()
        preserved.append("id=" + version["id"])
        preserved.append("preimage=" + preimage)
        preserved.append("version_sha256=" + recomputed)
        reasons.append(version["id"] + " preimage=" + preimage)
        reasons.append(version["id"] + " version_sha256=" + recomputed)
        if recomputed != version["version_sha256"]:
            _add(rejected, HASH_MISMATCH)
            reasons.append(
                version["id"]
                + " declared "
                + version["version_sha256"]
                + " does not match recomputed "
                + recomputed
            )
        if version["source_sha256"] != root_source:
            _add(rejected, SOURCE_CHANGED)
            reasons.append(version["id"] + " changed source_sha256")

        if version["id"] in first_index:
            _add(rejected, IN_PLACE)
            reasons.append("version id " + version["id"] + " was submitted more than once")
        else:
            first_index[version["id"]] = index

        parent_id = version["parent_id"]
        if parent_id is None:
            if index != 0:
                _add(rejected, MISSING_PARENT)
                reasons.append(version["id"] + " parent_id is null after the first version")
            else:
                reasons.append(version["id"] + " parent=null")
        elif parent_id == version["id"] or parent_id not in id_list:
            _add(rejected, MISSING_PARENT)
            reasons.append(version["id"] + " parent_id " + parent_id + " does not exist in the list")
        else:
            parent = parsed[first_index.get(parent_id, id_list.index(parent_id))]
            before = object_bytes(parent)
            if version["id"] != parent["id"]:
                fork_version(parent, version["id"], version["parameters"])
            require(object_bytes(parent) == before, "parent version mutated")
            token = version["id"] + " parentByteIdentical=true"
            reasons.append(token)
            preserved.append(token)

    return {
        "rejectedClaims": rejected,
        "reasons": reasons,
        "preservedResults": preserved,
        "versions": parsed,
    }


def evaluate_binding(versions: list[dict], running_export_recipe_id: Any, live_parameters: Any) -> dict[str, Any]:
    rejected: list[str] = []
    reasons: list[str] = []
    preserved: list[str] = []
    running_id = require_text(running_export_recipe_id, "runningExportRecipeId")
    require(type(live_parameters) is dict, "liveParameters must be an object")
    validate_json_value(live_parameters, "liveParameters")
    by_id: dict[str, dict] = {}
    for version in versions:
        if version["id"] not in by_id:
            by_id[version["id"]] = version
    preserved.append("runningExportRecipeId=" + running_id)
    frozen = by_id.get(running_id)
    if frozen is None:
        _add(rejected, EXPORT_UNBOUND)
        reasons.append("running export is not bound to a stored recipe version")
        return {"rejectedClaims": rejected, "reasons": reasons, "preservedResults": preserved}

    frozen_canon = canonical_json(frozen["parameters"])
    live_canon = canonical_json(live_parameters)
    preserved.append("frozenParameters=" + frozen_canon)
    preserved.append("liveParameters=" + live_canon)
    if live_canon == frozen_canon:
        parent = by_id.get(frozen["parent_id"]) if frozen["parent_id"] is not None else None
        if parent is not None and canonical_json(parent["parameters"]) != frozen_canon:
            _add(rejected, EXPORT_FOLLOWED)
            reasons.append("running export followed the edited recipe instead of staying on its parent")
        else:
            reasons.append("running export remains bound to its frozen recipe")
    else:
        matches = [
            version
            for version in versions
            if version["id"] != frozen["id"] and canonical_json(version["parameters"]) == live_canon
        ]
        if not matches:
            _add(rejected, EDIT_IDENTITY)
            reasons.append("live edit did not receive a distinct recipe version")
        else:
            reasons.append("new edit identity " + matches[0]["id"])
            reasons.append("running export remains bound to its original recipe")
    return {"rejectedClaims": rejected, "reasons": reasons, "preservedResults": preserved}


def finish_result(
    case_id: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict[str, Any]:
    decision = "rejected" if rejected else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "negative or unmeasured result must not be qualified")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": open_questions,
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(preserved and isinstance(preserved[0], str), "evidence wiped")
    return result


def assess(document: dict) -> dict[str, Any]:
    """Apply the phase oracle to one frozen recipe and a concurrent edit."""
    require(type(document) is dict, "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = require_text(document["evidenceId"], "evidenceId")
    claim = require_text(document["claim"], "claim")
    require(type(document["applyMutant"]) is bool, "applyMutant must be a bool")
    require(type(document["mutatedInPlace"]) is bool, "mutatedInPlace must be a bool")
    source_material = document["sourceMaterial"]
    require(isinstance(source_material, str) and source_material != "", "sourceMaterial must be a non-empty string")

    caller_versions = document["versions"]
    require(isinstance(caller_versions, list), "versions must be a list")
    before = []
    for index, item in enumerate(caller_versions):
        require(type(item) is dict, f"versions[{index}] must be an object")
        before.append(object_bytes(item))
    parsed = parse_versions(caller_versions)
    chain = evaluate_chain(parsed, mutated_in_place=document["mutatedInPlace"])
    binding = evaluate_binding(parsed, document["runningExportRecipeId"], document["liveParameters"])
    after = [object_bytes(item) for item in caller_versions]
    require(before == after, "recipe versions were mutated")

    actual_source = source_digest(source_material)
    rejected: list[str] = []
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "goal: " + GOAL,
        "fixture: " + FIXTURE,
    ]
    if document["applyMutant"]:
        _add(rejected, MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    for claim_token in chain["rejectedClaims"] + binding["rejectedClaims"]:
        _add(rejected, claim_token)
    for version in parsed:
        if version["source_sha256"] != actual_source:
            _add(rejected, SOURCE_MISMATCH)
            reasons.append(version["id"] + " source_sha256 does not match source material")
            break
    reasons.extend(chain["reasons"])
    reasons.extend(binding["reasons"])
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("method: " + METHOD)
        reasons.append("deliverable: " + DELIVERABLE)
    preserved = [evidence, claim, "source_sha256=" + actual_source]
    preserved.extend(chain["preservedResults"])
    preserved.extend(binding["preservedResults"])
    questions = [
        "physical S23 measurement was not run",
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]
    result = finish_result(PHASE, reasons, rejected, preserved, questions)
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(any(item.startswith("preimage=") for item in result["preservedResults"]), "hash preimage missing")
    require(result["decision"] in {"recorded", "rejected"}, "decision must be recorded or rejected")
    return result
