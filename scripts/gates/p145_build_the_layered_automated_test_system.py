#!/usr/bin/env python3
"""P145 Build the layered automated test system.

Host fixture only. This module does not probe a device and does not qualify a
physical S23. Layers are host, jvm, android, gpu, and physical. Each layer has
passed, failed, and skipped counts.

Skipped tests are counted in skipped only. totalPassed and the honest
releasePassed equal the sum of per-layer passed counts and do not include
skipped. Adding skipped into a layer's passed count, or a caller releasePassed
that includes skipped, is rejected. The release summary lists every layer
separately. A missing physical layer is status not-run with passed 0, never
passed. The decision is recorded or rejected, never qualified or allowed.
"""

from __future__ import annotations

import copy
import hashlib
import math
import re
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P145"
WORKSTREAM = 19
TITLE = "Build the layered automated test system"
GOAL = "Separate host arithmetic, JVM policies, Android integration, GPU parity, and physical acceptance."
METHOD = (
    "Run fast deterministic contracts on every change, then focused integration suites and "
    "scheduled device experiments. Preserve failing evidence and classify unavailable hardware "
    "explicitly. Tests must call production interfaces or declared independent references, not "
    "duplicate trivial implementations."
)
FIXTURE = "A green host suite alongside an unavailable physical ten-bit codec test and a failing GPU color test."
ORACLE = (
    "The report keeps the GPU failure and unavailable device gate visible and does not declare "
    "the release fully qualified."
)
MUTANT = "Count skipped hardware tests as passing tests in the release summary."
DELIVERABLE = "Layered CI plan and machine-readable evidence aggregation"
DEPENDENCIES = ("P004", "P032", "P064", "P128", "P136", "P144")

OPEN_QUESTION = "physical S23 not run"
EVIDENCE_ID = "p145-layered-ci"
CLAIM = "layered-ci-evidence-aggregation"
LAYERS = ("host", "jvm", "android", "gpu", "physical")
HARDWARE_LAYERS = ("gpu", "physical")
OUTCOMES = frozenset({"passed", "failed", "skipped"})
ROW_KEYS = ("passed", "failed", "skipped", "status")
SUMMARY_ROW_KEYS = frozenset(ROW_KEYS)
COUNT_KEYS = ("passed", "failed", "skipped")
IMPORT_MAX_BYTES = 8_000_000
IMPORT_MAX_DIMENSION = 8192
IMPORT_MAX_EXPANSION = 8
COVERAGE_HIGH = 0.8
EXCELLENT_VISUAL = 0.9
GPU_COLOR_ID = "gpu-color"
PHYSICAL_CODEC_ID = "physical-ten-bit-codec"

SKIPPED_ADDED_INTO_PASSED = "skipped-added-into-passed"
RELEASE_PASSED_INCLUDES_SKIPPED = "release-passed-includes-skipped"
RELEASE_PASSED_MISMATCH = "release-passed-mismatch"
RELEASE_SUMMARY_MISSING_LAYER = "release-summary-missing-layer"
RELEASE_SUMMARY_NOT_LAYERED = "release-summary-not-layered"
RELEASE_SUMMARY_MISMATCH = "release-summary-mismatch"
MISSING_PHYSICAL_COUNTED_AS_PASSED = "missing-physical-counted-as-passed"
GPU_FAILURE_HIDDEN = "gpu-failure-hidden"
UNAVAILABLE_DEVICE_GATE_HIDDEN = "unavailable-device-gate-hidden"
LAYER_COUNT_MISMATCH = "layer-count-mismatch"
RESULT_CATEGORY_HIDDEN = "result-category-hidden"
RELEASE_FULLY_QUALIFIED = "release-fully-qualified"
COUNT_SKIPPED_HARDWARE_AS_PASSING = "count-skipped-hardware-tests-as-passing"

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "declaresQualified",
    "layers",
    "releasePassed",
    "releaseSummary",
}
EVALUATE_KEYS = {
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "declaresQualified",
    "layers",
    "releasePassed",
    "releaseSummary",
}
COMMON_CASE_KEYS = {"evidenceId", "repeat", "layers", "releasePassed", "releaseSummary"}
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
ID_TEXT = re.compile(r"^[a-z0-9][a-z0-9._-]{0,80}\Z")

