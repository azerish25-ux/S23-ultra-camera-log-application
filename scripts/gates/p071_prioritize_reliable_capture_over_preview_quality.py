#!/usr/bin/env python3
"""P071 capture-priority scheduler under rising inference load.

Resource budgets degrade in a fixed order: reduce monitoring work, lower
inference frequency, pause optional effects, then stop capture only under its
own documented safety policy. The active preview quality is recorded. The
selected source mode and its recording resolution stay unchanged mid-take.

The deliberate mutant — lowering recording resolution without changing the
active mode label — is rejected. Source cadence stays intact until a
separately documented capture limit. This module does not probe a device,
does not qualify a physical S23, and does not execute TC-P071-01 through
TC-P071-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P071"
CASE_ID = "P071"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-capture-priority-scheduler-fixture"
METHOD = (
    "Define resource budgets and degradation order: reduce monitoring work, "
    "lower inference frequency, pause optional effects, then stop capture only "
    "under its own safety policy. Record which preview quality was active. "
    "Never silently alter the selected source recording mode mid-take."
)
FIXTURE = (
    "Increasing inference load while the camera and encoder approach their measured timing budget."
)
ORACLE = (
    "The preview degrades visibly and source cadence remains intact until a "
    "separately documented capture limit is reached."
)
MUTANT = "Lower recording resolution without changing the active mode label."
DECLARED_PATH = "declared"
MUTANT_PATH = "silent-resolution"
PATHS = (DECLARED_PATH, MUTANT_PATH)
HOST_LIMIT = "host fixture does not qualify a physical S23 or measured capture cadence"
ORDER = (
    "reduce-monitoring",
    "lower-inference",
    "pause-effects",
    "stop-capture",
)
LOADS = ("idle", "increasing")
HEADROOM = ("available", "approaching-limit")
QUALITIES = ("full", "reduced", "monitoring-off")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[a-z0-9-]+$")
SIZE = re.compile(r"^[1-9][0-9]*x[1-9][0-9]*$")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "budget",
    "source",
    "preview",
    "steps",
}
BUDGET_KEYS = {
    "inferenceLoad",
    "timingHeadroom",
    "captureLimitDocumented",
    "captureLimitReached",
}
SOURCE_KEYS = {
    "modeLabel",
    "recordingResolution",
    "selectedResolution",
    "cadenceIntact",
    "midTake",
}
PREVIEW_KEYS = {"activeQuality", "recorded", "degradedVisibly"}
STEP_KEYS = {"id", "applied", "order"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "withheld", "preview_degraded", "capture_stopped"}
_FAULT_ORDER = (
    "degradation-order",
    "undocumented-capture-limit",
    "capture-stopped-early",
    "capture-not-stopped",
    "silent-resolution-drop",
    "preview-quality-unrecorded",
    "cadence-broken-before-limit",
    "preview-not-degraded",
)
_FAULT_REASONS = {
    "degradation-order": "degradation order was not honored",
    "undocumented-capture-limit": "capture limit was reached without a separate document",
    "capture-stopped-early": "capture stopped before its own safety limit",
    "capture-not-stopped": "documented capture limit was reached but capture was not stopped",
    "silent-resolution-drop": "recording resolution changed without changing the active mode label",
    "preview-quality-unrecorded": "preview quality was not recorded",
    "cadence-broken-before-limit": "source cadence broke before the documented capture limit",
    "preview-not-degraded": (
        "preview did not degrade visibly while inference load approached the timing budget"
    ),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def _choice(value: object, allowed: tuple[str, ...], label: str) -> str:
    require(isinstance(value, str) and value in allowed, label + " is unsupported")
    return value


def _token(value: object, label: str) -> str:
    require(isinstance(value, str) and TOKEN.fullmatch(value) is not None, label + " must be a token")
    return value


def _size(value: object, label: str) -> str:
    require(
        isinstance(value, str) and SIZE.fullmatch(value) is not None,
        label + " must look like 3840x2160",
    )
    return value


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is a P071 capture-priority fixture."""
    exact_keys(document, DOCUMENT_KEYS, "scheduler")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P071")
    require(document["mapId"] == MAP_ID, "mapId must be s23-capture-priority-scheduler-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "scheduler needs the P071 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    budget = exact_keys(document["budget"], BUDGET_KEYS, "budget")
    _choice(budget["inferenceLoad"], LOADS, "inferenceLoad")
    _choice(budget["timingHeadroom"], HEADROOM, "timingHeadroom")
    _bool(budget["captureLimitDocumented"], "captureLimitDocumented")
    _bool(budget["captureLimitReached"], "captureLimitReached")
    source = exact_keys(document["source"], SOURCE_KEYS, "source")
    _token(source["modeLabel"], "modeLabel")
    _size(source["recordingResolution"], "recordingResolution")
    _size(source["selectedResolution"], "selectedResolution")
    _bool(source["cadenceIntact"], "cadenceIntact")
    _bool(source["midTake"], "midTake")
    preview = exact_keys(document["preview"], PREVIEW_KEYS, "preview")
    _choice(preview["activeQuality"], QUALITIES, "activeQuality")
    _bool(preview["recorded"], "recorded")
    _bool(preview["degradedVisibly"], "degradedVisibly")
    steps = document["steps"]
    require(type(steps) is list and len(steps) == len(ORDER), "steps must list the four degradation actions")
    for index, raw in enumerate(steps):
        step = exact_keys(raw, STEP_KEYS, f"step {index}")
        require(step["id"] == ORDER[index], f"step {index} id must be {ORDER[index]}")
        require(type(step["order"]) is int and step["order"] == index + 1, f"step {index} order is wrong")
        _bool(step["applied"], f"step {step['id']} applied")


def _stress(document: dict) -> bool:
    budget = document["budget"]
    return budget["inferenceLoad"] == "increasing" and budget["timingHeadroom"] == "approaching-limit"


def scheduler_faults(document: dict, path: str = DECLARED_PATH) -> list[str]:
    """Return capture-priority faults. The mutant never clears them."""
    validate_document(document)
    require(path in PATHS, "path must be declared or silent-resolution")
    steps = {step["id"]: step for step in document["steps"]}
    applied = [steps[name]["applied"] for name in ORDER]
    budget = document["budget"]
    source = document["source"]
    preview = document["preview"]
    limit = budget["captureLimitReached"]
    documented = budget["captureLimitDocumented"]
    stress = _stress(document)
    found: set[str] = set()
    for index, flag in enumerate(applied):
        if flag and not all(applied[:index]):
            found.add("degradation-order")
            break
    if (stress or limit) and not all(applied[:3]):
        found.add("degradation-order")
    if limit and not documented:
        found.add("undocumented-capture-limit")
    if applied[3] and not limit:
        found.add("capture-stopped-early")
    if limit and not applied[3]:
        found.add("capture-not-stopped")
    if source["recordingResolution"] != source["selectedResolution"] or path == MUTANT_PATH:
        found.add("silent-resolution-drop")
    if not preview["recorded"]:
        found.add("preview-quality-unrecorded")
    if stress and not limit and not source["cadenceIntact"]:
        found.add("cadence-broken-before-limit")
    if stress or limit:
        visible = preview["degradedVisibly"] and preview["activeQuality"] != "full"
        if not visible:
            found.add("preview-not-degraded")
    return [item for item in _FAULT_ORDER if item in found]


def _inventory(document: dict) -> list[str]:
    source = document["source"]
    preview = document["preview"]
    budget = document["budget"]
    preserved = [
        f"mode:{source['modeLabel']}",
        f"selected-resolution:{source['selectedResolution']}",
        f"recording-resolution:{source['recordingResolution']}",
        f"cadence-intact:{str(source['cadenceIntact']).lower()}",
        f"mid-take:{str(source['midTake']).lower()}",
        f"capture-limit-documented:{str(budget['captureLimitDocumented']).lower()}",
        f"capture-limit-reached:{str(budget['captureLimitReached']).lower()}",
        f"inference-load:{budget['inferenceLoad']}",
        f"timing-headroom:{budget['timingHeadroom']}",
        f"preview-quality:{preview['activeQuality']}",
        f"preview-recorded:{str(preview['recorded']).lower()}",
        f"preview-degraded:{str(preview['degradedVisibly']).lower()}",
    ]
    for step in document["steps"]:
        preserved.append(
            f"step:{step['id']}:order={step['order']}:applied={str(step['applied']).lower()}"
        )
    return preserved


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS, "unexpected decision")
    require(decision not in _FORBIDDEN, "P071 must not decide qualified or allowed")
    require(
        bool(reasons) and all(isinstance(item, str) and item for item in reasons),
        "reasons must be a non-empty list of strings",
    )
    for items in (rejected, preserved, questions):
        require(all(isinstance(item, str) and item for item in items), "result lists must be non-empty strings")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def assess(document: dict, path: str = DECLARED_PATH) -> dict:
    """Degrade preview before capture, and reject a silent resolution drop.

    ``path`` ``silent-resolution`` is the deliberate mutant. It lowers the
    recording resolution without changing the active mode label. That path
    stays ``rejected`` even when the fixture resolutions still match. The
    mode label, selected resolution, and preview quality remain in
    ``preservedResults``. The decision is never ``qualified`` or ``allowed``.
    """
    faults = scheduler_faults(document, path)
    source = document["source"]
    preview = document["preview"]
    budget = document["budget"]
    reasons = [ORACLE, METHOD]
    questions = [
        "host fixture is not a physical S23 measurement",
        HOST_LIMIT,
        f"active preview quality {preview['activeQuality']} stays in the inventory",
        f"selected mode {source['modeLabel']} stays in the inventory",
    ]
    for fault in faults:
        reasons.append(_FAULT_REASONS[fault])
    mutant = path == MUTANT_PATH
    if mutant:
        reasons.append(MUTANT)
        reasons.append("lowering recording resolution without relabeling the mode does not preserve cadence")
        questions.append("mutant silent resolution drop was rejected without erasing the selected mode")
    else:
        reasons.append("selected source mode was not altered by the declared scheduler")
    if budget["captureLimitReached"]:
        reasons.append("a capture limit flag is present on this fixture")
    else:
        reasons.append("the separately documented capture limit has not been reached")
    if preview["recorded"]:
        reasons.append(f"active preview quality {preview['activeQuality']} was recorded")
    reasons.append(HOST_LIMIT)
    preserved = _inventory(document)
    if faults:
        return _result("rejected", reasons, faults, preserved, questions)
    if budget["captureLimitReached"] and budget["captureLimitDocumented"]:
        reasons.append("capture stopped under its documented safety policy")
        reasons.append("source cadence remained intact until the capture limit")
        return _result("capture_stopped", reasons, [], preserved, questions)
    if _stress(document):
        reasons.append("preview degraded visibly and source cadence remained intact")
        return _result("preview_degraded", reasons, [], preserved, questions)
    questions.append("resource budget was not under the fixture stress, so the oracle was not applied")
    reasons.append("resource budget was not under the fixture stress")
    return _result("withheld", reasons, [], preserved, questions)
