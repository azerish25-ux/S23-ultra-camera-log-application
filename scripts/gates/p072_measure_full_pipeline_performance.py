#!/usr/bin/env python3
"""P072 integrated full-pipeline performance report.

Capture, copies, inference, rendering, encoding, decoding, I/O, and queue
occupancy are measured together. Cold-start numbers stay separate from the
sustained thermal state. Live and deferred modes are different workflows.

The fixture is a fast standalone depth model whose integrated path stalls on
repeated format conversion and memory copies. The report names that
bottleneck. Standalone inference latency is not a camera frame rate.

The deliberate mutant — end-to-end performance taken from the fastest
individual kernel — is rejected. This module does not probe a device, does
not qualify a physical S23, and does not execute TC-P072-01 through TC-P072-08.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


PHASE = "P072"
CASE_ID = "P072"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-full-pipeline-performance-fixture"
METHOD = (
    "Measure capture, copies, inference, rendering, encoding, decoding, I/O, and queue "
    "occupancy together. Warm up where appropriate, retain cold-start results separately, "
    "and report sustained thermal state. Compare live and deferred modes as different workflows."
)
FIXTURE = (
    "A fast standalone depth model whose integrated path stalls because of repeated "
    "format conversion and memory copies."
)
ORACLE = (
    "The report attributes the actual bottleneck and does not advertise standalone "
    "inference latency as camera frame rate."
)
MUTANT = "Compute end-to-end performance from the fastest individual kernel."
INTEGRATED_PATH = "integrated"
MUTANT_PATH = "fastest-kernel"
PATHS = (INTEGRATED_PATH, MUTANT_PATH)
MODEL_ID = "standalone-depth"
HOST_LIMIT = "host fixture does not qualify a physical S23 or a measured camera frame rate"
STAGE_IDS = (
    "capture",
    "copies",
    "inference",
    "rendering",
    "encoding",
    "decoding",
    "io",
    "queue",
)
LATENCY_IDS = tuple(item for item in STAGE_IDS if item != "queue")
CAUSES = ("format-conversion", "stage-latency")
SOURCES = ("integrated", "standalone-inference", "fastest-kernel")
MODES = ("live", "deferred")
THERMALS = ("cold", "warm", "sustained")
COMPARISONS = ("distinct", "collapsed")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[a-z0-9-]+$")
LATENCY = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
COUNT = re.compile(r"0|[1-9][0-9]*")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "model",
    "attribution",
    "workflowComparison",
    "stages",
    "conversions",
    "workflows",
}
MODEL_KEYS = {"id", "standaloneInferenceMs", "integratedStall"}
ATTRIBUTION_KEYS = {"bottleneck", "cause", "frameRateSource"}
STAGE_KEYS = {"id", "latencyMs", "occupancy"}
CONVERSION_KEYS = {"id", "repeats", "copyBytes"}
WORKFLOW_KEYS = {
    "mode",
    "thermal",
    "warmup",
    "coldStartRetained",
    "coldStartMs",
    "sustainedMs",
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
_DECISIONS = {"rejected", "withheld", "bottleneck_attributed"}
_COPY_PRIORITIES = (
    "reduce-repeated-format-conversion",
    "reduce-memory-copies",
    "keep-standalone-inference-off-the-frame-rate-claim",
)


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


def _token(value: object, label: str) -> str:
    require(isinstance(value, str) and TOKEN.fullmatch(value) is not None, label + " must be a token")
    return value


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def _choice(value: object, allowed: tuple[str, ...], label: str) -> str:
    require(isinstance(value, str) and value in allowed, label + " is unsupported")
    return value


def _latency(value: object, label: str) -> str:
    require(isinstance(value, str) and LATENCY.fullmatch(value) is not None, label + " must be a canonical latency")
    return value


def _count(value: object, label: str, positive: bool) -> str:
    require(isinstance(value, str) and COUNT.fullmatch(value) is not None, label + " must be a canonical count")
    if positive:
        require(value != "0", label + " must be positive")
    return value


def _format_decimal(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P072 pipeline performance fixture shape."""
    exact_keys(document, DOCUMENT_KEYS, "performance report")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P072")
    require(document["mapId"] == MAP_ID, "mapId must be s23-full-pipeline-performance-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "performance report needs the P072 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    _choice(document["workflowComparison"], COMPARISONS, "workflowComparison")
    model = exact_keys(document["model"], MODEL_KEYS, "model")
    require(model["id"] == MODEL_ID, "model id must be standalone-depth")
    _latency(model["standaloneInferenceMs"], "standaloneInferenceMs")
    _bool(model["integratedStall"], "integratedStall")
    attribution = exact_keys(document["attribution"], ATTRIBUTION_KEYS, "attribution")
    _choice(attribution["bottleneck"], LATENCY_IDS, "attribution bottleneck")
    _choice(attribution["cause"], CAUSES, "attribution cause")
    _choice(attribution["frameRateSource"], SOURCES, "frameRateSource")
    stages = document["stages"]
    require(type(stages) is list and len(stages) == len(STAGE_IDS), "stages must list every pipeline stage")
    seen: list[str] = []
    for index, raw in enumerate(stages):
        stage = exact_keys(raw, STAGE_KEYS, f"stage {index}")
        stage_id = _choice(stage["id"], STAGE_IDS, f"stage {index} id")
        require(stage_id == STAGE_IDS[index], "stages must follow capture through queue order")
        _latency(stage["latencyMs"], f"stage {stage_id} latencyMs")
        _count(stage["occupancy"], f"stage {stage_id} occupancy", False)
        seen.append(stage_id)
    require(tuple(seen) == STAGE_IDS, "stage ids drifted")
    by_id = {stage["id"]: stage for stage in stages}
    require(
        model["standaloneInferenceMs"] == by_id["inference"]["latencyMs"],
        "standalone inference latency must match the inference stage",
    )
    conversions = document["conversions"]
    require(type(conversions) is list, "conversions must be a list")
    seen_conversions: set[str] = set()
    for index, raw in enumerate(conversions):
        conversion = exact_keys(raw, CONVERSION_KEYS, f"conversion {index}")
        conversion_id = _token(conversion["id"], f"conversion {index} id")
        require(conversion_id not in seen_conversions, "duplicate conversion id: " + conversion_id)
        seen_conversions.add(conversion_id)
        _count(conversion["repeats"], f"conversion {conversion_id} repeats", True)
        _count(conversion["copyBytes"], f"conversion {conversion_id} copyBytes", False)
    workflows = document["workflows"]
    require(type(workflows) is list and len(workflows) == 2, "workflows must list live and deferred")
    for index, raw in enumerate(workflows):
        workflow = exact_keys(raw, WORKFLOW_KEYS, f"workflow {index}")
        mode = _choice(workflow["mode"], MODES, f"workflow {index} mode")
        require(mode == MODES[index], "workflows must list live then deferred")
        _choice(workflow["thermal"], THERMALS, f"workflow {mode} thermal")
        _bool(workflow["warmup"], f"workflow {mode} warmup")
        _bool(workflow["coldStartRetained"], f"workflow {mode} coldStartRetained")
        cold = _latency(workflow["coldStartMs"], f"workflow {mode} coldStartMs")
        sustained = _latency(workflow["sustainedMs"], f"workflow {mode} sustainedMs")
        require(
            Decimal(cold) > Decimal(sustained),
            f"workflow {mode} cold start must stay numerically separate from sustained",
        )
    if model["integratedStall"]:
        require(conversions, "an integrated stall needs the repeated conversion record")
        copies = Decimal(by_id["copies"]["latencyMs"])
        require(
            all(copies > Decimal(by_id[stage_id]["latencyMs"]) for stage_id in LATENCY_IDS if stage_id != "copies"),
            "integrated stall requires copies to be strictly slower than every other latency stage",
        )
        require(
            any(int(item["repeats"]) >= 2 and int(item["copyBytes"]) > 0 for item in conversions),
            "integrated stall requires a repeated format conversion with memory copies",
        )


def measure(document: dict) -> dict[str, str]:
    """Sum latency stages. The fastest kernel is recorded and is not the integrated total."""
    validate_document(document)
    by_id = {stage["id"]: stage for stage in document["stages"]}
    pairs = [(stage_id, Decimal(by_id[stage_id]["latencyMs"])) for stage_id in LATENCY_IDS]
    total = sum((item[1] for item in pairs), Decimal("0"))
    fastest = min(pairs, key=lambda item: (item[1], LATENCY_IDS.index(item[0])))
    slowest = max(pairs, key=lambda item: (item[1], -LATENCY_IDS.index(item[0])))
    cause = "format-conversion" if document["model"]["integratedStall"] else "stage-latency"
    return {
        "integrated": _format_decimal(total),
        "fastestStage": fastest[0],
        "fastestMs": by_id[fastest[0]]["latencyMs"],
        "bottleneck": slowest[0],
        "bottleneckMs": by_id[slowest[0]]["latencyMs"],
        "cause": cause,
    }


def _priorities(measured: dict[str, str]) -> tuple[str, ...]:
    if measured["cause"] == "format-conversion" and measured["bottleneck"] == "copies":
        return _COPY_PRIORITIES
    return (
        "reduce-" + measured["bottleneck"],
        "keep-standalone-inference-off-the-frame-rate-claim",
    )


def _inventory(document: dict, measured: dict[str, str]) -> list[str]:
    model = document["model"]
    attribution = document["attribution"]
    preserved = [
        (
            f"model:{model['id']}:standalone-inference-ms={model['standaloneInferenceMs']}:"
            f"stall={str(model['integratedStall']).lower()}"
        ),
        f"computed-bottleneck:{measured['bottleneck']}",
        f"computed-bottleneck-ms:{measured['bottleneckMs']}",
        f"computed-cause:{measured['cause']}",
        f"computed-integrated-ms:{measured['integrated']}",
        f"computed-fastest-stage:{measured['fastestStage']}",
        f"computed-fastest-kernel-ms:{measured['fastestMs']}",
        f"authored-bottleneck:{attribution['bottleneck']}",
        f"authored-cause:{attribution['cause']}",
        f"authored-frame-rate-source:{attribution['frameRateSource']}",
        f"workflow-comparison:{document['workflowComparison']}",
    ]
    for stage in document["stages"]:
        preserved.append(f"stage:{stage['id']}:latency={stage['latencyMs']}:occupancy={stage['occupancy']}")
    queue = next(stage for stage in document["stages"] if stage["id"] == "queue")
    preserved.append("queue-occupancy:" + queue["occupancy"])
    for conversion in document["conversions"]:
        preserved.append(
            f"conversion:{conversion['id']}:repeats={conversion['repeats']}:bytes={conversion['copyBytes']}"
        )
    for workflow in document["workflows"]:
        preserved.append(
            f"workflow:{workflow['mode']}:thermal={workflow['thermal']}:"
            f"warmup={str(workflow['warmup']).lower()}:"
            f"cold-retained={str(workflow['coldStartRetained']).lower()}:"
            f"cold={workflow['coldStartMs']}:sustained={workflow['sustainedMs']}"
        )
    for priority in _priorities(measured):
        preserved.append("priority:" + priority)
    return preserved


def _faults(document: dict, measured: dict[str, str], path: str) -> list[str]:
    attribution = document["attribution"]
    rejected: list[str] = []
    if attribution["bottleneck"] != measured["bottleneck"]:
        rejected.append("misattributed-bottleneck")
    if attribution["cause"] != measured["cause"]:
        rejected.append("misattributed-cause")
    source = attribution["frameRateSource"]
    if source == "standalone-inference":
        rejected.append("inference-as-frame-rate")
    elif source == "fastest-kernel":
        rejected.append("fastest-kernel-extrapolation")
    if document["workflowComparison"] != "distinct":
        rejected.append("collapsed-workflows")
    live = document["workflows"][0]
    if Decimal(live["sustainedMs"]) != Decimal(measured["integrated"]):
        rejected.append("live-sustained-mismatch")
    for workflow in document["workflows"]:
        if not workflow["coldStartRetained"]:
            rejected.append("discarded-cold-start:" + workflow["mode"])
        if workflow["thermal"] == "sustained" and not workflow["warmup"]:
            rejected.append("sustained-without-warmup:" + workflow["mode"])
    if path == MUTANT_PATH and "fastest-kernel-extrapolation" not in rejected:
        rejected.append("fastest-kernel-extrapolation")
    return rejected


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS, "unexpected decision")
    require(decision not in _FORBIDDEN, "P072 must not decide qualified or allowed")
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


