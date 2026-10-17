#!/usr/bin/env python3
"""P133 Implement accessible focus and recipe controls.

Host reference only. This module does not probe a device and does not qualify
a physical S23. Every control must carry an id, a non-empty accessible_name, a
role, and a non-gesture path (button, slider, or stepper). An unlabeled canvas
(accessible_name empty, or role canvas with no name) is rejected. Focus order
must include record and stop. Minimum target size is reported; a size below 48
with no alternative labeled control is rejected. Recipe controls stay separate
from capture controls.
"""

from __future__ import annotations

import math
import re
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P133"
WORKSTREAM = 17
TITLE = "Implement accessible focus and recipe controls"
GOAL = "Make visual editing possible without relying solely on tiny unlabeled gestures."
METHOD = (
    "Provide accessible names, state descriptions, keyboard or switch navigation where applicable, "
    "and numeric alternatives for ROIs and focus controls. Do not convey failure only through color. "
    "Preserve focus order across panels and orientation changes."
)
FIXTURE = (
    "A screen-reader user selects a grey-reference ROI, changes virtual focus, "
    "and cancels a development job."
)
ORACLE = (
    "All actions have usable labels and state feedback, and cancellation remains "
    "available without a precision gesture."
)
MUTANT = "Expose a custom control only as an unlabeled canvas."
DELIVERABLE = "Accessibility interaction tests and semantic control audit"
DEPENDENCIES = ("P132",)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p133-accessible-focus-recipe"
CLAIM = "accessible-focus-and-recipe-controls-host-reference"
MIN_TARGET_DP = 48
RECORD_ID = "record"
STOP_ID = "stop"
SOURCE_STATUS_ID = "source-status"
AUDIO_WARNING_ID = "audio-warning"
STORAGE_WARNING_ID = "storage-warning"
ROI_ID = "grey-reference-roi"
FOCUS_ID = "virtual-focus"
CANCEL_ID = "cancel-development"
RECIPE_ID = "film-recipe"
RECIPE_EVIDENCE_ID = "recipe-evidence"
FIXTURE_SOURCE_MODE = "1080p SDR"
FIXTURE_RECIPE_LABEL = "large-format film"

ACCESSIBILITY_RULE = (
    "each control has id, accessible_name (non-empty), role, and a non-gesture path "
    "(button, slider, or stepper); a control that is only an unlabeled canvas "
    "(accessible_name empty or role canvas with no name) is rejected; focus order must "
    "include record and stop; minimum target size is reported; size below 48 with no "
    "alternative labeled control is rejected; recipe controls are separate from capture controls"
)

ROLES = frozenset({"button", "slider", "stepper", "canvas"})
PATHS = frozenset({"button", "slider", "stepper", "canvas", "gesture"})
NON_GESTURE_PATHS = frozenset({"button", "slider", "stepper"})
NUMERIC_PATHS = frozenset({"slider", "stepper"})
FAMILIES = frozenset({"capture", "recipe", "focus", "roi", "cancel", "warning", "monitoring"})
PANELS = frozenset({"capture", "recipe", "focus", "monitoring", "development"})
EXPECTED_PANEL = {
    "capture": "capture",
    "recipe": "recipe",
    "focus": "focus",
    "roi": "focus",
    "cancel": "development",
    "warning": "monitoring",
    "monitoring": "monitoring",
}
NUMERIC_FAMILIES = frozenset({"focus", "roi"})
CAPTURE_IDS = frozenset({RECORD_ID, STOP_ID})

UNLABELED_CANVAS = "unlabeled-canvas-only-control"
NON_GESTURE_PATH_MISSING = "non-gesture-path-missing"
FOCUS_ORDER_MISSING_RECORD_STOP = "focus-order-missing-record-or-stop"
FOCUS_ORDER_SKIPS_CONTROL = "focus-order-skips-control"
UNDERSIZED_WITHOUT_ALTERNATIVE = "target-below-48-without-labeled-alternative"
RECIPE_NOT_SEPARATE = "recipe-controls-not-separate-from-capture"
RECIPE_OR_CAPTURE_MISSING = "recipe-or-capture-controls-missing"
MISSING_STATE = "missing-state-description"
CANCEL_UNAVAILABLE = "cancellation-unavailable-without-precision-gesture"
COLOR_ONLY = "failure-conveyed-only-by-color"
MISSING_NUMERIC = "roi-or-focus-missing-numeric-alternative"
RECORD_OR_STOP_MISSING = "record-or-stop-control-missing"
PANEL_MISMATCH = "control-panel-does-not-match-family"

