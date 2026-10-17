"""TC-P143-07 Parameter matching alters content.

Host reference. Look matching may change only declared rendering parameters.
Facial geometry, texture replacement, and other content synthesis are rejected.
A generated scene is not preserved camera footage. Release looks stay distinct.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P143-07",
    "phase": "P143",
    "workstream": 18,
    "name": "Parameter matching alters content",
    "intervention": "Use an automatic look suggestion that changes facial geometry or replaces scene texture.",
    "expected": "Reject unrequested content synthesis and restrict matching to declared rendering parameters.",
    "negative": "A visually similar generated scene is not preserved camera footage.",
    "repeat": "Repeat faces, text, fine patterns, and moving objects.",
}

NEGATIVE_TOKEN = "unrequested-content-synthesis"
NOT_CAMERA = "generated-scene-is-not-camera-footage"
OUTSIDE = "matching-outside-declared-parameters"
CONTENT = frozenset({"faces", "text", "fine-patterns", "moving-objects"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "looks",
    "dropAmbiguous",
    "suggestionApplied",
    "declaredParameters",
    "changedContent",
    "facialGeometryChanged",
    "sceneTextureReplaced",
    "contentSynthesis",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p143_support_release_specific_and_scene_specific_looks.py"
    spec = importlib.util.spec_from_file_location("p143_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    applied = _GATE.require_bool(payload["suggestionApplied"], "suggestionApplied")
    declared_value = payload["declaredParameters"]
    _GATE.require(isinstance(declared_value, list), "declaredParameters must be a list")
    declared = []
    for index, item in enumerate(declared_value):
        declared.append(_GATE.require_text(item, f"declaredParameters[{index}]"))
    changed_value = payload["changedContent"]
    _GATE.require(isinstance(changed_value, list), "changedContent must be a list")
    changed = []
    for index, item in enumerate(changed_value):
        name = _GATE.require_text(item, f"changedContent[{index}]")
        _GATE.require(name in CONTENT, "changedContent item is not a content class")
        changed.append(name)
    facial = _GATE.require_bool(payload["facialGeometryChanged"], "facialGeometryChanged")
    texture = _GATE.require_bool(payload["sceneTextureReplaced"], "sceneTextureReplaced")
    synthesis = _GATE.require_bool(payload["contentSynthesis"], "contentSynthesis")
    if facial or texture or synthesis or changed:
        faults.append(NEGATIVE_TOKEN)
        faults.append(NOT_CAMERA)
    if applied:
        allowed = set(declared)
        outside = sorted({
            key
            for look in bundle["looks"]
            for key in look["parameters"]
            if key not in allowed
        })
        if outside:
            faults.append(OUTSIDE)
    extra = [{
        "suggestionApplied": applied,
        "declaredParameters": declared,
        "changedContent": changed,
        "facialGeometryChanged": facial,
        "sceneTextureReplaced": texture,
        "contentSynthesis": synthesis,
    }]
    return _GATE.finish_case(CASE, bundle, faults, extra, {
        NEGATIVE_TOKEN: CASE["negative"],
        NOT_CAMERA: "a visually similar generated scene is not preserved camera footage",
        OUTSIDE: "matching is restricted to declared rendering parameters",
    })
