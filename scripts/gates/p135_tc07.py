"""TC-P135-07 Unfair comparison view.

Host fixture. Matched source hashes and frame indexes are required. A
non-zero sync offset must be disclosed. contrast_boost other than 1 and
automatic contrast boost are rejected. A preference on an unfair comparison
is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P135-07",
    "phase": "P135",
    "workstream": 17,
    "name": "Unfair comparison view",
    "intervention": "Compare outputs at different times, scales, or display transforms without making those differences visible.",
    "expected": "Align comparable content or clearly disclose the mismatch before presenting a preference judgment.",
    "negative": "Automatically enhancing one side of a comparison must fail.",
    "repeat": "Repeat source-versus-result, recipe revisions, and different output aspect ratios.",
}

PREFERENCE_UNFAIR = "preference-on-unfair-comparison"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "comparison",
    "preferenceJudgment",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p135_build_side_by_side_comparison_tools.py"
    spec = importlib.util.spec_from_file_location("p135_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    preference = _GATE.require_bool(payload["preferenceJudgment"], "preferenceJudgment")
    unfair = any(token in faults for token in _GATE.UNFAIR_TOKENS)
    if preference and unfair:
        faults.append(PREFERENCE_UNFAIR)
    extra = [{
        "preferenceJudgment": preference,
        "matchedInputs": bundle["info"]["matchedInputs"],
        "framesMatch": bundle["info"]["framesMatch"],
        "sourcesMatch": bundle["info"]["sourcesMatch"],
        "contrastBoostUnity": bundle["info"]["contrastBoostUnity"],
        "automaticContrastBoost": bundle["info"]["automaticContrastBoost"],
        "offsetAccepted": bundle["info"]["offsetAccepted"],
        "unfair": unfair,
    }]
    texts = {
        _GATE.AUTOMATIC_CONTRAST_BOOST: CASE["negative"],
        _GATE.CONTRAST_NOT_UNITY: CASE["negative"],
        PREFERENCE_UNFAIR: "a preference requires aligned content or a disclosed mismatch",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
