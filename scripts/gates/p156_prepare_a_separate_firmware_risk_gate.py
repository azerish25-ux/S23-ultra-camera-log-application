#!/usr/bin/env python3
"""P156 Prepare a separate firmware risk gate.

Host reference only. This module does not probe a device, does not flash
firmware, and does not qualify a physical S23. Authorization requires
device_serial, image_digest, a user_authorized bool, and nonempty
stop_conditions. similar_name_only true (another phone with a similar name
accepted the image) is rejected. user_authorized false means do not proceed
and is recorded as blocked. Missing stop conditions is rejected. A complete
checklist is only recorded; this gate never authorizes flashing. The decision
is recorded or rejected, never qualified or allowed.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P156"
WORKSTREAM = 20
TITLE = "Prepare a separate firmware risk gate"
GOAL = "Require explicit authorization and a device-specific safety plan before irreversible changes."
METHOD = (
    "Document model variant, bootloader state, verified backups, recovery images, rollback limits, "
    "security consequences, and potential permanent state changes. A general request to build an app "
    "does not authorize flashing. Keep ordinary development operational without firmware changes."
)
FIXTURE = "A proposed flash with an unverified image and no confirmed recovery route for the exact device variant."
ORACLE = "The gate remains closed and the directive continues with non-destructive app work."
MUTANT = "Proceed because another phone with a similar name accepted the image."
DELIVERABLE = "Firmware authorization checklist and stop conditions"
DEPENDENCIES = ("P155",)

AUTHORIZATION_RULE = (
    "Authorization requires device_serial, image_digest, user_authorized bool, and stop_conditions "
    "nonempty. similar_name_only true is rejected. user_authorized false means do not proceed and is "
    "recorded as blocked. Missing stop conditions is rejected. This gate does not authorize flashing; "
    "it only records whether the checklist is complete. The decision is never qualified or allowed."
)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p156-firmware-risk-gate"
CLAIM = "firmware-authorization-checklist-host-reference"

DEVICE_SERIAL = "R5CW10S23A"
MODEL_VARIANT = "SM-S911B"
BOOTLOADER_STATE = "locked"
ROLLBACK_LIMITS = "rollback-not-confirmed"
SECURITY_CONSEQUENCES = "bootloader-or-knox-security-state-may-change"
PERMANENT_STATE_CHANGES = "warranty-bit-or-efuse-may-be-permanent"
RECOVERY_PLACEHOLDER = "unconfirmed"
SIMILAR_ACCEPTED_NAME = "Galaxy S23"
SIMILAR_PROPOSED_NAME = "Galaxy S23 Ultra"
DIFFERENT_DEVICE_NAME = "Pixel 8"

STOP_PERMANENT_STATE = "permanent-state-change"
STOP_UNVERIFIED_IMAGE = "unverified-image"
STOP_NO_RECOVERY = "no-confirmed-recovery-route-for-exact-device-variant"
STOP_USER_NOT_AUTHORIZED = "user-not-authorized"
STOP_GENERAL_APP_REQUEST = "general-app-request-does-not-authorize-flashing"

SIMILAR_NAME_ONLY = "similar-name-only"
MISSING_STOP_CONDITIONS = "missing-stop-conditions"
PROCEED_REFUSED = "flash-not-authorized-by-this-gate"
GENERAL_APP_REQUEST = "general-app-request-does-not-authorize-flash"
NOT_DEVICE_SPECIFIC = "authorization-not-device-specific"

RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = frozenset({"recorded", "rejected"})
DIGEST_RE = re.compile(r"[0-9a-f]{64}")
SERIAL_RE = re.compile(r"[A-Z0-9]{8,20}")
NAME_DROPPED_TOKENS = frozenset({"samsung", "phone", "the"})

IMAGE_DIGEST = hashlib.sha256(b"p156-unverified-proposed-flash").hexdigest()
RECOVERY_DIGEST = hashlib.sha256(b"p156-verified-recovery-image").hexdigest()

NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]

CORE_KEYS = {
    "evidenceId",
    "claim",
    "applyMutant",
    "device_serial",
    "image_digest",
    "user_authorized",
    "stop_conditions",
    "similar_name_only",
    "model_variant",
    "bootloader_state",
    "verified_backups",
    "recovery_image",
    "recovery_confirmed",
    "rollback_limits",
    "security_consequences",
    "permanent_state_changes",
    "image_verified",
    "exact_device_match",
    "general_app_request",
    "device_specific_authorization",
    "claims_proceed",
}
CASE_COMMON_KEYS = CORE_KEYS | {"repeat"}
DOCUMENT_KEYS = CORE_KEYS | {"schemaVersion", "phase", "implementationBaseRevision"}

FIXTURE_STOP_CONDITIONS = (
    STOP_PERMANENT_STATE,
    STOP_UNVERIFIED_IMAGE,
    STOP_NO_RECOVERY,
    STOP_USER_NOT_AUTHORIZED,
    STOP_GENERAL_APP_REQUEST,
)

FAULT_TEXT = {
    SIMILAR_NAME_ONLY: MUTANT,
    MISSING_STOP_CONDITIONS: "missing stop conditions",
    PROCEED_REFUSED: "this gate does not authorize flashing",
    GENERAL_APP_REQUEST: "A general request to build an app does not authorize flashing.",
    NOT_DEVICE_SPECIFIC: "authorization is not device-specific",
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
    require(type(value) is int and not isinstance(value, bool), label + " must be an int")
    return value


def require_number(value: object, label: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number",
    )
    number = float(value)
    require(number == number and number not in (float("inf"), float("-inf")), label + " must be finite")
    return number


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def is_digest(value: str) -> bool:
    return DIGEST_RE.fullmatch(value) is not None


def require_digest(value: object, label: str) -> str:
    text = require_text(value, label)
    require(is_digest(text), label + " must be a sha256 hex digest")
    return text


def require_serial(value: object, label: str) -> str:
    text = require_text(value, label)
    require(SERIAL_RE.fullmatch(text) is not None, label + " must be an exact device serial")
    return text


def normalize_device_name(name: str) -> str:
    """Fold case and separators so 'Galaxy-S23' and 'galaxy s23' compare alike."""
    cleaned = name.casefold().replace("-", " ").replace("_", " ")
    tokens = [token for token in cleaned.split() if token not in NAME_DROPPED_TOKENS]
    return " ".join(tokens)


def similar_device_names(left: str, right: str) -> bool:
    """True when two marketing names refer to the same family but are not evidence of the same phone.

    'Galaxy S23' and 'Galaxy S23 Ultra' are similar. A different family is not.
    Similarity is never authorization for a different device_serial.
    """
    require(isinstance(left, str) and isinstance(right, str), "device names must be strings")
    accepted = normalize_device_name(left)
    proposed = normalize_device_name(right)
    if not accepted or not proposed:
        return False
    if accepted == proposed:
        return True
    return accepted in proposed or proposed in accepted


def required_stop_conditions(state: dict[str, Any]) -> list[str]:
    """Stop conditions demanded by the hazards actually present on this checklist."""
    needed = [STOP_PERMANENT_STATE]
    if state["image_verified"] is not True:
        needed.append(STOP_UNVERIFIED_IMAGE)
    if state["recovery_confirmed"] is not True or state["exact_device_match"] is not True:
        needed.append(STOP_NO_RECOVERY)
    if state["user_authorized"] is not True:
        needed.append(STOP_USER_NOT_AUTHORIZED)
    if state["general_app_request"] is True and state["device_specific_authorization"] is not True:
        needed.append(STOP_GENERAL_APP_REQUEST)
    return needed


def parse_stop_conditions(value: object) -> list[str]:
    require(isinstance(value, list), "stop_conditions must be a list")
    stops: list[str] = []
    for index, item in enumerate(value):
        stops.append(require_text(item, f"stop_conditions[{index}]"))
    require(len(stops) == len(set(stops)), "stop_conditions must be unique")
    return stops


def parse_core(mapping: dict, label: str) -> dict[str, Any]:
    evidence = require_text(mapping["evidenceId"], "evidenceId")
    claim = require_text(mapping["claim"], "claim")
    apply_mutant = require_bool(mapping["applyMutant"], "applyMutant")
    serial = require_serial(mapping["device_serial"], "device_serial")
    digest = require_digest(mapping["image_digest"], "image_digest")
    user_authorized = require_bool(mapping["user_authorized"], "user_authorized")
    stops = parse_stop_conditions(mapping["stop_conditions"])
    similar = require_bool(mapping["similar_name_only"], "similar_name_only")
    model_variant = require_text(mapping["model_variant"], "model_variant")
    bootloader_state = require_text(mapping["bootloader_state"], "bootloader_state")
    verified_backups = require_bool(mapping["verified_backups"], "verified_backups")
    recovery_confirmed = require_bool(mapping["recovery_confirmed"], "recovery_confirmed")
    if recovery_confirmed:
        recovery_image = require_digest(mapping["recovery_image"], "recovery_image")
    else:
        recovery_image = require_text(mapping["recovery_image"], "recovery_image")
    rollback_limits = require_text(mapping["rollback_limits"], "rollback_limits")
    security_consequences = require_text(mapping["security_consequences"], "security_consequences")
    permanent_state_changes = require_text(mapping["permanent_state_changes"], "permanent_state_changes")
    image_verified = require_bool(mapping["image_verified"], "image_verified")
    exact_device_match = require_bool(mapping["exact_device_match"], "exact_device_match")
    general_app_request = require_bool(mapping["general_app_request"], "general_app_request")
    device_specific = require_bool(mapping["device_specific_authorization"], "device_specific_authorization")
    claims_proceed = require_bool(mapping["claims_proceed"], "claims_proceed")
    require(
        not (device_specific and not user_authorized),
        "device_specific_authorization requires user_authorized",
    )
    require(label in {"document", "payload", "case"}, "unknown parse label")
    return {
        "evidenceId": evidence,
        "claim": claim,
        "applyMutant": apply_mutant,
        "device_serial": serial,
        "image_digest": digest,
        "user_authorized": user_authorized,
        "stop_conditions": stops,
        "similar_name_only": similar,
        "model_variant": model_variant,
        "bootloader_state": bootloader_state,
        "verified_backups": verified_backups,
        "recovery_image": recovery_image,
        "recovery_confirmed": recovery_confirmed,
        "rollback_limits": rollback_limits,
        "security_consequences": security_consequences,
        "permanent_state_changes": permanent_state_changes,
        "image_verified": image_verified,
        "exact_device_match": exact_device_match,
        "general_app_request": general_app_request,
        "device_specific_authorization": device_specific,
        "claims_proceed": claims_proceed,
    }


def checklist_is_complete(state: dict[str, Any], missing: list[str], faults: list[str]) -> bool:
    """True only when every safety item is present. Completeness is not permission to flash."""
    if faults or missing:
        return False
    return (
        state["user_authorized"] is True
        and state["device_specific_authorization"] is True
        and state["image_verified"] is True
        and state["verified_backups"] is True
        and state["recovery_confirmed"] is True
        and state["exact_device_match"] is True
        and is_digest(state["recovery_image"])
        and state["similar_name_only"] is False
        and state["applyMutant"] is False
        and state["claims_proceed"] is False
    )


def analyze_computation(state: dict[str, Any]) -> dict[str, Any]:
    needed = required_stop_conditions(state)
    present = set(state["stop_conditions"])
    missing = [item for item in needed if item not in present]
    faults: list[str] = []
    if not state["stop_conditions"] or missing:
        faults.append(MISSING_STOP_CONDITIONS)
    if state["similar_name_only"] is True or state["applyMutant"] is True:
        faults.append(SIMILAR_NAME_ONLY)
    if state["claims_proceed"] is True:
        faults.append(PROCEED_REFUSED)
    if (
        state["user_authorized"] is True
        and state["general_app_request"] is True
        and state["device_specific_authorization"] is not True
    ):
        faults.append(GENERAL_APP_REQUEST)
    if (
        state["user_authorized"] is True
        and state["device_specific_authorization"] is not True
        and state["general_app_request"] is not True
    ):
        faults.append(NOT_DEVICE_SPECIFIC)
    faults = dedupe(faults)
    blocked = state["user_authorized"] is False
    complete = checklist_is_complete(state, missing, faults)
    if blocked:
        status = "blocked"
    elif complete:
        status = "checklist-complete"
    else:
        status = "gate-closed"
    names_similar = similar_device_names(SIMILAR_ACCEPTED_NAME, SIMILAR_PROPOSED_NAME)
    snapshot = {
        "deviceSerial": state["device_serial"],
        "imageDigest": state["image_digest"],
        "userAuthorized": state["user_authorized"],
        "stopConditions": list(state["stop_conditions"]),
        "missingStopConditions": missing,
        "similarNameOnly": state["similar_name_only"] or state["applyMutant"],
        "blocked": blocked,
        "checklistComplete": complete,
        "flashAuthorized": False,
        "proceed": False,
        "gateClosed": True,
        "status": status,
        "similarNameExample": {
            "acceptedName": SIMILAR_ACCEPTED_NAME,
            "proposedName": SIMILAR_PROPOSED_NAME,
            "namesSimilar": names_similar,
            "serialsDiffer": True,
        },
    }
    extra_reasons = [
        "authorization rule: " + AUTHORIZATION_RULE,
        "gate closed; this gate does not authorize flashing",
        "flashAuthorized false; proceed false",
        "similar-name example: " + SIMILAR_ACCEPTED_NAME + " vs " + SIMILAR_PROPOSED_NAME,
    ]
    if blocked:
        extra_reasons.append("user_authorized is false; do not proceed; recorded as blocked")
    if complete:
        extra_reasons.append("checklist complete; flashing remains unauthorized")
    elif not faults:
        extra_reasons.append("checklist incomplete; gate remains closed; non-destructive app work continues")
    if missing:
        extra_reasons.append("missing stop conditions: " + ", ".join(missing))
    if state["similar_name_only"] or state["applyMutant"]:
        extra_reasons.append("mutant rejected: " + MUTANT)
    if state["claims_proceed"]:
        extra_reasons.append("proceed refused; ordinary development stays operational without firmware changes")
    return {
        "faults": faults,
        "snapshot": snapshot,
        "extraReasons": extra_reasons,
        "evidence": state["evidenceId"],
        "claim": state["claim"],
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
    require(result["decision"] != "qualified" and result["decision"] != "allowed", "decision never qualified or allowed")
    require(bool(result["reasons"]), "reasons must be non-empty")
    require(result["preservedResults"][1]["flashAuthorized"] is False, "flash must stay unauthorized")
    require(result["preservedResults"][1]["proceed"] is False, "gate must not proceed")
    require(result["preservedResults"][1]["gateClosed"] is True, "gate must remain closed")
    return result


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
        reasons.append("firmware checklist recorded; not a physical qualification and not a flash authorization")
    return reasons


def _lead_document() -> list[str]:
    return [
        "host reference only; not a physical S23 measurement",
        "physical S23 was not run",
        "goal: " + GOAL,
        "method: " + METHOD,
        "fixture: " + FIXTURE,
        "oracle: " + ORACLE,
    ]


def _lead_payload() -> list[str]:
    return [
        "host reference only; not a physical S23 measurement",
        "physical S23 was not run",
        "oracle: " + ORACLE,
        "fixture: " + FIXTURE,
    ]


def assess(document: dict) -> dict[str, Any]:
    """Record whether the firmware checklist is complete. Never authorize a flash."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    state = parse_core(document, "document")
    analysis = analyze_computation(state)
    reasons = _reasons(analysis, _lead_document(), None)
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a phase document or a core firmware-checklist payload."""
    require(isinstance(payload, dict), "payload must be an object")
    if "schemaVersion" in payload or "implementationBaseRevision" in payload or "phase" in payload:
        return assess(payload)
    require(set(payload) == CORE_KEYS, "invalid payload keys")
    state = parse_core(payload, "payload")
    analysis = analyze_computation(state)
    reasons = _reasons(analysis, _lead_payload(), None)
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


def begin_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(CASE_COMMON_KEYS) | set(extra_keys), "invalid payload keys")
    repeat = require_text(payload["repeat"], "repeat")
    state = parse_core(payload, "case")
    analysis = analyze_computation(state)
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


def core_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "device_serial": DEVICE_SERIAL,
        "image_digest": IMAGE_DIGEST,
        "user_authorized": False,
        "stop_conditions": list(FIXTURE_STOP_CONDITIONS),
        "similar_name_only": False,
        "model_variant": MODEL_VARIANT,
        "bootloader_state": BOOTLOADER_STATE,
        "verified_backups": False,
        "recovery_image": RECOVERY_PLACEHOLDER,
        "recovery_confirmed": False,
        "rollback_limits": ROLLBACK_LIMITS,
        "security_consequences": SECURITY_CONSEQUENCES,
        "permanent_state_changes": PERMANENT_STATE_CHANGES,
        "image_verified": False,
        "exact_device_match": False,
        "general_app_request": True,
        "device_specific_authorization": False,
        "claims_proceed": False,
    }
    payload.update(overrides)
    return payload


def complete_checklist_payload(**overrides: Any) -> dict[str, Any]:
    """Every safety item is documented. The gate still does not authorize flashing."""
    payload = core_payload(
        user_authorized=True,
        stop_conditions=[STOP_PERMANENT_STATE],
        verified_backups=True,
        recovery_image=RECOVERY_DIGEST,
        recovery_confirmed=True,
        image_verified=True,
        exact_device_match=True,
        general_app_request=False,
        device_specific_authorization=True,
        claims_proceed=False,
        similar_name_only=False,
        applyMutant=False,
    )
    payload.update(overrides)
    return payload


def fixture_document() -> dict[str, Any]:
    core = core_payload()
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        **core,
    }


def document_from_core(core: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        **core,
    }
