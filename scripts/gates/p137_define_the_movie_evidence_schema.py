#!/usr/bin/env python3
"""P137 Define the movie evidence schema.

Host reference only. This module does not probe a device and does not qualify
a physical S23. Every movie field is one of three states: fact, reconstruction,
or unknown. A fact requires a source_id. An unknown value is null. A missing
production lens filled with a guessed name and marked documented or fact is
rejected. A reconstruction is not relabelled fact. A record that mixes those
states on one claim is rejected. Counts of each state are retained.
"""

from __future__ import annotations

import copy
import math
import re
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P137"
WORKSTREAM = 18
TITLE = "Define the movie evidence schema"
GOAL = "Represent production facts, reconstruction choices, and unknowns as different data types."
METHOD = (
    "Store movie, scene family, acquisition format, stock, camera and lens facts, "
    "processing notes, release reference, citations, confidence, and our recipe parameters. "
    "Every documented or contradicted claim needs a source; unknown values remain null rather than guessed."
)
FIXTURE = "A film with documented stock choices but no verified lens information for the selected scene."
ORACLE = (
    "The recipe can use a clearly reconstructed virtual lens while retaining the "
    "production lens field as unknown."
)
MUTANT = "Fill missing lens fields with plausible cinema equipment and mark them documented."
DELIVERABLE = "Movie-claim schema and evidence-state tests"
DEPENDENCIES = ("P007", "P073", "P089", "P121")

STATES = ("fact", "reconstruction", "unknown")
STATE_SET = frozenset(STATES)
DOCUMENTED = "documented"
GUESSED_LENS = "Cooke S4/i 50mm"
EVIDENCE_ID = "p137-movie-evidence"
CLAIM = "movie-evidence-schema-host-reference"
RECORD_ID = "northwater-selected-scene"
PHYSICAL_NOTE = "physical S23 capture was not run"
OPEN_QUESTION = PHYSICAL_NOTE

PRODUCTION_LENS_NAMES = frozenset({"lens", "production_lens", "camera_lens"})
RECONSTRUCTION_ONLY = frozenset({
    "virtual_lens",
    "recipe_parameters",
    "virtual_aperture",
    "grade",
    "grain",
})
POPULARITY_SOURCES = frozenset({"popularity", "rating"})
DECLARED_PARAMETERS = frozenset({"virtual_aperture", "grade", "grain", "virtual_lens"})
CONTENT_ALTERATIONS = frozenset({
    "faces",
    "facial_geometry",
    "text",
    "fine_patterns",
    "moving_objects",
    "scene_texture",
    "generated_scene",
})
REMOVAL_ALIASES = {
    "camera": "camera",
    "lens": "lens",
    "stock": "stock",
    "process": "processing_notes",
    "processing_notes": "processing_notes",
    "release-version": "release_reference",
    "release_reference": "release_reference",
}
RECIPE_OPERATIONS = frozenset({"save", "rename", "share", "update"})
ASSET_KINDS = frozenset({
    "still",
    "lut",
    "profile",
    "promotional-image",
    "commercial-lut",
    "research-weights",
})
REDISTRIBUTION = frozenset({"unknown", "licensed", "denied", "public-visibility"})
EDITIONS = frozenset({"theatrical", "digital", "hdr", "unidentified"})
VARIANT_MODES = frozenset({"color", "monochrome"})

GUESSED_LENS_DOCUMENTED = "guessed-lens-marked-documented"
GUESSED_LENS_FACT = "guessed-lens-marked-fact"
RELABELLED_FACT = "reconstruction-relabelled-fact"
MIXED_STATE = "mixed-state"
DOCUMENTED_STATE = "documented-state-rejected"
TITLE_MATCH = "title-match-establishes-every-scene"
VARIANTS_MISSING = "variants-not-represented"
SCENE_UNCERTAINTY_DROPPED = "scene-uncertainty-dropped"
USER_PREFERENCE = "user-preference-replaced-sourced-metadata"
VERSION_NOT_CREATED = "reconstruction-version-not-created"
PARAMETER_UNCHANGED = "reconstruction-parameter-unchanged"
REMOTE_REQUIRED = "remote-generation-required"
UNAPPROVED_BYTES = "unapproved-bytes-in-bundle"
PUBLIC_AS_LICENCE = "public-visibility-as-licence"
AVERAGED_EDITIONS = "averaged-editions-as-fact"
CONTENT_SYNTHESIS = "unrequested-content-synthesis"
GENERATED_SCENE = "generated-scene-not-footage"
POPULARITY_CERTIFIES = "popularity-certified-identification"

