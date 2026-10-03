#!/usr/bin/env python3
"""P061 source normalization router.

Inspect declared tags, decode the transfer and color representation actually
present, and keep source lineage on every recipe and output. Upstream ISP
processing is recorded as not invertible. Flattened SDR does not grow scene
values. An untagged import stays unresolved. None of the three paths is
promoted to RAW-derived Log.

The deliberate mutant — one inverse curve on every source, ignoring metadata —
is rejected. This module does not probe a device, does not qualify a physical
S23, and does not execute TC-P061-01 through TC-P061-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P061"
CASE_ID = "P061"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-source-normalization-router-fixture"
METHOD = (
    "Inspect source tags, decode the actual transfer and color representation, "
    "and preserve the fact that upstream ISP processing may not be invertible. "
    "Keep source lineage in every recipe and output. Do not invent missing scene "
    "values from flattened SDR."
)
FIXTURE = (
    "The same visible frame supplied as declared HLG, SDR, and an untagged imported video."
)
ORACLE = (
    "Each path receives its correct or explicitly unresolved interpretation; "
    "none is silently promoted to RAW-derived Log."
)
MUTANT = "Apply one inverse curve to every source regardless of metadata."
FRAME_ID = "same-visible-frame"
INVERSE_CURVE = "display-to-scene-guess"
FORBIDDEN_PROMOTION = "RAW-derived-Log"
INSPECT = "inspect"
ONE_INVERSE = "one-inverse"
ROUTES = (INSPECT, ONE_INVERSE)
HOST_LIMIT = (
    "host fixture does not qualify a physical S23, sensor-derived Log, "
    "ten-bit fidelity, or cinema-camera equivalence"
)

HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[a-z0-9-]+$")
DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")

TAGS = ("HLG", "SDR", "untagged")
TRANSFERS = ("HLG", "Rec.709", "unknown")
PRIMARIES = ("Rec.2020", "Rec.709", "unknown")
RANGES = ("video", "full", "unknown")
ACQUISITIONS = ("isp-processed-hlg", "isp-processed-sdr", "imported-video")

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "frameId",
    "inverseCurve",
    "forbiddenPromotion",
    "sources",
}
SOURCE_KEYS = {
    "id",
    "declaredTag",
    "transfer",
    "primaries",
    "range",
    "acquisition",
    "ispInvertible",
    "visibleCode",
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
_DECISIONS = {"rejected", "withheld", "routed"}


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


def _decimal(value: object, label: str) -> str:
    require(
        isinstance(value, str) and DECIMAL.fullmatch(value) is not None,
        label + " must be a canonical decimal string",
    )
    return value


def _choice(value: object, allowed: tuple[str, ...], label: str) -> str:
    require(value in allowed, label + " is unsupported")
    return value


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is a P061 router fixture."""
    exact_keys(document, DOCUMENT_KEYS, "router")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P061")
    require(document["mapId"] == MAP_ID, "mapId must be s23-source-normalization-router-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "router needs the P061 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    require(document["frameId"] == FRAME_ID, "frameId must be same-visible-frame")
    require(document["inverseCurve"] == INVERSE_CURVE, "inverseCurve drifted")
    require(document["forbiddenPromotion"] == FORBIDDEN_PROMOTION, "forbiddenPromotion drifted")
    sources = document["sources"]
    require(type(sources) is list and len(sources) == 3, "sources must be the HLG, SDR, and untagged trio")
    seen_ids: set[str] = set()
    tags: list[str] = []
    codes: list[str] = []
    for index, source in enumerate(sources):
        exact_keys(source, SOURCE_KEYS, f"source {index}")
        source_id = _token(source["id"], f"source {index} id")
        require(source_id not in seen_ids, "duplicate source id")
        seen_ids.add(source_id)
        tags.append(_choice(source["declaredTag"], TAGS, f"source {index} declaredTag"))
        _choice(source["transfer"], TRANSFERS, f"source {index} transfer")
        _choice(source["primaries"], PRIMARIES, f"source {index} primaries")
        _choice(source["range"], RANGES, f"source {index} range")
        _choice(source["acquisition"], ACQUISITIONS, f"source {index} acquisition")
        require(type(source["ispInvertible"]) is bool, f"source {index} ispInvertible must be a bool")
        codes.append(_decimal(source["visibleCode"], f"source {index} visibleCode"))
    require(set(tags) == set(TAGS), "declared tags must be HLG, SDR, and untagged")
    require(len(set(codes)) == 1, "the three supplies must be the same visible frame")


def classify(source: dict) -> str:
    """Return the honest interpretation, or contradictory when tags disagree.

    Unknown transfer or primaries on an untagged import are unresolved. A
    declared HLG or SDR path is contradictory when the decoded transfer,
    primaries, or acquisition do not match that declaration, including any
    claim that ISP processing is invertible.
    """
    tag = source["declaredTag"]
    transfer = source["transfer"]
    primaries = source["primaries"]
    acquisition = source["acquisition"]
    invertible = source["ispInvertible"]
    if tag == "HLG":
        if (
            transfer == "HLG"
            and primaries == "Rec.2020"
            and acquisition == "isp-processed-hlg"
            and invertible is False
        ):
            return "hlg-derived"
        return "contradictory"
    if tag == "SDR":
        if (
            transfer == "Rec.709"
            and primaries == "Rec.709"
            and acquisition == "isp-processed-sdr"
            and invertible is False
        ):
            return "sdr-derived"
        return "contradictory"
    if (
        transfer == "unknown"
        and primaries == "unknown"
        and acquisition == "imported-video"
        and invertible is False
    ):
        return "unresolved"
    return "contradictory"


def _inventory(document: dict) -> list[str]:
    rows = [f"frame:{document['frameId']}"]
    for source in document["sources"]:
        rows.append(
            "source:{id}:{tag}:{transfer}:{primaries}:{range}:{acquisition}".format(
                id=source["id"],
                tag=source["declaredTag"],
                transfer=source["transfer"],
                primaries=source["primaries"],
                range=source["range"],
                acquisition=source["acquisition"],
            )
        )
        rows.append(f"visible:{source['id']}:{source['visibleCode']}")
        rows.append(
            f"isp-invertible:{source['id']}:{str(source['ispInvertible']).lower()}"
        )
        rows.append(
            f"decoded:{source['id']}:{source['transfer']}:{source['primaries']}:{source['range']}"
        )
    return rows


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS, "unexpected decision")
    require(decision not in _FORBIDDEN, "P061 must not decide qualified or allowed")
    require(
        bool(reasons) and all(isinstance(item, str) and item for item in reasons),
        "reasons must be a non-empty list of strings",
    )
    for _key, items in (
        ("rejectedClaims", rejected),
        ("preservedResults", preserved),
        ("openQuestions", questions),
    ):
        require(all(isinstance(item, str) and item for item in items), _key + " must be strings")
    require(FORBIDDEN_PROMOTION not in {decision}, "RAW-derived Log is not a decision")
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


