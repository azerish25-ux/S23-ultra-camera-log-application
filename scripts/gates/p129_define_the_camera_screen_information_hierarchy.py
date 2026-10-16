#!/usr/bin/env python3
"""P129 Define the camera screen information hierarchy.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P129-01 through TC-P129-08 modules.

The screen has three slots plus a warnings list:

- capture must include record and stop (persistent; not a scrolling panel)
- monitoring holds scopes and aids and is optional
- processing holds looks and is optional

Record and stop stay in the capture slot. They are rejected when they exist
only inside a scrolling processing panel, and ``record_in_scroll_only`` true
is rejected on its own. A control id shared by capture and processing is
rejected. Permission, thermal, and storage warnings stay visible: a severe
warning with ``warnings_visible`` false is rejected. The hierarchy is recorded.
It is never a usability study pass and the decision is never qualified.
"""

from __future__ import annotations

from typing import Any


BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P129"
TITLE = "Define the camera screen information hierarchy"
WORKSTREAM = 17
DEPENDENCIES = ("P017", "P024", "P121")
GOAL = (
    "Keep recording, source mode, exposure, audio, and warnings visible "
    "without overcrowding the viewfinder."
)
METHOD = (
    "Separate persistent capture controls from expandable advanced settings. "
    "Show requested versus applied values only where meaningful and label "
    "provisional information. Design portrait and landscape layouts around "
    "stable Record and Stop targets, not a scrolling toolbar."
)
FIXTURE = (
    "Landscape mode with large text, a storage warning, microphone meters, "
    "and the manual controls panel open."
)
ORACLE = (
    "Record and Stop remain reachable, warnings remain readable, and the "
    "viewfinder is not accidentally replaced by settings."
)
MUTANT = "Place Stop inside a scrollable control list that moves during recording."
DELIVERABLE = "Camera screen specification and layout interaction tests"
SCHEMA_VERSION = 1

SLOT_CAPTURE = "capture"
SLOT_MONITORING = "monitoring"
SLOT_PROCESSING = "processing"
SLOT_NAMES = (SLOT_CAPTURE, SLOT_MONITORING, SLOT_PROCESSING)
RECORD_ID = "record"
STOP_ID = "stop"
REQUIRED_CAPTURE_IDS = (RECORD_ID, STOP_ID)
SEVERE_WARNING_KINDS = ("permission", "thermal", "storage")
SEVERE_WARNING_KIND_SET = frozenset(SEVERE_WARNING_KINDS)

RECORD_OR_STOP_NOT_IN_CAPTURE = "record-or-stop-not-in-capture"
RECORD_IN_SCROLL_ONLY = "record-in-scroll-only"
SHARED_CONTROL_IDENTITY = "shared-control-identity"
SEVERE_WARNING_HIDDEN = "severe-warning-hidden"
VIEWFINDER_REPLACED = "viewfinder-replaced-by-settings"
USABILITY_STUDY_CLAIMED = "usability-study-claimed-as-pass"

SLOT_RULES = (
    "Screen slots are capture, monitoring, and processing, plus a warnings list. "
    "Capture must include record and stop. "
    "Monitoring (scopes and aids) is optional. "
    "Processing (looks) is optional. "
    "Record and stop must be in the capture slot, not only inside a scrolling processing panel. "
    "record_in_scroll_only true is rejected. "
    "A control id present in both capture and processing is rejected. "
    "Permission, thermal, and storage warnings must stay visible. "
    "A severe warning with warnings_visible false is rejected. "
    "The hierarchy is recorded, never a usability study pass."
)

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "record_in_scroll_only",
    "warnings_visible",
    "viewfinder_replaced",
    "usability_study_pass",
    "slots",
    "warnings",
}
EVALUATE_KEYS = {
    "caseId",
    "evidenceId",
    "claim",
    "capture",
    "monitoring",
    "processing",
    "warnings",
    "record_in_scroll_only",
    "warnings_visible",
    "viewfinder_replaced",
    "usability_study_pass",
    "applyMutant",
}
CONTROL_KEYS = {"id", "label"}
WARNING_KEYS = {"kind", "text"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = frozenset({"recorded", "rejected"})
PHYSICAL_NOTE = "physical S23 measurement was not run"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_text(value: Any, label: str) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(),
            f"{label} must be a non-empty string")
    return value