NAME_TEXT = re.compile(r"[a-z][a-z0-9_]*\Z")
RECORD_TEXT = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
SOURCE_TEXT = re.compile(r"[a-z0-9][a-z0-9._:-]*\Z")
STATE_SPLIT = re.compile(r"[|/,+&]+")

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "record",
}
EVALUATE_KEYS = {"caseId", "evidenceId", "claim", "record"}
RECORD_KEYS = {"recordId", "lensVerified", "fields"}
FIELD_REQUIRED = {"name", "state", "value", "source_id"}
FIELD_OPTIONAL = {"priorState", "guessed", "alsoState", "states"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
NON_CLAIM_QUESTIONS = [
    PHYSICAL_NOTE,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]
FAULT_TEXT = {
    GUESSED_LENS_DOCUMENTED: "A plausible equipment guess marked documented must fail.",
    GUESSED_LENS_FACT: "a plausible equipment guess marked fact must fail",
    RELABELLED_FACT: "reconstruction must not be relabelled fact",
    MIXED_STATE: "the schema rejects a record that mixes evidence states",
    DOCUMENTED_STATE: "documented is not an evidence state; use fact, reconstruction, or unknown",
    TITLE_MATCH: "A title match alone must not establish every scene\u2019s technical recipe.",
    VARIANTS_MISSING: "supported acquisition variants must stay represented",
    SCENE_UNCERTAINTY_DROPPED: "scene-level uncertainty must be preserved",
    USER_PREFERENCE: "User preferences must not replace the cinematographer\u2019s sourced metadata.",
    VERSION_NOT_CREATED: "a creative edit must create a new reconstruction version",
    PARAMETER_UNCHANGED: "a named reconstruction parameter must actually change",
    REMOTE_REQUIRED: "A remote generation call must not be required for basic catalogue lookup.",
    UNAPPROVED_BYTES: "unapproved bytes are excluded from the release bundle",
    PUBLIC_AS_LICENCE: "Public visibility must not be treated as a redistribution licence.",
    AVERAGED_EDITIONS: "Averaging inconsistent editions into a historical fact must fail.",
    CONTENT_SYNTHESIS: "matching is restricted to declared rendering parameters",
    GENERATED_SCENE: "A visually similar generated scene is not preserved camera footage.",
    POPULARITY_CERTIFIES: "Popularity cannot certify a stock or lens identification.",
}

CATALOGUE = (
    {
        "id": "northwater",
        "title": "Northwater",
        "alternateTitles": ("Lamp of the North",),
        "stocks": ("Eastman 5293", "5293"),
        "formats": ("35mm-4-perf",),
        "monochrome": False,
        "sceneFamilies": ("night-interior", "day-exterior"),
        "evidenceStatus": {
            "stock": "fact",
            "lens": "unknown",
            "virtual_lens": "reconstruction",
        },
    },
    {
        "id": "glass-orchard",
        "title": "Glass Orchard",
        "alternateTitles": ("The Glass Orchard",),
        "stocks": ("Double-X",),
        "formats": ("16mm",),
        "monochrome": True,
        "sceneFamilies": ("day-exterior",),
        "evidenceStatus": {
            "stock": "fact",
            "lens": "unknown",
            "virtual_lens": "reconstruction",
        },
    },
    {
        "id": "kiln-road",
        "title": "Kiln Road",
        "alternateTitles": ("Kiln",),
        "stocks": ("Eastman 5293",),
        "formats": ("65mm-5-perf", "35mm-4-perf"),
        "monochrome": False,
        "sceneFamilies": ("night-interior",),
        "evidenceStatus": {
            "stock": "reconstruction",
            "lens": "unknown",
            "virtual_lens": "reconstruction",
        },
    },
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_text(value: object, label: str) -> str:
    require(
        isinstance(value, str) and bool(value.strip()) and value == value.strip(),
        label + " must be a non-empty string",
    )
    return value


def require_bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def require_number(value: object, label: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number",
    )
    number = float(value)
    require(math.isfinite(number), label + " must be finite")
    return number


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def blank_counts() -> dict[str, int]:
    return {state: 0 for state in STATES}


def counts_reason(counts: dict[str, int]) -> str:
    return (
        "stateCounts fact="
        + str(counts["fact"])
        + " reconstruction="
        + str(counts["reconstruction"])
        + " unknown="
        + str(counts["unknown"])
    )


def _validate_json_value(value: Any, label: str) -> None:
    if value is None or type(value) is bool or isinstance(value, str):
        return
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        require(math.isfinite(float(value)), label + " must be finite")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            require(
                isinstance(key, str) and bool(key.strip()) and key == key.strip(),
                label + " keys must be non-empty strings",
            )
            _validate_json_value(item, label + "." + key)
        return
    raise ValueError(label + " must be JSON-compatible")


def _known_state(part: str, label: str) -> str:
    require(
        part in STATE_SET or part == DOCUMENTED,
        label + " must be fact, reconstruction, or unknown",
    )
    return part


def split_state(raw: object, label: str) -> tuple[list[str], bool]:
    if isinstance(raw, list):
        require(len(raw) >= 1, label + " state must not be empty")
        parts = [_known_state(require_text(item, label + ".state"), label) for item in raw]
        return parts, len(parts) != 1
    require(isinstance(raw, str), label + " state must be a string")
    require(bool(raw.strip()) and raw == raw.strip(), label + " state must be a non-empty string")
    if any(ch.isspace() for ch in raw):
        parts = [part for part in raw.split() if part]
    else:
        parts = [part.strip() for part in STATE_SPLIT.split(raw) if part.strip()]
    require(parts, label + " state must not be empty")
    for part in parts:
        _known_state(part, label)
    return parts, len(parts) != 1


def parse_field(value: Any, label: str = "field") -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    extra = set(value) - FIELD_REQUIRED - FIELD_OPTIONAL
    missing = FIELD_REQUIRED - set(value)
    require(not missing, label + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, label + " has unexpected fields: " + ", ".join(sorted(extra)))
    name = require_text(value["name"], label + ".name")
    require(NAME_TEXT.fullmatch(name) is not None, label + ".name is not a field token")
    parts, mixed = split_state(value["state"], label)
    source = value["source_id"]
    if source is not None:
        source = require_text(source, label + ".source_id")
        require(SOURCE_TEXT.fullmatch(source) is not None, label + ".source_id is not a source token")
    guessed = False
    if "guessed" in value:
        guessed = require_bool(value["guessed"], label + ".guessed")
    prior = None
    if "priorState" in value:
        prior = _known_state(require_text(value["priorState"], label + ".priorState"), label)
    also = None
    if "alsoState" in value:
        also = _known_state(require_text(value["alsoState"], label + ".alsoState"), label)
        mixed = True
    if "states" in value:
        listed = value["states"]
        require(isinstance(listed, list) and len(listed) >= 1, label + ".states must be a non-empty list")
        listed_parts = [_known_state(require_text(item, label + ".states"), label) for item in listed]
        if len(listed_parts) != 1 or listed_parts != parts:
            mixed = True
    raw_value = value["value"]
    _validate_json_value(raw_value, label + ".value")
    single = parts[0] if len(parts) == 1 and not mixed else None
    if single == "unknown":
        require(raw_value is None, "state unknown must have value null")
        require(source is None, "state unknown must not carry a source_id")
    if single == "fact":
        require(source is not None, "state fact requires a source_id")
        require(raw_value is not None, "state fact must have a value")
    if single == "reconstruction":
        require(raw_value is not None, "state reconstruction must have a value")
    submitted = value["state"] if isinstance(value["state"], str) else list(parts)
    return {
        "name": name,
        "parts": parts,
        "mixed": mixed or len(set(parts)) != 1,
        "submittedState": submitted,
        "value": raw_value,
        "source_id": source,
        "guessed": guessed,
        "priorState": prior,
        "alsoState": also,
    }


def parse_record(value: Any, label: str = "record") -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    missing = RECORD_KEYS - set(value)
    extra = set(value) - RECORD_KEYS
    require(not missing, label + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, label + " has unexpected fields: " + ", ".join(sorted(extra)))
    record_id = require_text(value["recordId"], label + ".recordId")
    require(RECORD_TEXT.fullmatch(record_id) is not None, label + ".recordId is not a record token")
    lens_verified = require_bool(value["lensVerified"], label + ".lensVerified")
    fields = value["fields"]
    require(isinstance(fields, list) and len(fields) >= 1, label + ".fields must be a non-empty list")
    parsed = [parse_field(item, f"{label}.fields[{index}]") for index, item in enumerate(fields)]
    return {"recordId": record_id, "lensVerified": lens_verified, "fields": parsed}


def _public_field(
    name: str,
    retained: str | None,
    submitted: object,
    submitted_value: object,
    retained_value: object,
    source_id: str | None,
) -> dict[str, Any]:
    return {
        "name": name,
        "state": retained,
        "submittedState": submitted,
        "submittedValue": submitted_value,
        "value": retained_value,
        "source_id": source_id,
    }


def judge_record(record: dict) -> dict[str, Any]:
    """Classify each field and reject mixed, guessed, or relabelled claims.

    Counts cover retained states only. A rejected fact promotion does not
    increase the fact count. Unknown stays null.
    """
    parsed = parse_record(record)
    faults: list[str] = []
    by_name: dict[str, dict[str, Any]] = {}
    for field in parsed["fields"]:
        previous = by_name.get(field["name"])
        if previous is None:
            by_name[field["name"]] = field
            continue
        if previous["parts"] != field["parts"] or previous["mixed"] or field["mixed"]:
            previous["mixed"] = True
            field["mixed"] = True
            faults.append(MIXED_STATE)
        else:
            raise ValueError("duplicate field " + field["name"])
    counts = blank_counts()
    retained: list[dict[str, Any]] = []
    lens_verified = parsed["lensVerified"]
    for field in parsed["fields"]:
        name = field["name"]
        submitted_value = field["value"]
        if field["mixed"] or len(set(field["parts"])) != 1:
            faults.append(MIXED_STATE)
            retained.append(
                _public_field(name, None, field["submittedState"], submitted_value, None, None)
            )
            continue
        state = field["parts"][0]
        source = field["source_id"]
        if state == DOCUMENTED:
            if name in PRODUCTION_LENS_NAMES:
                faults.append(GUESSED_LENS_DOCUMENTED)
            else:
                faults.append(DOCUMENTED_STATE)
            retained_state = "unknown" if field["priorState"] in (None, "unknown") else (
                field["priorState"] if field["priorState"] in STATE_SET else None
            )
            if retained_state in counts:
                counts[retained_state] += 1
            retained_value = None if retained_state == "unknown" else submitted_value
            retained_source = None if retained_state != "fact" else source
            retained.append(
                _public_field(
                    name,
                    retained_state,
                    field["submittedState"],
                    submitted_value,
                    retained_value,
                    retained_source,
                )
            )
            continue
        relabel = (field["priorState"] == "reconstruction" and state == "fact") or (
            name in RECONSTRUCTION_ONLY and state == "fact"
        )
        if relabel:
            faults.append(RELABELLED_FACT)
        guessed_fact = (
            name in PRODUCTION_LENS_NAMES
            and state == "fact"
            and submitted_value is not None
            and (field["guessed"] or (not lens_verified) or field["priorState"] == "unknown")
        )
        if guessed_fact:
            faults.append(GUESSED_LENS_FACT)
        if relabel:
            retained_state = "reconstruction"
            retained_value = submitted_value
            retained_source = None
        elif guessed_fact:
            retained_state = "unknown"
            retained_value = None
            retained_source = None
        else:
            retained_state = state
            retained_value = submitted_value
            retained_source = source
        counts[retained_state] += 1
        retained.append(
            _public_field(
                name,
                retained_state,
                field["submittedState"],
                submitted_value,
                retained_value,
                retained_source,
            )
        )
    ordered = dedupe(faults)
    reasons = [counts_reason(counts)]
    if not ordered:
        reasons.append("fact, reconstruction, and unknown stayed distinct")
    return {
        "recordId": parsed["recordId"],
        "lensVerified": lens_verified,
        "faults": ordered,
        "stateCounts": counts,
        "retainedFields": retained,
        "reasons": reasons,
    }


def find_field(fields: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for field in fields:
        if field["name"] == name:
            return field
    return None


def make_field(
    name: str,
    state: str,
    value: Any,
    source_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    field: dict[str, Any] = {
        "name": name,
        "state": state,
        "value": value,
        "source_id": source_id,
    }
    field.update(extra)
    return field


def fixture_fields() -> list[dict[str, Any]]:
    return [
        make_field("movie", "fact", "Northwater", "src-northwater-title"),
        make_field("scene_family", "fact", "night-interior", "src-northwater-scene"),
        make_field("acquisition_format", "fact", "35mm-4-perf", "src-northwater-format"),
        make_field("stock", "fact", "Eastman 5293", "src-northwater-stock"),
        make_field("camera", "fact", "Arriflex 535", "src-northwater-camera"),
        make_field("lens", "unknown", None, None),
        make_field("processing_notes", "unknown", None, None),
        make_field("release_reference", "fact", "theatrical", "src-northwater-release"),
        make_field(
            "citations",
            "fact",
            ["src-northwater-stock", "src-northwater-camera"],
            "src-northwater-stock",
        ),
        make_field("confidence", "reconstruction", "partial-scene", None),
        make_field(
            "recipe_parameters",
            "reconstruction",
            {
                "virtual_lens": "virtual-spherical-50mm",
                "aperture": "T2.8",
                "label": "reconstruction",
            },
            None,
        ),
        make_field("virtual_lens", "reconstruction", "virtual-spherical-50mm", None),
    ]


def fixture_record() -> dict[str, Any]:
    return {
        "recordId": RECORD_ID,
        "lensVerified": False,
        "fields": fixture_fields(),
    }


def fixture_document() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "record": fixture_record(),
    }


def apply_lens_mutant(record: dict) -> dict[str, Any]:
    """Fill the missing production lens with plausible equipment marked documented."""
    require(isinstance(record, dict), "record must be an object")
    clone = copy.deepcopy(record)
    require(isinstance(clone.get("fields"), list), "record.fields must be a list")
    clone["lensVerified"] = False
    guessed = make_field(
        "lens",
        DOCUMENTED,
        GUESSED_LENS,
        None,
        guessed=True,
        priorState="unknown",
    )
    replaced = False
    for index, field in enumerate(clone["fields"]):
        if isinstance(field, dict) and field.get("name") == "lens":
            clone["fields"][index] = guessed
            replaced = True
            break
    if not replaced:
        clone["fields"].append(guessed)
    return clone


def strip_fields(record: dict, removed: list) -> dict[str, Any]:
    require(isinstance(removed, list), "removed must be a list")
    names: list[str] = []
    for item in removed:
        require(isinstance(item, str) and item in REMOVAL_ALIASES, "removed field is not repeatable")
        names.append(REMOVAL_ALIASES[item])
    clone = copy.deepcopy(record)
    require(isinstance(clone, dict) and isinstance(clone.get("fields"), list), "record.fields must be a list")
    found: set[str] = set()
    for field in clone["fields"]:
        require(isinstance(field, dict), "field must be an object")
        if field.get("name") in names:
            field["state"] = "unknown"
            field["value"] = None
            field["source_id"] = None
            for optional in ("guessed", "priorState", "alsoState", "states"):
                field.pop(optional, None)
            found.add(field["name"])
    missing = [name for name in names if name not in found]
    require(not missing, "record missing fields: " + ", ".join(missing))
    return clone


def detail_from_judged(judged: dict[str, Any]) -> dict[str, Any]:
    retained = judged["retainedFields"]
    return {
        "stateCounts": judged["stateCounts"],
        "retainedFields": retained,
        "productionLens": find_field(retained, "lens"),
        "virtualLens": find_field(retained, "virtual_lens"),
        "stock": find_field(retained, "stock"),
        "recordId": judged["recordId"],
    }


def seal(
    case_id: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    open_questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    decision = "rejected" if faults else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "decision cannot be qualified or allowed")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": dedupe(faults),
        "preservedResults": preserved,
        "openQuestions": list(open_questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(OPEN_QUESTION in result["openQuestions"], "physical S23 not run must be noted")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(bool(result["rejectedClaims"]) == (result["decision"] == "rejected"), "decision does not match claims")
    return result


def finish_host(
    case_id: str,
    evidence: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    repeat: str,
    fault_text: dict[str, str] | None = None,
) -> dict[str, Any]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    ordered = dedupe(faults)
    body = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "repeat " + repeat,
        *reasons,
    ]
    for token in ordered:
        body.append(text.get(token, token))
    if not ordered:
        body.append("recorded; fact, reconstruction, and unknown remain distinct; not a physical qualification")
    questions = list(NON_CLAIM_QUESTIONS) + [repeat]
    return seal(case_id, ordered, body, preserved, questions, evidence)


def _phase_reasons(judged: dict[str, Any], faults: list[str], mutant: bool) -> list[str]:
    reasons = [
        "host reference only; not a physical S23 measurement",
        "goal: " + GOAL,
        "method: " + METHOD,
        "fixture: " + FIXTURE,
        "oracle: " + ORACLE,
        *judged["reasons"],
    ]
    for token in faults:
        reasons.append(FAULT_TEXT[token])
    if mutant:
        reasons.append("mutant rejected: " + MUTANT)
    if not faults:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("movie evidence schema recorded; fact, reconstruction, and unknown stay distinct")
    return reasons


def assess(document: dict) -> dict[str, Any]:
    """Record a typed movie claim, or reject a guessed lens, relabel, or mixed state."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = require_text(document["evidenceId"], "evidenceId")
    claim = require_text(document["claim"], "claim")
    apply_mutant = require_bool(document["applyMutant"], "applyMutant")
    incoming = document["record"]
    judged_input = apply_lens_mutant(incoming) if apply_mutant else incoming
    judged = judge_record(judged_input)
    faults = list(judged["faults"])
    reasons = _phase_reasons(judged, faults, apply_mutant)
    preserved = [evidence, detail_from_judged(judged), claim]
    return seal(PHASE, faults, reasons, preserved, NON_CLAIM_QUESTIONS, evidence)


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate one movie-evidence record. A phase document is assessed."""
    require(isinstance(payload, dict), "payload must be an object")
    if "schemaVersion" in payload:
        return assess(payload)
    if payload.get("decision") in {"qualified", "allowed"}:
        raise ValueError("decision cannot be qualified or allowed")
    missing = EVALUATE_KEYS - set(payload)
    extra = set(payload) - EVALUATE_KEYS
    require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))
    case_id = require_text(payload["caseId"], "caseId")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    claim = require_text(payload["claim"], "claim")
    judged = judge_record(payload["record"])
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        *judged["reasons"],
    ]
    for token in judged["faults"]:
        reasons.append(FAULT_TEXT[token])
    if not judged["faults"]:
        reasons.append("movie evidence schema recorded; fact, reconstruction, and unknown stay distinct")
    preserved = [evidence, detail_from_judged(judged), claim]
    return seal(case_id, list(judged["faults"]), reasons, preserved, NON_CLAIM_QUESTIONS, evidence)


def levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for index, char in enumerate(left, 1):
        current = [index]
        for other_index, other in enumerate(right, 1):
            insert = current[other_index - 1] + 1
            delete = previous[other_index] + 1
            replace = previous[other_index - 1] + (char != other)
            current.append(min(insert, delete, replace))
        previous = current
    return previous[-1]


def _match_distance(query: str, text: str) -> int:
    folded_query = query.casefold()
    folded_text = text.casefold()
    if folded_query == folded_text:
        return 0
    if len(folded_query) >= 4 and (folded_query in folded_text or folded_text in folded_query):
        return 0
    return levenshtein(folded_query, folded_text)


def _passes_filter(item: dict[str, Any], filters: dict[str, Any]) -> bool:
    if filters["format"] is not None and filters["format"] not in item["formats"]:
        return False
    if filters["monochrome"] is not None and filters["monochrome"] is not item["monochrome"]:
        return False
    if filters["sceneFamily"] is not None and filters["sceneFamily"] not in item["sceneFamilies"]:
        return False
    return True


def search_catalogue(query: str, filters: dict, remote_required: bool) -> dict[str, Any]:
    """Offline catalogue lookup. Network is never used. Remote requirement is a fault."""
    query = require_text(query, "query")
    require(len(query) >= 3, "query is too short")
    require(isinstance(filters, dict), "filters must be an object")
    require(set(filters) == {"format", "monochrome", "sceneFamily"}, "filters keys are invalid")
    if filters["format"] is not None:
        require_text(filters["format"], "filters.format")
    if filters["monochrome"] is not None:
        require_bool(filters["monochrome"], "filters.monochrome")
    if filters["sceneFamily"] is not None:
        require_text(filters["sceneFamily"], "filters.sceneFamily")
    remote = require_bool(remote_required, "remoteRequired")
    candidates: list[dict[str, Any]] = []
    for item in CATALOGUE:
        if not _passes_filter(item, filters):
            continue
        keys = [("title", item["title"])]
        keys.extend(("alternateTitle", title) for title in item["alternateTitles"])
        keys.extend(("stock", stock) for stock in item["stocks"])
        best: tuple[int, str, str] | None = None
        for label, text in keys:
            distance = _match_distance(query, text)
            if distance <= 2 and (best is None or distance < best[0]):
                best = (distance, label, text)
        if best is None:
            continue
        candidates.append({
            "id": item["id"],
            "title": item["title"],
            "distance": best[0],
            "matchedOn": best[1],
            "matchedText": best[2],
            "evidenceStatus": dict(item["evidenceStatus"]),
            "networkUsed": False,
        })
    candidates.sort(key=lambda item: (item["distance"], item["id"]))
    faults = [REMOTE_REQUIRED] if remote else []
    counts = blank_counts()
    for candidate in candidates:
        for status in candidate["evidenceStatus"].values():
            if status in counts:
                counts[status] += 1
    return {
        "candidates": candidates,
        "faults": faults,
        "stateCounts": counts,
        "networkUsed": False,
    }


