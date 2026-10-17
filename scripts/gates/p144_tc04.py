"""TC-P144-04 Offline search ambiguity.

Misspelled titles, alternate titles, and stock names resolve to local
candidates with a visible match and evidence status. Basic catalogue lookup
must not require a remote generation call.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P144-04",
    "phase": "P144",
    "workstream": 18,
    "name": "Offline search ambiguity",
    "intervention": "Search misspelled titles, alternate titles, or stock names without network access.",
    "expected": "Return relevant local candidates with transparent matching and evidence status.",
    "negative": "A remote generation call must not be required for basic catalogue lookup.",
    "repeat": "Repeat filtered searches for format, monochrome, and scene family.",
}

MATCHES = frozenset({
    "title",
    "alternate-title",
    "stock-name",
    "misspelling",
    "format",
    "monochrome",
    "scene-family",
    "star_rating",
})
EVIDENCE_STATUSES = frozenset({"sourced", "reconstructed", "unidentified", "unknown"})
CANDIDATE_KEYS = {"candidate_id", "match", "evidence_status"}
REMOTE = "remote-generation-required-for-catalogue-lookup"
OPAQUE = "matching-not-transparent"
NO_CANDIDATES = "no-local-candidates"
NETWORK = "offline-lookup-depended-on-network"
STAR_MATCH = "star-rating-used-as-search-identification"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "query",
    "network_used",
    "remote_generation_required",
    "transparent_matching",
    "candidates",
    "recipe",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p144_validate_recipe_fidelity_and_honesty.py"
    spec = importlib.util.spec_from_file_location("p144_gate_for_tc04", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _candidate(value: object, label: str) -> dict:
    _GATE.require(isinstance(value, dict), label + " must be an object")
    _GATE.require(set(value) == CANDIDATE_KEYS, label + " keys are invalid")
    match = _GATE.require_text(value["match"], label + ".match")
    _GATE.require(match in MATCHES, label + ".match is not recognized")
    status = _GATE.require_text(value["evidence_status"], label + ".evidence_status")
    _GATE.require(status in EVIDENCE_STATUSES, label + ".evidence_status is not recognized")
    return {
        "candidate_id": _GATE.require_text(value["candidate_id"], label + ".candidate_id"),
        "match": match,
        "evidence_status": status,
    }


def evaluate(payload: dict) -> dict:
    _GATE.require_keys(payload, set(PAYLOAD_KEYS))
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    query = _GATE.require_text(payload["query"], "query")
    network = _GATE.require_bool(payload["network_used"], "network_used")
    remote = _GATE.require_bool(payload["remote_generation_required"], "remote_generation_required")
    transparent = _GATE.require_bool(payload["transparent_matching"], "transparent_matching")
    raw = payload["candidates"]
    _GATE.require(isinstance(raw, list), "candidates must be a list")
    candidates = [_candidate(item, "candidates[{}]".format(index)) for index, item in enumerate(raw)]
    scored = _GATE.score_recipe(payload["recipe"], "recipe")
    faults = list(scored["faults"])
    if remote:
        faults.append(REMOTE)
    if network:
        faults.append(NETWORK)
    if not transparent:
        faults.append(OPAQUE)
    if not candidates:
        faults.append(NO_CANDIDATES)
    if any(item["match"] == "star_rating" for item in candidates):
        faults.append(STAR_MATCH)
    record = {
        "query": query,
        "network_used": network,
        "remote_generation_required": remote,
        "transparent_matching": transparent,
        "candidates": candidates,
        "report": scored["report"],
    }
    texts = {
        REMOTE: CASE["negative"],
        OPAQUE: "local matches must expose how they matched and their evidence status",
        NO_CANDIDATES: "basic catalogue lookup must return local candidates",
        NETWORK: "basic catalogue lookup must not depend on the network",
        STAR_MATCH: _GATE.STAR_NOTE,
    }
    return _GATE.case_result(CASE, evidence, repeat, faults, [record], texts)