def require_bool(value: Any, label: str) -> bool:
    require(type(value) is bool, f"{label} must be a bool")
    return value


def _normalize_warning_kind(kind: str) -> str:
    token = kind.strip().lower().replace("_", "-").replace(" ", "-")
    if token in {"missing-permission", "permission-missing"}:
        return "permission"
    return token


def _controls(items: Any, slot_name: str, *, strict_objects: bool) -> list[dict[str, str]]:
    require(isinstance(items, list), f"{slot_name} must be a list")
    parsed: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        label_prefix = f"{slot_name}[{index}]"
        if isinstance(item, str):
            require(not strict_objects, f"{label_prefix} must be an object")
            ident = require_text(item, label_prefix)
            role = ident
            control_label = ident
        elif isinstance(item, dict):
            if strict_objects:
                require(set(item) == CONTROL_KEYS, f"{label_prefix} keys must be id and label")
            else:
                require("id" in item, f"{label_prefix} must include id")
                extra = set(item) - {"id", "label", "role"}
                require(not extra, f"{label_prefix} has unexpected fields")
            ident = require_text(item["id"], f"{label_prefix}.id")
            if "label" in item:
                control_label = require_text(item["label"], f"{label_prefix}.label")
            else:
                control_label = ident
            if "role" in item:
                role = require_text(item["role"], f"{label_prefix}.role")
            else:
                role = ident
        else:
            raise ValueError(f"{label_prefix} must be a control")
        require(ident not in seen, f"duplicate control id in {slot_name}: {ident}")
        seen.add(ident)
        parsed.append({"id": ident, "label": control_label, "role": role})
    return parsed


def _warnings(items: Any, *, strict_objects: bool) -> list[str]:
    require(isinstance(items, list), "warnings must be a list")
    kinds: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        label = f"warnings[{index}]"
        if isinstance(item, str):
            require(not strict_objects, f"{label} must be an object")
            kind = _normalize_warning_kind(require_text(item, label))
        elif isinstance(item, dict):
            if strict_objects:
                require(set(item) == WARNING_KEYS, f"{label} keys must be kind and text")
            else:
                require("kind" in item, f"{label} must include kind")
                extra = set(item) - WARNING_KEYS
                require(not extra, f"{label} has unexpected fields")
            kind = _normalize_warning_kind(require_text(item["kind"], f"{label}.kind"))
            if "text" in item:
                require_text(item["text"], f"{label}.text")
        else:
            raise ValueError(f"{label} must be a warning")
        require(kind not in seen, f"duplicate warning kind: {kind}")
        seen.add(kind)
        kinds.append(kind)
    return kinds


def _has_capture_action(controls: list[dict[str, str]], name: str) -> bool:
    return any(item["id"] == name or item["role"] == name for item in controls)


def _join(ids: list[str]) -> str:
    return ",".join(ids) if ids else "none"