def _variant(value: Any, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    keys = {"sceneFamily", "acquisition", "stock", "mode", "state", "source_id"}
    require(set(value) == keys, label + " keys are invalid")
    scene = require_text(value["sceneFamily"], label + ".sceneFamily")
    acquisition = require_text(value["acquisition"], label + ".acquisition")
    stock = require_text(value["stock"], label + ".stock")
    mode = require_text(value["mode"], label + ".mode")
    require(mode in VARIANT_MODES, label + ".mode is not color or monochrome")
    state = require_text(value["state"], label + ".state")
    require(state in STATE_SET, label + ".state must be fact, reconstruction, or unknown")
    source = value["source_id"]
    if state == "fact":
        source = require_text(source, label + ".source_id")
        require(SOURCE_TEXT.fullmatch(source) is not None, label + ".source_id is not a source token")
    elif state == "unknown":
        require(source is None, "state unknown must not carry a source_id")
    elif source is not None:
        source = require_text(source, label + ".source_id")
    return {
        "sceneFamily": scene,
        "acquisition": acquisition,
        "stock": stock,
        "mode": mode,
        "state": state,
        "source_id": source,
    }


def judge_variants(variants: Any, assign_to_every_shot: bool, title_match_only: bool, scene_unknowns: Any) -> dict[str, Any]:
    require(isinstance(variants, list) and len(variants) >= 1, "variants must be a non-empty list")
    parsed = [_variant(item, f"variants[{index}]") for index, item in enumerate(variants)]
    assign = require_bool(assign_to_every_shot, "assignToEveryShot")
    title_match = require_bool(title_match_only, "titleMatchOnly")
    require(isinstance(scene_unknowns, list), "sceneUnknowns must be a list")
    unknowns: list[str] = []
    for item in scene_unknowns:
        name = require_text(item, "sceneUnknowns")
        require(NAME_TEXT.fullmatch(name) is not None, "sceneUnknowns entry is not a field token")
        unknowns.append(name)
    faults: list[str] = []
    signatures = {(item["acquisition"], item["stock"], item["mode"], item["sceneFamily"]) for item in parsed}
    if len(parsed) < 2 or len(signatures) < 2:
        faults.append(VARIANTS_MISSING)
    if assign or title_match:
        faults.append(TITLE_MATCH)
    for item in parsed:
        if item["source_id"] == "title-match":
            faults.append(TITLE_MATCH)
    if "lens" not in unknowns:
        faults.append(SCENE_UNCERTAINTY_DROPPED)
    counts = blank_counts()
    for item in parsed:
        counts[item["state"]] += 1
    counts["unknown"] += len(unknowns)
    return {
        "variants": parsed,
        "sceneUnknowns": [{"name": name, "state": "unknown", "value": None} for name in unknowns],
        "faults": dedupe(faults),
        "stateCounts": counts,
    }


def _same_value(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=0.0)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_same_value(a, b) for a, b in zip(left, right))
    if isinstance(left, dict) and isinstance(right, dict):
        return set(left) == set(right) and all(_same_value(left[key], right[key]) for key in left)
    return left == right


