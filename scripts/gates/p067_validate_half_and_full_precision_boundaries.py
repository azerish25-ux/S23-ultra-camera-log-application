#!/usr/bin/env python3
"""P067 half and full precision boundaries.

CPU double references are compared with GPU outputs for signed dark values,
bright highlights, matrix cancellation, and long accumulations. Overflow,
denormal handling, and texture conversion are part of the same differential.
A precision reduction is accepted only as an explicit graph decision whose
absolute error stays inside the declared budget, or the affected operation
is promoted.

The deliberate mutant — every intermediate replaced with FP16 without testing
accumulated error — is rejected. That replacement does not erase the
differential inventory. This module does not probe a device, does not qualify
a physical S23, and does not execute TC-P067-01 through TC-P067-08.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


PHASE = "P067"
CASE_ID = "P067"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-precision-boundary-fixture"
METHOD = (
    "Compare CPU double references with GPU outputs for signed dark values, bright highlights, "
    "matrix cancellation, and long accumulations. Test overflow, denormal handling, and texture "
    "conversion. Precision reductions must be explicit graph decisions with bounded error."
)
FIXTURE = (
    "A bright narrow highlight convolved with a large kernel and a near-neutral matrix cancellation case."
)
ORACLE = (
    "The chosen precision stays within the declared error budget or the graph promotes the affected operation."
)
MUTANT = "Replace every intermediate with FP16 without testing accumulated error."
DECLARED_PATH = "declared"
MUTANT_PATH = "fp16-everywhere"
PATHS = (DECLARED_PATH, MUTANT_PATH)
REFERENCE = "cpu-double"
COMPARED = "gpu-output"
HOST_LIMIT = "host fixture does not qualify a physical S23 or a measured GPU precision boundary"
PRECISIONS = ("fp16", "fp32", "fp64")
PROBES = (
    "signed-dark",
    "bright-highlight",
    "highlight-kernel",
    "matrix-cancellation",
    "long-accumulation",
    "overflow",
    "denormal",
    "texture-conversion",
)
SIGNATURES = ("highlight-kernel", "matrix-cancellation")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[a-z0-9-]+$")
# Canonical signed decimal: no leading zeros, no trailing fractional zeros, not "-0".
_SIGNED = re.compile(
    r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])"
)
_UNSIGNED = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "suite",
    "operations",
}
SUITE_KEYS = {"reference", "compared", "framesProcessed"}
OPERATION_KEYS = {
    "id",
    "probe",
    "cpuDouble",
    "gpuOutput",
    "chosenPrecision",
    "requiredPrecision",
    "errorBudget",
    "explicitReduction",
    "accumulatedErrorTested",
    "promoted",
    "overflow",
    "denormal",
    "textureConversion",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "withheld", "precision_bounded"}
_RANK = {"fp16": 0, "fp32": 1, "fp64": 2}


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


def _signed(value: object, label: str) -> str:
    require(
        isinstance(value, str) and _SIGNED.fullmatch(value) is not None and value != "-0",
        label + " must be a canonical signed decimal",
    )
    return value


def _unsigned(value: object, label: str) -> str:
    require(
        isinstance(value, str) and _UNSIGNED.fullmatch(value) is not None,
        label + " must be a canonical non-negative decimal",
    )
    return value


def _canonical(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text.startswith("."):
        text = "0" + text
    if text.startswith("-."):
        text = "-0" + text[1:]
    if text in {"", "-0", "-"}:
        return "0"
    return text


def absolute_error(cpu: str, gpu: str) -> str:
    """Absolute difference between a CPU double reference and a GPU output."""
    return _canonical(abs(Decimal(cpu) - Decimal(gpu)))


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is a P067 precision-boundary fixture."""
    exact_keys(document, DOCUMENT_KEYS, "precision budget")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P067")
    require(document["mapId"] == MAP_ID, "mapId must be s23-precision-boundary-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "precision budget needs the P067 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    suite = exact_keys(document["suite"], SUITE_KEYS, "suite")
    require(suite["reference"] == REFERENCE, "suite reference must be cpu-double")
    require(suite["compared"] == COMPARED, "suite compared must be gpu-output")
    _bool(suite["framesProcessed"], "framesProcessed")
    operations = document["operations"]
    require(type(operations) is list, "operations must be a list")
    seen: set[str] = set()
    for index, raw in enumerate(operations):
        operation = exact_keys(raw, OPERATION_KEYS, f"operation {index}")
        op_id = operation["id"]
        require(isinstance(op_id, str) and TOKEN.fullmatch(op_id) is not None, f"operation {index} id must be a token")
        require(op_id not in seen, "duplicate operation id: " + op_id)
        seen.add(op_id)
        _choice(operation["probe"], PROBES, f"operation {op_id} probe")
        _signed(operation["cpuDouble"], f"operation {op_id} cpuDouble")
        _signed(operation["gpuOutput"], f"operation {op_id} gpuOutput")
        chosen = _choice(operation["chosenPrecision"], PRECISIONS, f"operation {op_id} chosenPrecision")
        required = _choice(operation["requiredPrecision"], PRECISIONS, f"operation {op_id} requiredPrecision")
        budget = _unsigned(operation["errorBudget"], f"operation {op_id} errorBudget")
        require(Decimal(budget) > 0, f"operation {op_id} errorBudget must be positive")
        explicit = _bool(operation["explicitReduction"], f"operation {op_id} explicitReduction")
        _bool(operation["accumulatedErrorTested"], f"operation {op_id} accumulatedErrorTested")
        _bool(operation["promoted"], f"operation {op_id} promoted")
        _bool(operation["overflow"], f"operation {op_id} overflow")
        _bool(operation["denormal"], f"operation {op_id} denormal")
        _bool(operation["textureConversion"], f"operation {op_id} textureConversion")
        if explicit and _RANK[chosen] >= _RANK[required]:
            raise ValueError(f"operation {op_id} explicitReduction requires a lower chosen precision")


def operation_faults(operation: dict) -> list[str]:
    """Return precision-budget faults. Untested FP16 is never within budget."""
    error = Decimal(absolute_error(operation["cpuDouble"], operation["gpuOutput"]))
    within = error <= Decimal(operation["errorBudget"])
    chosen = operation["chosenPrecision"]
    required = operation["requiredPrecision"]
    faults: list[str] = []
    if chosen == "fp16" and not operation["accumulatedErrorTested"]:
        faults.append("untested-fp16")
    if _RANK[chosen] < _RANK[required] and not operation["explicitReduction"]:
        faults.append("silent-reduction")
    if operation["promoted"] and chosen == "fp16":
        faults.append("false-promotion")
    if operation["overflow"] and (chosen == "fp16" or not operation["promoted"]):
        faults.append("unresolved-overflow")
    if operation["denormal"] and (chosen == "fp16" or not operation["promoted"]):
        faults.append("unresolved-denormal")
    if operation["textureConversion"] and chosen == "fp16" and not operation["explicitReduction"]:
        faults.append("silent-texture-conversion")
    if operation["textureConversion"] and not operation["accumulatedErrorTested"]:
        faults.append("untested-texture-conversion")
    if not within:
        faults.append("over-budget")
    return faults


def _status(operation: dict, faults: list[str]) -> str:
    if faults:
        return "rejected"
    if operation["promoted"]:
        return "promoted"
    return "within-budget"


def _flag(value: bool) -> str:
    return str(value).lower()


def _inventory(document: dict, statuses: dict[str, str]) -> list[str]:
    preserved: list[str] = []
    suite = document["suite"]
    preserved.append(
        "suite:reference="
        + suite["reference"]
        + ":compared="
        + suite["compared"]
        + ":frames-processed="
        + _flag(suite["framesProcessed"])
    )
    for operation in document["operations"]:
        error = absolute_error(operation["cpuDouble"], operation["gpuOutput"])
        preserved.append(
            f"op:{operation['id']}:probe={operation['probe']}:chosen={operation['chosenPrecision']}:"
            f"required={operation['requiredPrecision']}:cpu={operation['cpuDouble']}:gpu={operation['gpuOutput']}:"
            f"budget={operation['errorBudget']}:error={error}:explicit={_flag(operation['explicitReduction'])}:"
            f"tested={_flag(operation['accumulatedErrorTested'])}:promoted={_flag(operation['promoted'])}:"
            f"overflow={_flag(operation['overflow'])}:denormal={_flag(operation['denormal'])}:"
            f"texture={_flag(operation['textureConversion'])}:status={statuses[operation['id']]}"
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
    require(decision not in _FORBIDDEN, "P067 must not decide qualified or allowed")
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
    """Accept bounded or promoted precision, and reject blanket untested FP16.

    ``path`` ``fp16-everywhere`` is the deliberate mutant. It does not rewrite
    recorded CPU or GPU values and it does not drop operations. The decision is
    never ``qualified`` or ``allowed``.
    """
    validate_document(document)
    require(path in PATHS, "path must be declared or fp16-everywhere")
    reasons = [ORACLE, "CPU double references were compared with GPU outputs"]
    questions = [
        "host fixture is not a physical S23 measurement",
        HOST_LIMIT,
    ]
    statuses: dict[str, str] = {}
    rejected: list[str] = []
    for operation in document["operations"]:
        faults = operation_faults(operation)
        status = _status(operation, faults)
        statuses[operation["id"]] = status
        error = absolute_error(operation["cpuDouble"], operation["gpuOutput"])
        if faults:
            rejected.append(operation["id"])
            reasons.append(f"{operation['id']} rejected: " + ", ".join(faults))
        else:
            reasons.append(
                f"{operation['id']} {status} with error {error} inside budget {operation['errorBudget']}"
            )
    acceptable = {"within-budget", "promoted"}
    if SIGNATURES[0] in statuses and SIGNATURES[1] in statuses:
        if statuses[SIGNATURES[0]] in acceptable and statuses[SIGNATURES[1]] in acceptable:
            reasons.append(
                "highlight kernel and matrix cancellation stayed inside the budget or were promoted"
            )
    if any(item["promoted"] for item in document["operations"]):
        questions.append("promotion is a graph decision, not a measured device result")
    if path == MUTANT_PATH:
        rejected.append("fp16-without-accumulated-error")
        reasons.append(MUTANT)
        reasons.append("replacing every intermediate with FP16 does not test accumulated error")
        questions.append("mutant FP16 replacement was rejected without erasing the differential inventory")
    if document["suite"]["framesProcessed"]:
        rejected.append("device-frames-claimed")
        reasons.append("processed device frames are not part of this host differential")
    else:
        reasons.append("no device frames were processed")
    reasons.append(HOST_LIMIT)
    preserved = _inventory(document, statuses)
    if rejected:
        return _result("rejected", reasons, rejected, preserved, questions)
    if not document["operations"]:
        questions.append("no differential operations were supplied")
        return _result("withheld", reasons, rejected, preserved, questions)
    reasons.append("chosen precisions stayed inside the declared error budget or were promoted")
    return _result("precision_bounded", reasons, rejected, preserved, questions)