FAULT_TEXT = {
    SKIPPED_ADDED_INTO_PASSED: "skipped tests were added into passed",
    RELEASE_PASSED_INCLUDES_SKIPPED: "releasePassed includes skipped tests",
    RELEASE_PASSED_MISMATCH: "releasePassed does not equal the sum of passed",
    RELEASE_SUMMARY_MISSING_LAYER: "a release summary must list each layer separately",
    RELEASE_SUMMARY_NOT_LAYERED: "a release summary must list each layer separately",
    RELEASE_SUMMARY_MISMATCH: "release summary does not match the layer results",
    MISSING_PHYSICAL_COUNTED_AS_PASSED: "a missing physical layer is not run, not passed",
    GPU_FAILURE_HIDDEN: "the GPU failure must stay visible",
    UNAVAILABLE_DEVICE_GATE_HIDDEN: "the unavailable device gate must stay visible",
    LAYER_COUNT_MISMATCH: "reported layer counts do not match test outcomes",
    RESULT_CATEGORY_HIDDEN: "passed, failed, and skipped must all stay visible",
    RELEASE_FULLY_QUALIFIED: ORACLE,
    COUNT_SKIPPED_HARDWARE_AS_PASSING: MUTANT,
}

FIXTURE_TESTS = {
    "host": (("host-arithmetic", "passed"), ("host-contract", "passed")),
    "jvm": (("jvm-policy", "passed"),),
    "android": (("android-integration", "passed"),),
    "gpu": ((GPU_COLOR_ID, "failed"), ("gpu-parity", "passed")),
    "physical": ((PHYSICAL_CODEC_ID, "skipped"),),
}

RETAINED_MEDIA_SHA256 = hashlib.sha256(b"p145-retained-take").hexdigest()


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


def require_int(value: object, label: str, minimum: int = 0) -> int:
    require(type(value) is int, label + " must be an int")
    require(value >= minimum, label + " is below " + str(minimum))
    return value


def require_number(value: object, label: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number",
    )
    number = float(value)
    require(math.isfinite(number), label + " must be finite")
    return number


def require_sha256(value: object, label: str) -> str:
    text = require_text(value, label)
    require(
        len(text) == 64 and all(character in "0123456789abcdefABCDEF" for character in text),
        label + " must be sha256 hex",
    )
    return text


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def path_escapes(path: str) -> bool:
    if path.startswith("/") or path.startswith("\\") or re.match(r"^[A-Za-z]:", path):
        return True
    parts = re.split(r"[\\/]+", path)
    return ".." in parts or path == ""


def fixture_layers() -> dict[str, list[dict[str, str]]]:
    layers: dict[str, list[dict[str, str]]] = {}
    for name in LAYERS:
        layers[name] = [{"id": test_id, "outcome": outcome} for test_id, outcome in FIXTURE_TESTS[name]]
    return layers


def _blank_counts() -> dict[str, int]:
    return {"passed": 0, "failed": 0, "skipped": 0}


def _status_for(name: str, present: bool, counts: dict[str, int]) -> str:
    del name
    if not present or (counts["passed"] == 0 and counts["failed"] == 0 and counts["skipped"] == 0):
        return "not-run"
    if counts["failed"] > 0:
        return "failed"
    if counts["passed"] == 0 and counts["skipped"] > 0:
        return "unavailable"
    if counts["skipped"] > 0:
        return "partial"
    return "passed"


def _is_skip_launder(actual: dict[str, int], reported: dict[str, int]) -> bool:
    moved = actual["skipped"] - reported["skipped"]
    return (
        moved > 0
        and reported["passed"] == actual["passed"] + moved
        and reported["failed"] == actual["failed"]
    )


