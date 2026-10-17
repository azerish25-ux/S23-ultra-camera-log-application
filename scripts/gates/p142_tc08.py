"""TC-P142-08 Preference mistaken for factual accuracy.

Host reference. User rating order is stored apart from evidence completeness.
A popular recipe cannot certify a stock or a lens.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P142-08",
    "phase": "P142",
    "workstream": 18,
    "name": "Preference mistaken for factual accuracy",
    "intervention": "Give a popular reconstructed recipe higher user ratings than a well-sourced alternative.",
    "expected": "Keep appearance preference separate from evidence completeness and historical claims.",
    "negative": "Popularity cannot certify a stock or lens identification.",
    "repeat": "Repeat blind comparisons, expert review, and conflicting production sources.",
}

NEGATIVE_TOKEN = "popularity-cannot-certify-stock-or-lens"
PREFERENCE_AS_EVIDENCE = "preference-substituted-for-evidence"
RECIPE_KEYS = {
    "id",
    "rating",
    "evidenceComplete",
    "certifiesStock",
    "certifiesLens",
    "historicalClaim",
}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "source",
    "reference",
    "suggestion",
    "recipes",
    "evidenceRanking",
    "preferenceRanking",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p142_implement_constrained_reference_matching.py"
    spec = importlib.util.spec_from_file_location("p142_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def clean_recipes():
    return [
        {
            "id": "popular",
            "rating": 4.8,
            "evidenceComplete": False,
            "certifiesStock": False,
            "certifiesLens": False,
            "historicalClaim": False,
        },
        {
            "id": "sourced",
            "rating": 3.2,
            "evidenceComplete": True,
            "certifiesStock": True,
            "certifiesLens": True,
            "historicalClaim": True,
        },
    ]


def evidence_order(recipes: list[dict]) -> list[str]:
    ordered = sorted(recipes, key=lambda recipe: (not recipe["evidenceComplete"], recipe["id"]))
    return [recipe["id"] for recipe in ordered]


def preference_order(recipes: list[dict]) -> list[str]:
    ordered = sorted(recipes, key=lambda recipe: (-recipe["rating"], recipe["id"]))
    return [recipe["id"] for recipe in ordered]


def _ids(value: object, label: str) -> list[str]:
    _GATE.require(isinstance(value, list) and value, label + " must be a non-empty list")
    return [_GATE.require_text(item, label) for item in value]


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    raw = payload["recipes"]
    _GATE.require(isinstance(raw, list) and len(raw) >= 2, "recipes needs at least two entries")
    recipes = []
    seen = set()
    for index, item in enumerate(raw):
        label = "recipes[" + str(index) + "]"
        _GATE.require(isinstance(item, dict) and set(item) == RECIPE_KEYS, label + " keys are invalid")
        recipe_id = _GATE.require_text(item["id"], label + ".id")
        _GATE.require(recipe_id not in seen, "duplicate recipe id")
        seen.add(recipe_id)
        rating = _GATE.require_number(item["rating"], label + ".rating")
        complete = _GATE.require_bool(item["evidenceComplete"], label + ".evidenceComplete")
        stock = _GATE.require_bool(item["certifiesStock"], label + ".certifiesStock")
        lens = _GATE.require_bool(item["certifiesLens"], label + ".certifiesLens")
        historical = _GATE.require_bool(item["historicalClaim"], label + ".historicalClaim")
        if not complete and (stock or lens or historical):
            faults.append(NEGATIVE_TOKEN)
        recipes.append({
            "id": recipe_id,
            "rating": rating,
            "evidenceComplete": complete,
            "certifiesStock": stock,
            "certifiesLens": lens,
            "historicalClaim": historical,
        })
    evidence_ranking = _ids(payload["evidenceRanking"], "evidenceRanking")
    preference_ranking = _ids(payload["preferenceRanking"], "preferenceRanking")
    expected_evidence = evidence_order(recipes)
    expected_preference = preference_order(recipes)
    if evidence_ranking != expected_evidence or preference_ranking != expected_preference:
        faults.append(PREFERENCE_AS_EVIDENCE)
    if evidence_ranking == preference_ranking and expected_evidence != expected_preference:
        faults.append(PREFERENCE_AS_EVIDENCE)
    extra = [{
        "evidenceRanking": expected_evidence,
        "preferenceRanking": expected_preference,
        "ratingsSeparateFromEvidence": expected_evidence != expected_preference,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            PREFERENCE_AS_EVIDENCE: CASE["expected"],
        },
    )
