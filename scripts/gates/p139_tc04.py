"""TC-P139-04 Offline search ambiguity.

Host fixture. Misspelled titles, alternate titles, and stock names resolve
against a local catalogue. Each hit keeps its evidence status and fact hash.
A remote generation call is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P139-04"
NAME = "Offline search ambiguity"
INTERVENTION = "Search misspelled titles, alternate titles, or stock names without network access."
EXPECTED = "Return relevant local candidates with transparent matching and evidence status."
NEGATIVE = "A remote generation call must not be required for basic catalogue lookup."
REPEAT = "Repeat filtered searches for format, monochrome, and scene family."
NEGATIVE_TOKEN = "remote-generation-required-for-catalogue-lookup"
ALLOWED_REPEATS = {"format", "monochrome", "scene-family", REPEAT}
EVIDENCE_STATES = {"documented", "creative-reconstruction", "partial", "unknown"}
ENTRY_KEYS = {
    "title",
    "alternateTitles",
    "stock",
    "format",
    "monochrome",
    "sceneFamily",
    "evidenceStatus",
    "fact_hash",
}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "query",
    "catalogue",
    "filter",
    "networkAvailable",
    "remoteGenerationCalled",
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


def levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for index, character in enumerate(left, 1):
        current = [index]
        for other_index, other in enumerate(right, 1):
            current.append(
                min(
                    current[other_index - 1] + 1,
                    previous[other_index] + 1,
                    previous[other_index - 1] + (character != other),
                )
            )
        previous = current
    return previous[-1]


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def match_reason(entry: dict, query: str) -> str | None:
    folded = _normalize(query)
    if not folded:
        return None
    for name in [entry["title"], *entry["alternateTitles"]]:
        candidate = _normalize(name)
        if folded == candidate:
            return "exact-title"
        if min(len(folded), len(candidate)) >= 4 and levenshtein(folded, candidate) <= 2:
            return "typo-title"
    stock = _normalize(entry["stock"])
    if folded in stock or stock in folded:
        return "stock-name"
    return None


def passes_filter(entry: dict, selection: dict | None) -> bool:
    if selection is None:
        return True
    if "format" in selection and entry["format"] != selection["format"]:
        return False
    if "monochrome" in selection and entry["monochrome"] is not selection["monochrome"]:
        return False
    if "sceneFamily" in selection and entry["sceneFamily"] != selection["sceneFamily"]:
        return False
    return True


def _filter(repeat: str, value):
    if repeat == REPEAT:
        if value is None:
            return None
    elif value is None:
        raise ValueError("filter is required for this repeat")
    if value is None:
        return None
    if type(value) is not dict or not value:
        raise ValueError("filter must be an object")
    allowed = {"format", "monochrome", "sceneFamily"}
    if not set(value) <= allowed:
        raise ValueError("filter keys are invalid")
    parsed = {}
    if "format" in value:
        parsed["format"] = _CORE.require_text(value["format"], "filter.format")
    if "monochrome" in value:
        if type(value["monochrome"]) is not bool:
            raise ValueError("filter.monochrome must be a bool")
        parsed["monochrome"] = value["monochrome"]
    if "sceneFamily" in value:
        parsed["sceneFamily"] = _CORE.require_text(value["sceneFamily"], "filter.sceneFamily")
    if repeat == "format" and "format" not in parsed:
        raise ValueError("format repeat requires a format filter")
    if repeat == "monochrome" and "monochrome" not in parsed:
        raise ValueError("monochrome repeat requires a monochrome filter")
    if repeat == "scene-family" and "sceneFamily" not in parsed:
        raise ValueError("scene-family repeat requires a sceneFamily filter")
    return parsed


def _catalogue(value):
    if not isinstance(value, list) or not value:
        raise ValueError("catalogue must be a non-empty list")
    parsed = []
    for index, item in enumerate(value):
        if type(item) is not dict or set(item) != ENTRY_KEYS:
            raise ValueError(f"catalogue[{index}] keys are invalid")
        alternates = item["alternateTitles"]
        if not isinstance(alternates, list) or not all(isinstance(name, str) and name.strip() for name in alternates):
            raise ValueError(f"catalogue[{index}].alternateTitles is invalid")
        if type(item["monochrome"]) is not bool:
            raise ValueError(f"catalogue[{index}].monochrome must be a bool")
        status = item["evidenceStatus"]
        if status not in EVIDENCE_STATES:
            raise ValueError(f"catalogue[{index}].evidenceStatus is invalid")
        parsed.append(
            {
                "title": _CORE.require_text(item["title"], f"catalogue[{index}].title"),
                "alternateTitles": list(alternates),
                "stock": _CORE.require_text(item["stock"], f"catalogue[{index}].stock"),
                "format": _CORE.require_text(item["format"], f"catalogue[{index}].format"),
                "monochrome": item["monochrome"],
                "sceneFamily": _CORE.require_text(item["sceneFamily"], f"catalogue[{index}].sceneFamily"),
                "evidenceStatus": status,
                "fact_hash": _CORE.require_digest(item["fact_hash"], f"catalogue[{index}].fact_hash"),
            }
        )
    return parsed


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _CORE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _CORE.require_text(payload["repeat"], "repeat")
    if repeat not in ALLOWED_REPEATS:
        raise ValueError("repeat is not a catalogue filter")
    query = _CORE.require_text(payload["query"], "query")
    if type(payload["networkAvailable"]) is not bool or type(payload["remoteGenerationCalled"]) is not bool:
        raise ValueError("network flags must be bools")
    catalogue = _catalogue(payload["catalogue"])
    selection = _filter(repeat, payload["filter"])
    review = _CORE.review_reconstructions(
        payload["productionFacts"],
        payload["reconstructions"],
        declared_fact_hash=payload["fact_hash"],
        prior_canonical=payload["prior_canonical"],
        mutated_facts=payload["mutated_facts"],
        bound_object_id=None,
    )
    hits = []
    for entry in catalogue:
        reason = match_reason(entry, query)
        if reason and passes_filter(entry, selection):
            hits.append((entry, reason))
    faults = list(review["faults"])
    reasons = [
        f"{CASE_ID} {NAME}",
        EXPECTED,
        INTERVENTION,
        f"repeat {repeat}",
        "query=" + query,
        "networkAvailable=" + str(payload["networkAvailable"]).lower(),
    ]
    reasons.extend(review["reasons"])
    if payload["remoteGenerationCalled"]:
        faults.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    preserved = [evidence, "query=" + query, "candidateCount=" + str(len(hits))]
    for entry, reason in hits:
        preserved.append(
            "candidate="
            + entry["title"]
            + " match="
            + reason
            + " evidence="
            + entry["evidenceStatus"]
            + " fact_hash="
            + entry["fact_hash"]
        )
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
