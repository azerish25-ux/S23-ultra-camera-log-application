"""TC-P143-08 Preference mistaken for factual accuracy.

Host reference. Appearance preference stays separate from evidence completeness
and historical claims. Popularity cannot certify a stock or lens identification.
Release looks stay distinct.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P143-08",
    "phase": "P143",
    "workstream": 18,
    "name": "Preference mistaken for factual accuracy",
    "intervention": "Give a popular reconstructed recipe higher user ratings than a well-sourced alternative.",
    "expected": "Keep appearance preference separate from evidence completeness and historical claims.",
    "negative": "Popularity cannot certify a stock or lens identification.",
    "repeat": "Repeat blind comparisons, expert review, and conflicting production sources.",
}

NEGATIVE_TOKEN = "popularity-certifies-identification"
STATUSES = frozenset({"reconstructed", "sourced"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "looks",
    "dropAmbiguous",
    "appearancePreference",
    "evidenceCompleteness",
    "recipeStatus",
    "popularityCertifies",
    "certifiedIdentification",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p143_support_release_specific_and_scene_specific_looks.py"
    spec = importlib.util.spec_from_file_location("p143_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    preference = _GATE.require_number(payload["appearancePreference"], "appearancePreference")
    completeness = _GATE.require_number(payload["evidenceCompleteness"], "evidenceCompleteness")
    status = _GATE.require_text(payload["recipeStatus"], "recipeStatus")
    _GATE.require(status in STATUSES, "recipeStatus is not recognized")
    popularity = _GATE.require_bool(payload["popularityCertifies"], "popularityCertifies")
    identification = payload["certifiedIdentification"]
    if identification is not None:
        identification = _GATE.require_text(identification, "certifiedIdentification")
    if popularity or (identification is not None and status == "reconstructed"):
        faults.append(NEGATIVE_TOKEN)
    extra = [{
        "appearancePreference": preference,
        "evidenceCompleteness": completeness,
        "recipeStatus": status,
        "popularityCertifies": popularity,
        "certifiedIdentification": identification,
        "preferenceSeparateFromEvidence": True,
    }]
    return _GATE.finish_case(CASE, bundle, faults, extra, {NEGATIVE_TOKEN: CASE["negative"]})
