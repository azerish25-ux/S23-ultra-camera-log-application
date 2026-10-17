"""TC-P144-07 Parameter matching alters content.

Look matching may touch declared rendering parameters only. Facial geometry,
texture, text, fine patterns, and moving objects are not free to change.
A generated scene is not preserved camera footage.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P144-07",
    "phase": "P144",
    "workstream": 18,
    "name": "Parameter matching alters content",
    "intervention": "Use an automatic look suggestion that changes facial geometry or replaces scene texture.",
    "expected": "Reject unrequested content synthesis and restrict matching to declared rendering parameters.",
    "negative": "A visually similar generated scene is not preserved camera footage.",
    "repeat": "Repeat faces, text, fine patterns, and moving objects.",
}

CONTENT_CHANGES = frozenset({
    "facial-geometry",
    "faces",
    "scene-texture",
    "text",
    "fine-patterns",
    "moving-objects",
})
RENDERING_PARAMETERS = frozenset({
    "virtual-aperture",
    "grade",
    "grain",
    "halation",
    "contrast",
    "saturation",
})
SYNTHESIS = "unrequested-content-synthesis"
NOT_FOOTAGE = "generated-scene-is-not-preserved-camera-footage"
ALTERED = "parameter-matching-altered-content"
NOT_RENDER = "matching-left-declared-rendering-parameters"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "declared_parameters",
    "content_changes",
    "unrequested_synthesis",
    "generated_scene_as_footage",
    "recipe",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p144_validate_recipe_fidelity_and_honesty.py"
    spec = importlib.util.spec_from_file_location("p144_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _names(value: object, label: str, allowed: frozenset) -> list[str]:
    _GATE.require(isinstance(value, list), label + " must be a list")
    names = [_GATE.require_text(item, label) for item in value]
    for name in names:
        _GATE.require(name in allowed, label + " contains an unrecognized name")
    return names


def evaluate(payload: dict) -> dict:
    _GATE.require_keys(payload, set(PAYLOAD_KEYS))
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    parameters = _names(payload["declared_parameters"], "declared_parameters", RENDERING_PARAMETERS | CONTENT_CHANGES)
    changes = _names(payload["content_changes"], "content_changes", CONTENT_CHANGES)
    synthesis = _GATE.require_bool(payload["unrequested_synthesis"], "unrequested_synthesis")
    generated = _GATE.require_bool(payload["generated_scene_as_footage"], "generated_scene_as_footage")
    _GATE.require(parameters, "declared_parameters must name at least one parameter")
    scored = _GATE.score_recipe(payload["recipe"], "recipe")
    faults = list(scored["faults"])
    if any(name in CONTENT_CHANGES for name in parameters):
        faults.append(NOT_RENDER)
    if changes:
        faults.append(ALTERED)
    if synthesis:
        faults.append(SYNTHESIS)
    if generated:
        faults.append(NOT_FOOTAGE)
    record = {
        "declared_parameters": parameters,
        "content_changes": changes,
        "unrequested_synthesis": synthesis,
        "generated_scene_as_footage": generated,
        "report": scored["report"],
    }
    texts = {
        SYNTHESIS: "unrequested content synthesis is rejected",
        NOT_FOOTAGE: CASE["negative"],
        ALTERED: "parameter matching must not alter scene content",
        NOT_RENDER: "matching is restricted to declared rendering parameters",
    }
    return _GATE.case_result(CASE, evidence, repeat, faults, [record], texts)
