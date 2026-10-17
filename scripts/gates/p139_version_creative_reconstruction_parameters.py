#!/usr/bin/env python3
"""P139 Version creative reconstruction parameters.

Host fixture only. This module does not probe a device and does not qualify a
physical S23.

Production facts are an immutable dict. fact_hash is SHA-256 of that dict's
canonical JSON (sorted keys, no extra whitespace). A creative edit stores a new
reconstruction version with parent_id and its own parameter_hash. The fact hash
on that version stays the original. The first reconstruction may use parent_id
null. A later version whose parent is missing is rejected. Overwriting a
documented fact key is rejected when the same facts object was mutated, when
fact_hash changes, or when mutated_facts is true.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P139"
WORKSTREAM = 18
TITLE = "Version creative reconstruction parameters"
GOAL = "Make our interpretation editable without modifying the underlying production facts."
METHOD = (
    "Keep a recipe graph linked to, but distinct from, evidence records. Version exposure, "
    "stock model, virtual lens, grain, halation, print response, and grade independently. "
    "A user adaptation becomes a derivative recipe with its own name and provenance."
)
FIXTURE = "A user changes the virtual aperture and print contrast of a movie-inspired recipe."
ORACLE = (
    "The original documented facts remain unchanged and the edited appearance is stored as a user reconstruction."
)
MUTANT = (
    "Overwrite the cinematographer\u2019s documented settings with the user\u2019s creative changes."
)
DELIVERABLE = "Reconstruction versioning and immutable fact tests"
DEPENDENCIES = ("P138",)

EVIDENCE_ID = "p139-reconstruction-versions"
CLAIM = "immutable-production-facts-host-reference"
PARENT_ID = "rr-1"
CHILD_ID = "rr-2"
PARENT_NAME = "movie-inspired"
CHILD_NAME = "user-aperture-contrast"
PARENT_PROVENANCE = "catalogue-recipe"
CHILD_PROVENANCE = "user-derivative"
CREATIVE_LABEL = "creative-reconstruction"
USER_LABEL = "user-reconstruction"

OPEN_QUESTION = "physical S23 measurement was not run"
NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]

DOCUMENTED_FACT_KEYS = (
    "camera",
    "cinematographer",
    "documentedAperture",
    "documentedPrintContrast",
    "lens",
    "process",
    "releaseVersion",
    "stock",
    "title",
)
CREATIVE_PARAMETER_KEYS = (
    "exposure",
    "stockModel",
    "virtualLens",
    "virtualAperture",
    "grain",
    "halation",
    "printResponse",
    "printContrast",
    "grade",
)
CINEMATOGRAPHER_KEYS = ("documentedAperture", "documentedPrintContrast")
LABELS = frozenset({CREATIVE_LABEL, USER_LABEL})

SAME_OBJECT_MUTATED = "same-object-mutated"
FACT_HASH_CHANGED = "fact-hash-changed"
MUTATED_FACTS = "mutated-facts"
DOCUMENTED_KEY_OVERWRITTEN = "documented-fact-key-overwritten"
UNKNOWN_FACT_FILLED = "unknown-fact-filled"
MISSING_PARENT = "missing-parent-version"
PARAMETER_HASH_MISMATCH = "parameter-hash-mismatch"
ID_REUSED = "reconstruction-id-reused"
NOT_USER_RECONSTRUCTION = "edit-not-stored-as-user-reconstruction"
DERIVATIVE_IDENTITY = "derivative-missing-own-name-or-provenance"
PARAMETERS_OUTSIDE = "parameters-outside-declared-rendering-set"

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "mutated_facts",
    "productionFacts",
    "fact_hash",
    "prior_canonical",
    "reconstructions",
}
EVALUATE_KEYS = {
    "caseId",
    "evidenceId",
    "claim",
    "applyMutant",
    "mutated_facts",
    "productionFacts",
    "fact_hash",
    "prior_canonical",
    "bound_object_id",
    "reconstructions",
}
RECONSTRUCTION_KEYS = {
    "id",
    "name",
    "provenance",
    "parent_id",
    "fact_hash",
    "parameters",
    "parameter_hash",
    "label",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DIGEST = re.compile(r"^[0-9a-f]{64}$")

FAULT_TEXT = {
    SAME_OBJECT_MUTATED: "the same production-facts object was mutated",
    FACT_HASH_CHANGED: "fact_hash changed",
    MUTATED_FACTS: "mutated_facts is true",
    DOCUMENTED_KEY_OVERWRITTEN: "a documented fact key was overwritten",
    UNKNOWN_FACT_FILLED: "an unknown production fact was filled instead of staying unknown",
    MISSING_PARENT: "a later reconstruction parent is missing",
    PARAMETER_HASH_MISMATCH: "parameter_hash does not match the canonical parameter preimage",
    ID_REUSED: "a creative edit reused a reconstruction id",
    NOT_USER_RECONSTRUCTION: "the edited appearance was not stored as a user reconstruction",
    DERIVATIVE_IDENTITY: "a user adaptation must have its own name and provenance",
    PARAMETERS_OUTSIDE: "reconstruction parameters must stay inside the declared rendering set",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _add(claims: list[str], claim: str) -> None:
    if claim not in claims:
        claims.append(claim)


def require_text(value: Any, label: str) -> str:
    require(
        isinstance(value, str) and bool(value.strip()) and value == value.strip(),
        f"{label} must be a non-empty string",
    )
    return value


def require_id(value: Any, label: str) -> str:
    text = require_text(value, label)
    require(not any(character.isspace() for character in text), f"{label} must not contain whitespace")
    return text


def require_digest(value: Any, label: str) -> str:
    require(
        isinstance(value, str) and DIGEST.fullmatch(value) is not None,
        f"{label} must be 64 lowercase hex characters",
    )
    return value


def require_bool(value: Any, label: str) -> bool:
    require(type(value) is bool, f"{label} must be a bool")
    return value


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


def hash_facts(facts: dict) -> str:
    """SHA-256 of the canonical JSON of an immutable production-facts dict."""
    require(type(facts) is dict, "production facts must be an object")
    return hashlib.sha256(canonical_json(facts).encode("utf-8")).hexdigest()


def parameter_preimage(parent_id: str | None, fact_hash: str, parameters: dict) -> str:
    if parent_id is not None:
        require_id(parent_id, "parent")
    require_digest(fact_hash, "facts")
    require(type(parameters) is dict, "params must be an object")
    return canonical_json({"facts": fact_hash, "params": parameters, "parent": parent_id})


def compute_parameter_hash(parent_id: str | None, fact_hash: str, parameters: dict) -> str:
    preimage = parameter_preimage(parent_id, fact_hash, parameters)
    return hashlib.sha256(preimage.encode("utf-8")).hexdigest()


def sample_facts() -> dict[str, Any]:
    return {
        "camera": "Arricam ST",
        "cinematographer": "sourced-production-account",
        "documentedAperture": "T2.8",
        "documentedPrintContrast": "normal",
        "lens": None,
        "process": "standard-print",
        "releaseVersion": "theatrical-35mm",
        "stock": "Kodak Vision3 250D",
        "title": "Night Ferry",
    }


def parent_parameters() -> dict[str, Any]:
    return {
        "exposure": 0,
        "stockModel": "vision3-250d-inspired",
        "virtualLens": "50mm-reconstructed",
        "virtualAperture": 2.8,
        "grain": 0.18,
        "halation": 0.12,
        "printResponse": "normal",
        "printContrast": 1,
        "grade": "neutral",
    }


def child_parameters() -> dict[str, Any]:
    parameters = parent_parameters()
    parameters["virtualAperture"] = 4
    parameters["printContrast"] = 1.4
    return parameters


def parse_facts(facts: Any, label: str) -> dict[str, Any]:
    require(type(facts) is dict, f"{label} must be an object")
    require(
        set(facts) == set(DOCUMENTED_FACT_KEYS),
        f"{label} keys must be the documented production facts",
    )
    parsed: dict[str, Any] = {}
    for key in DOCUMENTED_FACT_KEYS:
        value = facts[key]
        if value is None:
            parsed[key] = None
            continue
        if type(value) is str:
            require(value == value.strip() and value != "", f"{label}.{key} must be a non-empty string or null")
            parsed[key] = value
            continue
        if type(value) is int or (type(value) is float and math.isfinite(value)):
            parsed[key] = value
            continue
        raise ValueError(f"{label}.{key} is not a documented fact value")
    return parsed


def require_canonical_facts(text: Any, label: str) -> dict[str, Any]:
    require(isinstance(text, str) and text != "", f"{label} must be canonical JSON text")
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not JSON") from exc
    facts = parse_facts(loaded, label)
    require(canonical_json(facts) == text, f"{label} must be canonical JSON")
    return facts


def parse_parameters(parameters: Any, label: str) -> dict[str, Any]:
    require(type(parameters) is dict, f"{label} must be an object")
    parsed: dict[str, Any] = {}
    for key, value in parameters.items():
        require(type(key) is str, f"{label} keys must be strings")
        if value is None or type(value) is str or type(value) is bool or type(value) is int:
            parsed[key] = value
            continue
        if type(value) is float:
            require(math.isfinite(value), f"{label}.{key} must be finite")
            parsed[key] = value
            continue
        raise ValueError(f"{label}.{key} is not a rendering parameter")
    missing = [key for key in CREATIVE_PARAMETER_KEYS if key not in parsed]
    require(not missing, f"{label} missing creative parameters: " + ", ".join(missing))
    return parsed


def make_reconstruction(
    version_id: str,
    name: str,
    provenance: str,
    parent_id: str | None,
    fact_hash: str,
    parameters: dict,
    label: str,
) -> dict[str, Any]:
    version_id = require_id(version_id, "id")
    name = require_text(name, "name")
    provenance = require_text(provenance, "provenance")
    if parent_id is not None:
        parent_id = require_id(parent_id, "parent_id")
    fact_hash = require_digest(fact_hash, "fact_hash")
    require(label in LABELS, "label must name a creative or user reconstruction")
    params = parse_parameters(copy.deepcopy(parameters), "parameters")
    outside = set(params) - set(CREATIVE_PARAMETER_KEYS)
    require(not outside, "parameters overwrite a documented or undeclared key: " + ", ".join(sorted(outside)))
    return {
        "id": version_id,
        "name": name,
        "provenance": provenance,
        "parent_id": parent_id,
        "fact_hash": fact_hash,
        "parameters": params,
        "parameter_hash": compute_parameter_hash(parent_id, fact_hash, params),
        "label": label,
    }


def creative_edit(
    facts: dict,
    parent: dict | None,
    new_id: str,
    name: str,
    provenance: str,
    parameters: dict,
) -> dict[str, Any]:
    """Store a derivative reconstruction. Does not modify production facts or the parent."""
    require(type(facts) is dict, "production facts must be an object")
    before_facts = canonical_json(facts)
    digest = hash_facts(facts)
    parent_before = None
    parent_id = None
    label = CREATIVE_LABEL
    if parent is not None:
        require(type(parent) is dict and set(parent) == RECONSTRUCTION_KEYS, "parent reconstruction is invalid")
        parent_before = canonical_json(parent)
        parent_id = parent["id"]
        require(parent["fact_hash"] == digest, "fact hash changed")
        label = USER_LABEL
    child = make_reconstruction(new_id, name, provenance, parent_id, digest, parameters, label)
    require(canonical_json(facts) == before_facts, "same object mutated")
    require(child["fact_hash"] == digest, "fact hash changed")
    if parent is not None:
        require(canonical_json(parent) == parent_before, "parent reconstruction mutated")
        require(child["fact_hash"] == parent["fact_hash"], "fact hash changed")
        require(child["parent_id"] == parent["id"], "parent id was dropped")
        require(child["parameter_hash"] != parent["parameter_hash"], "parameter hash was not versioned")
    return child


def bind_facts(facts: dict) -> dict[str, Any]:
    """Snapshot a live facts dict so a later in-place edit is visible by object identity."""
    parsed = parse_facts(facts, "productionFacts")
    return {
        "object_id": id(facts),
        "canonical": canonical_json(parsed),
        "fact_hash": hash_facts(parsed),
        "facts": parsed,
    }


def reconstructions_for(facts: dict) -> list[dict[str, Any]]:
    parent = creative_edit(
        facts,
        None,
        PARENT_ID,
        PARENT_NAME,
        PARENT_PROVENANCE,
        parent_parameters(),
    )
    child = creative_edit(
        facts,
        parent,
        CHILD_ID,
        CHILD_NAME,
        CHILD_PROVENANCE,
        child_parameters(),
    )
    return [parent, child]


def sample_reconstructions() -> list[dict[str, Any]]:
    return reconstructions_for(sample_facts())


def parse_reconstruction(item: Any, index: int) -> dict[str, Any]:
    require(type(item) is dict, f"reconstructions[{index}] must be an object")
    require(
        set(item) == RECONSTRUCTION_KEYS,
        f"reconstructions[{index}] keys are invalid",
    )
    parent_id = item["parent_id"]
    if parent_id is not None:
        parent_id = require_id(parent_id, f"reconstructions[{index}].parent_id")
    label = require_text(item["label"], f"reconstructions[{index}].label")
    require(label in LABELS, f"reconstructions[{index}].label is not a reconstruction label")
    parameters = parse_parameters(item["parameters"], f"reconstructions[{index}].parameters")
    return {
        "id": require_id(item["id"], f"reconstructions[{index}].id"),
        "name": require_text(item["name"], f"reconstructions[{index}].name"),
        "provenance": require_text(item["provenance"], f"reconstructions[{index}].provenance"),
        "parent_id": parent_id,
        "fact_hash": require_digest(item["fact_hash"], f"reconstructions[{index}].fact_hash"),
        "parameters": parameters,
        "parameter_hash": require_digest(item["parameter_hash"], f"reconstructions[{index}].parameter_hash"),
        "label": label,
    }


def fact_overwrite_faults(
    facts: dict,
    *,
    declared_fact_hash: str,
    prior_canonical: str,
    mutated_facts: bool,
    bound_object_id: int | None,
) -> dict[str, Any]:
    """Reject a documented-fact overwrite from identity, hash, or mutated_facts."""
    parsed = parse_facts(facts, "productionFacts")
    original = require_canonical_facts(prior_canonical, "prior_canonical")
    declared = require_digest(declared_fact_hash, "fact_hash")
    require_bool(mutated_facts, "mutated_facts")
    require(bound_object_id is None or type(bound_object_id) is int, "bound_object_id must be an int or null")
    current_canonical = canonical_json(parsed)
    current_hash = hashlib.sha256(current_canonical.encode("utf-8")).hexdigest()
    original_hash = hashlib.sha256(prior_canonical.encode("utf-8")).hexdigest()
    faults: list[str] = []
    reasons: list[str] = []
    if bound_object_id is not None and bound_object_id == id(facts) and current_canonical != prior_canonical:
        _add(faults, SAME_OBJECT_MUTATED)
        reasons.append(FAULT_TEXT[SAME_OBJECT_MUTATED])
    if declared != current_hash or declared != original_hash or current_hash != original_hash:
        _add(faults, FACT_HASH_CHANGED)
        reasons.append(
            "fact_hash changed: declared "
            + declared
            + " current "
            + current_hash
            + " original "
            + original_hash
        )
    if mutated_facts:
        _add(faults, MUTATED_FACTS)
        reasons.append(FAULT_TEXT[MUTATED_FACTS])
    for key in DOCUMENTED_FACT_KEYS:
        previous = original[key]
        current = parsed[key]
        if previous is not None and current != previous:
            _add(faults, DOCUMENTED_KEY_OVERWRITTEN)
            reasons.append("documented fact key overwritten: " + key)
            if key in CINEMATOGRAPHER_KEYS:
                _add(faults, MUTANT)
                reasons.append("mutant rejected: " + MUTANT)
        elif previous is None and current is not None:
            _add(faults, UNKNOWN_FACT_FILLED)
            reasons.append("unknown fact filled: " + key)
    return {
        "facts": parsed,
        "current_canonical": current_canonical,
        "current_hash": current_hash,
        "original_hash": original_hash,
        "faults": faults,
        "reasons": reasons,
    }


def review_reconstructions(
    facts: dict,
    reconstructions: Any,
    *,
    declared_fact_hash: str,
    prior_canonical: str,
    mutated_facts: bool,
    bound_object_id: int | None,
) -> dict[str, Any]:
    require(isinstance(reconstructions, list) and len(reconstructions) > 0, "reconstructions must be a non-empty list")
    before_facts = canonical_json(facts) if type(facts) is dict else None
    before_versions = []
    for index, item in enumerate(reconstructions):
        require(type(item) is dict, f"reconstructions[{index}] must be an object")
        before_versions.append(canonical_json(item))
    overview = fact_overwrite_faults(
        facts,
        declared_fact_hash=declared_fact_hash,
        prior_canonical=prior_canonical,
        mutated_facts=mutated_facts,
        bound_object_id=bound_object_id,
    )
    parsed = [parse_reconstruction(item, index) for index, item in enumerate(reconstructions)]
    require(canonical_json(facts) == before_facts, "production facts were mutated during review")
    require(
        [canonical_json(item) for item in reconstructions] == before_versions,
        "reconstructions were mutated during review",
    )
    faults = list(overview["faults"])
    reasons = list(overview["reasons"])
    preserved = [
        "fact_hash=" + overview["original_hash"],
        "factCanonical=" + overview["current_canonical"],
    ]
    seen_ids: dict[str, dict[str, Any]] = {}
    original_hash = overview["original_hash"]
    current_hash = overview["current_hash"]
    for index, version in enumerate(parsed):
        preimage = parameter_preimage(version["parent_id"], version["fact_hash"], version["parameters"])
        recomputed = hashlib.sha256(preimage.encode("utf-8")).hexdigest()
        preserved.append("id=" + version["id"])
        preserved.append("label=" + version["label"])
        preserved.append("preimage=" + preimage)
        preserved.append("parameter_hash=" + recomputed)
        reasons.append(version["id"] + " preimage=" + preimage)
        reasons.append(version["id"] + " parameter_hash=" + recomputed)
        reasons.append(version["id"] + " fact_hash=" + version["fact_hash"])
        if recomputed != version["parameter_hash"]:
            _add(faults, PARAMETER_HASH_MISMATCH)
            reasons.append(version["id"] + " parameter_hash does not match its preimage")
        if version["fact_hash"] != original_hash or version["fact_hash"] != current_hash:
            _add(faults, FACT_HASH_CHANGED)
            reasons.append(version["id"] + " fact_hash is not the unchanged production-fact hash")
        outside = sorted(set(version["parameters"]) - set(CREATIVE_PARAMETER_KEYS))
        documented_inside = sorted(set(outside) & set(DOCUMENTED_FACT_KEYS))
        if outside:
            _add(faults, PARAMETERS_OUTSIDE)
            reasons.append(version["id"] + " parameters leave the declared rendering set: " + ", ".join(outside))
        if documented_inside:
            _add(faults, DOCUMENTED_KEY_OVERWRITTEN)
            reasons.append(version["id"] + " parameters overwrite documented facts: " + ", ".join(documented_inside))
        parent_id = version["parent_id"]
        if parent_id is None:
            if index != 0:
                _add(faults, MISSING_PARENT)
                reasons.append(version["id"] + " parent is missing")
            else:
                reasons.append(version["id"] + " parent=null")
        elif parent_id == version["id"] or parent_id not in seen_ids:
            _add(faults, MISSING_PARENT)
            reasons.append(version["id"] + " parent is missing")
        else:
            parent = seen_ids[parent_id]
            reasons.append(version["id"] + " parent=" + parent_id)
            reasons.append(version["id"] + " fact hash unchanged")
            if version["fact_hash"] != parent["fact_hash"]:
                _add(faults, FACT_HASH_CHANGED)
                reasons.append(version["id"] + " changed the parent fact hash")
            if version["label"] != USER_LABEL:
                _add(faults, NOT_USER_RECONSTRUCTION)
                reasons.append(version["id"] + " was not stored as a user reconstruction")
            if version["name"] == parent["name"] or version["provenance"] == parent["provenance"]:
                _add(faults, DERIVATIVE_IDENTITY)
                reasons.append(version["id"] + " is missing its own name or provenance")
            changed = [
                key
                for key in CREATIVE_PARAMETER_KEYS
                if version["parameters"][key] != parent["parameters"][key]
            ]
            reasons.append(version["id"] + " changed=" + ",".join(changed))
        if version["id"] in seen_ids:
            _add(faults, ID_REUSED)
            reasons.append("reconstruction id " + version["id"] + " was reused")
        else:
            seen_ids[version["id"]] = version
    if parsed and not faults:
        reasons.append("fact hash unchanged")
    return {
        "faults": faults,
        "reasons": reasons,
        "preserved": preserved,
        "versions": parsed,
        "original_hash": original_hash,
        "current_hash": current_hash,
    }


def finish_result(
    case_id: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[Any],
    open_questions: list[str],
) -> dict[str, Any]:
    decision = "rejected" if rejected else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": _dedupe(rejected),
        "preservedResults": preserved,
        "openQuestions": list(open_questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(bool(preserved) and isinstance(preserved[0], str) and preserved[0] != "", "evidence wiped")
    require(OPEN_QUESTION in result["openQuestions"], "physical S23 measurement was not noted")
    require(result["decision"] not in {"qualified", "allowed"}, "decision qualified the fixture")
    return result


def _dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def _decide(
    *,
    case_id: str,
    evidence: str,
    claim: str,
    apply_mutant: bool,
    mutated_facts: bool,
    production_facts: dict,
    fact_hash: str,
    prior_canonical: str,
    bound_object_id: int | None,
    reconstructions: list,
    extra_reasons: list[str] | None = None,
) -> dict[str, Any]:
    evidence = require_text(evidence, "evidenceId")
    claim = require_text(claim, "claim")
    require_bool(apply_mutant, "applyMutant")
    review = review_reconstructions(
        production_facts,
        reconstructions,
        declared_fact_hash=fact_hash,
        prior_canonical=prior_canonical,
        mutated_facts=mutated_facts,
        bound_object_id=bound_object_id,
    )
    faults = list(review["faults"])
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "goal: " + GOAL,
        "fixture: " + FIXTURE,
        "fact_hash=" + review["original_hash"],
    ]
    if extra_reasons:
        reasons.extend(extra_reasons)
    reasons.extend(review["reasons"])
    if apply_mutant:
        _add(faults, MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    for token in faults:
        text = FAULT_TEXT.get(token)
        if text and text not in reasons:
            reasons.append(text)
    if not faults:
        reasons.append("method: " + METHOD)
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("creative edit stored without modifying production facts")
    preserved: list[Any] = [evidence, claim]
    preserved.extend(review["preserved"])
    result = finish_result(case_id, reasons, faults, preserved, NON_CLAIM_QUESTIONS)
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(any(item.startswith("fact_hash=") for item in result["preservedResults"] if isinstance(item, str)), "fact hash dropped")
    return result


def assess(document: dict) -> dict[str, Any]:
    """Record a user reconstruction whose production facts stay immutable."""
    require(type(document) is dict, "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    return _decide(
        case_id=PHASE,
        evidence=document["evidenceId"],
        claim=document["claim"],
        apply_mutant=document["applyMutant"],
        mutated_facts=document["mutated_facts"],
        production_facts=document["productionFacts"],
        fact_hash=document["fact_hash"],
        prior_canonical=document["prior_canonical"],
        bound_object_id=None,
        reconstructions=document["reconstructions"],
    )


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate one reconstruction edit. Invalid shapes raise ValueError."""
    require(type(payload) is dict, "payload must be an object")
    missing = EVALUATE_KEYS - set(payload)
    extra = set(payload) - EVALUATE_KEYS
    require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))
    case_id = require_text(payload["caseId"], "caseId")
    return _decide(
        case_id=case_id,
        evidence=payload["evidenceId"],
        claim=payload["claim"],
        apply_mutant=payload["applyMutant"],
        mutated_facts=payload["mutated_facts"],
        production_facts=payload["productionFacts"],
        fact_hash=payload["fact_hash"],
        prior_canonical=payload["prior_canonical"],
        bound_object_id=payload["bound_object_id"],
        reconstructions=payload["reconstructions"],
    )


def fixture_document() -> dict[str, Any]:
    facts = sample_facts()
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "mutated_facts": False,
        "productionFacts": facts,
        "fact_hash": hash_facts(facts),
        "prior_canonical": canonical_json(facts),
        "reconstructions": reconstructions_for(facts),
    }


def bundle_for(facts: dict | None = None, reconstructions: list | None = None) -> dict[str, Any]:
    """Fact fields shared by the case gates. Hashes are recomputed, not copied by hand."""
    body = sample_facts() if facts is None else parse_facts(facts, "productionFacts")
    versions = reconstructions_for(body) if reconstructions is None else reconstructions
    return {
        "productionFacts": body,
        "fact_hash": hash_facts(body),
        "prior_canonical": canonical_json(body),
        "reconstructions": versions,
        "mutated_facts": False,
    }