def assess(document: dict, path: str = INTEGRATED_PATH) -> dict:
    """Attribute the integrated bottleneck, and reject fastest-kernel extrapolation.

    ``path`` ``fastest-kernel`` is the deliberate mutant. It does not replace
    the integrated sum with the fastest stage, and it does not advertise
    standalone inference latency as a camera frame rate. The stage inventory
    stays in ``preservedResults``. The decision is never ``qualified`` or
    ``allowed``.
    """
    require(path in PATHS, "path must be integrated or fastest-kernel")
    measured = measure(document)
    rejected = _faults(document, measured, path)
    reasons = [
        ORACLE,
        "capture, copies, inference, rendering, encoding, decoding, I/O, and queue occupancy were measured together",
        (
            f"computed bottleneck {measured['bottleneck']} at {measured['bottleneckMs']} ms; "
            f"integrated latency {measured['integrated']} ms"
        ),
        (
            f"fastest kernel {measured['fastestStage']} at {measured['fastestMs']} ms "
            "is not the integrated latency and is not a camera frame rate"
        ),
    ]
    questions = [
        "host fixture is not a physical S23 measurement",
        HOST_LIMIT,
        "cold-start results stay separate from the sustained thermal state",
        "live and deferred are different workflows",
    ]
    if measured["cause"] == "format-conversion":
        reasons.append("repeated format conversion and memory copies stall the integrated path")
    reasons.append("live and deferred modes were kept as different workflows")
    reasons.append("cold-start results were retained as separate numbers from sustained latency")
    if path == MUTANT_PATH:
        reasons.append(MUTANT)
        reasons.append("end-to-end performance was not computed from the fastest individual kernel")
        questions.append("mutant fastest-kernel extrapolation was rejected")
    reasons.append(HOST_LIMIT)
    preserved = _inventory(document, measured)
    if rejected:
        reasons.append("authored performance claims that contradict the integrated measurement were rejected")
        return _result("rejected", reasons, rejected, preserved, questions)
    if not any(workflow["thermal"] == "sustained" for workflow in document["workflows"]):
        reasons.append("sustained thermal state was not reported")
        questions.append("sustained thermal state was not reported")
        return _result("withheld", reasons, rejected, preserved, questions)
    reasons.append(
        f"sustained thermal state attributes bottleneck {measured['bottleneck']} "
        f"rather than standalone inference {measured['fastestMs']} ms"
    )
    return _result("bottleneck_attributed", reasons, rejected, preserved, questions)
