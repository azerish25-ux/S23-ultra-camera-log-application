"""TC-P139-08 Preference mistaken for factual accuracy.

Host fixture. User rating is a preference. The historical stock or lens claim
stays with the reconstruction that matches production facts. Popularity cannot
certify an identification the facts do not support.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P139-08"
NAME = "Preference mistaken for factual accuracy"
INTERVENTION = "Give a popular reconstructed recipe higher user ratings than a well-sourced alternative."
EXPECTED = "Keep appearance preference separate from evidence completeness and historical claims."
NEGATIVE = "Popularity cannot certify a stock or lens identification."
REPEAT = "Repeat blind comparisons, expert review, and conflicting production sources."
NEGATIVE_TOKEN = "popularity-certified-stock-or-lens"
ALLOWED_REPEATS = {"blind-comparison", "expert-review", "conflicting-sources", REPEAT}
EVIDENCE_STATES = {"documented", "creative", "unknown"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "recipes",
    "chosenId",
    "productionFacts",
    "fact_hash",
    "prior_canonical",
    "reconstructions",
    "mutated_facts",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_SPEC = importlib.util.spec_from_file_location(
    "p139_version_creative_reconstruction_parameters",
    Path(__file__).resolve().parent / "p139_version_creative_reconstruction_parameters.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _optional_text(value, label: str):
    if value is None:
        return None
    return _CORE.require_text(value, label)


def _recipes(value):
    if not isinstance(value, list) or len(value) < 2:
        raise ValueError("recipes must list at least two reconstructions")
    parsed = []
    seen = set()
    for index, item in enumerate(value):
        if type(item) is not dict or set(item) != {"id", "rating", "evidence", "stock", "lens"}:
            raise ValueError(f"recipes[{index}] keys are invalid")
        rating = item["rating"]
        if type(rating) is bool or not isinstance(rating, (int, float)):
            raise ValueError(f"recipes[{index}].rating must be a number")
        if type(rating) is float and rating != rating:
            raise ValueError(f"recipes[{index}].rating must be finite")
        evidence = item["evidence"]
        if evidence not in EVIDENCE_STATES:
            raise ValueError(f"recipes[{index}].evidence is invalid")
        recipe_id = _CORE.require_id(item["id"], f"recipes[{index}].id")
        if recipe_id in seen:
            raise ValueError("recipe id repeated")
        seen.add(recipe_id)
        parsed.append(
            {
                "id": recipe_id,
                "rating": rating,
                "evidence": evidence,
                "stock": _optional_text(item["stock"], f"recipes[{index}].stock"),
                "lens": _optional_text(item["lens"], f"recipes[{index}].lens"),
            }
        )
    return parsed


def _matches_facts(recipe: dict, facts: dict) -> bool:
    if recipe["evidence"] != "documented":
        return False
    if recipe["stock"] is not None and recipe["stock"] != facts["stock"]:
        return False
    if recipe["lens"] is not None and recipe["lens"] != facts["lens"]:
        return False
    if recipe["lens"] is not None and facts["lens"] is None:
        return False
    return True


def _certifies(recipe: dict, facts: dict) -> bool:
    if recipe["stock"] is not None and recipe["stock"] != facts["stock"]:
        return True
    if recipe["lens"] is not None and recipe["lens"] != facts["lens"]:
        return True
    if recipe["lens"] is not None and facts["lens"] is None:
        return True
    if recipe["evidence"] != "documented" and (recipe["stock"] is not None or recipe["lens"] is not None):
        return True
    if recipe["evidence"] != "documented":
        return True
    return False


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _CORE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _CORE.require_text(payload["repeat"], "repeat")
    if repeat not in ALLOWED_REPEATS:
        raise ValueError("repeat is not a preference comparison")
    recipes = _recipes(payload["recipes"])
    chosen_id = payload["chosenId"]
    if chosen_id is not None:
        chosen_id = _CORE.require_id(chosen_id, "chosenId")
    review = _CORE.review_reconstructions(
        payload["productionFacts"],
        payload["reconstructions"],
        declared_fact_hash=payload["fact_hash"],
        prior_canonical=payload["prior_canonical"],
        mutated_facts=payload["mutated_facts"],
        bound_object_id=None,
    )
    facts = _CORE.parse_facts(payload["productionFacts"], "productionFacts")
    popular = max(recipes, key=lambda recipe: (recipe["rating"], recipe["id"]))
    historical = [recipe for recipe in recipes if _matches_facts(recipe, facts)]
    faults = list(review["faults"])
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION, f"repeat {repeat}"]
    reasons.extend(review["reasons"])
    reasons.append("preference=" + popular["id"])
    if historical:
        claim = sorted(historical, key=lambda recipe: recipe["id"])[0]
        reasons.append("historicalClaim=" + claim["id"])
        historical_id = claim["id"]
    else:
        reasons.append("historicalClaim=uncertain")
        historical_id = "uncertain"
    if popular["id"] != historical_id:
        reasons.append("appearance preference stays separate from the historical claim")
    by_id = {recipe["id"]: recipe for recipe in recipes}
    if chosen_id is not None:
        if chosen_id not in by_id:
            raise ValueError("chosenId is not a recipe")
        chosen = by_id[chosen_id]
        if _certifies(chosen, facts):
            faults.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
    documented_stocks = sorted(
        {
            recipe["stock"]
            for recipe in recipes
            if recipe["evidence"] == "documented" and recipe["stock"] is not None
        }
    )
    preserved = [evidence, "preference=" + popular["id"], "historicalClaim=" + historical_id]
    if len(documented_stocks) > 1:
        preserved.append("conflictingStocks=" + ",".join(documented_stocks))
        reasons.append("conflicting documented stocks remain unresolved")
    preserved.extend(review["preserved"])
    result = _CORE.finish_result(
        CASE_ID,
        reasons,
        faults,
        preserved,
        [_CORE.OPEN_QUESTION, REPEAT],
    )
    if tuple(result) != RESULT_KEYS or evidence not in result["preservedResults"]:
        raise ValueError("result contract drifted")
    return result
