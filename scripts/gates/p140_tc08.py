"""TC-P140-08 Preference mistaken for factual accuracy.

Host reference. Evidence completeness orders recipes. Popularity and user
ratings do not certify stock or lens identification.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P140-08",
    "phase": "P140",
    "workstream": 18,
    "name": "Preference mistaken for factual accuracy",
    "intervention": "Give a popular reconstructed recipe higher user ratings than a well-sourced alternative.",
    "expected": "Keep appearance preference separate from evidence completeness and historical claims.",
    "negative": "Popularity cannot certify a stock or lens identification.",
    "repeat": "Repeat blind comparisons, expert review, and conflicting production sources.",
}
NEGATIVE_TOKEN = "popularity-cannot-certify-stock-or-lens-identification"
POPULARITY_SORT = "invented-popularity-sort"
RECIPE_KEYS = ("id", "stock", "lens", "evidenceCompleteness", "popularity", "preferenceRating")
COMPLETENESS = frozenset({"documented", "partial", "unknown", "preference"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "recipes",
    "sort",
    "query",
    "popularityCertifiesStock",
    "popularityCertifiesLens",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p140_implement_offline_search_and_filtering.py"
    spec = importlib.util.spec_from_file_location("p140_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    recipes = payload["recipes"]
    _GATE.require(isinstance(recipes, list) and len(recipes) >= 2, "recipes must contain at least two alternatives")
    parsed: list[dict] = []
    seen: set[str] = set()
    for index, recipe in enumerate(recipes):
        _GATE.require(isinstance(recipe, dict) and set(recipe) == set(RECIPE_KEYS), f"recipes[{index}] keys are invalid")
        recipe_id = _GATE.require_text(recipe["id"], f"recipes[{index}].id")
        _GATE.require(recipe_id not in seen, "duplicate recipe id")
        seen.add(recipe_id)
        completeness = _GATE.require_text(recipe["evidenceCompleteness"], f"recipes[{index}].evidenceCompleteness")
        _GATE.require(completeness in COMPLETENESS, "evidenceCompleteness is not recognized")
        parsed.append({
            "id": recipe_id,
            "stock": _GATE.require_text(recipe["stock"], f"recipes[{index}].stock"),
            "lens": _GATE.require_text(recipe["lens"], f"recipes[{index}].lens"),
            "evidenceCompleteness": completeness,
            "popularity": _GATE.require_number(recipe["popularity"], f"recipes[{index}].popularity"),
            "preferenceRating": _GATE.require_number(recipe["preferenceRating"], f"recipes[{index}].preferenceRating"),
        })
    sort = _GATE.require_text(payload["sort"], "sort")
    _GATE.require(sort in {"id", "evidenceCompleteness", "popularity"}, "sort is not recognized")
    query = _GATE.require_text(payload["query"], "query")
    certifies_stock = _GATE.require_bool(payload["popularityCertifiesStock"], "popularityCertifiesStock")
    certifies_lens = _GATE.require_bool(payload["popularityCertifiesLens"], "popularityCertifiesLens")
    faults: list[str] = []
    if certifies_stock or certifies_lens:
        faults.append(NEGATIVE_TOKEN)
    if sort == "popularity":
        faults.append(POPULARITY_SORT)
    retrieve_sort = "id" if sort == "id" else "evidenceQuality"
    reported_sort = "id" if sort == "id" else "evidenceCompleteness"
    catalogue = [
        {
            "id": recipe["id"],
            "title": recipe["stock"] + " " + recipe["lens"],
            "stockNames": [recipe["stock"]],
            "lens": recipe["lens"],
            "evidenceQuality": recipe["evidenceCompleteness"],
            "evidenceStatus": recipe["evidenceCompleteness"],
            "popularity": recipe["popularity"],
            "privateRecipe": False,
        }
        for recipe in parsed
    ]
    index = _GATE.build_token_index(catalogue)
    found = _GATE.retrieve(index, query, sort=retrieve_sort)
    again = _GATE.retrieve(index, query, sort=retrieve_sort)
    _GATE.require(found == again, "recipe lookup was not deterministic")
    by_popularity = [recipe["id"] for recipe in sorted(parsed, key=lambda item: (-item["popularity"], item["id"]))]
    preserved = [
        evidence,
        {
            "ids": found,
            "orderedBy": reported_sort,
            "popularityOrder": by_popularity,
            "popularityCertifies": False,
            "recipes": [
                {
                    "id": recipe["id"],
                    "evidenceCompleteness": recipe["evidenceCompleteness"],
                    "popularity": recipe["popularity"],
                    "preferenceRating": recipe["preferenceRating"],
                }
                for recipe in parsed
            ],
        },
    ]
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + _GATE.ORACLE,
        CASE["expected"],
        "repeat " + repeat,
        "orderedBy=" + reported_sort,
        "ids=" + ",".join(found),
    ]
    if NEGATIVE_TOKEN in faults:
        reasons.append(CASE["negative"])
    if not faults:
        reasons.append("preference stays separate from evidence completeness")
    return _GATE.finish_result(CASE["id"], evidence, faults, reasons, preserved, [CASE["repeat"], repeat])
