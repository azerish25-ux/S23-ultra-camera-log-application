#!/usr/bin/env python3
"""P148 Verify offline privacy and permissions.

Host reference only. This module does not probe a device and does not qualify
a physical S23. permissions is a list of {name, required, used}. A permission
that is used but not required is rejected. Network endpoints must be empty
when offline_claim is true. A nonempty analytics_payload while offline_claim
is true sends thumbnails and is rejected. Camera and microphone may be
required only when capture needs them. An unused required permission is
recorded as a warning and is not hidden. The decision is recorded or rejected,
never qualified or allowed.

Privacy rule: a permission used but not required is rejected. Network
endpoints must be empty for an offline claim. Sending thumbnails
(analytics_payload nonempty) while offline_claim is true is rejected. Camera
and microphone may be required only when capture needs them. Unused required
permissions are recorded as a warning, not hidden. The decision is never
qualified.
"""

from __future__ import annotations

import math
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P148"
WORKSTREAM = 19
TITLE = "Verify offline privacy and permissions"
GOAL = "Make local processing and minimum permission use observable properties."
METHOD = (
    "Audit network traffic, permission prompts, logging, crash reports, and exported "
    "metadata. The default render path must not upload frames, depth maps, faces, or "
    "audio. Optional content downloads are explicit and separable from operation after "
    "installation."
)
FIXTURE = (
    "Airplane-mode capture and development with all model assets installed, plus a "
    "diagnostic export."
)
ORACLE = (
    "The workflow succeeds locally and the report omits personal paths and unnecessary "
    "identifiers."
)
MUTANT = "Send image thumbnails to analytics while describing the app as entirely offline."
DELIVERABLE = "Privacy test report and permission inventory"
DEPENDENCIES = ("P147",)

PRIVACY_RULE = (
    "A permission used but not required is rejected. Network endpoints must be empty "
    "for an offline claim. Sending thumbnails (analytics_payload nonempty) while "
    "offline_claim is true is rejected. Camera and microphone may be required only "
    "when capture needs them. Unused required permissions are recorded as a warning, "
    "not hidden. The decision is never qualified."
)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p148-offline-privacy"
CLAIM = "offline-privacy-and-permissions-host-reference"
CLEAN_EXPORT = (
    "airplane-mode local capture and development; model assets installed; "
    "diagnostic export omits personal paths and unnecessary identifiers"
)

USED_NOT_REQUIRED = "permission-used-not-required"
OFFLINE_ENDPOINTS = "offline-claim-with-network-endpoints"
THUMBNAIL_OFFLINE = "analytics-thumbnail-while-offline"
CAPTURE_PERMISSION = "permission-required-without-capture-need"
WARNINGS_HIDDEN = "unused-required-warning-hidden"
PRIVATE_UPLOAD = "private-upload-on-default-path"
PERSONAL_MARKER = "personal-path-or-identifier"
IMPLICIT_DOWNLOAD = "optional-download-not-explicit"
OPERATION_NETWORK = "operation-depends-on-network"

HIGH_COVERAGE = 0.8
MAX_DIMENSION = 8192
MAX_LENGTH = 8_000_000
MAX_ALLOCATION = 8_000_000