def _parse_test(raw: Any, layer: str, seen: set[str]) -> dict[str, Any]:
    require(isinstance(raw, dict), layer + " test must be an object")
    unknown = set(raw) - {"id", "outcome", "unavailable"}
    require(not unknown, layer + " test has unexpected fields")
    require("id" in raw and "outcome" in raw, layer + " test requires id and outcome")
    test_id = require_text(raw["id"], layer + " test id")
    require(ID_TEXT.fullmatch(test_id) is not None, "test id is not a token")
    require(test_id not in seen, "duplicate test id " + test_id)
    seen.add(test_id)
    outcome = raw["outcome"]
    require(outcome in OUTCOMES, "outcome must be passed, failed, or skipped")
    unavailable = False
    if "unavailable" in raw:
        unavailable = require_bool(raw["unavailable"], "unavailable")
    if unavailable and outcome == "failed":
        raise ValueError("unavailable test cannot be failed")
    laundered = bool(unavailable and outcome == "passed")
    honest = "skipped" if laundered else outcome
    return {
        "id": test_id,
        "outcome": honest,
        "rawOutcome": outcome,
        "unavailable": unavailable,
        "laundered": laundered,
        "layer": layer,
    }


def _parse_reported(entry: dict, layer: str) -> dict[str, int] | None:
    present = [key for key in COUNT_KEYS if key in entry]
    if not present:
        return None
    require(len(present) == 3, layer + " counts must include passed, failed, and skipped")
    return {key: require_int(entry[key], layer + " " + key) for key in COUNT_KEYS}


def parse_layers(value: Any) -> dict[str, Any]:
    require(isinstance(value, dict), "layers must be an object")
    unknown = set(value) - set(LAYERS)
    require(not unknown, "unknown layer: " + ", ".join(sorted(unknown)))
    tests: dict[str, list[dict[str, Any]]] = {}
    reported: dict[str, dict[str, int] | None] = {}
    present: dict[str, bool] = {}
    seen: set[str] = set()
    for name in LAYERS:
        if name not in value:
            tests[name] = []
            reported[name] = None
            present[name] = False
            continue
        entry = value[name]
        present[name] = True
        if isinstance(entry, list):
            raw_tests = entry
            reported[name] = None
        elif isinstance(entry, dict):
            require("tests" in entry, name + " layer requires tests")
            unknown_fields = set(entry) - {"tests", *COUNT_KEYS}
            require(not unknown_fields, name + " layer has unexpected fields")
            raw_tests = entry["tests"]
            require(isinstance(raw_tests, list), name + " tests must be a list")
            reported[name] = _parse_reported(entry, name)
        else:
            raise ValueError(name + " layer must be a list or an object")
        tests[name] = [_parse_test(item, name, seen) for item in raw_tests]
    return {"tests": tests, "reported": reported, "present": present}


def _layer_public(tests: list[dict[str, Any]], present: bool, name: str) -> dict[str, Any]:
    counts = _blank_counts()
    ids = {key: [] for key in COUNT_KEYS}
    for test in tests:
        outcome = test["outcome"]
        counts[outcome] += 1
        ids[outcome].append(test["id"])
    status = _status_for(name, present, counts)
    return {
        "passed": counts["passed"],
        "failed": counts["failed"],
        "skipped": counts["skipped"],
        "status": status,
        "passedIds": ids["passed"],
        "failedIds": ids["failed"],
        "skippedIds": ids["skipped"],
    }


def count_rows(parsed: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        name: _layer_public(parsed["tests"][name], parsed["present"][name], name)
        for name in LAYERS
    }


def total_passed(rows: dict[str, dict[str, Any]]) -> int:
    """Sum of per-layer passed counts. Skipped tests are not included."""
    return sum(rows[name]["passed"] for name in LAYERS)


def total_failed(rows: dict[str, dict[str, Any]]) -> int:
    return sum(rows[name]["failed"] for name in LAYERS)


