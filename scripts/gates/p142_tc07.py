"""TC-P142-07 Parameter matching alters content.

Host reference. Matching stays on declared exposure, contrast, and saturation.
Facial geometry, scene texture, stylization, and a changed hash labelled as
source footage are not preserved camera footage.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P142-07",
    "phase": "P142",
    "workstream": 18,
    "name": "Parameter matching alters content",
    "intervention": "Use an automatic look suggestion that changes facial geometry or replaces scene texture.",
    "expected": "Reject unrequested content synthesis and restrict matching to declared rendering parameters.",
    "negative": "A visually similar generated scene is not preserved camera footage.",
    "repeat": "Repeat faces, text, fine patterns, and moving objects.",
}

NEGATIVE_TOKEN = "visually-similar-generated-scene-is-not-camera-footage"
SYNTHESIS = "unrequested-content-synthesis"
SUBJECTS = {"faces", "text", "fine-patterns", "moving-objects"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "source",
    "reference",
    "suggestion",
    "subject",
    "altered",
    "visuallySimilar",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p142_implement_constrained_reference_matching.py"
    spec = importlib.util.spec_from_file_location("p142_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    subject = _GATE.require_text(payload["subject"], "subject")
    _GATE.require(subject in SUBJECTS, "subject is not recognized")
    altered = _GATE.require_bool(payload["altered"], "altered")
    similar = _GATE.require_bool(payload["visuallySimilar"], "visuallySimilar")
    suggestion = bundle["suggestion"]
    synthesized = altered or suggestion["changes_facial_geometry"] or suggestion["replaces_scene_texture"]
    generated = (
        suggestion["method"].casefold() == _GATE.METHOD_STYLIZE
        or not bundle["info"]["hashMatchesSource"]
        or synthesized
    )
    if synthesized:
        faults.append(SYNTHESIS)
    if similar and generated:
        faults.append(NEGATIVE_TOKEN)
    parameters = [suggestion[name] for name in _GATE.PARAMETER_NAMES]
    if any(not isinstance(item, float) for item in parameters):
        faults.append(SYNTHESIS)
    extra = [{
        "subject": subject,
        "altered": altered,
        "visuallySimilar": similar,
        "parameters": _GATE.PARAMETER_NAMES,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            SYNTHESIS: CASE["expected"],
        },
    )