def judge_derivative(
    historical: dict,
    derivative: dict,
    operation: str,
    changed: list,
    historical_version: str,
    derivative_version: str,
) -> dict[str, Any]:
    operation = require_text(operation, "operation")
    require(operation in RECIPE_OPERATIONS, "operation is not save, rename, share, or update")
    historical_version = require_text(historical_version, "historicalVersion")
    derivative_version = require_text(derivative_version, "derivativeVersion")
    require(isinstance(changed, list) and len(changed) >= 1, "changed must name a reconstruction parameter")
    changed_names: list[str] = []
    for item in changed:
        name = require_text(item, "changed")
        require(name in {"virtual_aperture", "grade", "grain"}, "changed parameter is not aperture, grade, or grain")
        changed_names.append(name)
    before = judge_record(historical)
    after = judge_record(derivative)
    faults = list(before["faults"]) + list(after["faults"])
    before_fields = {item["name"]: item for item in before["retainedFields"]}
    after_fields = {item["name"]: item for item in after["retainedFields"]}
    for name, field in before_fields.items():
        if field["state"] != "fact":
            continue
        other = after_fields.get(name)
        if other is None or other["state"] != "fact" or other["source_id"] != field["source_id"]:
            faults.append(USER_PREFERENCE)
            continue
        if not _same_value(other["value"], field["value"]):
            faults.append(USER_PREFERENCE)
    if historical_version == derivative_version:
        faults.append(VERSION_NOT_CREATED)
    for name in changed_names:
        earlier = before_fields.get(name)
        later = after_fields.get(name)
        if later is None or later["state"] != "reconstruction":
            faults.append(RELABELLED_FACT if later and later["submittedState"] == "fact" else PARAMETER_UNCHANGED)
            continue
        if earlier is not None and _same_value(earlier["value"], later["value"]):
            faults.append(PARAMETER_UNCHANGED)
    counts = blank_counts()
    for field in after["retainedFields"]:
        if field["state"] in counts:
            counts[field["state"]] += 1
    return {
        "faults": dedupe(faults),
        "stateCounts": counts,
        "historicalFacts": [field for field in before["retainedFields"] if field["state"] == "fact"],
        "derivative": after,
        "operation": operation,
        "historicalVersion": historical_version,
        "derivativeVersion": derivative_version,
        "changed": changed_names,
    }