def total_skipped(rows: dict[str, dict[str, Any]]) -> int:
    return sum(rows[name]["skipped"] for name in LAYERS)


def summary_rows(rows: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        name: {key: rows[name][key] for key in ROW_KEYS}
        for name in LAYERS
    }


def honest_release_summary(layers: Any) -> dict[str, dict[str, Any]]:
    return summary_rows(count_rows(parse_layers(layers)))


def honest_release_passed(layers: Any) -> int:
    return total_passed(count_rows(parse_layers(layers)))


def _reported_faults(parsed: dict[str, Any], rows: dict[str, dict[str, Any]]) -> list[str]:
    faults: list[str] = []
    for name in LAYERS:
        for test in parsed["tests"][name]:
            if test["laundered"]:
                faults.append(SKIPPED_ADDED_INTO_PASSED)
                break
        reported = parsed["reported"][name]
        if reported is None:
            continue
        actual = {key: rows[name][key] for key in COUNT_KEYS}
        if reported == actual:
            continue
        if _is_skip_launder(actual, reported):
            faults.append(SKIPPED_ADDED_INTO_PASSED)
        else:
            faults.append(LAYER_COUNT_MISMATCH)
    return faults


def _release_passed_fault(release_passed: int, passed: int, skipped: int, hardware_skipped: int) -> list[str]:
    if release_passed == passed:
        return []
    includes_hardware = (
        hardware_skipped > 0
        and release_passed > passed
        and release_passed - passed <= hardware_skipped
    )
    includes_any_skip = skipped > 0 and release_passed > passed and release_passed - passed <= skipped
    if includes_hardware or includes_any_skip:
        return [RELEASE_PASSED_INCLUDES_SKIPPED]
    return [RELEASE_PASSED_MISMATCH]


def _parse_summary_row(raw: Any, name: str) -> dict[str, Any] | None:
    require(isinstance(raw, dict), name + " summary row must be an object")
    if not SUMMARY_ROW_KEYS <= set(raw):
        return None
    unknown = set(raw) - SUMMARY_ROW_KEYS
    require(not unknown, name + " summary row has unexpected fields")
    return {
        "passed": require_int(raw["passed"], name + " summary passed"),
        "failed": require_int(raw["failed"], name + " summary failed"),
        "skipped": require_int(raw["skipped"], name + " summary skipped"),
        "status": require_text(raw["status"], name + " summary status"),
    }


def _summary_faults(caller: Any, rows: dict[str, dict[str, Any]]) -> list[str]:
    require(isinstance(caller, dict), "releaseSummary must be an object")
    faults: list[str] = []
    known = [name for name in LAYERS if name in caller]
    if len(known) != len(LAYERS):
        if not known:
            faults.append(RELEASE_SUMMARY_NOT_LAYERED)
        else:
            faults.append(RELEASE_SUMMARY_MISSING_LAYER)
        if "physical" not in caller:
            faults.append(UNAVAILABLE_DEVICE_GATE_HIDDEN)
    extra = set(caller) - set(LAYERS)
    if extra and known:
        raise ValueError("releaseSummary has unknown layer: " + ", ".join(sorted(extra)))
    for name in known:
        parsed = _parse_summary_row(caller[name], name)
        if parsed is None:
            faults.append(RESULT_CATEGORY_HIDDEN)
            continue
        actual = {key: rows[name][key] for key in ROW_KEYS}
        counts_differ = any(parsed[key] != actual[key] for key in COUNT_KEYS)
        if counts_differ and _is_skip_launder(actual, parsed):
            faults.append(SKIPPED_ADDED_INTO_PASSED)
        elif counts_differ or parsed["status"] != actual["status"]:
            faults.append(RELEASE_SUMMARY_MISMATCH)
        if name == "physical" and actual["status"] == "not-run" and (
            parsed["status"] == "passed" or parsed["passed"] > 0
        ):
            faults.append(MISSING_PHYSICAL_COUNTED_AS_PASSED)
        if name == "gpu" and actual["failed"] > 0 and (parsed["failed"] == 0 or parsed["status"] == "passed"):
            faults.append(GPU_FAILURE_HIDDEN)
        if (
            name == "physical"
            and actual["status"] in {"not-run", "unavailable"}
            and parsed["status"] in {"passed", "qualified"}
        ):
            faults.append(UNAVAILABLE_DEVICE_GATE_HIDDEN)
    return faults


