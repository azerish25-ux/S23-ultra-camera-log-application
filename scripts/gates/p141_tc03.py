"""TC-P141-03 Creative edit overwrites evidence.

Host fixture. A user derivative may change virtual aperture, grade, or grain
only by creating a new reconstruction version. Historical lens, stock, and
process facts stay untouched. Rights are still judged per asset.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P141-03",
    "phase": "P141",
    "workstream": 18,
    "name": "Creative edit overwrites evidence",
    "intervention": "Change virtual aperture, grade, or grain inside a user derivative recipe.",
    "expected": "Create a new reconstruction version without altering historical production facts.",
    "negative": "User preferences must not replace the cinematographer\u2019s sourced metadata.",
    "repeat": "Repeat recipe save, rename, share, and update from a newer catalogue package.",
}

NEGATIVE_TOKEN = "user-preference-replaces-sourced-metadata"
SAME_VERSION = "derivative-reuses-historical-version"
HISTORICAL_KEYS = {"lens", "stock", "process"}
DERIVATIVE_KEYS = {"version_id", "virtual_aperture", "grade", "grain", "lens", "stock", "process"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "assets",
    "historical",
    "derivative",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p141_manage_reference_media_rights_and_attribution.py"
    spec = importlib.util.spec_from_file_location("p141_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _historical(value: object) -> dict:
    _GATE.require(isinstance(value, dict) and set(value) == HISTORICAL_KEYS, "historical keys are invalid")
    return {
        "lens": _GATE.require_text(value["lens"], "historical.lens"),
        "stock": _GATE.require_text(value["stock"], "historical.stock"),
        "process": _GATE.require_text(value["process"], "historical.process"),
    }


def _derivative(value: object) -> dict:
    _GATE.require(isinstance(value, dict) and set(value) == DERIVATIVE_KEYS, "derivative keys are invalid")
    return {
        "version_id": _GATE.require_text(value["version_id"], "derivative.version_id"),
        "virtual_aperture": _GATE.require_text(value["virtual_aperture"], "derivative.virtual_aperture"),
        "grade": _GATE.require_text(value["grade"], "derivative.grade"),
        "grain": _GATE.require_text(value["grain"], "derivative.grain"),
        "lens": _GATE.require_text(value["lens"], "derivative.lens"),
        "stock": _GATE.require_text(value["stock"], "derivative.stock"),
        "process": _GATE.require_text(value["process"], "derivative.process"),
    }


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    historical = _historical(payload["historical"])
    derivative = _derivative(payload["derivative"])
    replaced = [key for key in ("lens", "stock", "process") if derivative[key] != historical[key]]
    if replaced:
        faults.append(NEGATIVE_TOKEN)
    if derivative["version_id"] == "historical":
        faults.append(SAME_VERSION)
    extra = [{
        "historical": historical,
        "version_id": derivative["version_id"],
        "virtual_aperture": derivative["virtual_aperture"],
        "grade": derivative["grade"],
        "grain": derivative["grain"],
        "replacedFacts": replaced,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            SAME_VERSION: "a creative edit must create a new reconstruction version",
        },
    )
