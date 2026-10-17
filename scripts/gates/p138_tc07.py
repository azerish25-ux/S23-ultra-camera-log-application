"""TC-P138-07 Parameter matching alters content.

Host fixture. Look matching may name declared rendering parameters only.
Facial geometry, texture replacement, and other content synthesis are rejected.
A generated scene is not preserved camera footage.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P138-07",
    "phase": "P138",
    "workstream": 18,
    "name": "Parameter matching alters content",
    "intervention": "Use an automatic look suggestion that changes facial geometry or replaces scene texture.",
    "expected": "Reject unrequested content synthesis and restrict matching to declared rendering parameters.",
    "negative": "A visually similar generated scene is not preserved camera footage.",
    "repeat": "Repeat faces, text, fine patterns, and moving objects.",
}

NEGATIVE_TOKEN = "generated-scene-is-not-preserved-camera-footage"
SYNTHESIS = "unrequested-content-synthesis"
DECLARED = {"virtual-aperture", "grade", "grain", "halation", "diffusion"}
CONTENT = {"facial-geometry", "scene-texture", "faces", "text", "fine-patterns", "moving-objects"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "family",
    "max_entries",
    "declaredParameters",
    "contentChanges",
    "acceptGeneratedScene",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p138_build_the_first_sourced_recipe_family.py"
    spec = importlib.util.spec_from_file_location("p138_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _tokens(value: object, allowed: set[str], label: str) -> list[str]:
    _GATE.require(isinstance(value, list), label + " must be a list")
    parsed: list[str] = []
    for index, item in enumerate(value):
        token = _GATE.require_text(item, f"{label}[{index}]")
        _GATE.require(token in allowed, label + " contains an undeclared token")
        _GATE.require(token not in parsed, "duplicate " + label)
        parsed.append(token)
    return parsed


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_family_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    declared = _tokens(payload["declaredParameters"], DECLARED | CONTENT, "declaredParameters")
    changes = _tokens(payload["contentChanges"], CONTENT, "contentChanges")
    accept_generated = _GATE.require_bool(payload["acceptGeneratedScene"], "acceptGeneratedScene")
    rendering = [item for item in declared if item in DECLARED]
    if any(item in CONTENT for item in declared) or changes:
        faults.append(SYNTHESIS)
    if accept_generated:
        faults.append(NEGATIVE_TOKEN)
    if not rendering and SYNTHESIS not in faults and NEGATIVE_TOKEN not in faults:
        raise ValueError("matching requires at least one declared rendering parameter")
    extra = [{
        "declaredParameters": rendering,
        "contentChanges": changes,
        "acceptGeneratedScene": accept_generated,
        "stockUnchanged": [entry["stock"] for entry in bundle["analysis"]["entries"]],
        "lensUnchanged": [entry["lens"] for entry in bundle["analysis"]["entries"]],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            SYNTHESIS: "matching is restricted to declared rendering parameters",
        },
    )
