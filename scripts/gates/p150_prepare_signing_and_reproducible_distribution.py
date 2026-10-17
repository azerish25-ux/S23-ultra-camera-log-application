#!/usr/bin/env python3
"""P150 Prepare signing and reproducible distribution.

Host reference only. This module does not probe a device and does not qualify
a physical S23. A release plan separates debug convenience from a user-facing
release. The plan names build_type (debug or release), signing (debug, upload,
or none), and update_preserves_private_footage. Recommending uninstall while
warns_footage_loss is false is rejected. Debug signing labelled as a production
update is rejected. A release build with signing none is not reproducible for
users and is rejected. recorded_source_revision must be the same source_revision.
An update that does not preserve private footage is rejected.

Update rule: a release plan has build_type debug or release, signing debug,
upload, or none, and update_preserves_private_footage bool. Recommending
uninstall without a footage-loss warning (warns_footage_loss false while
recommends_uninstall true) is rejected. Debug signing must not be labelled a
production update. Release with signing none is rejected as not reproducible
for users. The same source revision must be recorded. Private footage
preservation false on an update is rejected.
"""

from __future__ import annotations

from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P150"
WORKSTREAM = 19
TITLE = "Prepare signing and reproducible distribution"
GOAL = "Separate debug convenience from a maintainable release and update process."
METHOD = (
    "Use owner-controlled signing, pinned dependencies, reproducible source records, "
    "and explicit version migration tests. Keep secrets outside the repository. "
    "Verify installation and update without losing private sources, profiles, recipes, "
    "or recovery records."
)
FIXTURE = "An update from an earlier signed release containing private RAW sources and a pending render job."
ORACLE = (
    "The update preserves compatible data and handles migration explicitly; "
    "signing mismatch is not solved by silently uninstalling user data."
)
MUTANT = "Recommend uninstalling the previous app without warning about private footage loss."
DELIVERABLE = "Release signing plan and update preservation tests"
DEPENDENCIES = ("P149",)

UPDATE_RULE = (
    "A release plan has build_type debug or release, signing debug, upload, or none, "
    "and update_preserves_private_footage bool. Recommending uninstall without a "
    "footage-loss warning (warns_footage_loss false while recommends_uninstall true) "
    "is rejected. Debug signing must not be labelled a production update. Release with "
    "signing none is rejected as not reproducible for users. The same source revision "
    "must be recorded. Private footage preservation false on an update is rejected."
)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p150-signing-distribution"
CLAIM = "signing-and-reproducible-distribution-host-reference"
HIGH_COVERAGE = 0.8
MAX_DIMENSION = 8192
MAX_LENGTH = 8_000_000
MAX_ALLOCATION = 8_000_000

UNINSTALL_WITHOUT_WARNING = "uninstall-without-footage-loss-warning"
DEBUG_SIGNING_AS_PRODUCTION = "debug-signing-labelled-production-update"
RELEASE_NOT_REPRODUCIBLE = "release-signing-none-not-reproducible"
SOURCE_REVISION_NOT_RECORDED = "source-revision-not-the-same"
PRIVATE_FOOTAGE_LOST = "private-footage-not-preserved-on-update"

RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = frozenset({"recorded", "rejected"})
BUILD_TYPES = frozenset({"debug", "release"})
SIGNING_MODES = frozenset({"debug", "upload", "none"})
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
    "build_type",
    "signing",
    "update_preserves_private_footage",
    "warns_footage_loss",
    "recommends_uninstall",
    "labelled_production_update",
    "source_revision",
    "recorded_source_revision",
    "is_update",
}
CORE_KEYS = {
    "evidenceId",
    "claim",
    "applyMutant",
    "build_type",
    "signing",
    "update_preserves_private_footage",
    "warns_footage_loss",
    "recommends_uninstall",
    "labelled_production_update",
    "source_revision",
    "recorded_source_revision",
    "is_update",
}
CASE_COMMON_KEYS = CORE_KEYS | {"repeat"}
RESULT_STATUSES = frozenset({"pass", "fail", "skip", "unavailable"})
SUMMARY_KEYS = ("pass", "fail", "skip", "unavailable")
FORBIDDEN_RELEASE_SCOPES = frozenset({"native-resolution", "camera-equivalence"})
FEATURE_STATES = frozenset({"implemented", "experimental", "physically-qualified"})
MIGRATIONS = frozenset({"explicit", "refused", "silent-uninstall", "none"})
PRIVATE_TRANSMISSIONS = frozenset({"frames", "depth", "audio", "metadata", "private-metadata"})
TRANSMISSION_KINDS = PRIVATE_TRANSMISSIONS | {"thumbnail", "none"}

