#!/usr/bin/env python3
"""P157 Design instrumented low-level experiments.

Host reference only. This module does not probe a device and does not qualify
a physical S23. An experiment has a change description, a reversible bool,
observation fields, and a captured_output bool. Calling a mode unlocked
(unlocked_claim true) without captured_output is rejected. A change that is
not reversible must list a recovery step or be rejected. Observations must
include distinct before and after identifiers. The protocol is recorded only
as a design, not as a completed device experiment. The decision is never
qualified or allowed.

One hypothesized constraint is changed at a time. The baseline is preserved,
the experiment checksum and log are recorded, and failure triggers are defined
before execution. Thermal safeguards stay enabled. Capability metadata is not
falsified to make an unsupported mode appear available.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P157"
WORKSTREAM = 20
TITLE = "Design instrumented low-level experiments"
GOAL = "Make any authorized low-level change minimal, observable, and reversible where technically possible."
METHOD = (
    "Change one hypothesized constraint at a time, preserve the baseline, record checksums and logs, "
    "and define failure triggers before execution. Do not disable thermal safeguards or falsify "
    "capability metadata to make unsupported modes appear available."
)
FIXTURE = "A modification that changes advertised stream metadata but produces no valid additional sensor frames."
ORACLE = "The experiment fails its actual-delivery hypothesis despite the expanded menu."
MUTANT = "Call an advertised mode unlocked without capturing and validating its output."
DELIVERABLE = "Instrumented experimental protocol and observation schema"
DEPENDENCIES = ("P156",)

PROTOCOL_RULE = (
    "An experiment has a change description, a reversible bool, observation fields, and a "
    "captured_output bool. Calling a mode unlocked (unlocked_claim true) without captured_output "
    "is rejected. A change that is not reversible must list a recovery step or be rejected. "
    "Observations must include before and after identifiers. The protocol is recorded only as a "
    "design, not as a completed device experiment. The decision is never qualified."
)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p157-instrumented-experiment-design"
CLAIM = "instrumented-low-level-experiment-design"
LOG_ID = "p157-design-log"
PROTOCOL_DESIGN = "design"
PROTOCOL_KINDS = frozenset({"design", "completed", "executed"})

UNLOCKED_WITHOUT_OUTPUT = "unlocked-claim-without-captured-output"
IRREVERSIBLE_WITHOUT_RECOVERY = "irreversible-change-without-recovery-step"
OBSERVATION_IDENTIFIERS_MISSING = "observation-before-after-identifiers-missing"
NOT_A_DESIGN = "protocol-not-recorded-as-design"
COMPLETED_DEVICE_EXPERIMENT = "completed-device-experiment-claimed"
BASELINE_NOT_PRESERVED = "baseline-not-preserved"
CHECKSUM_MISMATCH = "checksum-does-not-match-experiments"
FAILURE_TRIGGERS_MISSING = "failure-triggers-not-defined-before-execution"
THERMAL_SAFEGUARD_DISABLED = "thermal-safeguard-disabled"
CAPABILITY_METADATA_FALSIFIED = "capability-metadata-falsified"
NOT_ONE_CONSTRAINT = "not-one-constraint-at-a-time"

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
    "protocolKind",
    "deviceExperimentCompleted",
    "baselinePreserved",
    "checksum",
    "logId",
    "failureTriggers",
    "thermalSafeguardDisabled",
    "capabilityMetadataFalsified",
    "experiments",
}
CORE_KEYS = {
    "evidenceId",
    "claim",
    "applyMutant",
    "protocolKind",
    "deviceExperimentCompleted",
    "baselinePreserved",
    "checksum",
    "logId",
    "failureTriggers",
    "thermalSafeguardDisabled",
    "capabilityMetadataFalsified",
    "experiments",
}
CASE_COMMON_KEYS = CORE_KEYS | {"repeat"}
EXPERIMENT_KEYS = {
    "id",
    "change",
    "constraints",
    "reversible",
    "recoveryStep",
    "observations",
    "captured_output",
    "unlocked_claim",
}
OBSERVATION_KEYS = {"before", "after"}
FAILURE_TRIGGERS = (
    "no-valid-additional-sensor-frames",
    "checksum-mismatch",
    "thermal-safeguard-trip",
)

FAULT_TEXT = {
    UNLOCKED_WITHOUT_OUTPUT: (
        "unlocked_claim is true without captured_output; " + MUTANT
    ),
    IRREVERSIBLE_WITHOUT_RECOVERY: (
        "a change that is not reversible must list a recovery step"
    ),
    OBSERVATION_IDENTIFIERS_MISSING: (
        "observations must include distinct before and after identifiers"
    ),
    NOT_A_DESIGN: "the protocol is recorded only as a design, not as a completed device experiment",
    COMPLETED_DEVICE_EXPERIMENT: "a completed device experiment is outside this design record",
    BASELINE_NOT_PRESERVED: "the baseline was not preserved",
    CHECKSUM_MISMATCH: "the recorded checksum does not match the experiment observations",
    FAILURE_TRIGGERS_MISSING: "failure triggers must be defined before execution",
    THERMAL_SAFEGUARD_DISABLED: "thermal safeguards must not be disabled",
    CAPABILITY_METADATA_FALSIFIED: (
        "capability metadata must not be falsified to make an unsupported mode appear available"
    ),
    NOT_ONE_CONSTRAINT: "change one hypothesized constraint at a time",
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


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def _identifier_ok(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def make_experiment(
    experiment_id: str,
    change: str,
    constraint: str,
    *,
    reversible: bool = True,
    recovery_step: str | None = None,
    before: str = "obs-before",
    after: str = "obs-after",
    captured_output: bool = True,
    unlocked_claim: bool = False,
) -> dict[str, Any]:
    return {
        "id": experiment_id,
        "change": change,
        "constraints": [constraint],
        "reversible": reversible,
        "recoveryStep": recovery_step,
        "observations": {"before": before, "after": after},
        "captured_output": captured_output,
        "unlocked_claim": unlocked_claim,
    }


def fixture_experiments() -> list[dict[str, Any]]:
    """One reversible constraint change with captured output. Not an unlock claim."""
    return [
        make_experiment(
            "encoder-scheduling",
            "Vary one hypothesized encoder scheduling constraint and keep the baseline checksum.",
            "encoder-scheduling",
            reversible=True,
            recovery_step=None,
            before="obs-baseline-encoder-scheduling",
            after="obs-after-encoder-scheduling",
            captured_output=True,
            unlocked_claim=False,
        )
    ]


def unlocked_metadata_experiment() -> dict[str, Any]:
    """Fixture mutant: advertised stream metadata changes, but no sensor frames are captured."""
    return make_experiment(
        "advertised-stream-metadata",
        "Change advertised stream metadata so an unsupported mode appears in the menu.",
        "advertised-stream-metadata",
        reversible=True,
        recovery_step=None,
        before="obs-baseline-stream-metadata",
        after="obs-expanded-stream-menu",
        captured_output=False,
        unlocked_claim=True,
    )


def irreversible_without_recovery_experiment() -> dict[str, Any]:
    return make_experiment(
        "unverified-flash",
        "Flash an image without a listed recovery step.",
        "flash-image",
        reversible=False,
        recovery_step=None,
        before="obs-before-flash",
        after="obs-after-flash",
        captured_output=False,
        unlocked_claim=False,
    )


def protocol_checksum(experiments: list[dict[str, Any]]) -> str:
    """SHA-256 of the canonical experiment rows, including observation identifiers."""
    rows = []
    for item in experiments:
        observations = item["observations"]
        rows.append({
            "after": observations["after"],
            "before": observations["before"],
            "captured_output": item["captured_output"],
            "change": item["change"],
            "constraints": list(item["constraints"]),
            "id": item["id"],
            "recoveryStep": item["recoveryStep"],
            "reversible": item["reversible"],
            "unlocked_claim": item["unlocked_claim"],
        })
    blob = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def parse_observations(value: object, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    require(set(value) == OBSERVATION_KEYS, label + " keys must be before and after")
    before = value["before"]
    after = value["after"]
    require(isinstance(before, str), label + ".before must be a string")
    require(isinstance(after, str), label + ".after must be a string")
    ok = _identifier_ok(before) and _identifier_ok(after) and before != after
    return {"before": before, "after": after, "identifiersOk": ok}


def parse_experiment(value: object, index: int) -> dict[str, Any]:
    require(isinstance(value, dict), f"experiments[{index}] must be an object")
    require(set(value) == EXPERIMENT_KEYS, f"experiments[{index}] keys are invalid")
    constraints = value["constraints"]
    require(isinstance(constraints, list), f"experiments[{index}].constraints must be a list")
    parsed_constraints = [
        require_text(item, f"experiments[{index}].constraints[{constraint_index}]")
        for constraint_index, item in enumerate(constraints)
    ]
    recovery = value["recoveryStep"]
    if recovery is not None:
        recovery = require_text(recovery, f"experiments[{index}].recoveryStep")
    observations = parse_observations(value["observations"], f"experiments[{index}].observations")
    return {
        "id": require_text(value["id"], f"experiments[{index}].id"),
        "change": require_text(value["change"], f"experiments[{index}].change"),
        "constraints": parsed_constraints,
        "reversible": require_bool(value["reversible"], f"experiments[{index}].reversible"),
        "recoveryStep": recovery,
        "observations": observations,
        "captured_output": require_bool(value["captured_output"], f"experiments[{index}].captured_output"),
        "unlocked_claim": require_bool(value["unlocked_claim"], f"experiments[{index}].unlocked_claim"),
    }


def parse_experiments(value: object) -> list[dict[str, Any]]:
    require(isinstance(value, list) and bool(value), "experiments must be a non-empty list")
    experiments = [parse_experiment(item, index) for index, item in enumerate(value)]
    ids = [item["id"] for item in experiments]
    require(len(ids) == len(set(ids)), "experiment ids must be unique")
    return experiments


def parse_failure_triggers(value: object) -> list[str]:
    require(isinstance(value, list), "failureTriggers must be a list")
    triggers = [require_text(item, f"failureTriggers[{index}]") for index, item in enumerate(value)]
    require(len(triggers) == len(set(triggers)), "failureTriggers must be unique")
    return triggers


def parse_checksum(value: object) -> str:
    text = require_text(value, "checksum")
    require(len(text) == 64 and all(char in "0123456789abcdef" for char in text), "checksum must be sha256 hex")
    return text


def _checksum_material(experiments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Public shape used by protocol_checksum, without parser-only fields."""
    material = []
    for item in experiments:
        material.append({
            "id": item["id"],
            "change": item["change"],
            "constraints": list(item["constraints"]),
            "reversible": item["reversible"],
            "recoveryStep": item["recoveryStep"],
            "observations": {
                "before": item["observations"]["before"],
                "after": item["observations"]["after"],
            },
            "captured_output": item["captured_output"],
            "unlocked_claim": item["unlocked_claim"],
        })
    return material


