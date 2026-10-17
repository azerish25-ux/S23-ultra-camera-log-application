"""TC-P141-04 Offline search ambiguity.

Host fixture. Misspelled titles, alternate titles, and stock names resolve
from local candidates. Each candidate carries a match explanation and an
evidence status. A remote generation call is not required. Rights are still
judged per asset.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P141-04",
    "phase": "P141",
    "workstream": 18,
    "name": "Offline search ambiguity",
    "intervention": "Search misspelled titles, alternate titles, or stock names without network access.",
    "expected": "Return relevant local candidates with transparent matching and evidence status.",
    "negative": "A remote generation call must not be required for basic catalogue lookup.",
    "repeat": "Repeat filtered searches for format, monochrome, and scene family.",
}

NEGATIVE_TOKEN = "remote-generation-required-for-catalogue-lookup"
OPAQUE_MATCH = "candidate-match-not-transparent"
EVIDENCE_OVERCLAIM = "candidate-evidence-status-overclaimed"
EVIDENCE_STATUSES = frozenset({"sourced", "partial", "unknown", "conflicting"})
CANDIDATE_KEYS = {"candidate_id", "match", "evidenceStatus"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "assets",
    "query",
    "remoteGenerationRequired",
    "candidates",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p141_manage_reference_media_rights_and_attribution.py"
    spec = importlib.util.spec_from_file_location("p141_gate_for_tc04", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_candidates(value: object) -> tuple[list[dict], bool, bool]:
    _GATE.require(isinstance(value, list), "candidates must be a list")
    parsed = []
    opaque = False
    overclaimed = False
    seen: set[str] = set()
    for index, item in enumerate(value):
        _GATE.require(
            isinstance(item, dict) and set(item) == CANDIDATE_KEYS,
            f"candidates[{index}] keys are invalid",
        )
        candidate_id = _GATE.require_text(item["candidate_id"], f"candidates[{index}].candidate_id")
        _GATE.require(candidate_id not in seen, "duplicate candidate_id " + candidate_id)
        seen.add(candidate_id)
        match = item["match"]
        status = item["evidenceStatus"]
        _GATE.require(isinstance(match, str), f"candidates[{index}].match must be a string")
        _GATE.require(isinstance(status, str), f"candidates[{index}].evidenceStatus must be a string")
        if not match.strip() or match != match.strip():
            opaque = True
        if status.casefold() in {"qualified", "allowed"} or status not in EVIDENCE_STATUSES:
            overclaimed = True
        parsed.append({"candidate_id": candidate_id, "match": match, "evidenceStatus": status})
    return parsed, opaque, overclaimed


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    query = _GATE.require_text(payload["query"], "query")
    remote = _GATE.require_bool(payload["remoteGenerationRequired"], "remoteGenerationRequired")
    candidates, opaque, overclaimed = _parse_candidates(payload["candidates"])
    if remote:
        faults.append(NEGATIVE_TOKEN)
    if opaque:
        faults.append(OPAQUE_MATCH)
    if overclaimed:
        faults.append(EVIDENCE_OVERCLAIM)
    extra = [{
        "query": query,
        "remoteGenerationRequired": remote,
        "candidateIds": [item["candidate_id"] for item in candidates],
        "matches": [item["match"] for item in candidates],
        "evidenceStatuses": [item["evidenceStatus"] for item in candidates],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            OPAQUE_MATCH: "local candidates must explain the match",
            EVIDENCE_OVERCLAIM: "candidate evidence status must stay sourced, partial, unknown, or conflicting",
        },
    )
