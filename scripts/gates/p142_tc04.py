"""TC-P142-04 Offline search ambiguity.

Host reference. Misspelled titles, alternate titles, and stock names resolve
against a local catalogue. A remote generation call is not required.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P142-04",
    "phase": "P142",
    "workstream": 18,
    "name": "Offline search ambiguity",
    "intervention": "Search misspelled titles, alternate titles, or stock names without network access.",
    "expected": "Return relevant local candidates with transparent matching and evidence status.",
    "negative": "A remote generation call must not be required for basic catalogue lookup.",
    "repeat": "Repeat filtered searches for format, monochrome, and scene family.",
}

NEGATIVE_TOKEN = "remote-generation-required-for-catalogue-lookup"
OPAQUE_MATCH = "opaque-or-incorrect-local-match"
ENTRY_KEYS = {
    "id",
    "title",
    "alternateTitles",
    "stockNames",
    "format",
    "monochrome",
    "sceneFamily",
    "evidenceStatus",
}
FILTER_KEYS = {"format", "monochrome", "sceneFamily"}
HIT_KEYS = {"id", "match", "evidenceStatus"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "source",
    "reference",
    "suggestion",
    "offline",
    "query",
    "filters",
    "catalogue",
    "returned",
    "remoteGenerationRequired",
    "networkUsed",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p142_implement_constrained_reference_matching.py"
    spec = importlib.util.spec_from_file_location("p142_gate_for_tc04", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _norm(text: str) -> str:
    return "".join(ch for ch in text.casefold() if ch.isalnum())


def _levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for index, char in enumerate(left, 1):
        current = [index]
        for inner, other in enumerate(right, 1):
            insert = current[inner - 1] + 1
            delete = previous[inner] + 1
            substitute = previous[inner - 1] + (char != other)
            current.append(min(insert, delete, substitute))
        previous = current
    return previous[-1]


def _entry(value: object, label: str) -> dict:
    _GATE.require(isinstance(value, dict) and set(value) == ENTRY_KEYS, label + " keys are invalid")
    alternates = value["alternateTitles"]
    stocks = value["stockNames"]
    _GATE.require(isinstance(alternates, list), label + ".alternateTitles must be a list")
    _GATE.require(isinstance(stocks, list), label + ".stockNames must be a list")
    status = _GATE.require_text(value["evidenceStatus"], label + ".evidenceStatus")
    _GATE.require(status in {"known", "partial", "unknown"}, label + ".evidenceStatus is not recognized")
    return {
        "id": _GATE.require_text(value["id"], label + ".id"),
        "title": _GATE.require_text(value["title"], label + ".title"),
        "alternateTitles": [_GATE.require_text(item, label + ".alternateTitles") for item in alternates],
        "stockNames": [_GATE.require_text(item, label + ".stockNames") for item in stocks],
        "format": _GATE.require_text(value["format"], label + ".format"),
        "monochrome": _GATE.require_bool(value["monochrome"], label + ".monochrome"),
        "sceneFamily": _GATE.require_text(value["sceneFamily"], label + ".sceneFamily"),
        "evidenceStatus": status,
    }


def local_hits(catalogue: list[dict], query: str, filters: dict) -> list[dict]:
    folded = _norm(query)
    _GATE.require(bool(folded), "query must contain a searchable character")
    hits = []
    for entry in catalogue:
        if filters["format"] is not None and entry["format"] != filters["format"]:
            continue
        if filters["monochrome"] is not None and entry["monochrome"] is not filters["monochrome"]:
            continue
        if filters["sceneFamily"] is not None and entry["sceneFamily"] != filters["sceneFamily"]:
            continue
        names = [entry["title"], *entry["alternateTitles"], *entry["stockNames"]]
        best = None
        reason = None
        for name in names:
            normalized = _norm(name)
            if not normalized:
                continue
            distance = _levenshtein(folded, normalized)
            kind = None
            if distance == 0:
                kind = "exact"
            elif distance <= 2:
                kind = "edit-distance"
            elif folded in normalized or normalized in folded:
                kind = "substring"
            if kind is None:
                continue
            rank = {"exact": 0, "edit-distance": 1, "substring": 2}[kind]
            candidate = (rank, distance)
            if best is None or candidate < best:
                best = candidate
                reason = kind
        if reason is not None:
            hits.append({
                "id": entry["id"],
                "match": reason,
                "evidenceStatus": entry["evidenceStatus"],
            })
    return hits


def fixture_catalogue():
    return [
        {
            "id": "br",
            "title": "Blade Runner",
            "alternateTitles": ["BladeRunner"],
            "stockNames": ["5219"],
            "format": "35mm",
            "monochrome": False,
            "sceneFamily": "night-street",
            "evidenceStatus": "partial",
        },
        {
            "id": "br-mono",
            "title": "Blade Runner",
            "alternateTitles": [],
            "stockNames": ["5222"],
            "format": "35mm",
            "monochrome": True,
            "sceneFamily": "night-street",
            "evidenceStatus": "known",
        },
        {
            "id": "seven",
            "title": "Seven Samurai",
            "alternateTitles": ["Shichinin no Samurai"],
            "stockNames": [],
            "format": "35mm",
            "monochrome": True,
            "sceneFamily": "period",
            "evidenceStatus": "known",
        },
        {
            "id": "br2049",
            "title": "Blade Runner 2049",
            "alternateTitles": [],
            "stockNames": [],
            "format": "digital",
            "monochrome": False,
            "sceneFamily": "night-street",
            "evidenceStatus": "unknown",
        },
    ]


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    offline = _GATE.require_bool(payload["offline"], "offline")
    query = _GATE.require_text(payload["query"], "query")
    remote = _GATE.require_bool(payload["remoteGenerationRequired"], "remoteGenerationRequired")
    network = _GATE.require_bool(payload["networkUsed"], "networkUsed")
    filters = payload["filters"]
    _GATE.require(isinstance(filters, dict) and set(filters) == FILTER_KEYS, "filters keys are invalid")
    parsed_filters = {
        "format": None if filters["format"] is None else _GATE.require_text(filters["format"], "filters.format"),
        "monochrome": None
        if filters["monochrome"] is None
        else _GATE.require_bool(filters["monochrome"], "filters.monochrome"),
        "sceneFamily": None
        if filters["sceneFamily"] is None
        else _GATE.require_text(filters["sceneFamily"], "filters.sceneFamily"),
    }
    catalogue_raw = payload["catalogue"]
    _GATE.require(isinstance(catalogue_raw, list) and catalogue_raw, "catalogue must be a non-empty list")
    catalogue = [_entry(item, "catalogue[" + str(index) + "]") for index, item in enumerate(catalogue_raw)]
    returned_raw = payload["returned"]
    _GATE.require(isinstance(returned_raw, list), "returned must be a list")
    returned = []
    for index, hit in enumerate(returned_raw):
        label = "returned[" + str(index) + "]"
        _GATE.require(isinstance(hit, dict) and set(hit) == HIT_KEYS, label + " keys are invalid")
        status = _GATE.require_text(hit["evidenceStatus"], label + ".evidenceStatus")
        match = _GATE.require_text(hit["match"], label + ".match")
        _GATE.require(match in {"exact", "edit-distance", "substring"}, label + ".match is not recognized")
        _GATE.require(status in {"known", "partial", "unknown"}, label + ".evidenceStatus is not recognized")
        returned.append({
            "id": _GATE.require_text(hit["id"], label + ".id"),
            "match": match,
            "evidenceStatus": status,
        })
    expected = local_hits(catalogue, query, parsed_filters)
    if returned != expected:
        faults.append(OPAQUE_MATCH)
    if remote or network or (offline and network):
        faults.append(NEGATIVE_TOKEN)
    extra = [{"offline": offline, "query": query, "hits": expected, "filters": parsed_filters}]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            OPAQUE_MATCH: CASE["expected"],
        },
    )