CAMERA_NAMES = frozenset({"camera", "android.permission.camera"})
MICROPHONE_NAMES = frozenset({
    "microphone",
    "android.permission.record_audio",
    "record_audio",
})
FORBIDDEN_UPLOADS = frozenset({
    "frames",
    "frame",
    "depth",
    "depth-map",
    "depth-maps",
    "depth map",
    "depth maps",
    "faces",
    "face",
    "audio",
    "private-metadata",
    "private metadata",
})
THUMBNAIL_UPLOADS = frozenset({"thumbnail", "thumbnails"})
PERSONAL_MARKERS = (
    "/home/",
    "/users/",
    "\\users\\",
    "/data/user/",
    "file://",
    "content://",
    "imei",
    "android_id",
    "serial=",
    "account-id",
    "accountid",
)
PERMISSION_KEYS = frozenset({"name", "required", "used"})
PRIVATE_TRANSMISSIONS = frozenset({
    "frames",
    "depth",
    "depth-maps",
    "audio",
    "faces",
    "metadata",
    "private-metadata",
})
TRANSMISSION_KINDS = PRIVATE_TRANSMISSIONS | {"thumbnail", "none"}
RESULT_STATUSES = frozenset({"pass", "fail", "skip", "unavailable"})
SUMMARY_KEYS = ("pass", "fail", "skip", "unavailable")
FORBIDDEN_RELEASE_SCOPES = frozenset({"native-resolution", "camera-equivalence"})
FEATURE_STATES = frozenset({"implemented", "experimental", "physically-qualified"})
MIGRATIONS = frozenset({"explicit", "refused", "silent-uninstall", "none"})

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
    "offline_claim",
    "permissions",
    "network_endpoints",
    "analytics_payload",
    "capture_needs_camera",
    "capture_needs_microphone",
    "visible_warnings",
    "hide_warnings",
    "uploads",
    "diagnostic_export",
    "optional_downloads_explicit",
    "operation_requires_network",
}
CORE_KEYS = {
    "evidenceId",
    "claim",
    "applyMutant",
    "offline_claim",
    "permissions",
    "network_endpoints",
    "analytics_payload",
    "capture_needs_camera",
    "capture_needs_microphone",
    "visible_warnings",
    "hide_warnings",
    "uploads",
    "diagnostic_export",
    "optional_downloads_explicit",
    "operation_requires_network",
}
CASE_COMMON_KEYS = CORE_KEYS | {"repeat"}