def assess(document: dict, route: str = INSPECT) -> dict:
    """Route HLG, SDR, and untagged supplies, or reject the one-inverse mutant.

    ``route`` ``one-inverse`` applies ``display-to-scene-guess`` to every
    source and labels each RAW-derived Log. That decision is ``rejected``.
    Source tags, decoded transfer, and acquisition stay in preservedResults.
    The decision is never ``qualified`` or ``allowed``.
    """
    validate_document(document)
    require(route in ROUTES, "route must be inspect or one-inverse")
    preserved = _inventory(document)
    questions = [
        "host fixture is not a physical S23 measurement",
        "upstream ISP processing may not be invertible",
        "flattened SDR does not yield scene values",
        "untagged imported video stays unresolved unless tags exist",
    ]
    reasons = [ORACLE, METHOD]
    rejected: list[str] = []
    interpretations: list[str] = []

    for source in document["sources"]:
        kind = classify(source)
        interpretations.append(kind)
        if kind == "contradictory":
            rejected.append(f"contradictory:{source['id']}")
            reasons.append(
                f"{source['id']} tags disagree; interpretation was not invented"
            )
        elif source["range"] == "unknown" and kind != "unresolved":
            questions.append(f"range:{source['id']}:unknown")

    if route == ONE_INVERSE:
        rejected = ["one-inverse-curve", "silent-raw-log-promotion", *rejected]
        reasons.append(MUTANT)
        reasons.append(
            f"one inverse curve {INVERSE_CURVE} was applied to every source regardless of metadata"
        )
        questions.append("mutant route rejected")
        for source in document["sources"]:
            preserved.append(f"inverse:{INVERSE_CURVE}:{source['id']}")
            preserved.append(f"attempted:{source['id']}:{FORBIDDEN_PROMOTION}")
            preserved.append(f"scene:{source['id']}:invented")
        reasons.append(HOST_LIMIT)
        return _result("rejected", reasons, rejected, preserved, questions)

    for source, kind in zip(document["sources"], interpretations):
        preserved.append(f"interpretation:{source['id']}:{kind}")
        preserved.append(f"recipe:{source['id']}:{source['acquisition']}")
        preserved.append(f"output:{source['id']}:{kind}:{source['acquisition']}")
        preserved.append(f"scene:{source['id']}:not-invented")
        reasons.append(
            f"{source['id']} interpreted as {kind}; transfer {source['transfer']}; "
            f"primaries {source['primaries']}"
        )
    preserved.append("inverse:not-applied")
    preserved.append("scene-values:not-invented")
    reasons.append("lineage kept on every recipe and output")
    reasons.append("no source was promoted to " + FORBIDDEN_PROMOTION)
    if any(kind == "raw-derived-log" or kind == FORBIDDEN_PROMOTION for kind in interpretations):
        rejected.append("silent-raw-log-promotion")
    if rejected:
        decision = "rejected"
    elif interpretations == ["hlg-derived", "sdr-derived", "unresolved"] or (
        set(interpretations) == {"hlg-derived", "sdr-derived", "unresolved"}
        and interpretations.count("hlg-derived") == 1
        and interpretations.count("sdr-derived") == 1
        and interpretations.count("unresolved") == 1
    ):
        decision = "routed"
        reasons.append("HLG, SDR, and untagged paths stayed distinct")
    else:
        decision = "withheld"
        reasons.append("a path was neither its matching interpretation nor explicitly unresolved")
    reasons.append(HOST_LIMIT)
    return _result(decision, reasons, rejected, preserved, questions)
