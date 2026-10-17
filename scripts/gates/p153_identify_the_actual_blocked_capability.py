#!/usr/bin/env python3
"""P153 Identify the actual blocked capability.

Host reference only. This module does not probe a device and does not qualify
a physical S23. A hypothesis names a capability, a measurement_id or null,
observed_fps, advertised_fps, and a blame of app, codec, thermal, firmware, or
unknown. Blaming firmware or Samsung while measurement_id is null is rejected.
A concrete question is recorded only when the capability and the missing
measurement are both named. Low fps alone is not proof of a restriction: an
unmeasured fps drop cannot prove a firmware restriction, a Samsung restriction,
or any vendor block. The fixture is a RAW route limited by measured disk
throughput, so the plan must address storage and buffering, and an application
path, before any firmware modification. The decision is never qualified.
"""

from __future__ import annotations

import math
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P153"
WORKSTREAM = 20
TITLE = "Identify the actual blocked capability"
GOAL = "State a concrete research question before proposing firmware work."
METHOD = (
    "Use current public diagnostics and failed qualified app experiments to locate the "
    "bottleneck: sensor stream, HAL exposure, codec interface, synchronization, or app "
    "performance. Specify the desired observation and an alternative application-level "
    "path. Avoid vague goals such as unlock everything."
)
FIXTURE = "A RAW route limited by measured disk throughput rather than a denied camera mode."
ORACLE = "The research plan addresses storage and buffering before proposing a firmware modification."
MUTANT = "Attribute every low frame rate to Samsung restrictions without measurements."
DELIVERABLE = "Blocked-capability hypothesis and evidence dossier"
DEPENDENCIES = ("P008", "P016", "P040", "P152")
SLUG = "identify_the_actual_blocked_capability"

HYPOTHESIS_RULE = (
    "A hypothesis has capability, measurement_id or null, observed_fps, advertised_fps, "
    "and blamed (app, codec, thermal, firmware, unknown). Blaming firmware or Samsung "
    "with measurement_id null is rejected. A concrete question is recorded only when "
    "capability and the missing measurement are named. Low fps alone is not proof of a "
    "restriction. An unmeasured fps drop cannot prove a firmware restriction, a Samsung "
    "restriction, or any vendor block. The decision is never qualified."
)
UNMEASURED_FPS_CANNOT_PROVE = (
    "a firmware restriction, a Samsung restriction, or any vendor block"
)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p153-blocked-capability"
CLAIM = "blocked-capability-hypothesis-host-reference"

BLAMES = frozenset({"app", "codec", "thermal", "firmware", "unknown"})
ADDRESSES = frozenset({
    "storage",
    "buffering",
    "firmware",
    "app",
    "codec",
    "thermal",
    "sensor-stream",
    "hal",
    "synchronization",
    "alternative-app-path",
})
LIMITER_CAUSES = frozenset({
    "disk-throughput",
    "denied-camera-mode",
    "scheduling",
    "codec",
    "thermal",
    "sensor-stream",
    "unknown",
})

UNMEASURED_FIRMWARE = "unmeasured-firmware-blame"
UNMEASURED_SAMSUNG = "unmeasured-samsung-blame"
LOW_FPS_ALONE = "low-fps-alone-is-not-a-restriction"
RESTRICTION_UNMEASURED = "restriction-without-measurement"
UNNAMED_CONCRETE = "unnamed-concrete-question"
VAGUE_UNLOCK = "vague-unlock-everything"
CONCRETE_MISSING = "concrete-question-missing"
QUESTION_NOT_HYPOTHESIZED = "question-capability-not-hypothesized"
FIRMWARE_BEFORE_STORAGE = "firmware-before-storage-and-buffering"
DISK_UNMEASURED = "disk-throughput-unmeasured"
LIMITER_NOT_DISK = "limiter-is-not-measured-disk-throughput"
ROUTE_NOT_RAW = "raw-route-required"
ALTERNATIVE_MISSING = "alternative-application-path-missing"
MUTANT_FPS = "unmeasured-samsung-fps-attribution"

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
    "hypotheses",
    "questions",
    "plan",
    "limiter",
    "applyMutant",
}
CORE_KEYS = {
    "evidenceId",
    "claim",
    "hypotheses",
    "questions",
    "plan",
    "limiter",
    "applyMutant",
}
CASE_COMMON_KEYS = CORE_KEYS | {"repeat"}
HYPOTHESIS_KEYS = {
    "capability",
    "measurement_id",
    "observed_fps",
    "advertised_fps",
    "blamed",
    "vendor",
    "claims_restriction",
}
QUESTION_KEYS = {"capability", "missing_measurement", "text", "concrete"}
PLAN_KEYS = {"id", "addresses"}
LIMITER_KEYS = {"route", "cause", "measurement_id"}