FAULT_TEXT = {
    USED_NOT_REQUIRED: "a permission is used but not required",
    OFFLINE_ENDPOINTS: "network endpoints must be empty for an offline claim",
    THUMBNAIL_OFFLINE: MUTANT,
    CAPTURE_PERMISSION: "camera and microphone may be required only when capture needs them",
    WARNINGS_HIDDEN: "unused required permissions must be recorded as a warning, not hidden",
    PRIVATE_UPLOAD: "the default render path must not upload frames, depth maps, faces, or audio",
    PERSONAL_MARKER: ORACLE,
    IMPLICIT_DOWNLOAD: (
        "optional content downloads must be explicit and separable from operation after installation"
    ),
    OPERATION_NETWORK: "operation after installation must not depend on the network",
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


def sensor_kind(name: str) -> str | None:
    folded = name.casefold()
    if folded in CAMERA_NAMES:
        return "camera"
    if folded in MICROPHONE_NAMES:
        return "microphone"
    return None


def warning_for(name: str) -> str:
    return "unused-required:" + name


def personal_markers(text: str) -> list[str]:
    folded = text.casefold()
    return [marker for marker in PERSONAL_MARKERS if marker.casefold() in folded]


def parse_string_list(value: object, label: str) -> list[str]:
    require(isinstance(value, list), label + " must be a list")
    return [require_text(item, f"{label}[{index}]") for index, item in enumerate(value)]


def parse_permissions(value: object) -> list[dict[str, Any]]:
    require(isinstance(value, list), "permissions must be a list")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        require(isinstance(item, dict), f"permissions[{index}] must be an object")
        require(set(item) == PERMISSION_KEYS, f"permissions[{index}] keys are invalid")
        rows.append({
            "name": require_text(item["name"], f"permissions[{index}].name"),
            "required": require_bool(item["required"], f"permissions[{index}].required"),
            "used": require_bool(item["used"], f"permissions[{index}].used"),
        })
    names = [row["name"] for row in rows]
    require(len(names) == len(set(names)), "permission names must be unique")
    return rows


def analyze_privacy(
    *,
    permissions: list[dict[str, Any]],
    offline_claim: bool,
    network_endpoints: list[str],
    analytics_payload: list[str],
    capture_needs_camera: bool,
    capture_needs_microphone: bool,
    visible_warnings: list[str],
    hide_warnings: bool,
    uploads: list[str],
    diagnostic_export: str,
    optional_downloads_explicit: bool,
    operation_requires_network: bool,
    apply_mutant: bool,
) -> dict[str, Any]:
    """Apply the offline privacy and minimum-permission rule."""
    faults: list[str] = []
    warnings: list[str] = []
    used_not_required: list[str] = []
    without_need: list[str] = []
    for permission in permissions:
        name = permission["name"]
        required = permission["required"]
        used = permission["used"]
        if required and not used:
            warnings.append(warning_for(name))
        if used and not required:
            used_not_required.append(name)
            faults.append(USED_NOT_REQUIRED)
        kind = sensor_kind(name)
        needs = capture_needs_camera if kind == "camera" else capture_needs_microphone
        if required and kind is not None and not needs:
            without_need.append(name)
            faults.append(CAPTURE_PERMISSION)
    warnings_hidden = hide_warnings or list(visible_warnings) != warnings
    if warnings_hidden:
        faults.append(WARNINGS_HIDDEN)
    analytics_nonempty = len(analytics_payload) > 0
    thumbnail_upload = offline_claim and any(item.casefold() in THUMBNAIL_UPLOADS for item in uploads)
    if (offline_claim and analytics_nonempty) or thumbnail_upload or apply_mutant:
        faults.append(THUMBNAIL_OFFLINE)
    if offline_claim and network_endpoints:
        faults.append(OFFLINE_ENDPOINTS)
    if (not offline_claim) and network_endpoints and not optional_downloads_explicit:
        faults.append(IMPLICIT_DOWNLOAD)
    if operation_requires_network:
        faults.append(OPERATION_NETWORK)
    markers = personal_markers(diagnostic_export)
    if markers:
        faults.append(PERSONAL_MARKER)
    forbidden = [item for item in uploads if item.casefold() in FORBIDDEN_UPLOADS]
    if forbidden:
        faults.append(PRIVATE_UPLOAD)
    snapshot = {
        "offline_claim": offline_claim,
        "permissions": permissions,
        "usedNotRequired": used_not_required,
        "requiredWithoutCaptureNeed": without_need,
        "warnings": warnings,
        "warningsHidden": warnings_hidden,
        "network_endpoints": list(network_endpoints),
        "analyticsNonempty": analytics_nonempty or apply_mutant or thumbnail_upload,
        "uploads": list(uploads),
        "forbiddenUploads": forbidden,
        "personalMarkers": markers,
        "optional_downloads_explicit": optional_downloads_explicit,
        "operation_requires_network": operation_requires_network,
        "hide_warnings": hide_warnings,
        "capture_needs_camera": capture_needs_camera,
        "capture_needs_microphone": capture_needs_microphone,
    }
    extra = ["privacy rule: " + PRIVACY_RULE]
    for warning in warnings:
        extra.append("warning: " + warning)
    if used_not_required:
        extra.append("used but not required: " + ", ".join(used_not_required))
    if without_need:
        extra.append("required without capture need: " + ", ".join(without_need))
    if offline_claim and network_endpoints:
        extra.append("network endpoints: " + ", ".join(network_endpoints))
    if markers:
        extra.append("personal markers: " + ", ".join(markers))
    if forbidden:
        extra.append("forbidden uploads: " + ", ".join(forbidden))
    if apply_mutant:
        extra.append("mutant sends thumbnails while the app is described as entirely offline")
    return {
        "faults": dedupe(faults),
        "snapshot": snapshot,
        "extraReasons": extra,
        "applyMutant": apply_mutant,
        "warnings": warnings,
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


def _core_from_mapping(mapping: dict) -> dict[str, Any]:
    evidence = require_text(mapping["evidenceId"], "evidenceId")
    claim = require_text(mapping["claim"], "claim")
    apply_mutant = require_bool(mapping["applyMutant"], "applyMutant")
    permissions = parse_permissions(mapping["permissions"])
    offline_claim = require_bool(mapping["offline_claim"], "offline_claim")
    endpoints = parse_string_list(mapping["network_endpoints"], "network_endpoints")
    analytics = parse_string_list(mapping["analytics_payload"], "analytics_payload")
    needs_camera = require_bool(mapping["capture_needs_camera"], "capture_needs_camera")
    needs_microphone = require_bool(mapping["capture_needs_microphone"], "capture_needs_microphone")
    visible = parse_string_list(mapping["visible_warnings"], "visible_warnings")
    hide_warnings = require_bool(mapping["hide_warnings"], "hide_warnings")
    uploads = parse_string_list(mapping["uploads"], "uploads")
    diagnostic = require_text(mapping["diagnostic_export"], "diagnostic_export")
    explicit = require_bool(mapping["optional_downloads_explicit"], "optional_downloads_explicit")
    requires_network = require_bool(mapping["operation_requires_network"], "operation_requires_network")
    analysis = analyze_privacy(
        permissions=permissions,
        offline_claim=offline_claim,
        network_endpoints=endpoints,
        analytics_payload=analytics,
        capture_needs_camera=needs_camera,
        capture_needs_microphone=needs_microphone,
        visible_warnings=visible,
        hide_warnings=hide_warnings,
        uploads=uploads,
        diagnostic_export=diagnostic,
        optional_downloads_explicit=explicit,
        operation_requires_network=requires_network,
        apply_mutant=apply_mutant,
    )
    analysis["evidence"] = evidence
    analysis["claim"] = claim
    return analysis


def _reasons(analysis: dict[str, Any], lead: list[str], fault_text: dict[str, str] | None) -> list[str]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    reasons = list(lead)
    reasons.extend(analysis["extraReasons"])
    for token in analysis["faults"]:
        reasons.append(text.get(token, token))
    if analysis["applyMutant"]:
        reasons.append("mutant rejected: " + MUTANT)
    if not analysis["faults"]:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("privacy report recorded; not a physical qualification")
    return reasons


def assess(document: dict) -> dict[str, Any]:
    """Record an offline privacy report and permission inventory, or reject it."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    analysis = _core_from_mapping(document)
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
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a phase document or a core privacy payload."""
    require(isinstance(payload, dict), "payload must be an object")
    if (
        "schemaVersion" in payload
        or "implementationBaseRevision" in payload
        or "phase" in payload
    ):
        return assess(payload)
    require(set(payload) == CORE_KEYS, "invalid payload keys")
    analysis = _core_from_mapping(payload)
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
    analysis = _core_from_mapping(payload)
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


def clean_permissions() -> list[dict[str, Any]]:
    return [
        {"name": "camera", "required": True, "used": True},
        {"name": "microphone", "required": True, "used": True},
    ]


def core_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "offline_claim": True,
        "permissions": clean_permissions(),
        "network_endpoints": [],
        "analytics_payload": [],
        "capture_needs_camera": True,
        "capture_needs_microphone": True,
        "visible_warnings": [],
        "hide_warnings": False,
        "uploads": [],
        "diagnostic_export": CLEAN_EXPORT,
        "optional_downloads_explicit": True,
        "operation_requires_network": False,
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
        "applyMutant": core["applyMutant"],
        "offline_claim": core["offline_claim"],
        "permissions": core["permissions"],
        "network_endpoints": core["network_endpoints"],
        "analytics_payload": core["analytics_payload"],
        "capture_needs_camera": core["capture_needs_camera"],
        "capture_needs_microphone": core["capture_needs_microphone"],
        "visible_warnings": core["visible_warnings"],
        "hide_warnings": core["hide_warnings"],
        "uploads": core["uploads"],
        "diagnostic_export": core["diagnostic_export"],
        "optional_downloads_explicit": core["optional_downloads_explicit"],
        "operation_requires_network": core["operation_requires_network"],
    }
