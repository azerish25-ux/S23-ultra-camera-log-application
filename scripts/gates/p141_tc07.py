"""TC-P141-07 Parameter matching alters content.

Host fixture. Automatic look matching may touch only declared rendering
parameters. Facial geometry, texture replacement, and other content synthesis
are rejected. A generated scene is not preserved camera footage. Rights are
still judged per asset.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P141-07",
    "phase": "P141",
    "workstream": 18,
    "name": "Parameter matching alters content",
    "intervention": "Use an automatic look suggestion that changes facial geometry or replaces scene texture.",
    "expected": "Reject unrequested content synthesis and restrict matching to declared rendering parameters.",
    "negative": "A visually similar generated scene is not preserved camera footage.",
    "repeat": "Repeat faces, text, fine patterns, and moving objects.",
}

NEGATIVE_TOKEN = "generated-scene-not-preserved-footage"
SYNTHESIS = "unrequested-content-synthesis"
OUTSIDE = "matching-outside-declared-parameters"
CONTENT_CHANGES = frozenset(
    {
        "faces",
        "text",
        "fine-patterns",
        "moving-objects",
        "facial-geometry",
        "scene-texture",
    }
)
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "assets",
    "declaredParameters",
    "changes",
    "presentedAsFootage",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p141_manage_reference_media_rights_and_attribution.py"
    spec = importlib.util.spec_from_file_location("p141_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _tokens(value: object, label: str) -> list[str]:
    _GATE.require(isinstance(value, list), label + " must be a list")
    parsed = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        token = _GATE.require_text(item, f"{label}[{index}]")
        _GATE.require(token not in seen, "duplicate " + label + " " + token)
        seen.add(token)
        parsed.append(token)
    return parsed


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    declared = _tokens(payload["declaredParameters"], "declaredParameters")
    changes = _tokens(payload["changes"], "changes")
    presented = _GATE.require_bool(payload["presentedAsFootage"], "presentedAsFootage")
    _GATE.require(len(declared) >= 1, "declaredParameters must name at least one rendering parameter")
    content = [token for token in changes if token in CONTENT_CHANGES]
    outside = [token for token in changes if token not in declared]
    if content:
        faults.append(SYNTHESIS)
    if outside:
        faults.append(OUTSIDE)
    if presented:
        faults.append(NEGATIVE_TOKEN)
    extra = [{
        "declaredParameters": declared,
        "changes": changes,
        "contentChanges": content,
        "outsideParameters": outside,
        "presentedAsFootage": presented,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            SYNTHESIS: "unrequested content synthesis is rejected",
            OUTSIDE: "matching is restricted to declared rendering parameters",
        },
    )
