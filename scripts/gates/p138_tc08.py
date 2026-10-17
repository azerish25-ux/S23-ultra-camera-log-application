"""TC-P138-08 Preference mistaken for factual accuracy.

Host fixture. User ratings order appearance preference only. A popular
reconstruction does not certify stock or lens. Historical claims stay with
traced production facts.
"""

from __future__ import annotations

import math
import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P138-08",
    "phase": "P138",
    "workstream": 18,
    "name": "Preference mistaken for factual accuracy",
    "intervention": "Give a popular reconstructed recipe higher user ratings than a well-sourced alternative.",
    "expected": "Keep appearance preference separate from evidence completeness and historical claims.",
    "negative": "Popularity cannot certify a stock or lens identification.",
    "repeat": "Repeat blind comparisons, expert review, and conflicting production sources.",
}

NEGATIVE_TOKEN = "popularity-certifies-stock-or-lens"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "family",
    "max_entries",
    "ratings",
    "claimedFactualRecipeId",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p138_build_the_first_sourced_recipe_family.py"
    spec = importlib.util.spec_from_file_location("p138_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def parse_ratings(raw: object, recipe_ids: set[str]) -> dict[str, float]:
    _GATE.require(isinstance(raw, dict), "ratings must be an object")
    _GATE.require(set(raw) == recipe_ids, "ratings must cover every recipe and no others")
    ratings: dict[str, float] = {}
    for recipe_id, value in raw.items():
        _GATE.require(
            isinstance(value, (int, float)) and not isinstance(value, bool),
            "rating must be a number",
        )
        number = float(value)
        _GATE.require(math.isfinite(number) and number >= 0, "rating must be a finite non-negative number")
        ratings[recipe_id] = number
    return ratings


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_family_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    entries = bundle["analysis"]["entries"]
    ratings = parse_ratings(payload["ratings"], {entry["recipe_id"] for entry in entries})
    claimed = payload["claimedFactualRecipeId"]
    if claimed is not None:
        claimed = _GATE.require_text(claimed, "claimedFactualRecipeId")
        _GATE.require(claimed in ratings, "claimed factual recipe is not in the family")
    by_id = {entry["recipe_id"]: entry for entry in entries}
    highest_id = min(
        (recipe_id for recipe_id, _rating in ratings.items()),
        key=lambda recipe_id: (-ratings[recipe_id], recipe_id),
    )
    sourced_ids = [entry["recipe_id"] for entry in entries if entry["traces"]]
    if claimed is not None:
        target = by_id[claimed]
        popular = ratings[claimed] == ratings[highest_id]
        traced_claim = bool(target["traces"]) and not target["reconstruction"]
        if popular and (target["reconstruction"] or not traced_claim):
            faults.append(NEGATIVE_TOKEN)
        elif not traced_claim:
            faults.append(NEGATIVE_TOKEN)
    extra = [{
        "highestRatedRecipeId": highest_id,
        "highestRating": ratings[highest_id],
        "sourcedRecipeIds": sourced_ids,
        "claimedFactualRecipeId": claimed,
        "preferenceSeparateFromEvidence": NEGATIVE_TOKEN not in faults,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {NEGATIVE_TOKEN: CASE["negative"]},
    )