def visibility_reasons(rows: dict[str, dict[str, Any]]) -> list[str]:
    reasons: list[str] = []
    gpu_failed = rows["gpu"]["failedIds"]
    if gpu_failed:
        reasons.append("gpu failure visible: " + ",".join(gpu_failed))
    physical = rows["physical"]
    if physical["status"] == "not-run":
        reasons.append("physical layer not run")
        reasons.append("unavailable device gate visible: physical not-run")
    elif physical["skippedIds"]:
        reasons.append("unavailable device gate visible: " + ",".join(physical["skippedIds"]))
    passed = total_passed(rows)
    skipped = total_skipped(rows)
    reasons.append("total passed " + str(passed) + " excludes skipped " + str(skipped))
    reasons.append("release summary lists " + ", ".join(LAYERS))
    return reasons


def public_summary(rows: dict[str, dict[str, Any]], caller_release_passed: int) -> dict[str, Any]:
    passed = total_passed(rows)
    failed = total_failed(rows)
    skipped = total_skipped(rows)
    require(passed == sum(rows[name]["passed"] for name in LAYERS), "total passed drifted")
    require(
        passed + skipped == sum(rows[name]["passed"] + rows[name]["skipped"] for name in LAYERS),
        "skipped leaked into passed",
    )
    summary = {
        "layers": {
            name: {
                "passed": rows[name]["passed"],
                "failed": rows[name]["failed"],
                "skipped": rows[name]["skipped"],
                "status": rows[name]["status"],
                "passedIds": list(rows[name]["passedIds"]),
                "failedIds": list(rows[name]["failedIds"]),
                "skippedIds": list(rows[name]["skippedIds"]),
            }
            for name in LAYERS
        },
        "totalPassed": passed,
        "totalFailed": failed,
        "totalSkipped": skipped,
        "releasePassed": passed,
        "callerReleasePassed": caller_release_passed,
        "skippedIncludedInPassed": False,
        "qualified": False,
        "physicalNotRun": rows["physical"]["status"] == "not-run",
    }
    require(set(summary["layers"]) == set(LAYERS), "release summary dropped a layer")
    require(summary["qualified"] is False, "summary must not qualify the release")
    return summary


def analyze(
    layers: Any,
    release_passed: int,
    release_summary: Any,
    *,
    apply_mutant: bool = False,
    declares_qualified: bool = False,
) -> dict[str, Any]:
    parsed = parse_layers(layers)
    rows = count_rows(parsed)
    faults = _reported_faults(parsed, rows)
    hardware_skipped = sum(rows[name]["skipped"] for name in HARDWARE_LAYERS)
    faults.extend(_release_passed_fault(
        release_passed,
        total_passed(rows),
        total_skipped(rows),
        hardware_skipped,
    ))
    faults.extend(_summary_faults(release_summary, rows))
    if declares_qualified:
        faults.append(RELEASE_FULLY_QUALIFIED)
    if apply_mutant:
        faults.append(COUNT_SKIPPED_HARDWARE_AS_PASSING)
    index = {test["id"]: test for name in LAYERS for test in parsed["tests"][name]}
    return {
        "faults": dedupe(faults),
        "reasons": visibility_reasons(rows),
        "summary": public_summary(rows, release_passed),
        "rows": rows,
        "index": index,
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
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
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
    require(OPEN_QUESTION in result["openQuestions"], "physical S23 not run must be noted")
    require(result["reasons"], "reasons must be retained")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    return result


def _phase_reasons(info: dict[str, Any], *, repeat: str | None) -> list[str]:
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "goal: " + GOAL,
        "method: " + METHOD,
        "fixture: " + FIXTURE,
        "oracle: " + ORACLE,
    ]
    if repeat is not None:
        reasons.append("repeat " + repeat)
    reasons.extend(info["reasons"])
    return reasons


