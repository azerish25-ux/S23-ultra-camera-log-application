"""TC-P142-02 Whole-film overgeneralization.

Host reference. Supported acquisition variants stay on the shots that have
their own evidence. A title match cannot assign one recipe to every scene.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P142-02",
    "phase": "P142",
    "workstream": 18,
    "name": "Whole-film overgeneralization",
    "intervention": "Provide a source describing several acquisition methods and attempt to assign one to every shot.",
    "expected": "Represent supported variants and preserve uncertainty at scene level.",
    "negative": "A title match alone must not establish every scene\u2019s technical recipe.",
    "repeat": "Repeat mixed color/monochrome, mixed formats, and location-specific stock choices.",
}

NEGATIVE_TOKEN = "title-match-alone-established-scene-recipe"
UNCERTAINTY_ERASED = "scene-uncertainty-erased"
UNSUPPORTED = "unsupported-acquisition-method"
SHOT_KEYS = {"scene_id", "method", "evidence", "color", "format", "stock"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "source",
    "reference",
    "suggestion",
    "acquisitionMethods",
    "shots",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p142_implement_constrained_reference_matching.py"
    spec = importlib.util.spec_from_file_location("p142_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def clean_shots():
    return [
        {
            "scene_id": "sc1",
            "method": "35mm-color",
            "evidence": "camera-report",
            "color": True,
            "format": "35mm",
            "stock": "5219",
        },
        {
            "scene_id": "sc2",
            "method": "unknown",
            "evidence": "uncertain",
            "color": False,
            "format": "16mm",
            "stock": None,
        },
        {
            "scene_id": "sc3",
            "method": "16mm-monochrome",
            "evidence": "location-note",
            "color": False,
            "format": "16mm",
            "stock": "7222",
        },
    ]


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    methods = payload["acquisitionMethods"]
    _GATE.require(isinstance(methods, list) and len(methods) >= 2, "acquisitionMethods needs variants")
    parsed_methods = []
    for index, method in enumerate(methods):
        parsed_methods.append(_GATE.require_text(method, "acquisitionMethods[" + str(index) + "]"))
    shots = payload["shots"]
    _GATE.require(isinstance(shots, list) and shots, "shots must be a non-empty list")
    parsed = []
    for index, shot in enumerate(shots):
        label = "shots[" + str(index) + "]"
        _GATE.require(isinstance(shot, dict) and set(shot) == SHOT_KEYS, label + " keys are invalid")
        method = _GATE.require_text(shot["method"], label + ".method")
        evidence = _GATE.require_text(shot["evidence"], label + ".evidence")
        _GATE.require(
            evidence in {"camera-report", "title", "uncertain", "location-note"},
            label + ".evidence is not recognized",
        )
        color = _GATE.require_bool(shot["color"], label + ".color")
        image_format = _GATE.require_text(shot["format"], label + ".format")
        stock = shot["stock"]
        if stock is not None:
            stock = _GATE.require_text(stock, label + ".stock")
        row = {
            "scene_id": _GATE.require_text(shot["scene_id"], label + ".scene_id"),
            "method": method,
            "evidence": evidence,
            "color": color,
            "format": image_format,
            "stock": stock,
        }
        if evidence == "title" and method != "unknown":
            faults.append(NEGATIVE_TOKEN)
        if evidence == "uncertain" and method != "unknown":
            faults.append(UNCERTAINTY_ERASED)
        if method != "unknown" and method not in parsed_methods:
            faults.append(UNSUPPORTED)
        parsed.append(row)
    if len(parsed_methods) > 1 and parsed and all(row["evidence"] == "title" for row in parsed):
        if len({row["method"] for row in parsed}) == 1:
            faults.append(NEGATIVE_TOKEN)
    extra = [{
        "acquisitionMethods": parsed_methods,
        "scenes": [
            {
                "scene_id": row["scene_id"],
                "method": row["method"],
                "color": row["color"],
                "format": row["format"],
                "stock": row["stock"],
            }
            for row in parsed
        ],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            UNCERTAINTY_ERASED: CASE["expected"],
            UNSUPPORTED: "an assigned method must be one of the supported variants",
        },
    )