def judge_hierarchy(
    capture: Any,
    monitoring: Any,
    processing: Any,
    warnings: Any,
    record_in_scroll_only: Any,
    warnings_visible: Any,
    *,
    viewfinder_replaced: Any = False,
    usability_study_pass: Any = False,
    apply_mutant: Any = False,
    strict_objects: bool = False,
) -> dict[str, Any]:
    """Judge capture, monitoring, and processing slots. Raises ValueError on invalid shapes."""
    capture_controls = _controls(capture, SLOT_CAPTURE, strict_objects=strict_objects)
    monitoring_controls = _controls(monitoring, SLOT_MONITORING, strict_objects=strict_objects)
    processing_controls = _controls(processing, SLOT_PROCESSING, strict_objects=strict_objects)
    warning_kinds = _warnings(warnings, strict_objects=strict_objects)
    scroll_only = require_bool(record_in_scroll_only, "record_in_scroll_only")
    visible = require_bool(warnings_visible, "warnings_visible")
    replaced = require_bool(viewfinder_replaced, "viewfinder_replaced")
    usability = require_bool(usability_study_pass, "usability_study_pass")
    mutant = require_bool(apply_mutant, "applyMutant")

    capture_ids = [item["id"] for item in capture_controls]
    monitoring_ids = [item["id"] for item in monitoring_controls]
    processing_ids = [item["id"] for item in processing_controls]
    missing = [
        name for name in REQUIRED_CAPTURE_IDS
        if not _has_capture_action(capture_controls, name)
    ]
    overlap = sorted(set(capture_ids) & set(processing_ids))
    severe = [kind for kind in warning_kinds if kind in SEVERE_WARNING_KIND_SET]

    rejected: list[str] = []
    reasons = [
        "slot rules: " + SLOT_RULES,
        f"capture={_join(capture_ids)}",
        f"monitoring={_join(monitoring_ids)}",
        f"processing={_join(processing_ids)}",
        f"warnings={_join(warning_kinds)}",
        f"record_in_scroll_only={str(scroll_only).lower()}",
        f"warnings_visible={str(visible).lower()}",
    ]
    if mutant:
        rejected.append(MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    if missing:
        rejected.append(RECORD_OR_STOP_NOT_IN_CAPTURE)
        reasons.append(
            "record and stop must be in the capture slot, not only inside a scrolling processing panel"
            + " (missing " + ",".join(missing) + ")"
        )
    if scroll_only:
        rejected.append(RECORD_IN_SCROLL_ONLY)
        reasons.append(
            "record_in_scroll_only is true; record and stop must not live only in the scrolling panel"
        )
    if overlap:
        rejected.append(SHARED_CONTROL_IDENTITY)
        reasons.append(
            "capture and processing share control id: " + ",".join(overlap)
        )
    if severe and not visible:
        rejected.append(SEVERE_WARNING_HIDDEN)
        reasons.append(
            "severe warning hidden (" + ",".join(severe) + "); permission, thermal, and storage stay visible"
        )
    elif severe:
        reasons.append("severe warnings visible: " + ",".join(severe))
    else:
        reasons.append("no severe permission, thermal, or storage warning")
    if replaced:
        rejected.append(VIEWFINDER_REPLACED)
        reasons.append("viewfinder was replaced by settings")
    if usability:
        rejected.append(USABILITY_STUDY_CLAIMED)
        reasons.append("hierarchy is recorded, never a usability study pass")
    else:
        reasons.append("hierarchy is recorded, not a usability study pass")

    preserved = [
        f"capture={_join(capture_ids)}",
        f"monitoring={_join(monitoring_ids)}",
        f"processing={_join(processing_ids)}",
        f"warnings={_join(warning_kinds)}",
        f"record_in_scroll_only={str(scroll_only).lower()}",
        f"warnings_visible={str(visible).lower()}",
        f"viewfinder_replaced={str(replaced).lower()}",
    ]
    return {
        "rejectedClaims": rejected,
        "reasons": reasons,
        "preservedResults": preserved,
        "captureIds": capture_ids,
        "monitoringIds": monitoring_ids,
        "processingIds": processing_ids,
        "warningKinds": warning_kinds,
    }


def seal_result(
    case_id: str,
    decision: str,
    reasons: list,
    rejected: list,
    preserved: list,
    questions: list,
    evidence: str,
) -> dict[str, Any]:
    """Seal the public result. ``qualified`` and ``allowed`` cannot be returned."""
    require_text(case_id, "caseId")
    require(decision in DECISIONS, "decision cannot be qualified")
    require(isinstance(reasons, list) and reasons, "reasons must be a non-empty list")
    require(isinstance(rejected, list), "rejectedClaims must be a list")
    require(isinstance(preserved, list) and preserved, "preservedResults must be a non-empty list")
    require(isinstance(questions, list) and questions, "openQuestions must be a non-empty list")
    rejected_out: list[str] = []
    for item in rejected:
        require(isinstance(item, str) and item.strip(), "rejected claim must be a non-empty string")
        if item not in rejected_out:
            rejected_out.append(item)
    reason_out = []
    for item in reasons:
        require(isinstance(item, str) and item.strip(), "reason must be a non-empty string")
        reason_out.append(item)
    preserved_out = []
    for item in preserved:
        require(isinstance(item, str) and item.strip(), "preserved result must be a non-empty string")
        preserved_out.append(item)
    question_out = []
    for item in questions:
        require(isinstance(item, str) and item.strip(), "open question must be a non-empty string")
        question_out.append(item)
    require(bool(rejected_out) == (decision == "rejected"), "decision does not match rejected claims")
    require(evidence in preserved_out, "evidence wiped")
    require(any("physical S23" in item for item in question_out), "physical S23 not run must be noted")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reason_out,
        "rejectedClaims": rejected_out,
        "preservedResults": preserved_out,
        "openQuestions": question_out,
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(result["decision"] not in {"qualified", "allowed"}, "decision cannot be qualified")
    return result


def _questions() -> list[str]:
    return [
        PHYSICAL_NOTE,
        "hierarchy is recorded and is not a usability study pass",
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]


def _decide(case_id: str, evidence: str, claim: str, judged: dict[str, Any]) -> dict[str, Any]:
    rejected = list(judged["rejectedClaims"])
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "goal: " + GOAL,
        "fixture: " + FIXTURE,
    ]
    reasons.extend(judged["reasons"])
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("camera screen hierarchy recorded")
        reasons.append("method: " + METHOD)
        reasons.append("deliverable: " + DELIVERABLE)
    preserved = [evidence, claim]
    preserved.extend(judged["preservedResults"])
    return seal_result(case_id, decision, reasons, rejected, preserved, _questions(), evidence)