CASES = (
    {
        "id": "TC-P153-01",
        "phase": "P153",
        "workstream": 20,
        "name": "Wrong bottleneck attribution",
        "intervention": "Present a throughput problem caused by storage or scheduling as evidence of a hidden firmware restriction.",
        "expected": "Require controlled isolation of the bottleneck before low-level modification is proposed.",
        "negative": "Assuming every slow path is vendor blocking must fail.",
        "repeat": "Repeat acquisition-only, saved-source, development, and encoder-stage measurements.",
    },
    {
        "id": "TC-P153-02",
        "phase": "P153",
        "workstream": 20,
        "name": "Incomplete public source",
        "intervention": "Provide a public kernel or firmware-related package that omits proprietary imaging components.",
        "expected": "Describe exactly what can be inspected and keep missing components unknown.",
        "negative": "A source archive must not be called a complete camera firmware implementation without evidence.",
        "repeat": "Repeat different device variants and software versions.",
    },
    {
        "id": "TC-P153-03",
        "phase": "P153",
        "workstream": 20,
        "name": "Unexplored reversible alternative",
        "intervention": "Fail one codec or camera interface while another public route remains untested.",
        "expected": "Evaluate plausible reversible alternatives before declaring the broader capture goal blocked.",
        "negative": "One failed P010 route must not prove all ten-bit encoding impossible.",
        "repeat": "Repeat surface input, reduced geometry, deferred processing, and scheduling changes.",
    },
    {
        "id": "TC-P153-04",
        "phase": "P153",
        "workstream": 20,
        "name": "Missing explicit modification authorization",
        "intervention": "Prepare a flashing or irreversible device-change step without fresh specific user approval.",
        "expected": "Keep the operation unexecuted and continue non-destructive application work.",
        "negative": "A general app-development request does not authorize an irreversible flash.",
        "repeat": "Repeat bootloader changes, security-state changes, and unverified recovery images.",
    },
    {
        "id": "TC-P153-05",
        "phase": "P153",
        "workstream": 20,
        "name": "Advertised unlock without delivery",
        "intervention": "Change reported capability metadata but obtain no valid new sensor output.",
        "expected": "Fail the acquisition hypothesis despite the expanded mode menu.",
        "negative": "A newly visible setting is not proof of useful capture.",
        "repeat": "Repeat sample receipt, decoded fidelity, sustained cadence, and thermal checks.",
    },
    {
        "id": "TC-P153-06",
        "phase": "P153",
        "workstream": 20,
        "name": "Computational capture overclaim",
        "intervention": "Merge multiple exposures and present the result as a single unchanged sensor exposure.",
        "expected": "Label computational acquisition and measure motion artifacts and retained information separately.",
        "negative": "An attractive merge cannot erase its source-sampling provenance.",
        "repeat": "Repeat moving subjects, clipped channels, alignment failures, and temporal ghosts.",
    },
    {
        "id": "TC-P153-07",
        "phase": "P153",
        "workstream": 20,
        "name": "Advanced model cost regression",
        "intervention": "Adopt a larger research model that improves one artifact but exceeds practical memory or time budgets.",
        "expected": "Report the quality-cost tradeoff and retain the stable baseline until the adoption gate passes.",
        "negative": "A leaderboard position alone cannot justify replacement.",
        "repeat": "Repeat difficult-scene quality, sustained device load, and deferred job interruption.",
    },
    {
        "id": "TC-P153-08",
        "phase": "P153",
        "workstream": 20,
        "name": "Unreproducible research closure",
        "intervention": "Archive only favorable outputs while omitting failed experiments and essential setup details.",
        "expected": "Preserve enough evidence to reconstruct decisions and reproduce qualified results independently.",
        "negative": "A promotional reel cannot substitute for an engineering archive.",
        "repeat": "Repeat fresh-maintainer reproduction of capture, film rendering, optics, and rejected hypotheses.",
    },
)