def judge_asset(asset: Any) -> dict[str, Any]:
    require(isinstance(asset, dict), "asset must be an object")
    keys = {"kind", "publiclyAccessible", "redistribution", "citation", "bytesInBundle"}
    require(set(asset) == keys, "asset keys are invalid")
    kind = require_text(asset["kind"], "asset.kind")
    require(kind in ASSET_KINDS, "asset.kind is not a still, LUT, profile, or repeat kind")
    public = require_bool(asset["publiclyAccessible"], "asset.publiclyAccessible")
    redistribution = require_text(asset["redistribution"], "asset.redistribution")
    require(redistribution in REDISTRIBUTION, "asset.redistribution is not recognized")
    citation = require_text(asset["citation"], "asset.citation")
    bundled = require_bool(asset["bytesInBundle"], "asset.bytesInBundle")
    faults: list[str] = []
    if redistribution in {"unknown", "denied"} and bundled:
        faults.append(UNAPPROVED_BYTES)
    if redistribution == "public-visibility":
        faults.append(PUBLIC_AS_LICENCE)
        if bundled:
            faults.append(UNAPPROVED_BYTES)
    counts = blank_counts()
    counts["fact"] += 1
    if redistribution == "licensed":
        counts["fact"] += 1
    else:
        counts["unknown"] += 1
    return {
        "faults": dedupe(faults),
        "stateCounts": counts,
        "kind": kind,
        "publiclyAccessible": public,
        "redistribution": redistribution,
        "citation": citation,
        "bytesInBundle": bundled,
        "bundleExcluded": not bundled,
    }


