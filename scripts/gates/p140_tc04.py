"""TC-P140-04 Offline search ambiguity.

Host reference. Misspelled titles, alternate titles, and stock names resolve on
the local index. A remote generation call is not required.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P140-04",
    "phase": "P140",
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
    "claim",
    "catalogue",
    "query",
    "filters",
    "typoTolerance",
    "sort",
    "remote_model",
    "network_used",
    "dropQueryTokens",
    "recommendationIds",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p140_implement_offline_search_and_filtering.py"
    spec = importlib.util.spec_from_file_location("p140_gate_for_tc04", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    claim = _GATE.require_text(payload["claim"], "claim")
    remote_model = _GATE.require_bool(payload["remote_model"], "remote_model")
    network_used = _GATE.require_bool(payload["network_used"], "network_used")
    faults, trace = _GATE.judge_search(
        catalogue=payload["catalogue"],
        query=payload["query"],
        filters=payload["filters"],
        typo_tolerance=payload["typoTolerance"],
        sort=payload["sort"],
        remote_model=remote_model,
        network_used=network_used,
        apply_mutant=False,
        drop_query_tokens=_GATE.require_bool(payload["dropQueryTokens"], "dropQueryTokens"),
        recommendation_ids=payload["recommendationIds"],
    )
    if remote_model or network_used:
        faults = _GATE.dedupe([NEGATIVE_TOKEN, *faults])
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + _GATE.ORACLE,
        "retrieval: " + _GATE.RETRIEVAL_RULE,
        CASE["expected"],
        "repeat " + repeat,
        "remoteCall=false",
        "queryTokens=" + ",".join(trace["queryTokens"]),
    ]
    if NEGATIVE_TOKEN in faults:
        reasons.append(CASE["negative"])
    if not faults:
        reasons.append("local candidates recorded with evidence status; no network request")
    preserved = [evidence, trace, claim]
    return _GATE.finish_result(CASE["id"], evidence, faults, reasons, preserved, [CASE["repeat"], repeat])