def _finish_analyzed(
    case_id: str,
    evidence: str,
    claim: str,
    info: dict[str, Any],
    *,
    repeat: str | None,
    phase_preamble: bool,
) -> dict[str, Any]:
    reasons = _phase_reasons(info, repeat=repeat) if phase_preamble else list(info["reasons"])
    ordered = info["faults"]
    for token in ordered:
        reasons.append(FAULT_TEXT.get(token, token))
    if COUNT_SKIPPED_HARDWARE_AS_PASSING in ordered:
        reasons.append("mutant rejected: " + MUTANT)
    if not ordered:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("layered results recorded; release is not qualified")
    questions = list(NON_CLAIM_QUESTIONS)
    if repeat is not None:
        questions.append(repeat)
    preserved = [evidence, info["summary"], claim]
    return assemble(case_id, ordered, reasons, preserved, questions, evidence)


def fixture_document() -> dict[str, Any]:
    layers = fixture_layers()
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "declaresQualified": False,
        "layers": layers,
        "releasePassed": honest_release_passed(layers),
        "releaseSummary": honest_release_summary(layers),
    }


def assess(document: dict) -> dict[str, Any]:
    """Record an honest layered report, or reject skip laundering and qualification."""
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
    declares_qualified = require_bool(document["declaresQualified"], "declaresQualified")
    release_passed = require_int(document["releasePassed"], "releasePassed")
    info = analyze(
        document["layers"],
        release_passed,
        document["releaseSummary"],
        apply_mutant=apply_mutant,
        declares_qualified=declares_qualified,
    )
    return _finish_analyzed(PHASE, evidence, claim, info, repeat=None, phase_preamble=True)


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate one layered report. Same counts as assess, with an explicit repeat."""
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == EVALUATE_KEYS, "invalid payload keys")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    repeat = require_text(payload["repeat"], "repeat")
    claim = require_text(payload["claim"], "claim")
    apply_mutant = require_bool(payload["applyMutant"], "applyMutant")
    declares_qualified = require_bool(payload["declaresQualified"], "declaresQualified")
    release_passed = require_int(payload["releasePassed"], "releasePassed")
    info = analyze(
        payload["layers"],
        release_passed,
        payload["releaseSummary"],
        apply_mutant=apply_mutant,
        declares_qualified=declares_qualified,
    )
    return _finish_analyzed(PHASE, evidence, claim, info, repeat=repeat, phase_preamble=True)


def begin_layers(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(COMMON_CASE_KEYS) | set(extra_keys), "invalid payload keys")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    repeat = require_text(payload["repeat"], "repeat")
    release_passed = require_int(payload["releasePassed"], "releasePassed")
    info = analyze(payload["layers"], release_passed, payload["releaseSummary"])
    return {
        "evidence": evidence,
        "repeat": repeat,
        "faults": list(info["faults"]),
        "reasons": list(info["reasons"]),
        "summary": info["summary"],
        "rows": info["rows"],
        "index": info["index"],
    }


def finish_layers(
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
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        case["expected"],
        "repeat " + bundle["repeat"],
    ]
    reasons.extend(bundle["reasons"])
    ordered = dedupe(faults)
    for token in ordered:
        reasons.append(text.get(token, token))
    if not ordered:
        reasons.append("layered results recorded; release is not qualified")
    preserved = [bundle["evidence"], bundle["summary"], *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], ordered, reasons, preserved, questions, bundle["evidence"])


def layer_fields(layers: Any | None = None) -> dict[str, Any]:
    chosen = fixture_layers() if layers is None else copy.deepcopy(layers)
    return {
        "layers": chosen,
        "releasePassed": honest_release_passed(chosen),
        "releaseSummary": honest_release_summary(chosen),
    }