FAULT_TEXT = {
    UNMEASURED_FIRMWARE: "blaming firmware with measurement_id null is rejected",
    UNMEASURED_SAMSUNG: "blaming Samsung with measurement_id null is rejected",
    LOW_FPS_ALONE: "low fps alone is not proof of a restriction",
    RESTRICTION_UNMEASURED: "a restriction claim without a measurement_id is rejected",
    UNNAMED_CONCRETE: (
        "a concrete question is recorded only when capability and the missing measurement are named"
    ),
    VAGUE_UNLOCK: "vague goals such as unlock everything are not a research question",
    CONCRETE_MISSING: "no concrete question names both a capability and the missing measurement",
    QUESTION_NOT_HYPOTHESIZED: "the questioned capability is not one of the stated hypotheses",
    FIRMWARE_BEFORE_STORAGE: ORACLE,
    DISK_UNMEASURED: "disk throughput was named without a measurement_id",
    LIMITER_NOT_DISK: FIXTURE,
    ROUTE_NOT_RAW: FIXTURE,
    ALTERNATIVE_MISSING: "an alternative application-level path must be specified before firmware work",
    MUTANT_FPS: MUTANT,
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


def require_optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return require_text(value, label)


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
    require(math.isfinite(number), label + " must be finite")
    return number


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def is_samsung(vendor: str | None) -> bool:
    return vendor is not None and vendor.casefold() == "samsung"


def is_vague(value: str | None) -> bool:
    return value is not None and value.casefold() == "unlock everything"


def question_named(question: dict[str, Any]) -> bool:
    if question["capability"] is None or question["missing_measurement"] is None:
        return False
    if is_vague(question["capability"]) or is_vague(question["text"]):
        return False
    return True


def question_record(question: dict[str, Any]) -> str:
    return question["capability"] + " missing " + question["missing_measurement"]


def display_number(value: object) -> int | float:
    if type(value) is int:
        return value
    return float(value)


def require_str_list(value: object, label: str, *, allow_empty: bool) -> list[str]:
    require(isinstance(value, list), label + " must be a list")
    if not allow_empty:
        require(bool(value), label + " must be non-empty")
    items = [require_text(item, f"{label}[{index}]") for index, item in enumerate(value)]
    require(len(items) == len(set(items)), label + " entries must be unique")
    return items


def parse_hypothesis(value: object, index: int) -> dict[str, Any]:
    label = f"hypotheses[{index}]"
    require(isinstance(value, dict), label + " must be an object")
    require(set(value) == HYPOTHESIS_KEYS, label + " keys are invalid")
    capability = require_text(value["capability"], label + ".capability")
    measurement_id = require_optional_text(value["measurement_id"], label + ".measurement_id")
    observed = require_number(value["observed_fps"], label + ".observed_fps")
    advertised = require_number(value["advertised_fps"], label + ".advertised_fps")
    require(observed >= 0, label + ".observed_fps must be >= 0")
    require(advertised >= 0, label + ".advertised_fps must be >= 0")
    blamed = require_text(value["blamed"], label + ".blamed")
    require(blamed in BLAMES, label + ".blamed is not a recognized blame")
    vendor = require_optional_text(value["vendor"], label + ".vendor")
    claims = require_bool(value["claims_restriction"], label + ".claims_restriction")
    return {
        "capability": capability,
        "measurement_id": measurement_id,
        "observed_fps": display_number(value["observed_fps"]),
        "advertised_fps": display_number(value["advertised_fps"]),
        "observed_value": observed,
        "advertised_value": advertised,
        "blamed": blamed,
        "vendor": vendor,
        "claims_restriction": claims,
    }


def parse_hypotheses(value: object) -> list[dict[str, Any]]:
    require(isinstance(value, list) and bool(value), "hypotheses must be a non-empty list")
    rows = [parse_hypothesis(item, index) for index, item in enumerate(value)]
    return rows


def parse_question(value: object, index: int) -> dict[str, Any]:
    label = f"questions[{index}]"
    require(isinstance(value, dict), label + " must be an object")
    require(set(value) == QUESTION_KEYS, label + " keys are invalid")
    return {
        "capability": require_optional_text(value["capability"], label + ".capability"),
        "missing_measurement": require_optional_text(
            value["missing_measurement"], label + ".missing_measurement"
        ),
        "text": require_text(value["text"], label + ".text"),
        "concrete": require_bool(value["concrete"], label + ".concrete"),
    }


def parse_questions(value: object) -> list[dict[str, Any]]:
    require(isinstance(value, list), "questions must be a list")
    return [parse_question(item, index) for index, item in enumerate(value)]


def parse_plan(value: object) -> list[dict[str, str]]:
    require(isinstance(value, list) and bool(value), "plan must be a non-empty list")
    steps = []
    for index, item in enumerate(value):
        label = f"plan[{index}]"
        require(isinstance(item, dict), label + " must be an object")
        require(set(item) == PLAN_KEYS, label + " keys are invalid")
        step_id = require_text(item["id"], label + ".id")
        addresses = require_text(item["addresses"], label + ".addresses")
        require(addresses in ADDRESSES, label + ".addresses is not recognized")
        steps.append({"id": step_id, "addresses": addresses})
    ids = [step["id"] for step in steps]
    require(len(ids) == len(set(ids)), "plan ids must be unique")
    return steps


def parse_limiter(value: object) -> dict[str, Any]:
    require(isinstance(value, dict), "limiter must be an object")
    require(set(value) == LIMITER_KEYS, "limiter keys are invalid")
    cause = require_text(value["cause"], "limiter.cause")
    require(cause in LIMITER_CAUSES, "limiter.cause is not recognized")
    return {
        "route": require_text(value["route"], "limiter.route"),
        "cause": cause,
        "measurement_id": require_optional_text(value["measurement_id"], "limiter.measurement_id"),
    }


def _hypothesis_faults(row: dict[str, Any]) -> list[str]:
    faults: list[str] = []
    if row["blamed"] == "firmware" and row["measurement_id"] is None:
        faults.append(UNMEASURED_FIRMWARE)
    if is_samsung(row["vendor"]) and row["measurement_id"] is None:
        faults.append(UNMEASURED_SAMSUNG)
    drop = row["observed_value"] < row["advertised_value"]
    if row["claims_restriction"] and row["measurement_id"] is None:
        faults.append(LOW_FPS_ALONE if drop else RESTRICTION_UNMEASURED)
    return faults


def _question_faults(questions: list[dict[str, Any]], capabilities: set[str]) -> tuple[list[str], list[str]]:
    faults: list[str] = []
    concrete: list[str] = []
    for question in questions:
        if is_vague(question["text"]) or is_vague(question["capability"]):
            faults.append(VAGUE_UNLOCK)
        named = question_named(question)
        if question["concrete"] and not named:
            faults.append(UNNAMED_CONCRETE)
        if not named:
            continue
        record = question_record(question)
        concrete.append(record)
        if question["capability"] not in capabilities:
            faults.append(QUESTION_NOT_HYPOTHESIZED)
    if not concrete:
        faults.append(CONCRETE_MISSING)
    return faults, concrete


def _plan_faults(plan: list[dict[str, str]], limiter: dict[str, Any]) -> list[str]:
    faults: list[str] = []
    if limiter["route"].casefold() != "raw":
        faults.append(ROUTE_NOT_RAW)
    if limiter["cause"] != "disk-throughput":
        faults.append(LIMITER_NOT_DISK)
        return faults
    if limiter["measurement_id"] is None:
        faults.append(DISK_UNMEASURED)
    addresses = [step["addresses"] for step in plan]
    if "alternative-app-path" not in addresses:
        faults.append(ALTERNATIVE_MISSING)
    has_storage = "storage" in addresses
    has_buffering = "buffering" in addresses
    if not has_storage or not has_buffering:
        faults.append(FIRMWARE_BEFORE_STORAGE)
        return faults
    if "firmware" not in addresses:
        return faults
    firmware_at = addresses.index("firmware")
    if firmware_at < addresses.index("storage") or firmware_at < addresses.index("buffering"):
        faults.append(FIRMWARE_BEFORE_STORAGE)
    return faults


def analyze_computation(
    hypotheses: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    plan: list[dict[str, str]],
    limiter: dict[str, Any],
    apply_mutant: bool,
) -> dict[str, Any]:
    faults: list[str] = []
    for row in hypotheses:
        faults.extend(_hypothesis_faults(row))
    capabilities = {row["capability"] for row in hypotheses}
    question_faults, concrete = _question_faults(questions, capabilities)
    faults.extend(question_faults)
    faults.extend(_plan_faults(plan, limiter))
    drops = [row for row in hypotheses if row["observed_value"] < row["advertised_value"]]
    if apply_mutant and drops:
        faults.append(MUTANT_FPS)
    snapshot = {
        "fpsDrops": [
            {
                "capability": row["capability"],
                "measurement_id": row["measurement_id"],
                "observed_fps": row["observed_fps"],
                "advertised_fps": row["advertised_fps"],
                "blamed": row["blamed"],
                "vendor": row["vendor"],
                "claims_restriction": row["claims_restriction"],
            }
            for row in drops
        ],
        "concreteQuestions": list(concrete),
        "unnamedQuestions": len(questions) - len(concrete),
        "plan": [step["addresses"] for step in plan],
        "limiterCause": limiter["cause"],
        "limiterMeasurement": limiter["measurement_id"],
        "route": limiter["route"],
        "unmeasuredFpsCannotProve": UNMEASURED_FPS_CANNOT_PROVE,
        "mutantAttributedLowFps": bool(apply_mutant and drops),
    }
    extra_reasons = [
        "hypothesis rule: " + HYPOTHESIS_RULE,
        "an unmeasured fps drop cannot prove " + UNMEASURED_FPS_CANNOT_PROVE,
    ]
    if concrete:
        extra_reasons.append("concrete questions: " + "; ".join(concrete))
    if snapshot["mutantAttributedLowFps"]:
        extra_reasons.append("mutant rejected: " + MUTANT)
    return {
        "faults": dedupe(faults),
        "snapshot": snapshot,
        "extraReasons": extra_reasons,
        "concreteQuestions": concrete,
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
    require("physical S23 was not run" in " ".join(result["reasons"]), "physical run note missing")
    return result


def _core_from_mapping(mapping: dict, label: str) -> dict[str, Any]:
    evidence = require_text(mapping["evidenceId"], "evidenceId")
    claim = require_text(mapping["claim"], "claim")
    apply_mutant = require_bool(mapping["applyMutant"], "applyMutant")
    hypotheses = parse_hypotheses(mapping["hypotheses"])
    questions = parse_questions(mapping["questions"])
    plan = parse_plan(mapping["plan"])
    limiter = parse_limiter(mapping["limiter"])
    analysis = analyze_computation(hypotheses, questions, plan, limiter, apply_mutant)
    analysis["evidence"] = evidence
    analysis["claim"] = claim
    analysis["applyMutant"] = apply_mutant
    analysis["label"] = label
    analysis["hypotheses"] = hypotheses
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
        reasons.append("blocked-capability hypothesis recorded; not a physical qualification")
    return reasons


def _open_questions(concrete: list[str], extra: list[str] | None = None) -> list[str]:
    questions = list(NON_CLAIM_QUESTIONS) + list(concrete)
    if extra:
        questions.extend(extra)
    return questions


def assess(document: dict) -> dict[str, Any]:
    """Record a measured blocked-capability hypothesis, or reject an unmeasured blame."""
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
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(
        PHASE,
        analysis["faults"],
        reasons,
        preserved,
        _open_questions(analysis["concreteQuestions"]),
        analysis["evidence"],
    )


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a phase document or a core blocked-capability payload."""
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
    return assemble(
        PHASE,
        analysis["faults"],
        reasons,
        preserved,
        _open_questions(analysis["concreteQuestions"]),
        analysis["evidence"],
    )


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
        "hypotheses": analysis["hypotheses"],
        "concreteQuestions": list(analysis["concreteQuestions"]),
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
            case["id"] + " " + case["name"],
            "oracle: " + ORACLE,
            case["expected"],
            "repeat " + bundle["repeat"],
        ],
        fault_text,
    )
    preserved = [bundle["evidence"], bundle["snapshot"], bundle["claim"], *extra_preserved]
    questions = _open_questions(bundle["concreteQuestions"], [case["repeat"]])
    return assemble(case["id"], analysis["faults"], reasons, preserved, questions, bundle["evidence"])


def fixture_hypothesis(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "capability": "raw-route",
        "measurement_id": "disk-throughput-m1",
        "observed_fps": 8,
        "advertised_fps": 24,
        "blamed": "app",
        "vendor": None,
        "claims_restriction": False,
    }
    row.update(overrides)
    return row


def fixture_question(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "capability": "raw-route",
        "missing_measurement": "sustained-disk-write-megabytes-per-second",
        "text": "What sustained disk write rate limits the RAW route before any firmware change?",
        "concrete": True,
    }
    row.update(overrides)
    return row


def fixture_plan() -> list[dict[str, str]]:
    return [
        {"id": "buffer-depth", "addresses": "buffering"},
        {"id": "disk-throughput", "addresses": "storage"},
        {"id": "app-path", "addresses": "alternative-app-path"},
    ]


def fixture_limiter(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "route": "raw",
        "cause": "disk-throughput",
        "measurement_id": "disk-throughput-m1",
    }
    row.update(overrides)
    return row


def core_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "hypotheses": [fixture_hypothesis()],
        "questions": [fixture_question()],
        "plan": fixture_plan(),
        "limiter": fixture_limiter(),
        "applyMutant": False,
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
        "hypotheses": core["hypotheses"],
        "questions": core["questions"],
        "plan": core["plan"],
        "limiter": core["limiter"],
        "applyMutant": False,
    }
