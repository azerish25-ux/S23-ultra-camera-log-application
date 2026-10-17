"""TC-P144-08 Preference mistaken for factual accuracy.

A popular reconstructed recipe may outscore a sourced alternative on stars
and enjoyment. Popularity does not certify stock or lens identification.
Evidence completeness stays separate from appearance preference.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P144-08",
    "phase": "P144",
    "workstream": 18,
    "name": "Preference mistaken for factual accuracy",
    "intervention": "Give a popular reconstructed recipe higher user ratings than a well-sourced alternative.",
    "expected": "Keep appearance preference separate from evidence completeness and historical claims.",
    "negative": "Popularity cannot certify a stock or lens identification.",
    "repeat": "Repeat blind comparisons, expert review, and conflicting production sources.",
}

POPULARITY = "popularity-cannot-certify-stock-or-lens-identification"
PREFERENCE_MERGED = "appearance-preference-merged-with-evidence-completeness"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "popular",
    "sourced",
    "popularity_certifies_identification",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p144_validate_recipe_fidelity_and_honesty.py"
    spec = importlib.util.spec_from_file_location("p144_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _higher(left: dict, right: dict) -> bool:
    left_star = left["star_rating"]
    right_star = right["star_rating"]
    left_enjoy = left["enjoyment"]
    right_enjoy = right["enjoyment"]
    star_higher = (
        left_star is not None and right_star is not None and left_star > right_star
    )
    enjoy_higher = (
        left_enjoy is not None and right_enjoy is not None and left_enjoy > right_enjoy
    )
    return star_higher or enjoy_higher


def evaluate(payload: dict) -> dict:
    _GATE.require_keys(payload, set(PAYLOAD_KEYS))
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    certifies = _GATE.require_bool(
        payload["popularity_certifies_identification"], "popularity_certifies_identification"
    )
    popular = _GATE.score_recipe(payload["popular"], "popular")
    sourced = _GATE.score_recipe(payload["sourced"], "sourced")
    faults = list(popular["faults"]) + list(sourced["faults"])
    if certifies:
        faults.append(POPULARITY)
    popular_report = popular["report"]
    sourced_report = sourced["report"]
    claimed_correct = popular["recipe"]["identification"]["status"] == "correct"
    if _higher(popular["recipe"], sourced["recipe"]) and claimed_correct and not popular_report["identification"]["correct"]:
        faults.append(PREFERENCE_MERGED)
    record = {
        "popular": popular_report,
        "sourced": sourced_report,
        "popularity_certifies_identification": certifies,
        "preference_separate": not certifies and not popular_report["identification"]["correct"],
    }
    texts = {
        POPULARITY: CASE["negative"],
        PREFERENCE_MERGED: "appearance preference must stay separate from evidence completeness",
    }
    return _GATE.case_result(CASE, evidence, repeat, faults, [record], texts)