def analyze_computation(
    *,
    experiments: list[dict[str, Any]],
    protocol_kind: str,
    device_experiment_completed: bool,
    baseline_preserved: bool,
    checksum: str,
    failure_triggers: list[str],
    thermal_safeguard_disabled: bool,
    capability_metadata_falsified: bool,
    apply_mutant: bool,
) -> dict[str, Any]:
    faults: list[str] = []
    if protocol_kind != PROTOCOL_DESIGN:
        faults.append(NOT_A_DESIGN)
    if device_experiment_completed:
        faults.append(COMPLETED_DEVICE_EXPERIMENT)
    if not baseline_preserved:
        faults.append(BASELINE_NOT_PRESERVED)
    expected = protocol_checksum(_checksum_material(experiments))
    checksum_matches = checksum == expected
    if not checksum_matches:
        faults.append(CHECKSUM_MISMATCH)
    if not failure_triggers:
        faults.append(FAILURE_TRIGGERS_MISSING)
    if thermal_safeguard_disabled:
        faults.append(THERMAL_SAFEGUARD_DISABLED)
    if capability_metadata_falsified:
        faults.append(CAPABILITY_METADATA_FALSIFIED)

    unlocked_ids: list[str] = []
    irreversible_ids: list[str] = []
    observation_ids: list[str] = []
    constraint_counts: dict[str, int] = {}
    for experiment in experiments:
        experiment_id = experiment["id"]
        constraint_counts[experiment_id] = len(experiment["constraints"])
        if len(experiment["constraints"]) != 1:
            faults.append(NOT_ONE_CONSTRAINT)
        if experiment["reversible"] is False and experiment["recoveryStep"] is None:
            irreversible_ids.append(experiment_id)
            faults.append(IRREVERSIBLE_WITHOUT_RECOVERY)
        if experiment["observations"]["identifiersOk"] is False:
            observation_ids.append(experiment_id)
            faults.append(OBSERVATION_IDENTIFIERS_MISSING)
        if experiment["unlocked_claim"] is True and experiment["captured_output"] is False:
            unlocked_ids.append(experiment_id)
            faults.append(UNLOCKED_WITHOUT_OUTPUT)
    if apply_mutant:
        faults.append(UNLOCKED_WITHOUT_OUTPUT)

    recorded_as_design = protocol_kind == PROTOCOL_DESIGN and device_experiment_completed is False
    snapshot = {
        "protocolKind": protocol_kind,
        "deviceExperimentCompleted": device_experiment_completed,
        "recordedAsDesign": recorded_as_design,
        "qualification": "not-qualified",
        "experimentIds": [item["id"] for item in experiments],
        "unlockedWithoutOutput": unlocked_ids,
        "irreversibleWithoutRecovery": irreversible_ids,
        "observationIdentifierFaults": observation_ids,
        "constraintCounts": constraint_counts,
        "checksumMatches": checksum_matches,
        "expectedChecksum": expected,
        "baselinePreserved": baseline_preserved,
        "thermalSafeguardDisabled": thermal_safeguard_disabled,
        "capabilityMetadataFalsified": capability_metadata_falsified,
        "failureTriggerCount": len(failure_triggers),
        "applyMutant": apply_mutant,
    }
    extra_reasons = [
        "protocol rule: " + PROTOCOL_RULE,
        "experiment count " + str(len(experiments)),
        "checksum matches " + str(checksum_matches),
    ]
    if unlocked_ids or apply_mutant:
        extra_reasons.append(ORACLE)
        extra_reasons.append("oracle: " + ORACLE)
        names = ", ".join(unlocked_ids) if unlocked_ids else "applyMutant"
        extra_reasons.append("unlocked without captured output: " + names)
    if irreversible_ids:
        extra_reasons.append("irreversible without recovery: " + ", ".join(irreversible_ids))
    if observation_ids:
        extra_reasons.append("observation identifiers missing or not distinct: " + ", ".join(observation_ids))
    if recorded_as_design:
        extra_reasons.append("protocol is a design, not a completed device experiment")
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
    protocol_kind = require_text(mapping["protocolKind"], "protocolKind")
    require(protocol_kind in PROTOCOL_KINDS, "protocolKind is not recognized")
    device_completed = require_bool(mapping["deviceExperimentCompleted"], "deviceExperimentCompleted")
    baseline = require_bool(mapping["baselinePreserved"], "baselinePreserved")
    checksum = parse_checksum(mapping["checksum"])
    log_id = require_text(mapping["logId"], "logId")
    triggers = parse_failure_triggers(mapping["failureTriggers"])
    thermal = require_bool(mapping["thermalSafeguardDisabled"], "thermalSafeguardDisabled")
    falsified = require_bool(mapping["capabilityMetadataFalsified"], "capabilityMetadataFalsified")
    experiments = parse_experiments(mapping["experiments"])
    analysis = analyze_computation(
        experiments=experiments,
        protocol_kind=protocol_kind,
        device_experiment_completed=device_completed,
        baseline_preserved=baseline,
        checksum=checksum,
        failure_triggers=triggers,
        thermal_safeguard_disabled=thermal,
        capability_metadata_falsified=falsified,
        apply_mutant=apply_mutant,
    )
    analysis["evidence"] = evidence
    analysis["claim"] = claim
    analysis["applyMutant"] = apply_mutant
    analysis["logId"] = log_id
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
        reasons.append("instrumented experimental protocol recorded as a design; not a physical qualification")
    return reasons