CONTROL_KEYS = (
    "id",
    "accessible_name",
    "role",
    "path",
    "target_size",
    "family",
    "group",
    "panel",
    "state_description",
    "color_only_failure",
)
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "controls",
    "focusOrder",
}
EVALUATE_KEYS = {
    "caseId",
    "evidenceId",
    "applyMutant",
    "controls",
    "focusOrder",
}
COMMON_KEYS = {"evidenceId", "repeat", "controls", "focusOrder"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]
COMPLETE_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?\Z")
WORD = re.compile(r"[a-z0-9]+")

FAULT_TEXT = {
    UNLABELED_CANVAS: (
        "A control that is only an unlabeled canvas (accessible_name empty or role canvas "
        "with no name) is rejected."
    ),
    NON_GESTURE_PATH_MISSING: (
        "each control needs a non-gesture path (button, slider, or stepper)"
    ),
    FOCUS_ORDER_MISSING_RECORD_STOP: "focus order must include record and stop",
    FOCUS_ORDER_SKIPS_CONTROL: "focus order must include every control",
    UNDERSIZED_WITHOUT_ALTERNATIVE: (
        "target size below 48 with no alternative labeled control is rejected"
    ),
    RECIPE_NOT_SEPARATE: "recipe controls must stay separate from capture controls",
    RECIPE_OR_CAPTURE_MISSING: "recipe controls and capture controls are both required",
    MISSING_STATE: "each control needs a spoken state description",
    CANCEL_UNAVAILABLE: ORACLE,
    COLOR_ONLY: "failure must not be conveyed only through color",
    MISSING_NUMERIC: "ROI and focus controls need a numeric slider or stepper alternative",
    RECORD_OR_STOP_MISSING: "record and stop controls are required",
    PANEL_MISMATCH: "a control panel must match its family",
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


def require_number(value: object, label: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number",
    )
    number = float(value)
    require(math.isfinite(number), label + " must be finite")
    return number


def optional_plain_text(value: object, label: str) -> str:
    """Allow an empty string. Surrounding whitespace is invalid."""
    require(isinstance(value, str) and value == value.strip(), label + " must be a string")
    return value


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def format_size(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return format(value, "g")


def public_size(value: float) -> int | float:
    if float(value).is_integer():
        return int(value)
    return float(value)


def says_complete(text: str) -> bool:
    folded = text.casefold()
    if "100 percent" in folded or "100%" in folded:
        return True
    words = set(WORD.findall(folded))
    return "complete" in words or "completed" in words


def looks_like_virtual_format(label: str) -> bool:
    folded = label.casefold()
    return any(token in folded for token in ("imax", "70mm", "large-format", "large format"))


def same_label(left: str, right: str) -> bool:
    return left.casefold() == right.casefold()


def parse_complete_number(text: str, label: str) -> tuple[float | None, str]:
    require(isinstance(text, str), label + " must be a string")
    stripped = text.strip()
    if COMPLETE_NUMBER.fullmatch(stripped) is None:
        return None, "incomplete"
    value = float(stripped)
    if not math.isfinite(value):
        return None, "invalid"
    return value, "complete"


def parse_control(value: Any, index: int) -> dict[str, Any]:
    label = f"controls[{index}]"
    require(isinstance(value, dict), label + " must be an object")
    require(set(value) == set(CONTROL_KEYS), label + " keys are invalid")
    control_id = require_text(value["id"], label + ".id")
    accessible_name = optional_plain_text(value["accessible_name"], label + ".accessible_name")
    role = require_text(value["role"], label + ".role")
    require(role in ROLES, label + ".role is not recognized")
    path = require_text(value["path"], label + ".path")
    require(path in PATHS, label + ".path is not recognized")
    target_size = require_number(value["target_size"], label + ".target_size")
    require(target_size > 0, label + ".target_size must be positive")
    family = require_text(value["family"], label + ".family")
    require(family in FAMILIES, label + ".family is not recognized")
    group = require_text(value["group"], label + ".group")
    panel = require_text(value["panel"], label + ".panel")
    require(panel in PANELS, label + ".panel is not recognized")
    state_description = optional_plain_text(value["state_description"], label + ".state_description")
    color_only = require_bool(value["color_only_failure"], label + ".color_only_failure")
    return {
        "id": control_id,
        "accessible_name": accessible_name,
        "role": role,
        "path": path,
        "target_size": target_size,
        "family": family,
        "group": group,
        "panel": panel,
        "state_description": state_description,
        "color_only_failure": color_only,
    }


def parse_controls(value: Any) -> list[dict[str, Any]]:
    require(isinstance(value, list) and bool(value), "controls must be a non-empty list")
    parsed = [parse_control(item, index) for index, item in enumerate(value)]
    ids = [item["id"] for item in parsed]
    require(len(ids) == len(set(ids)), "control ids must be unique")
    return parsed


def parse_focus_order(value: Any, controls: list[dict[str, Any]]) -> list[str]:
    require(isinstance(value, list), "focusOrder must be a list")
    order: list[str] = []
    for index, item in enumerate(value):
        order.append(require_text(item, f"focusOrder[{index}]"))
    require(len(order) == len(set(order)), "focusOrder has duplicate ids")
    known = {control["id"] for control in controls}
    for item in order:
        require(item in known, "focusOrder references unknown control " + item)
    return order


def labeled_alternative(control: dict[str, Any], controls: list[dict[str, Any]]) -> bool:
    for other in controls:
        if other["id"] == control["id"] or other["group"] != control["group"]:
            continue
        if not other["accessible_name"]:
            continue
        if other["path"] not in NON_GESTURE_PATHS:
            continue
        if other["role"] == "canvas" and not other["accessible_name"]:
            continue
        if other["target_size"] < MIN_TARGET_DP:
            continue
        return True
    return False


def numeric_alternative(control: dict[str, Any], controls: list[dict[str, Any]]) -> bool:
    if control["path"] in NUMERIC_PATHS and bool(control["accessible_name"]):
        return True
    for other in controls:
        if other["id"] == control["id"] or other["group"] != control["group"]:
            continue
        if other["path"] in NUMERIC_PATHS and bool(other["accessible_name"]):
            return True
    return False


def usable_cancel(control: dict[str, Any]) -> bool:
    return (
        bool(control["accessible_name"])
        and control["path"] in NON_GESTURE_PATHS
        and bool(control["state_description"])
        and control["color_only_failure"] is False
    )


def audit(controls: list[dict[str, Any]], focus_order: list[str]) -> dict[str, Any]:
    """Apply the accessibility rule to one control surface.

    The committed surface is what later results preserve, including when the
    surface is rejected. Minimum target size is always reported.
    """
    faults: list[str] = []
    unlabeled: list[str] = []
    undersized: list[str] = []
    gesture_only: list[str] = []
    for control in controls:
        name = control["accessible_name"]
        canvas_without_name = control["role"] == "canvas" and not name
        if not name or canvas_without_name:
            unlabeled.append(control["id"])
            faults.append(UNLABELED_CANVAS)
        if control["path"] not in NON_GESTURE_PATHS:
            gesture_only.append(control["id"])
            faults.append(NON_GESTURE_PATH_MISSING)
        if not control["state_description"]:
            faults.append(MISSING_STATE)
        if control["color_only_failure"]:
            faults.append(COLOR_ONLY)
        if control["target_size"] < MIN_TARGET_DP and not labeled_alternative(control, controls):
            undersized.append(control["id"])
            faults.append(UNDERSIZED_WITHOUT_ALTERNATIVE)
        if control["family"] in NUMERIC_FAMILIES and not numeric_alternative(control, controls):
            faults.append(MISSING_NUMERIC)
        if control["panel"] != EXPECTED_PANEL[control["family"]]:
            faults.append(PANEL_MISMATCH)
    ids = {control["id"] for control in controls}
    focus_includes_record = RECORD_ID in focus_order
    focus_includes_stop = STOP_ID in focus_order
    if not (focus_includes_record and focus_includes_stop):
        faults.append(FOCUS_ORDER_MISSING_RECORD_STOP)
    if any(control["id"] not in focus_order for control in controls):
        faults.append(FOCUS_ORDER_SKIPS_CONTROL)
    if RECORD_ID not in ids or STOP_ID not in ids:
        faults.append(RECORD_OR_STOP_MISSING)
    recipe = [control for control in controls if control["family"] == "recipe"]
    capture = [control for control in controls if control["family"] == "capture"]
    recipe_missing = not recipe or not capture
    if recipe_missing:
        faults.append(RECIPE_OR_CAPTURE_MISSING)
    shared_groups = sorted({item["group"] for item in recipe} & {item["group"] for item in capture})
    shared_panels = sorted({item["panel"] for item in recipe} & {item["panel"] for item in capture})
    identity_clash = [
        item["id"]
        for item in recipe
        if item["id"] in CAPTURE_IDS or item["accessible_name"].casefold() in {"record", "stop"}
    ]
    panel_drift = any(item["panel"] != "recipe" for item in recipe) or any(
        item["panel"] != "capture" for item in capture
    )
    recipe_separate = not (shared_groups or shared_panels or identity_clash or panel_drift)
    if recipe and capture and not recipe_separate:
        faults.append(RECIPE_NOT_SEPARATE)
    cancels = [
        control
        for control in controls
        if control["family"] == "cancel" or control["id"] == CANCEL_ID
    ]
    cancel_available = any(usable_cancel(control) for control in cancels)
    if not cancel_available:
        faults.append(CANCEL_UNAVAILABLE)
    minimum = min(control["target_size"] for control in controls)
    return {
        "controls": controls,
        "focusOrder": list(focus_order),
        "minimumTargetSize": minimum,
        "focusIncludesRecord": focus_includes_record,
        "focusIncludesStop": focus_includes_stop,
        "recipeSeparate": recipe_separate and not recipe_missing,
        "recipeOrCaptureMissing": recipe_missing,
        "cancelAvailable": cancel_available,
        "unlabeledCanvasIds": unlabeled,
        "undersizedIds": undersized,
        "gestureOnlyIds": gesture_only,
        "recipeIds": [item["id"] for item in recipe],
        "captureIds": [item["id"] for item in capture],
        "cancelIds": [item["id"] for item in cancels],
        "sharedGroups": shared_groups,
        "faults": dedupe(faults),
    }


def audit_reasons(info: dict[str, Any]) -> list[str]:
    reasons = [
        "accessibility rule: " + ACCESSIBILITY_RULE,
        "minimumTargetSize=" + format_size(info["minimumTargetSize"]),
        "minimumTargetThreshold=" + str(MIN_TARGET_DP),
        "focusOrder=" + ",".join(info["focusOrder"]),
    ]
    if info["focusIncludesRecord"] and info["focusIncludesStop"]:
        reasons.append("focus order includes record and stop")
    else:
        reasons.append("focus order missing record or stop")
    if info["recipeSeparate"]:
        reasons.append("recipe controls are separate from capture controls")
    elif info["recipeOrCaptureMissing"]:
        reasons.append("recipe controls and capture controls must both be present and separate")
    else:
        reasons.append("recipe controls are not separate from capture controls")
    if info["cancelAvailable"]:
        reasons.append("cancellation available without a precision gesture")
    else:
        reasons.append("cancellation unavailable")
    if info["unlabeledCanvasIds"]:
        reasons.append("unlabeledCanvas=" + ",".join(info["unlabeledCanvasIds"]))
    if info["undersizedIds"]:
        reasons.append("undersized=" + ",".join(info["undersizedIds"]))
    return reasons


def public_audit(info: dict[str, Any]) -> dict[str, Any]:
    return {
        "minimumTargetSize": public_size(info["minimumTargetSize"]),
        "minimumTargetThreshold": MIN_TARGET_DP,
        "focusOrder": list(info["focusOrder"]),
        "focusIncludesRecord": info["focusIncludesRecord"],
        "focusIncludesStop": info["focusIncludesStop"],
        "recipeSeparate": info["recipeSeparate"],
        "recipeIds": list(info["recipeIds"]),
        "captureIds": list(info["captureIds"]),
        "cancelIds": list(info["cancelIds"]),
        "unlabeledCanvasIds": list(info["unlabeledCanvasIds"]),
        "undersizedIds": list(info["undersizedIds"]),
        "gestureOnlyIds": list(info["gestureOnlyIds"]),
        "cancelAvailable": info["cancelAvailable"],
        "sharedGroups": list(info["sharedGroups"]),
    }


def make_control(
    control_id: str,
    accessible_name: str,
    role: str,
    path: str,
    *,
    target_size: float = MIN_TARGET_DP,
    family: str,
    group: str | None = None,
    panel: str | None = None,
    state_description: str,
    color_only_failure: bool = False,
) -> dict[str, Any]:
    if group is None:
        group = control_id
    if panel is None:
        panel = EXPECTED_PANEL[family]
    return {
        "id": control_id,
        "accessible_name": accessible_name,
        "role": role,
        "path": path,
        "target_size": target_size,
        "family": family,
        "group": group,
        "panel": panel,
        "state_description": state_description,
        "color_only_failure": color_only_failure,
    }


def fixture_controls() -> list[dict[str, Any]]:
    return [
        make_control(
            RECORD_ID, "Record", "button", "button", family="capture", state_description="ready"
        ),
        make_control(
            STOP_ID, "Stop", "button", "button", family="capture", state_description="available"
        ),
        make_control(
            SOURCE_STATUS_ID,
            "Source status",
            "button",
            "button",
            family="capture",
            group="source",
            state_description=FIXTURE_SOURCE_MODE,
        ),
        make_control(
            AUDIO_WARNING_ID,
            "Audio warning",
            "button",
            "button",
            family="warning",
            state_description="audio warning readable",
        ),
        make_control(
            STORAGE_WARNING_ID,
            "Storage warning",
            "button",
            "button",
            family="warning",
            state_description="storage warning readable",
        ),
        make_control(
            ROI_ID,
            "Grey reference ROI",
            "stepper",
            "stepper",
            family="roi",
            state_description="selected",
        ),
        make_control(
            FOCUS_ID,
            "Virtual focus",
            "slider",
            "slider",
            family="focus",
            state_description="changed",
        ),
        make_control(
            CANCEL_ID,
            "Cancel development",
            "button",
            "button",
            family="cancel",
            state_description="available without a precision gesture",
        ),
        make_control(
            RECIPE_ID,
            "Film recipe",
            "stepper",
            "stepper",
            family="recipe",
            state_description=FIXTURE_RECIPE_LABEL + " simulated",
        ),
        make_control(
            RECIPE_EVIDENCE_ID,
            "Recipe evidence",
            "button",
            "button",
            family="recipe",
            state_description="simulated",
        ),
    ]


FIXTURE_FOCUS_ORDER = (
    RECORD_ID,
    STOP_ID,
    SOURCE_STATUS_ID,
    AUDIO_WARNING_ID,
    STORAGE_WARNING_ID,
    ROI_ID,
    FOCUS_ID,
    CANCEL_ID,
    RECIPE_ID,
    RECIPE_EVIDENCE_ID,
)


def fixture_focus_order() -> list[str]:
    return list(FIXTURE_FOCUS_ORDER)


def replace_control(controls: list[dict[str, Any]], control_id: str, **overrides: Any) -> list[dict[str, Any]]:
    found = False
    updated: list[dict[str, Any]] = []
    for control in controls:
        item = dict(control)
        if item["id"] == control_id:
            item.update(overrides)
            found = True
        updated.append(item)
    require(found, "unknown control " + control_id)
    return updated


def without_control(
    controls: list[dict[str, Any]], focus_order: list[str], control_id: str
) -> tuple[list[dict[str, Any]], list[str]]:
    updated = [dict(control) for control in controls if control["id"] != control_id]
    require(len(updated) != len(controls), "unknown control " + control_id)
    order = [item for item in focus_order if item != control_id]
    return updated, order


def find_control(controls: list[dict[str, Any]], control_id: str) -> dict[str, Any] | None:
    for control in controls:
        if control["id"] == control_id:
            return control
    return None


def fixture_document() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "controls": fixture_controls(),
        "focusOrder": fixture_focus_order(),
    }


def assemble(
    case_id: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    open_questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    decision = "rejected" if faults else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
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
    require(OPEN_QUESTION in result["openQuestions"], "open question missing")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    return result


def _host_preface() -> list[str]:
    return [
        "host reference only; not a physical S23 measurement",
        "goal: " + GOAL,
        "method: " + METHOD,
        "fixture: " + FIXTURE,
        "oracle: " + ORACLE,
    ]


def _apply_mutant(faults: list[str], apply_mutant: bool) -> list[str]:
    ordered = list(faults)
    if apply_mutant and UNLABELED_CANVAS not in ordered:
        ordered.append(UNLABELED_CANVAS)
    return ordered


def _decide(
    case_id: str,
    evidence: str,
    info: dict[str, Any],
    faults: list[str],
    *,
    claim: str | None,
    apply_mutant: bool,
    extra_reasons: list[str] | None = None,
    extra_preserved: list | None = None,
    open_questions: list[str] | None = None,
    fault_text: dict[str, str] | None = None,
) -> dict[str, Any]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    ordered = dedupe(_apply_mutant(faults, apply_mutant))
    reasons = _host_preface()
    if extra_reasons:
        reasons.extend(extra_reasons)
    reasons.extend(audit_reasons(info))
    for token in ordered:
        reasons.append(text.get(token, token))
    if apply_mutant:
        reasons.append("mutant rejected: " + MUTANT)
    elif UNLABELED_CANVAS in ordered:
        reasons.append(MUTANT)
    if not ordered:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("accessible controls recorded; not a physical qualification")
    preserved: list[Any] = [evidence, public_audit(info)]
    if claim is not None:
        preserved.append(claim)
    if extra_preserved:
        preserved.extend(extra_preserved)
    questions = list(NON_CLAIM_QUESTIONS if open_questions is None else open_questions)
    return assemble(case_id, ordered, reasons, preserved, questions, evidence)


def assess(document: dict) -> dict[str, Any]:
    """Record an accessible focus and recipe surface, or reject an unlabeled canvas."""
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
    controls = parse_controls(document["controls"])
    focus_order = parse_focus_order(document["focusOrder"], controls)
    info = audit(controls, focus_order)
    return _decide(
        PHASE,
        evidence,
        info,
        list(info["faults"]),
        claim=claim,
        apply_mutant=apply_mutant,
    )


def evaluate(payload: dict) -> dict[str, Any]:
    """Audit one control surface. Invalid shapes raise ValueError."""
    require(isinstance(payload, dict), "payload must be an object")
    missing = EVALUATE_KEYS - set(payload)
    extra = set(payload) - EVALUATE_KEYS
    require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))
    case_id = require_text(payload["caseId"], "caseId")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    apply_mutant = require_bool(payload["applyMutant"], "applyMutant")
    controls = parse_controls(payload["controls"])
    focus_order = parse_focus_order(payload["focusOrder"], controls)
    info = audit(controls, focus_order)
    return _decide(
        case_id,
        evidence,
        info,
        list(info["faults"]),
        claim=None,
        apply_mutant=apply_mutant,
    )


def begin_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(COMMON_KEYS) | set(extra_keys), "invalid payload keys")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    repeat = require_text(payload["repeat"], "repeat")
    controls = parse_controls(payload["controls"])
    focus_order = parse_focus_order(payload["focusOrder"], controls)
    info = audit(controls, focus_order)
    return {
        "evidence": evidence,
        "repeat": repeat,
        "controls": controls,
        "focusOrder": focus_order,
        "info": info,
        "faults": list(info["faults"]),
        "public": public_audit(info),
    }


def finish_case(
    case: dict,
    bundle: dict,
    faults: list[str],
    extra_preserved: list,
    fault_text: dict | None = None,
) -> dict[str, Any]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        case["expected"],
        "repeat " + bundle["repeat"],
    ]
    reasons.extend(audit_reasons(bundle["info"]))
    ordered = dedupe(faults)
    for token in ordered:
        reasons.append(text.get(token, token))
    if UNLABELED_CANVAS in ordered:
        reasons.append(MUTANT)
    if not ordered:
        reasons.append("accessible controls recorded; not a physical qualification")
    preserved = [bundle["evidence"], bundle["public"], *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], ordered, reasons, preserved, questions, bundle["evidence"])
