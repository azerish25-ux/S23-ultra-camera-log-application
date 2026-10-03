#!/usr/bin/env python3
"""P021 dual focus model: physical lens state versus virtual development focus.

Physical focus and virtual focus stay in separate namespaces and units.
A capture result confirms physical distance or the distance stays unknown.
Virtual focus may name a subject in relative depth and must not claim metres.
Source sharpness is independent of the virtual plane. Virtual refocus cannot
restore detail the lens never recorded sharply.

This module does not open a camera, does not qualify a physical Galaxy S23,
and does not execute TC-P021-01 through TC-P021-08.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


METHOD = (
    "Keep separate control namespaces and units. Confirm physical focus through "
    "available results and expose unknown distance honestly. Virtual focus may "
    "track a subject in relative depth without claiming metric distance; recording "
    "source sharpness remains independently important."
)
FIXTURE = (
    "A face selected for virtual focus while the physical lens is focused on a "
    "nearby foreground object."
)
ORACLE = (
    "The interface warns that virtual refocusing cannot restore source detail "
    "that was never sharply recorded."
)
MUTANT = "Overwrite the physical focus-distance field with the virtual focus target."

BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MODEL_ID = "s23-dual-focus-fixture"
CASE_ID = "P021"
PHYSICAL_NAMESPACE = "physical.lens"
VIRTUAL_NAMESPACE = "virtual.development"
PHYSICAL_UNIT = "metres"
VIRTUAL_UNIT = "relative_depth"
UNKNOWN_DISTANCE = "unknown"
MUTANT_CLAIM = "overwrite-physical-focus-distance"
METRIC_CLAIM = "virtual-metric-distance"
COUPLED_SHARPNESS_CLAIM = "source-sharpness-coupled-to-virtual-plane"
UNKNOWN_QUESTION = "physical focus distance is unknown"

HEX40 = re.compile(r"^[0-9a-f]{40}$")
DECIMAL_TEXT = re.compile(r"^(?:0|[1-9]\d*)(?:\.\d+)?$")
TOKEN_TEXT = re.compile(r"^[A-Za-z0-9_.-]+$")

MODEL_KEYS = {
    "schemaVersion",
    "phase",
    "modelId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "physical",
    "virtual",
    "sourceSharpness",
}
PHYSICAL_KEYS = {
    "namespace",
    "unit",
    "subject",
    "observedDistance",
    "confirmedByResult",
}
VIRTUAL_KEYS = {
    "namespace",
    "unit",
    "subject",
    "relativeDepth",
    "claimsMetricDistance",
}
SHARPNESS_KEYS = {
    "recordedSharpAtVirtualSubject",
    "independentOfVirtualPlane",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = {"rejected", "warned", "separated"}


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


def _bool(value: object, name: str) -> bool:
    require(type(value) is bool, name + " must be a bool")
    return value


def _token(value: object, name: str) -> str:
    require(isinstance(value, str) and TOKEN_TEXT.fullmatch(value) is not None, name + " must be a token")
    return value


def _positive_decimal(value: object, name: str) -> str:
    require(
        isinstance(value, str) and DECIMAL_TEXT.fullmatch(value) is not None,
        name + " must be a canonical positive decimal string",
    )
    parsed = Decimal(value)
    require(parsed > 0, name + " must be positive")
    return value


def _relative_depth(value: object) -> str:
    text = _positive_decimal(value, "virtual relativeDepth")
    require(Decimal(text) <= 1, "virtual relativeDepth must be in (0, 1]")
    return text


def validate_model(document: dict) -> None:
    """Raise ValueError unless document is a P021 dual-focus model.

    Namespaces and units are fixed and distinct. Physical distance is either
    confirmed by a capture result or null. Virtual depth is relative, not metres.
    """
    exact_keys(document, MODEL_KEYS, "focus model")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == "P021", "phase must be P021")
    require(document["modelId"] == MODEL_ID, "modelId must be s23-dual-focus-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "focus model needs the P021 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")

    physical = exact_keys(document["physical"], PHYSICAL_KEYS, "physical")
    require(physical["namespace"] == PHYSICAL_NAMESPACE, "physical namespace must stay physical.lens")
    require(physical["unit"] == PHYSICAL_UNIT, "physical unit must stay metres")
    _token(physical["subject"], "physical subject")
    confirmed = _bool(physical["confirmedByResult"], "physical confirmedByResult")
    distance = physical["observedDistance"]
    if confirmed:
        _positive_decimal(distance, "physical observedDistance")
    else:
        require(distance is None, "unconfirmed physical distance must be null, not a guessed number")

    virtual = exact_keys(document["virtual"], VIRTUAL_KEYS, "virtual")
    require(virtual["namespace"] == VIRTUAL_NAMESPACE, "virtual namespace must stay virtual.development")
    require(virtual["unit"] == VIRTUAL_UNIT, "virtual unit must stay relative_depth")
    require(virtual["namespace"] != physical["namespace"], "focus namespaces must stay separate")
    require(virtual["unit"] != physical["unit"], "focus units must stay separate")
    _token(virtual["subject"], "virtual subject")
    _relative_depth(virtual["relativeDepth"])
    _bool(virtual["claimsMetricDistance"], "virtual claimsMetricDistance")

    sharpness = exact_keys(document["sourceSharpness"], SHARPNESS_KEYS, "sourceSharpness")
    _bool(sharpness["recordedSharpAtVirtualSubject"], "recordedSharpAtVirtualSubject")
    _bool(sharpness["independentOfVirtualPlane"], "independentOfVirtualPlane")


def project_focus(document: dict) -> dict[str, Any]:
    """Project physical and virtual focus without copying either into the other.

    Unconfirmed physical distance is the string "unknown". Virtual relative
    depth is never written into the physical distance field. The oracle warning
    is present only when the virtual subject was not sharply recorded.
    """
    validate_model(document)
    physical = document["physical"]
    virtual = document["virtual"]
    sharpness = document["sourceSharpness"]
    if physical["confirmedByResult"] is True:
        distance = physical["observedDistance"]
    else:
        distance = UNKNOWN_DISTANCE
    sharp = sharpness["recordedSharpAtVirtualSubject"] is True
    return {
        "physical": {
            "namespace": physical["namespace"],
            "unit": physical["unit"],
            "subject": physical["subject"],
            "distance": distance,
            "confirmed": physical["confirmedByResult"] is True,
        },
        "virtual": {
            "namespace": virtual["namespace"],
            "unit": virtual["unit"],
            "subject": virtual["subject"],
            "relativeDepth": virtual["relativeDepth"],
            "claimsMetricDistance": virtual["claimsMetricDistance"] is True,
        },
        "warning": None if sharp else ORACLE,
        "sourceSharpAtVirtualSubject": sharp,
        "sourceSharpnessIndependent": sharpness["independentOfVirtualPlane"] is True,
    }


def _preserved(projected: dict[str, Any]) -> list[str]:
    physical = projected["physical"]
    virtual = projected["virtual"]
    return [
        "physical.namespace:" + physical["namespace"],
        "physical.unit:" + physical["unit"],
        "physical.subject:" + physical["subject"],
        "physical.distance:" + physical["distance"],
        "virtual.namespace:" + virtual["namespace"],
        "virtual.unit:" + virtual["unit"],
        "virtual.subject:" + virtual["subject"],
        "virtual.relativeDepth:" + virtual["relativeDepth"],
        "source.independent:" + str(projected["sourceSharpnessIndependent"]).lower(),
        "source.sharpAtVirtualSubject:" + str(projected["sourceSharpAtVirtualSubject"]).lower(),
    ]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in DECISIONS, "decision must be rejected, warned, or separated")
    require(decision not in {"qualified", "allowed"}, "decision must not be qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons), "reasons required")
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


def assess_model(document: dict, mutant: bool = False) -> dict[str, Any]:
    """Assess a dual-focus model. The mutant does not overwrite physical distance.

    mutant true is the deliberate failure: copy the virtual focus target into
    the physical focus-distance field. That claim is rejected. preservedResults
    keep the physical observation and the virtual target as separate facts.
    A virtual metric claim, or source sharpness derived from the virtual plane,
    is also rejected. Otherwise the decision is warned when the virtual subject
    was never sharp, and separated when it was.
    """
    require(type(mutant) is bool, "mutant must be a bool")
    projected = project_focus(document)
    physical = projected["physical"]
    virtual = projected["virtual"]
    # The mutant is rejected by leaving the projected physical distance untouched.
    require(
        physical["distance"] == (
            document["physical"]["observedDistance"]
            if document["physical"]["confirmedByResult"]
            else UNKNOWN_DISTANCE
        ),
        "physical focus-distance must not be overwritten",
    )
    require(physical["unit"] == PHYSICAL_UNIT, "physical unit must remain metres")
    require(virtual["unit"] == VIRTUAL_UNIT, "virtual unit must remain relative_depth")
    require(physical["namespace"] != virtual["namespace"], "namespaces collapsed")

    rejected: list[str] = []
    if mutant:
        rejected.append(MUTANT_CLAIM)
    if virtual["claimsMetricDistance"]:
        rejected.append(METRIC_CLAIM)
    if not projected["sourceSharpnessIndependent"]:
        rejected.append(COUPLED_SHARPNESS_CLAIM)

    reasons: list[str] = []
    if mutant:
        reasons.append(MUTANT)
        reasons.append(
            "physical focus-distance was not overwritten with the virtual focus target"
        )
    if virtual["claimsMetricDistance"]:
        reasons.append("virtual relative depth is not a metric focus distance")
    if not projected["sourceSharpnessIndependent"]:
        reasons.append("recording source sharpness must stay independent of the virtual plane")

    questions: list[str] = []
    if physical["distance"] == UNKNOWN_DISTANCE:
        questions.append(UNKNOWN_QUESTION)
        reasons.append("physical focus distance is unknown")
    else:
        reasons.append(
            "physical focus confirmed at " + physical["distance"] + " metres on " + physical["subject"]
        )
    if virtual["claimsMetricDistance"]:
        reasons.append(
            "virtual focus tracks " + virtual["subject"] + " at relative depth "
            + virtual["relativeDepth"] + " and must not be treated as metres"
        )
    else:
        reasons.append(
            "virtual focus tracks " + virtual["subject"] + " at relative depth "
            + virtual["relativeDepth"] + " without claiming metric distance"
        )
    if projected["sourceSharpnessIndependent"]:
        reasons.append("recording source sharpness is independent of the virtual focus plane")
    if projected["warning"] is not None:
        reasons.append(projected["warning"])

    if rejected:
        decision = "rejected"
    elif projected["warning"] is not None:
        decision = "warned"
    else:
        decision = "separated"
    return _result(decision, reasons, rejected, _preserved(projected), questions)