def _lead(include_goal: bool) -> list[str]:
    lead = [
        "host reference only; not a physical S23 measurement",
        "physical S23 was not run",
        "fixture: " + FIXTURE,
        "oracle: " + ORACLE,
    ]
    if include_goal:
        lead.extend([
            "goal: " + GOAL,
            "method: " + METHOD,
        ])
    return lead


def assess(document: dict) -> dict[str, Any]:
    """Record an instrumented experiment design, or reject it. Never qualifies a device."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    analysis = _core_from_mapping(document, "document")
    reasons = _reasons(analysis, _lead(True), None)
    if UNLOCKED_WITHOUT_OUTPUT in analysis["faults"]:
        reasons.append("mutant rejected: " + MUTANT)
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a phase document or a core experiment-protocol payload."""
    require(isinstance(payload, dict), "payload must be an object")
    if (
        "schemaVersion" in payload
        or "implementationBaseRevision" in payload
        or "phase" in payload
    ):
        return assess(payload)
    require(set(payload) == CORE_KEYS, "invalid payload keys")
    analysis = _core_from_mapping(payload, "payload")
    reasons = _reasons(analysis, _lead(False), None)
    if UNLOCKED_WITHOUT_OUTPUT in analysis["faults"]:
        reasons.append("mutant rejected: " + MUTANT)
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
        _lead(False) + [case["expected"], "repeat " + bundle["repeat"]],
        fault_text,
    )
    if UNLOCKED_WITHOUT_OUTPUT in analysis["faults"]:
        reasons.append("mutant rejected: " + MUTANT)
    preserved = [bundle["evidence"], bundle["snapshot"], bundle["claim"], *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], analysis["faults"], reasons, preserved, questions, bundle["evidence"])


def core_payload(**overrides: Any) -> dict[str, Any]:
    experiments = fixture_experiments()
    payload: dict[str, Any] = {
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "protocolKind": PROTOCOL_DESIGN,
        "deviceExperimentCompleted": False,
        "baselinePreserved": True,
        "checksum": protocol_checksum(experiments),
        "logId": LOG_ID,
        "failureTriggers": list(FAILURE_TRIGGERS),
        "thermalSafeguardDisabled": False,
        "capabilityMetadataFalsified": False,
        "experiments": experiments,
    }
    payload.update(overrides)
    if "experiments" in overrides and "checksum" not in overrides:
        payload["checksum"] = protocol_checksum(payload["experiments"])
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
        "protocolKind": core["protocolKind"],
        "deviceExperimentCompleted": False,
        "baselinePreserved": True,
        "checksum": core["checksum"],
        "logId": core["logId"],
        "failureTriggers": list(core["failureTriggers"]),
        "thermalSafeguardDisabled": False,
        "capabilityMetadataFalsified": False,
        "experiments": core["experiments"],
    }