FAULT_TEXT = {
    UNINSTALL_WITHOUT_WARNING: MUTANT,
    DEBUG_SIGNING_AS_PRODUCTION: "Debug signing must not be labelled a production update.",
    RELEASE_NOT_REPRODUCIBLE: (
        "Release with signing none is rejected as not reproducible for users."
    ),
    SOURCE_REVISION_NOT_RECORDED: "The same source revision must be recorded.",
    PRIVATE_FOOTAGE_LOST: "Private footage preservation false on an update is rejected.",
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


def release_plan_faults(
    *,
    build_type: str,
    signing: str,
    update_preserves_private_footage: bool,
    warns_footage_loss: bool,
    recommends_uninstall: bool,
    labelled_production_update: bool,
    source_revision: str,
    recorded_source_revision: str,
    is_update: bool,
    apply_mutant: bool,
) -> dict[str, Any]:
    """Apply the update rule. Flags are checked; this is not an applyNegative stub."""
    uninstall_without_warning = recommends_uninstall is True and warns_footage_loss is False
    debug_as_production = signing == "debug" and labelled_production_update is True
    release_not_reproducible = build_type == "release" and signing == "none"
    same_source_revision = source_revision == recorded_source_revision
    private_footage_lost = is_update is True and update_preserves_private_footage is False
    faults: list[str] = []
    if uninstall_without_warning or apply_mutant:
        faults.append(UNINSTALL_WITHOUT_WARNING)
    if debug_as_production:
        faults.append(DEBUG_SIGNING_AS_PRODUCTION)
    if release_not_reproducible:
        faults.append(RELEASE_NOT_REPRODUCIBLE)
    if not same_source_revision:
        faults.append(SOURCE_REVISION_NOT_RECORDED)
    if private_footage_lost:
        faults.append(PRIVATE_FOOTAGE_LOST)
    snapshot = {
        "build_type": build_type,
        "signing": signing,
        "update_preserves_private_footage": update_preserves_private_footage,
        "warns_footage_loss": warns_footage_loss,
        "recommends_uninstall": recommends_uninstall,
        "labelled_production_update": labelled_production_update,
        "source_revision": source_revision,
        "recorded_source_revision": recorded_source_revision,
        "is_update": is_update,
        "applyMutant": apply_mutant,
        "uninstall_without_warning": uninstall_without_warning or apply_mutant,
        "debug_signing_as_production": debug_as_production,
        "release_not_reproducible": release_not_reproducible,
        "same_source_revision": same_source_revision,
        "private_footage_lost": private_footage_lost,
        "owner_controlled_signing": signing == "upload",
    }
    extra_reasons = [
        "update rule: " + UPDATE_RULE,
        "build_type " + build_type + " signing " + signing,
        "source revision " + source_revision,
        "recorded source revision " + recorded_source_revision,
    ]
    if same_source_revision:
        extra_reasons.append("same source revision recorded: " + source_revision)
    else:
        extra_reasons.append("recorded source revision differs from the source revision")
    if signing == "upload":
        extra_reasons.append("upload signing is the owner-controlled production key")
    if build_type == "debug" and signing == "debug" and not labelled_production_update:
        extra_reasons.append("debug signing stays a debug convenience, not a production update")
    if private_footage_lost:
        extra_reasons.append("update would drop private footage")
    if uninstall_without_warning or apply_mutant:
        extra_reasons.append("uninstall recommended without a private-footage warning")
    return {
        "faults": dedupe(faults),
        "snapshot": snapshot,
        "extraReasons": extra_reasons,
    }


def _core_from_mapping(mapping: dict, label: str) -> dict[str, Any]:
    evidence = require_text(mapping["evidenceId"], "evidenceId")
    claim = require_text(mapping["claim"], "claim")
    apply_mutant = require_bool(mapping["applyMutant"], "applyMutant")
    build_type = require_text(mapping["build_type"], "build_type")
    require(build_type in BUILD_TYPES, "build_type must be debug or release")
    signing = require_text(mapping["signing"], "signing")
    require(signing in SIGNING_MODES, "signing must be debug, upload, or none")
    preserves = require_bool(
        mapping["update_preserves_private_footage"],
        "update_preserves_private_footage",
    )
    warns = require_bool(mapping["warns_footage_loss"], "warns_footage_loss")
    recommends = require_bool(mapping["recommends_uninstall"], "recommends_uninstall")
    labelled = require_bool(mapping["labelled_production_update"], "labelled_production_update")
    source_revision = require_text(mapping["source_revision"], "source_revision")
    recorded = require_text(mapping["recorded_source_revision"], "recorded_source_revision")
    is_update = require_bool(mapping["is_update"], "is_update")
    analysis = release_plan_faults(
        build_type=build_type,
        signing=signing,
        update_preserves_private_footage=preserves,
        warns_footage_loss=warns,
        recommends_uninstall=recommends,
        labelled_production_update=labelled,
        source_revision=source_revision,
        recorded_source_revision=recorded,
        is_update=is_update,
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
        reasons.append("signing plan recorded; not a physical qualification")
    return reasons


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


def assess(document: dict) -> dict[str, Any]:
    """Record a reproducible signed update plan, or reject it."""
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
    if UNINSTALL_WITHOUT_WARNING in analysis["faults"]:
        reasons.append("mutant rejected: " + MUTANT)
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a phase document or a core release-plan payload."""
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
    if UNINSTALL_WITHOUT_WARNING in analysis["faults"]:
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
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 was not run",
            "oracle: " + ORACLE,
            case["expected"],
            "repeat " + bundle["repeat"],
        ],
        fault_text,
    )
    if UNINSTALL_WITHOUT_WARNING in analysis["faults"]:
        reasons.append("mutant rejected: " + MUTANT)
    preserved = [bundle["evidence"], bundle["snapshot"], bundle["claim"], *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], analysis["faults"], reasons, preserved, questions, bundle["evidence"])


def core_payload(**overrides: Any) -> dict[str, Any]:
    """Owner-controlled upload signing of a release that keeps private footage."""
    payload: dict[str, Any] = {
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "build_type": "release",
        "signing": "upload",
        "update_preserves_private_footage": True,
        "warns_footage_loss": True,
        "recommends_uninstall": False,
        "labelled_production_update": True,
        "source_revision": BASE_REVISION,
        "recorded_source_revision": BASE_REVISION,
        "is_update": True,
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
        "build_type": core["build_type"],
        "signing": core["signing"],
        "update_preserves_private_footage": core["update_preserves_private_footage"],
        "warns_footage_loss": core["warns_footage_loss"],
        "recommends_uninstall": core["recommends_uninstall"],
        "labelled_production_update": core["labelled_production_update"],
        "source_revision": core["source_revision"],
        "recorded_source_revision": core["recorded_source_revision"],
        "is_update": core["is_update"],
    }


def uninstall_without_warning_plan(**overrides: Any) -> dict[str, Any]:
    """The deliberate mutant: recommend uninstall and do not warn about footage loss."""
    plan = core_payload(
        recommends_uninstall=True,
        warns_footage_loss=False,
    )
    plan.update(overrides)
    return plan
