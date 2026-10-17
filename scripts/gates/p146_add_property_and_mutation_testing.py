#!/usr/bin/env python3
"""P146 Add property and mutation testing.

Host reference only. This module does not probe a device and does not qualify
a physical S23. A mutation catalogue lists mutants with input, expected_detection,
and detected. A catalogue that is only happy-path examples (no mutant with a
changed field) is rejected. A mutant with expected_detection true and detected
false survives and is rejected. The fixture mutant replaces exact timestamp
pairing with nearest-neighbor matching on a close-but-wrong timestamp; the
metadata association test must kill it. For a list of numeric samples, shuffling
order must not change a commutative sum; if that property fails, the
implementation claim is rejected. Identical metadata on every property-suite
example is rejected.

Mutation rule: a catalogue entry is a mutant only when at least one field of
input differs from original, or a declared changedField / changedFields entry
names a change when original is absent. No changed field anywhere means the
catalogue is happy-path-only and is rejected. expected_detection true with
detected false is a surviving mutant and is rejected. Shuffling samples must
not change the commutative sum. Identical property-suite metadata is rejected.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P146"
WORKSTREAM = 19
TITLE = "Add property and mutation testing"
GOAL = "Prove that tests can detect plausible defects rather than merely execute lines."
METHOD = (
    "Generate valid and invalid numeric domains, temporal event sequences, geometry "
    "combinations, and malformed records. Introduce selected mutants such as range "
    "confusion, timestamp reuse, CFA swaps, and missing hash checks. Require critical "
    "mutants to be killed by the intended tests."
)
FIXTURE = "A mutation replacing exact timestamp pairing with nearest-neighbor matching."
ORACLE = "The metadata association test fails for the deliberately close-but-wrong timestamp fixture."
MUTANT = "Run only happy-path examples with conveniently identical metadata."
DELIVERABLE = "Property generators and critical mutation catalogue"
DEPENDENCIES = ("P145",)

MUTATION_RULE = (
    "A catalogue entry is a mutant only when at least one field of input differs from "
    "original (or a declared changedField is present when original is absent). A catalogue "
    "with no changed field is happy-path-only and is rejected. A mutant with expected_detection "
    "true and detected false survives and is rejected. The fixture that replaces exact "
    "timestamp pairing with nearest-neighbor matching on a close-but-wrong timestamp must be "
    "killed, because the metadata association test fails for that fixture. Shuffling numeric "
    "samples must not change the commutative sum; a failed property rejects the implementation "
    "claim. Identical metadata on every property-suite example is rejected."
)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p146-property-mutation"
CLAIM = "property-and-mutation-testing-host-reference"
CLOSE_TIMESTAMP_DELTA = 1_000_000
HIGH_COVERAGE = 0.8
MAX_DIMENSION = 8192
MAX_LENGTH = 8_000_000
MAX_ALLOCATION = 8_000_000
SUM_ABS_TOL = 1e-9
SUM_REL_TOL = 1e-9

HAPPY_PATH_ONLY = "happy-path-only-catalogue"
MUTANT_NOT_DETECTED = "mutant-not-detected"
NEAREST_NEIGHBOR_NOT_KILLED = "nearest-neighbor-timestamp-not-killed"
COMMUTATIVE_SUM_FAILED = "commutative-sum-property-failed"
IDENTICAL_METADATA = "identical-metadata-property-suite"

RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = frozenset({"recorded", "rejected"})
NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "samples",
    "shuffled",
    "reportedSum",
    "reportedShuffledSum",
    "propertySuite",
    "catalogue",
}
CORE_KEYS = {
    "evidenceId",
    "claim",
    "applyMutant",
    "samples",
    "shuffled",
    "reportedSum",
    "reportedShuffledSum",
    "propertySuite",
    "catalogue",
}
CASE_COMMON_KEYS = CORE_KEYS | {"repeat"}
REQUIRED_MUTANT_KEYS = {"input", "expected_detection", "detected"}
OPTIONAL_MUTANT_KEYS = {"id", "original", "changedField", "changedFields", "kind", "critical", "name"}
EXAMPLE_KEYS = {"id", "metadata"}
RESULT_STATUSES = frozenset({"pass", "fail", "skip", "unavailable"})
SUMMARY_KEYS = ("pass", "fail", "skip", "unavailable")
FORBIDDEN_RELEASE_SCOPES = frozenset({"native-resolution", "camera-equivalence"})
FEATURE_STATES = frozenset({"implemented", "experimental", "physically-qualified"})
MIGRATIONS = frozenset({"explicit", "refused", "silent-uninstall", "none"})
PRIVATE_TRANSMISSIONS = frozenset({"frames", "depth", "audio", "metadata", "private-metadata"})
TRANSMISSION_KINDS = PRIVATE_TRANSMISSIONS | {"thumbnail", "none"}

FIXTURE_SAMPLES = (1, 2, 3, 4)
FIXTURE_SHUFFLED = (4, 1, 3, 2)
SOURCE_SHA256 = hashlib.sha256(b"p146-source").hexdigest()

FAULT_TEXT = {
    HAPPY_PATH_ONLY: (
        "catalogue is only happy-path examples; no mutant has a changed field"
    ),
    MUTANT_NOT_DETECTED: (
        "a mutant with expected_detection true has detected false and survives"
    ),
    NEAREST_NEIGHBOR_NOT_KILLED: ORACLE,
    COMMUTATIVE_SUM_FAILED: (
        "shuffling numeric samples changed the commutative sum; the implementation claim is rejected"
    ),
    IDENTICAL_METADATA: MUTANT,
}


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


def require_int(value: object, label: str) -> int:
    require(type(value) is int, label + " must be an int")
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


def same_json(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=SUM_REL_TOL, abs_tol=SUM_ABS_TOL)
    if isinstance(left, str) or isinstance(right, str):
        return isinstance(left, str) and isinstance(right, str) and left == right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(same_json(a, b) for a, b in zip(left, right))
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return False
        return all(same_json(left[key], right[key]) for key in left)
    return False


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


def display_number(value: float) -> int | float:
    if float(value).is_integer():
        return int(value)
    return float(value)


def commutative_sum(samples: list[float]) -> float:
    """Order-independent sum. Addition is commutative, so a shuffle cannot change it."""
    total = 0.0
    for value in samples:
        total += float(value)
    return total


def sums_agree(left: float, right: float) -> bool:
    return math.isclose(float(left), float(right), rel_tol=SUM_REL_TOL, abs_tol=SUM_ABS_TOL)


def generate_numeric_domain(seed: int = 1) -> dict[str, Any]:
    """Valid finite samples and invalid markers. Invalid markers are not sums."""
    require(type(seed) is int and seed > 0, "seed must be a positive int")
    return {
        "domain": "numeric",
        "seed": seed,
        "valid": [seed, seed + 1, seed + 2, seed + 3],
        "invalid": ["nan", "inf", "-inf"],
    }


def generate_temporal_sequence(seed: int = 1) -> dict[str, Any]:
    require(type(seed) is int and seed > 0, "seed must be a positive int")
    base = 1_000_000 * seed
    return {
        "domain": "temporal",
        "seed": seed,
        "events": [
            {"t": base, "kind": "frame"},
            {"t": base + 1000, "kind": "metadata"},
            {"t": base, "kind": "timestamp-reuse"},
        ],
    }


def generate_geometry(seed: int = 1) -> dict[str, Any]:
    require(type(seed) is int and seed > 0, "seed must be a positive int")
    return {
        "domain": "geometry",
        "seed": seed,
        "width": 1920,
        "height": 1080,
        "transform": [1, 0, 0, 0, 1, 0, 0, 0, 1],
        "excessive": {"width": MAX_DIMENSION + seed, "height": MAX_DIMENSION + seed},
    }


def generate_malformed_record(seed: int = 1) -> dict[str, Any]:
    require(type(seed) is int and seed > 0, "seed must be a positive int")
    return {
        "domain": "malformed",
        "seed": seed,
        "length": -seed,
        "path": "../escape",
        "extension": "json",
        "headerValidated": False,
    }


def property_generators() -> list[dict[str, Any]]:
    return [
        generate_numeric_domain(1),
        generate_temporal_sequence(1),
        generate_geometry(1),
        generate_malformed_record(1),
    ]


def diff_fields(original: dict, updated: dict) -> list[str]:
    keys = sorted(set(original) | set(updated))
    changed: list[str] = []
    for key in keys:
        if key not in original or key not in updated or not same_json(original[key], updated[key]):
            changed.append(key)
    return changed


def _declared_changes(mutant: dict) -> list[str]:
    declared: list[str] = []
    if "changedField" in mutant and mutant["changedField"] is not None:
        declared.append(require_text(mutant["changedField"], "changedField"))
    if "changedFields" in mutant and mutant["changedFields"] is not None:
        fields = mutant["changedFields"]
        require(isinstance(fields, list) and bool(fields), "changedFields must be a non-empty list")
        for index, field in enumerate(fields):
            declared.append(require_text(field, f"changedFields[{index}]"))
    return dedupe(declared)


def changed_fields_of(mutant: dict) -> list[str]:
    """Fields a mutant actually changes. Happy-path examples change nothing."""
    if "original" in mutant:
        original = mutant["original"]
        require(isinstance(original, dict), "original must be an object")
        return diff_fields(original, mutant["input"])
    return _declared_changes(mutant)


def _timestamp_pair(payload: dict) -> tuple[float, float] | None:
    frame = payload.get("frameTimestampNs", payload.get("frameTimestamp"))
    meta = payload.get("metadataTimestampNs", payload.get("metadataTimestamp"))
    if frame is None and meta is None:
        return None
    frame_value = require_number(frame, "frame timestamp")
    meta_value = require_number(meta, "metadata timestamp")
    return frame_value, meta_value


def is_nearest_neighbor_fixture(mutant: dict, changed: list[str]) -> bool:
    """Exact pairing replaced by nearest-neighbor matching on a close-but-wrong timestamp."""
    updated = mutant["input"]
    if updated.get("pairing") != "nearest-neighbor":
        return False
    if "pairing" not in changed and "original" not in mutant:
        return False
    if "original" in mutant:
        original = mutant["original"]
        if not isinstance(original, dict) or original.get("pairing") != "exact":
            return False
        if "pairing" not in changed:
            return False
    pair = _timestamp_pair(updated)
    if pair is None:
        return True
    frame, meta = pair
    delta = abs(frame - meta)
    return 0 < delta <= CLOSE_TIMESTAMP_DELTA


def parse_samples(value: object, label: str) -> list[float]:
    require(isinstance(value, list) and len(value) >= 1, label + " must be a non-empty list")
    numbers: list[float] = []
    for index, item in enumerate(value):
        numbers.append(require_number(item, f"{label}[{index}]"))
    return numbers


def parse_example(value: object, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    require(set(value) == EXAMPLE_KEYS, label + " keys are invalid")
    example_id = require_text(value["id"], label + ".id")
    metadata = value["metadata"]
    require(isinstance(metadata, dict) and bool(metadata), label + ".metadata must be a non-empty object")
    _validate_json_value(metadata, label + ".metadata")
    return {"id": example_id, "metadata": metadata}


def parse_property_suite(value: object) -> list[dict[str, Any]]:
    require(isinstance(value, list) and len(value) >= 2, "propertySuite must contain at least 2 examples")
    examples = [parse_example(item, f"propertySuite[{index}]") for index, item in enumerate(value)]
    ids = [example["id"] for example in examples]
    require(len(ids) == len(set(ids)), "propertySuite ids must be unique")
    return examples


def metadata_identical(examples: list[dict[str, Any]]) -> bool:
    """True when every example labelled as this property suite carries the same metadata."""
    if len(examples) < 2:
        return False
    first = examples[0]["metadata"]
    return all(same_json(first, example["metadata"]) for example in examples[1:])


def parse_mutant(value: object, index: int) -> dict[str, Any]:
    require(isinstance(value, dict), f"catalogue[{index}] must be an object")
    keys = set(value)
    require(REQUIRED_MUTANT_KEYS <= keys <= REQUIRED_MUTANT_KEYS | OPTIONAL_MUTANT_KEYS,
            f"catalogue[{index}] keys are invalid")
    updated = value["input"]
    require(isinstance(updated, dict) and bool(updated), f"catalogue[{index}].input must be a non-empty object")
    _validate_json_value(updated, f"catalogue[{index}].input")
    expected = require_bool(value["expected_detection"], f"catalogue[{index}].expected_detection")
    detected = require_bool(value["detected"], f"catalogue[{index}].detected")
    mutant_id = value.get("id", f"mutant-{index}")
    mutant_id = require_text(mutant_id, f"catalogue[{index}].id")
    parsed: dict[str, Any] = {
        "id": mutant_id,
        "input": updated,
        "expected_detection": expected,
        "detected": detected,
    }
    if "original" in value:
        original = value["original"]
        require(isinstance(original, dict), f"catalogue[{index}].original must be an object")
        _validate_json_value(original, f"catalogue[{index}].original")
        parsed["original"] = original
    if "changedField" in value:
        parsed["changedField"] = value["changedField"]
    if "changedFields" in value:
        parsed["changedFields"] = value["changedFields"]
    if "kind" in value:
        parsed["kind"] = require_text(value["kind"], f"catalogue[{index}].kind")
    if "critical" in value:
        parsed["critical"] = require_bool(value["critical"], f"catalogue[{index}].critical")
    if "name" in value:
        parsed["name"] = require_text(value["name"], f"catalogue[{index}].name")
    # Validate declared change fields even when original wins the diff.
    if "original" not in parsed:
        _declared_changes(parsed)
    else:
        if "changedField" in parsed and parsed["changedField"] is not None:
            require_text(parsed["changedField"], f"catalogue[{index}].changedField")
        if "changedFields" in parsed and parsed["changedFields"] is not None:
            fields = parsed["changedFields"]
            require(isinstance(fields, list), f"catalogue[{index}].changedFields must be a list")
            for field_index, field in enumerate(fields):
                require_text(field, f"catalogue[{index}].changedFields[{field_index}]")
    return parsed


def parse_catalogue(value: object) -> list[dict[str, Any]]:
    require(isinstance(value, list), "catalogue must be a list")
    mutants = [parse_mutant(item, index) for index, item in enumerate(value)]
    ids = [mutant["id"] for mutant in mutants]
    require(len(ids) == len(set(ids)), "catalogue ids must be unique")
    return mutants


def property_failed(samples: list[float], shuffled: list[float], reported: float, reported_shuffled: float) -> bool:
    """True when a shuffle changes the sum or the implementation reports an order-dependent sum."""
    left = commutative_sum(samples)
    right = commutative_sum(shuffled)
    reported_matches = sums_agree(reported, left) and sums_agree(reported_shuffled, right)
    order_invariant = sums_agree(left, right) and sums_agree(reported, reported_shuffled)
    return not (reported_matches and order_invariant)


def analyze_computation(
    *,
    samples: list[float],
    shuffled: list[float],
    reported_sum: float,
    reported_shuffled_sum: float,
    examples: list[dict[str, Any]],
    mutants: list[dict[str, Any]],
    claim: str,
    apply_mutant: bool,
) -> dict[str, Any]:
    faults: list[str] = []
    changed_by_id: dict[str, list[str]] = {}
    killed: list[str] = []
    survived: list[str] = []
    nearest_killed = False
    any_changed = False
    for mutant in mutants:
        changed = changed_fields_of(mutant)
        changed_by_id[mutant["id"]] = changed
        if changed:
            any_changed = True
        expects = mutant["expected_detection"] is True
        detected = mutant["detected"] is True
        if expects and detected:
            killed.append(mutant["id"])
        if expects and not detected:
            survived.append(mutant["id"])
            faults.append(MUTANT_NOT_DETECTED)
        if is_nearest_neighbor_fixture(mutant, changed) and expects and detected:
            nearest_killed = True
    if not any_changed:
        faults.append(HAPPY_PATH_ONLY)
    if not nearest_killed:
        faults.append(NEAREST_NEIGHBOR_NOT_KILLED)
    identical = metadata_identical(examples)
    if identical or apply_mutant:
        faults.append(IDENTICAL_METADATA)
    left = commutative_sum(samples)
    right = commutative_sum(shuffled)
    failed_property = property_failed(samples, shuffled, reported_sum, reported_shuffled_sum)
    if failed_property:
        faults.append(COMMUTATIVE_SUM_FAILED)
        faults.append(claim)
    snapshot = {
        "commutativeSum": display_number(left),
        "shuffledSum": display_number(right),
        "reportedSum": display_number(reported_sum),
        "reportedShuffledSum": display_number(reported_shuffled_sum),
        "killedMutants": killed,
        "survivedMutants": survived,
        "changedFields": changed_by_id,
        "metadataIdentical": identical,
        "nearestNeighborKilled": nearest_killed,
        "propertyFailed": failed_property,
    }
    extra_reasons = [
        "commutative sum "
        + str(snapshot["commutativeSum"])
        + " shuffled sum "
        + str(snapshot["shuffledSum"]),
        "mutation rule: " + MUTATION_RULE,
    ]
    if nearest_killed:
        extra_reasons.append(
            "metadata association test fails for the close-but-wrong timestamp; nearest-neighbor mutant killed"
        )
    if survived:
        extra_reasons.append("surviving mutants: " + ", ".join(survived))
    if failed_property:
        extra_reasons.append("property failed; implementation claim rejected: " + claim)
    if identical:
        extra_reasons.append("every property-suite example carries identical metadata")
    return {
        "faults": dedupe(faults),
        "snapshot": snapshot,
        "extraReasons": extra_reasons,
    }


def assemble(
    case_id: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    open_questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    ordered = dedupe(faults)
    decision = "rejected" if ordered else "recorded"
    require(decision in DECISIONS, "decision must be recorded or rejected")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": ordered,
        "preservedResults": preserved,
        "openQuestions": list(open_questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(OPEN_QUESTION in result["openQuestions"], "open question missing")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(bool(result["reasons"]), "reasons must be non-empty")
    return result


def _core_from_mapping(mapping: dict, label: str) -> dict[str, Any]:
    evidence = require_text(mapping["evidenceId"], "evidenceId")
    claim = require_text(mapping["claim"], "claim")
    apply_mutant = require_bool(mapping["applyMutant"], "applyMutant")
    samples = parse_samples(mapping["samples"], "samples")
    shuffled = parse_samples(mapping["shuffled"], "shuffled")
    reported = require_number(mapping["reportedSum"], "reportedSum")
    reported_shuffled = require_number(mapping["reportedShuffledSum"], "reportedShuffledSum")
    examples = parse_property_suite(mapping["propertySuite"])
    mutants = parse_catalogue(mapping["catalogue"])
    analysis = analyze_computation(
        samples=samples,
        shuffled=shuffled,
        reported_sum=reported,
        reported_shuffled_sum=reported_shuffled,
        examples=examples,
        mutants=mutants,
        claim=claim,
        apply_mutant=apply_mutant,
    )
    analysis["evidence"] = evidence
    analysis["claim"] = claim
    analysis["applyMutant"] = apply_mutant
    analysis["label"] = label
    return analysis


def _reasons(analysis: dict[str, Any], lead: list[str], fault_text: dict[str, str] | None) -> list[str]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    reasons = list(lead)
    reasons.extend(analysis["extraReasons"])
    for token in analysis["faults"]:
        reasons.append(text.get(token, token))
    if not analysis["faults"]:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("property and mutation catalogue recorded; not a physical qualification")
    return reasons


def assess(document: dict) -> dict[str, Any]:
    """Record a killed mutation catalogue and a commutative property, or reject it."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    analysis = _core_from_mapping(document, "document")
    reasons = _reasons(
        analysis,
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 was not run",
            "goal: " + GOAL,
            "method: " + METHOD,
            "fixture: " + FIXTURE,
            "oracle: " + ORACLE,
        ],
        None,
    )
    if IDENTICAL_METADATA in analysis["faults"]:
        reasons.append("mutant rejected: " + MUTANT)
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a phase document or a core property-and-mutation payload."""
    require(isinstance(payload, dict), "payload must be an object")
    if (
        "schemaVersion" in payload
        or "implementationBaseRevision" in payload
        or "phase" in payload
    ):
        return assess(payload)
    require(set(payload) == CORE_KEYS, "invalid payload keys")
    analysis = _core_from_mapping(payload, "payload")
    reasons = _reasons(
        analysis,
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 was not run",
            "oracle: " + ORACLE,
            "fixture: " + FIXTURE,
        ],
        None,
    )
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


def begin_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(CASE_COMMON_KEYS) | set(extra_keys), "invalid payload keys")
    repeat = require_text(payload["repeat"], "repeat")
    analysis = _core_from_mapping(payload, "case")
    return {
        "evidence": analysis["evidence"],
        "claim": analysis["claim"],
        "repeat": repeat,
        "faults": list(analysis["faults"]),
        "analysis": analysis,
        "snapshot": analysis["snapshot"],
    }


def finish_case(
    case: dict,
    bundle: dict,
    faults: list[str],
    extra_preserved: list,
    fault_text: dict | None = None,
) -> dict[str, Any]:
    analysis = dict(bundle["analysis"])
    analysis["faults"] = dedupe(list(faults))
    reasons = _reasons(
        analysis,
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 was not run",
            "oracle: " + ORACLE,
            case["expected"],
            "repeat " + bundle["repeat"],
        ],
        fault_text,
    )
    preserved = [bundle["evidence"], bundle["snapshot"], bundle["claim"], *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], analysis["faults"], reasons, preserved, questions, bundle["evidence"])


def make_mutant(
    mutant_id: str,
    kind: str,
    original: dict,
    mutated: dict,
    *,
    detected: bool = True,
    expected_detection: bool = True,
) -> dict[str, Any]:
    return {
        "id": mutant_id,
        "kind": kind,
        "input": mutated,
        "original": original,
        "expected_detection": expected_detection,
        "detected": detected,
    }


def fixture_catalogue() -> list[dict[str, Any]]:
    return [
        make_mutant(
            "timestamp-nearest-neighbor",
            "nearest-neighbor",
            {
                "pairing": "exact",
                "frameTimestampNs": 1000000,
                "metadataTimestampNs": 1000000,
            },
            {
                "pairing": "nearest-neighbor",
                "frameTimestampNs": 1000000,
                "metadataTimestampNs": 1001000,
            },
        ),
        make_mutant(
            "range-confusion",
            "range-confusion",
            {"range": "legal", "code": 16},
            {"range": "full", "code": 0},
        ),
        make_mutant(
            "timestamp-reuse",
            "timestamp-reuse",
            {"frameId": 2, "timestampNs": 2000},
            {"frameId": 2, "timestampNs": 1000},
        ),
        make_mutant(
            "cfa-swap",
            "cfa-swap",
            {"cfa": "RGGB"},
            {"cfa": "BGGR"},
        ),
        make_mutant(
            "missing-hash",
            "missing-hash",
            {"hashChecked": True, "sha256": SOURCE_SHA256},
            {"hashChecked": False, "sha256": SOURCE_SHA256},
        ),
    ]


def fixture_suite() -> list[dict[str, Any]]:
    generated = property_generators()
    return [
        {"id": "numeric-domain", "metadata": generated[0]},
        {"id": "temporal-sequence", "metadata": generated[1]},
        {"id": "geometry-combinations", "metadata": generated[2]},
        {"id": "malformed-records", "metadata": generated[3]},
    ]


def fixture_sum() -> int:
    return display_number(commutative_sum(list(FIXTURE_SAMPLES)))  # type: ignore[return-value]


def core_payload(**overrides: Any) -> dict[str, Any]:
    total = fixture_sum()
    payload: dict[str, Any] = {
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "samples": list(FIXTURE_SAMPLES),
        "shuffled": list(FIXTURE_SHUFFLED),
        "reportedSum": total,
        "reportedShuffledSum": total,
        "propertySuite": fixture_suite(),
        "catalogue": fixture_catalogue(),
    }
    payload.update(overrides)
    return payload


def fixture_document() -> dict[str, Any]:
    core = core_payload()
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": core["evidenceId"],
        "claim": core["claim"],
        "applyMutant": False,
        "samples": core["samples"],
        "shuffled": core["shuffled"],
        "reportedSum": core["reportedSum"],
        "reportedShuffledSum": core["reportedShuffledSum"],
        "propertySuite": core["propertySuite"],
        "catalogue": core["catalogue"],
    }


def happy_path_catalogue() -> list[dict[str, Any]]:
    """Examples that copy original into input, so no field changes."""
    catalogue = fixture_catalogue()
    for mutant in catalogue:
        mutant["input"] = {key: value for key, value in mutant["original"].items()}
        mutant["detected"] = True
        mutant["expected_detection"] = True
    return catalogue


def identical_property_suite() -> list[dict[str, Any]]:
    suite = fixture_suite()
    metadata = suite[0]["metadata"]
    return [{"id": example["id"], "metadata": metadata} for example in suite]
