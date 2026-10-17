"""TC-P139-02 Whole-film overgeneralization.

Host fixture. Supported acquisition variants stay separate. A scene without a
matching method stays uncertain. A title match must not assign one stock to
every scene. Production facts stay immutable.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P139-02"
NAME = "Whole-film overgeneralization"
INTERVENTION = "Provide a source describing several acquisition methods and attempt to assign one to every shot."
EXPECTED = "Represent supported variants and preserve uncertainty at scene level."
NEGATIVE = "A title match alone must not establish every scene\u2019s technical recipe."
REPEAT = "Repeat mixed color/monochrome, mixed formats, and location-specific stock choices."
NEGATIVE_TOKEN = "title-match-alone-establishes-every-scene"
COLLAPSED = "scene-level-uncertainty-collapsed"
ALLOWED_REPEATS = {"mixed-color-monochrome", "mixed-formats", "location-specific-stock", REPEAT}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "title",
    "methods",
    "assignments",
    "titleMatchAlone",
    "productionFacts",
    "fact_hash",
    "prior_canonical",
    "reconstructions",
    "mutated_facts",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_SPEC = importlib.util.spec_from_file_location(
    "p139_version_creative_reconstruction_parameters",
    Path(__file__).resolve().parent / "p139_version_creative_reconstruction_parameters.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _methods(value):
    if not isinstance(value, list) or not value:
        raise ValueError("methods must be a non-empty list")
    parsed = []
    for index, item in enumerate(value):
        if type(item) is not dict or set(item) != {"scene", "stock", "format", "color"}:
            raise ValueError(f"methods[{index}] keys are invalid")
        color = item["color"]
        if color not in {"color", "monochrome"}:
            raise ValueError(f"methods[{index}].color is invalid")
        parsed.append(
            {
                "scene": _CORE.require_text(item["scene"], f"methods[{index}].scene"),
                "stock": _CORE.require_text(item["stock"], f"methods[{index}].stock"),
                "format": _CORE.require_text(item["format"], f"methods[{index}].format"),
                "color": color,
            }
        )
    return parsed


def _assignments(value):
    if not isinstance(value, list) or not value:
        raise ValueError("assignments must be a non-empty list")
    parsed = []
    for index, item in enumerate(value):
        if type(item) is not dict or set(item) != {"scene", "stock", "evidence"}:
            raise ValueError(f"assignments[{index}] keys are invalid")
        evidence = item["evidence"]
        if evidence not in {"documented", "uncertain", _CORE.CREATIVE_LABEL}:
            raise ValueError(f"assignments[{index}].evidence is invalid")
        stock = item["stock"]
        if evidence == "uncertain":
            if stock is not None:
                raise ValueError(f"assignments[{index}] uncertain scenes keep stock unknown")
        elif not isinstance(stock, str) or not stock.strip() or stock != stock.strip():
            raise ValueError(f"assignments[{index}].stock must be a string")
        parsed.append(
            {
                "scene": _CORE.require_text(item["scene"], f"assignments[{index}].scene"),
                "stock": stock,
                "evidence": evidence,
            }
        )
    return parsed


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _CORE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _CORE.require_text(payload["repeat"], "repeat")
    if repeat not in ALLOWED_REPEATS:
        raise ValueError("repeat is not a variant class")
    title = _CORE.require_text(payload["title"], "title")
    if type(payload["titleMatchAlone"]) is not bool:
        raise ValueError("titleMatchAlone must be a bool")
    methods = _methods(payload["methods"])
    assignments = _assignments(payload["assignments"])
    review = _CORE.review_reconstructions(
        payload["productionFacts"],
        payload["reconstructions"],
        declared_fact_hash=payload["fact_hash"],
        prior_canonical=payload["prior_canonical"],
        mutated_facts=payload["mutated_facts"],
        bound_object_id=None,
    )
    sourced: dict[str, list[dict]] = {}
    for method in methods:
        sourced.setdefault(method["scene"], []).append(method)
    faults = list(review["faults"])
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION, f"repeat {repeat}", "title=" + title]
    reasons.extend(review["reasons"])
    documented = [item for item in assignments if item["evidence"] == "documented"]
    for assignment in documented:
        options = sourced.get(assignment["scene"], [])
        exact = [item for item in options if item["stock"] == assignment["stock"]]
        if not exact:
            faults.append(NEGATIVE_TOKEN if payload["titleMatchAlone"] or not options else "scene-recipe-not-supported")
            reasons.append(assignment["scene"] + " was not given that stock by a source")
    stocks = {item["stock"] for item in documented}
    method_stocks = {item["stock"] for item in methods}
    if len(documented) >= 2 and len(stocks) == 1 and len(method_stocks) > 1:
        faults.append(COLLAPSED)
        reasons.append("one stock was assigned across scenes that use different methods")
        if payload["titleMatchAlone"]:
            faults.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
    if payload["titleMatchAlone"] and NEGATIVE_TOKEN in faults:
        reasons.append(NEGATIVE)
    preserved = [evidence, "title=" + title, "titleMatchAlone=" + str(payload["titleMatchAlone"]).lower()]
    for method in methods:
        preserved.append(
            "variant=" + method["scene"] + ":" + method["stock"] + ":" + method["format"] + ":" + method["color"]
        )
    for assignment in assignments:
        if assignment["evidence"] == "uncertain":
            preserved.append("scene=" + assignment["scene"] + " evidence=uncertain")
    preserved.extend(review["preserved"])
    result = _CORE.finish_result(
        CASE_ID,
        reasons,
        faults,
        preserved,
        [_CORE.OPEN_QUESTION, REPEAT],
    )
    if tuple(result) != RESULT_KEYS or evidence not in result["preservedResults"]:
        raise ValueError("result contract drifted")
    return result