def _slots(document: dict) -> dict[str, Any]:
    slots = document["slots"]
    require(isinstance(slots, dict), "slots must be an object")
    require(set(slots) == set(SLOT_NAMES), "slots must be capture, monitoring, and processing")
    return slots


def assess(document: dict) -> dict[str, Any]:
    """Record the camera-screen hierarchy, or reject a slot, warning, or mutant failure."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == SCHEMA_VERSION,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = require_text(document["evidenceId"], "evidenceId")
    claim = require_text(document["claim"], "claim")
    require_bool(document["applyMutant"], "applyMutant")
    slots = _slots(document)
    judged = judge_hierarchy(
        slots[SLOT_CAPTURE],
        slots[SLOT_MONITORING],
        slots[SLOT_PROCESSING],
        document["warnings"],
        document["record_in_scroll_only"],
        document["warnings_visible"],
        viewfinder_replaced=document["viewfinder_replaced"],
        usability_study_pass=document["usability_study_pass"],
        apply_mutant=document["applyMutant"],
        strict_objects=True,
    )
    return _decide(PHASE, evidence, claim, judged)


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a screen payload, or the phase document when one is given."""
    require(isinstance(payload, dict), "payload must be an object")
    if "schemaVersion" in payload or "slots" in payload:
        return assess(payload)
    missing = EVALUATE_KEYS - set(payload)
    extra = set(payload) - EVALUATE_KEYS
    require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))
    if payload.get("decision") in {"qualified", "allowed"}:
        raise ValueError("decision cannot be qualified")
    case_id = require_text(payload["caseId"], "caseId")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    claim = require_text(payload["claim"], "claim")
    judged = judge_hierarchy(
        payload["capture"],
        payload["monitoring"],
        payload["processing"],
        payload["warnings"],
        payload["record_in_scroll_only"],
        payload["warnings_visible"],
        viewfinder_replaced=payload["viewfinder_replaced"],
        usability_study_pass=payload["usability_study_pass"],
        apply_mutant=payload["applyMutant"],
        strict_objects=False,
    )
    return _decide(case_id, evidence, claim, judged)
