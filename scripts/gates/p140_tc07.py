"""TC-P140-07 Parameter matching alters content.

Host reference. Matching is restricted to declared rendering parameters.
Geometry, texture replacement, and generated scenes are not camera footage.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P140-07",
    "phase": "P140",
    "workstream": 18,
    "name": "Parameter matching alters content",
    "intervention": "Use an automatic look suggestion that changes facial geometry or replaces scene texture.",
    "expected": "Reject unrequested content synthesis and restrict matching to declared rendering parameters.",
    "negative": "A visually similar generated scene is not preserved camera footage.",
    "repeat": "Repeat faces, text, fine patterns, and moving objects.",
}
NEGATIVE_TOKEN = "visually-similar-generated-scene-is-not-preserved-camera-footage"
SYNTHESIS = "unrequested-content-synthesis"
NOT_RESTRICTED = "matching-not-restricted-to-declared-rendering-parameters"
ALLOWED = frozenset({"contrast", "grain", "halation", "saturation", "exposure", "printContrast"})
CONTENT = frozenset({"faces", "text", "fine-patterns", "moving-objects"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "contentClass",
    "declaredParameters",
    "altersFacialGeometry",
    "replacesSceneTexture",
    "generatedScene",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p140_implement_offline_search_and_filtering.py"
    spec = importlib.util.spec_from_file_location("p140_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    content = _GATE.require_text(payload["contentClass"], "contentClass")
    _GATE.require(content in CONTENT, "contentClass is not recognized")
    parameters = payload["declaredParameters"]
    _GATE.require(isinstance(parameters, dict) and parameters, "declaredParameters must be a non-empty object")
    rendered: dict[str, float] = {}
    for key in sorted(parameters):
        _GATE.require(isinstance(key, str) and key.strip() and key == key.strip(), "parameter name is invalid")
        rendered[key] = _GATE.require_number(parameters[key], "declaredParameters." + key)
    alters = _GATE.require_bool(payload["altersFacialGeometry"], "altersFacialGeometry")
    replaces = _GATE.require_bool(payload["replacesSceneTexture"], "replacesSceneTexture")
    generated = _GATE.require_bool(payload["generatedScene"], "generatedScene")
    faults: list[str] = []
    if any(key not in ALLOWED for key in rendered):
        faults.append(NOT_RESTRICTED)
    if alters or replaces or generated:
        faults.append(SYNTHESIS)
        faults.append(NEGATIVE_TOKEN)
    parameter_keys = sorted(key for key in rendered if key in ALLOWED)
    record = {
        "id": "render-match-" + content,
        "title": " ".join(parameter_keys) if parameter_keys else "undeclared",
        "contentClass": content,
        "evidenceStatus": "parameter-match" if not faults else "rejected-synthesis",
        "privateRecipe": False,
    }
    index = _GATE.build_token_index([record])
    query = " ".join(parameter_keys) if parameter_keys else content
    found = _GATE.retrieve(index, query)
    preserved = [
        evidence,
        {
            "contentClass": content,
            "parameterKeys": parameter_keys,
            "searchIds": found,
            "altersFacialGeometry": alters,
            "replacesSceneTexture": replaces,
            "generatedScene": generated,
            "preservedFootage": not faults,
        },
    ]
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + _GATE.ORACLE,
        CASE["expected"],
        "repeat " + repeat,
        "contentClass=" + content,
        "parameters=" + ",".join(parameter_keys),
    ]
    if NEGATIVE_TOKEN in faults:
        reasons.append(CASE["negative"])
    if not faults:
        reasons.append("match restricted to declared rendering parameters; footage unchanged")
    return _GATE.finish_result(CASE["id"], evidence, faults, reasons, preserved, [CASE["repeat"], repeat])