def _reference(value: Any, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    keys = {"edition", "appearance", "state", "source_id"}
    require(set(value) == keys, label + " keys are invalid")
    edition = require_text(value["edition"], label + ".edition")
    require(edition in EDITIONS, label + ".edition is not a known reference")
    state = require_text(value["state"], label + ".state")
    require(state in STATE_SET, label + ".state must be fact, reconstruction, or unknown")
    appearance = value["appearance"]
    _validate_json_value(appearance, label + ".appearance")
    source = value["source_id"]
    if state == "unknown":
        require(appearance is None, "state unknown must have value null")
        require(source is None, "state unknown must not carry a source_id")
    elif state == "fact":
        source = require_text(source, label + ".source_id")
        require(appearance is not None, "state fact must have a value")
    else:
        require(appearance is not None, "state reconstruction must have a value")
        if source is not None:
            source = require_text(source, label + ".source_id")
    return {"edition": edition, "appearance": appearance, "state": state, "source_id": source}


def judge_editions(references: Any, definitive: Any) -> dict[str, Any]:
    require(isinstance(references, list) and len(references) >= 2, "references must contain at least two editions")
    parsed = [_reference(item, f"references[{index}]") for index, item in enumerate(references)]
    appearances = [item["appearance"] for item in parsed if item["appearance"] is not None]
    distinct = []
    for appearance in appearances:
        if not any(_same_value(appearance, kept) for kept in distinct):
            distinct.append(appearance)
    counts = blank_counts()
    for item in parsed:
        counts[item["state"]] += 1
    faults: list[str] = []
    retained_definitive = None
    if definitive is not None:
        field = parse_field(definitive, "definitive")
        if field["mixed"] or len(set(field["parts"])) != 1:
            faults.append(MIXED_STATE)
        else:
            state = field["parts"][0]
            conflict = len(distinct) > 1 and state == "fact"
            numbers = [
                float(item)
                for item in appearances
                if isinstance(item, (int, float)) and not isinstance(item, bool)
            ]
            averaged = False
            if (
                len(numbers) >= 2
                and isinstance(field["value"], (int, float))
                and not isinstance(field["value"], bool)
            ):
                mean = sum(numbers) / len(numbers)
                averaged = math.isclose(float(field["value"]), mean, rel_tol=0.0, abs_tol=1e-9)
            if conflict or (averaged and state == "fact"):
                faults.append(AVERAGED_EDITIONS)
                counts["unknown"] += 1
                retained_definitive = _public_field(
                    field["name"], "unknown", field["submittedState"], field["value"], None, None
                )
            else:
                counts[state] += 1
                retained_definitive = _public_field(
                    field["name"],
                    state,
                    field["submittedState"],
                    field["value"],
                    field["value"],
                    field["source_id"],
                )
    return {
        "references": parsed,
        "distinctAppearances": len(distinct),
        "definitive": retained_definitive,
        "faults": dedupe(faults),
        "stateCounts": counts,
    }


def judge_match(footage_id: Any, output_id: Any, parameters: Any, alters: Any) -> dict[str, Any]:
    footage = require_text(footage_id, "footageId")
    output = require_text(output_id, "outputId")
    require(isinstance(parameters, dict), "parameters must be an object")
    require(isinstance(alters, list), "alters must be a list")
    declared: dict[str, Any] = {}
    faults: list[str] = []
    for key, value in parameters.items():
        require(isinstance(key, str) and key == key.strip() and key, "parameter name must be a non-empty string")
        _validate_json_value(value, "parameters." + key)
        if key not in DECLARED_PARAMETERS:
            faults.append(CONTENT_SYNTHESIS)
            if key in CONTENT_ALTERATIONS:
                faults.append(GENERATED_SCENE)
        else:
            declared[key] = value
    alter_names: list[str] = []
    for item in alters:
        name = require_text(item, "alters")
        alter_names.append(name)
        if name in CONTENT_ALTERATIONS or name not in DECLARED_PARAMETERS:
            faults.append(CONTENT_SYNTHESIS)
    if set(alter_names) & CONTENT_ALTERATIONS or footage != output:
        faults.append(GENERATED_SCENE)
    counts = blank_counts()
    counts["fact"] += 1
    counts["reconstruction"] += len(declared)
    return {
        "footageId": footage,
        "outputId": output if footage == output and GENERATED_SCENE not in faults else footage,
        "parameters": declared,
        "alters": alter_names,
        "faults": dedupe(faults),
        "stateCounts": counts,
        "preservedFootage": footage,
    }


def judge_preferences(recipes: Any) -> dict[str, Any]:
    require(isinstance(recipes, list) and len(recipes) >= 2, "recipes must contain at least two entries")
    parsed: list[dict[str, Any]] = []
    for index, recipe in enumerate(recipes):
        label = f"recipes[{index}]"
        require(isinstance(recipe, dict), label + " must be an object")
        keys = {"id", "rating", "stock", "lens", "certifiedByRating"}
        require(set(recipe) == keys, label + " keys are invalid")
        ident = require_text(recipe["id"], label + ".id")
        rating = require_number(recipe["rating"], label + ".rating")
        require(0.0 <= rating <= 5.0, label + ".rating must be from 0 to 5")
        certified = require_bool(recipe["certifiedByRating"], label + ".certifiedByRating")
        stock = parse_field(recipe["stock"], label + ".stock")
        lens = parse_field(recipe["lens"], label + ".lens")
        require(stock["name"] == "stock", label + ".stock must name stock")
        require(lens["name"] == "lens", label + ".lens must name lens")
        parsed.append({
            "id": ident,
            "rating": rating,
            "certifiedByRating": certified,
            "stock": stock,
            "lens": lens,
        })
    faults: list[str] = []
    counts = blank_counts()
    retained_recipes: list[dict[str, Any]] = []

    def promoted(field: dict[str, Any], certified: bool) -> bool:
        if field["mixed"] or len(set(field["parts"])) != 1:
            return False
        return field["parts"][0] == "fact" and (certified or field["source_id"] in POPULARITY_SOURCES)

    for recipe in parsed:
        entry_fields = []
        for field in (recipe["stock"], recipe["lens"]):
            if field["mixed"] or len(set(field["parts"])) != 1:
                faults.append(MIXED_STATE)
                entry_fields.append(
                    _public_field(field["name"], None, field["submittedState"], field["value"], None, None)
                )
                continue
            if promoted(field, recipe["certifiedByRating"]):
                faults.append(POPULARITY_CERTIFIES)
                retained_state = "unknown" if field["name"] == "lens" else "reconstruction"
                counts[retained_state] += 1
                entry_fields.append(
                    _public_field(
                        field["name"],
                        retained_state,
                        field["submittedState"],
                        field["value"],
                        None if retained_state == "unknown" else field["value"],
                        None,
                    )
                )
                continue
            state = field["parts"][0]
            counts[state] += 1
            entry_fields.append(
                _public_field(
                    field["name"],
                    state,
                    field["submittedState"],
                    field["value"],
                    field["value"],
                    field["source_id"],
                )
            )
        retained_recipes.append({
            "id": recipe["id"],
            "rating": recipe["rating"],
            "fields": entry_fields,
        })
    preferences = [{"id": recipe["id"], "rating": recipe["rating"]} for recipe in parsed]
    return {
        "faults": dedupe(faults),
        "stateCounts": counts,
        "preferences": preferences,
        "recipes": retained_recipes,
        "preferenceSeparate": True,
    }
