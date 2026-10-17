"""TC-P138-04 Offline search ambiguity.

Host fixture. Misspelled titles, aliases, and stock names resolve against the
local family only. A remote generation call is not required for that lookup.
Matching does not invent stock or lens values.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P138-04",
    "phase": "P138",
    "workstream": 18,
    "name": "Offline search ambiguity",
    "intervention": "Search misspelled titles, alternate titles, or stock names without network access.",
    "expected": "Return relevant local candidates with transparent matching and evidence status.",
    "negative": "A remote generation call must not be required for basic catalogue lookup.",
    "repeat": "Repeat filtered searches for format, monochrome, and scene family.",
}

NEGATIVE_TOKEN = "remote-generation-required-for-catalogue-lookup"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "family",
    "max_entries",
    "query",
    "aliases",
    "networkRequired",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p138_build_the_first_sourced_recipe_family.py"
    spec = importlib.util.spec_from_file_location("p138_gate_for_tc04", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def spelling_distance(query: str, candidate: str, limit: int = 2) -> int | None:
    left = query.casefold()
    right = candidate.casefold()
    if left == right:
        return 0
    if len(left) < 4 or len(right) < 4 or abs(len(left) - len(right)) > limit:
        return None
    previous = list(range(len(right) + 1))
    for i, ca in enumerate(left, 1):
        current = [i]
        lowest = i
        for j, cb in enumerate(right, 1):
            best = min(current[j - 1] + 1, previous[j] + 1, previous[j - 1] + (ca != cb))
            current.append(best)
            if best < lowest:
                lowest = best
        if lowest > limit:
            return None
        previous = current
    distance = previous[-1]
    return distance if distance <= limit else None


def parse_aliases(raw: object, recipe_ids: set[str]) -> dict[str, list[str]]:
    _GATE.require(isinstance(raw, dict), "aliases must be an object")
    parsed: dict[str, list[str]] = {}
    for recipe_id, titles in raw.items():
        key = _GATE.require_text(recipe_id, "alias recipe_id")
        _GATE.require(key in recipe_ids, "alias recipe_id is not in the family")
        _GATE.require(isinstance(titles, list), "alias titles must be a list")
        names = [_GATE.require_text(title, "alias") for title in titles]
        parsed[key] = names
    return parsed


def local_candidates(entries: list[dict], query: str, aliases: dict[str, list[str]]) -> list[dict]:
    found: list[dict] = []
    for entry in entries:
        options: list[tuple[int, int, str]] = []
        title_distance = spelling_distance(query, entry["film_title"])
        if title_distance is not None:
            options.append((title_distance, 0, "film_title"))
        for alias in aliases.get(entry["recipe_id"], []):
            alias_distance = spelling_distance(query, alias)
            if alias_distance is not None:
                options.append((alias_distance, 1, "alias"))
        if isinstance(entry["stock"], str):
            stock_distance = spelling_distance(query, entry["stock"])
            if stock_distance is not None:
                options.append((stock_distance, 2, "stock"))
        if isinstance(entry["lens"], str):
            lens_distance = spelling_distance(query, entry["lens"])
            if lens_distance is not None:
                options.append((lens_distance, 3, "lens"))
        if query.casefold() == entry["variant"]:
            options.append((0, 4, "variant"))
        if not options:
            continue
        distance, _priority, matched_on = min(options)
        found.append({
            "recipe_id": entry["recipe_id"],
            "film_title": entry["film_title"],
            "matchedOn": matched_on,
            "distance": distance,
            "evidenceStatus": "sourced" if entry["traces"] else "unknown",
            "stock": entry["stock"],
            "lens": entry["lens"],
        })
    found.sort(key=lambda item: (item["distance"], item["recipe_id"]))
    return found


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_family_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    query = _GATE.require_text(payload["query"], "query")
    network = _GATE.require_bool(payload["networkRequired"], "networkRequired")
    entries = bundle["analysis"]["entries"]
    aliases = parse_aliases(payload["aliases"], {entry["recipe_id"] for entry in entries})
    candidates = local_candidates(entries, query, aliases)
    if network:
        faults.append(NEGATIVE_TOKEN)
    if candidates:
        summary = ", ".join(
            f"{item['recipe_id']} via {item['matchedOn']} distance={item['distance']} {item['evidenceStatus']}"
            for item in candidates
        )
        match_reason = "local candidates: " + summary
    else:
        match_reason = "no local candidate; stock and lens were not invented"
    result = _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [{"query": query, "networkRequired": network, "candidates": candidates}],
        {NEGATIVE_TOKEN: CASE["negative"]},
    )
    result["reasons"].insert(4, match_reason)
    return result
