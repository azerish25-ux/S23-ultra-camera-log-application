"""TC-P143-04 Offline search ambiguity.

Host reference. Misspelled titles, alternate titles, and stock names resolve
from local candidates with a visible match and evidence status. A remote
generation call is not required. Release looks stay distinct.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P143-04",
    "phase": "P143",
    "workstream": 18,
    "name": "Offline search ambiguity",
    "intervention": "Search misspelled titles, alternate titles, or stock names without network access.",
    "expected": "Return relevant local candidates with transparent matching and evidence status.",
    "negative": "A remote generation call must not be required for basic catalogue lookup.",
    "repeat": "Repeat filtered searches for format, monochrome, and scene family.",
}

NEGATIVE_TOKEN = "remote-generation-required-for-catalogue-lookup"
OPAQUE_MATCH = "opaque-catalogue-match"
GENERATED_CANDIDATE = "remote-candidate-generated"
STATUSES = frozenset({"documented", "unknown", "creative-reconstruction", "ambiguous"})
CANDIDATE_KEYS = frozenset({"candidateId", "match", "evidenceStatus", "generated"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "looks",
    "dropAmbiguous",
    "query",
    "remoteGenerationRequired",
    "candidates",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p143_support_release_specific_and_scene_specific_looks.py"
    spec = importlib.util.spec_from_file_location("p143_gate_for_tc04", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _candidates(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list), "candidates must be a list")
    parsed = []
    for index, item in enumerate(value):
        label = f"candidates[{index}]"
        _GATE.require(isinstance(item, dict), label + " must be an object")
        _GATE.require(set(item) == CANDIDATE_KEYS, label + " keys are invalid")
        parsed.append({
            "candidateId": _GATE.require_text(item["candidateId"], label + ".candidateId"),
            "match": item["match"],
            "evidenceStatus": item["evidenceStatus"],
            "generated": _GATE.require_bool(item["generated"], label + ".generated"),
        })
    return parsed


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    query = _GATE.require_text(payload["query"], "query")
    remote = _GATE.require_bool(payload["remoteGenerationRequired"], "remoteGenerationRequired")
    candidates = _candidates(payload["candidates"])
    if remote:
        faults.append(NEGATIVE_TOKEN)
    for candidate in candidates:
        match = candidate["match"]
        status = candidate["evidenceStatus"]
        if not isinstance(match, str) or not match.strip() or not isinstance(status, str) or status not in STATUSES:
            faults.append(OPAQUE_MATCH)
        elif candidate["generated"]:
            faults.append(GENERATED_CANDIDATE)
    extra = [{
        "query": query,
        "remoteGenerationRequired": remote,
        "candidateIds": [item["candidateId"] for item in candidates],
        "localLookup": not remote,
    }]
    return _GATE.finish_case(CASE, bundle, faults, extra, {
        NEGATIVE_TOKEN: CASE["negative"],
        OPAQUE_MATCH: "local candidates need a visible match and evidence status",
        GENERATED_CANDIDATE: "a generated remote candidate is not a local catalogue hit",
    })
