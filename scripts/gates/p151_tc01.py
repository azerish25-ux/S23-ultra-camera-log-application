"""TC-P151-01 Skipped test laundering.

Host reference. Pass, fail, skip, and unavailable stay visible as separate
counts. A summary that folds skips or unavailable results into passes is
rejected. Asserting a claim whose required critical test did not pass is
rejected. Release-note badge rules still apply.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P151-01",
    "phase": "P151",
    "workstream": 19,
    "name": "Skipped test laundering",
    "intervention": "Combine passing host tests with unavailable hardware and a failing critical integration test.",
    "expected": "Keep every result category visible and block claims requiring the missing or failing evidence.",
    "negative": "Counting skips as passes must fail.",
    "repeat": "Repeat emulator-only, GPU-unavailable, and physical-codec-unavailable environments.",
}

NEGATIVE_TOKEN = "skips-counted-as-passes"
CATEGORY_HIDDEN = "result-category-hidden"
CLAIM_BLOCKED = "claim-blocked-by-missing-evidence"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "claims",
    "implementedFeatures",
    "aspirationalRequirements",
    "knownFailures",
    "results",
    "summary",
    "assertedClaims",
    "claimRequirements",
)
RESULT_KEYS = {"id", "status", "critical"}


def _load_gate():
    path = Path(__file__).resolve().parent / "p151_generate_honest_release_notes_and_capability_badges.py"
    spec = importlib.util.spec_from_file_location("p151_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_results(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list) and bool(value), "results must be a non-empty list")
    rows = []
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict), f"results[{index}] must be an object")
        _GATE.require(set(item) == RESULT_KEYS, f"results[{index}] keys are invalid")
        status = _GATE.require_text(item["status"], f"results[{index}].status")
        _GATE.require(status in _GATE.RESULT_STATUSES, f"results[{index}].status is not recognized")
        rows.append({
            "id": _GATE.require_text(item["id"], f"results[{index}].id"),
            "status": status,
            "critical": _GATE.require_bool(item["critical"], f"results[{index}].critical"),
        })
    ids = [row["id"] for row in rows]
    _GATE.require(len(ids) == len(set(ids)), "result ids must be unique")
    return rows


def _parse_summary(value: object) -> dict:
    _GATE.require(isinstance(value, dict), "summary must be an object")
    summary = {}
    for key in _GATE.SUMMARY_KEYS:
        if key not in value:
            continue
        count = _GATE.require_int(value[key], "summary." + key)
        _GATE.require(count >= 0, "summary." + key + " must be >= 0")
        summary[key] = count
    extra = set(value) - set(_GATE.SUMMARY_KEYS)
    _GATE.require(not extra, "summary has unexpected fields: " + ", ".join(sorted(extra)))
    return summary


def _parse_claims(value: object, label: str) -> list[str]:
    _GATE.require(isinstance(value, list), label + " must be a list")
    return [_GATE.require_text(item, f"{label}[{index}]") for index, item in enumerate(value)]


def _parse_requirements(value: object) -> dict:
    _GATE.require(isinstance(value, dict), "claimRequirements must be an object")
    requirements = {}
    for key, needed in value.items():
        claim = _GATE.require_text(key, "claimRequirements key")
        requirements[claim] = _parse_claims(needed, "claimRequirements." + claim)
    return requirements


def _laundering_faults(results: list[dict], summary: dict) -> list[str]:
    actual = {key: 0 for key in _GATE.SUMMARY_KEYS}
    for row in results:
        actual[row["status"]] += 1
    faults: list[str] = []
    for key in _GATE.SUMMARY_KEYS:
        if key not in summary:
            faults.append(CATEGORY_HIDDEN)
            continue
        if summary[key] == actual[key]:
            continue
        folded_into_passes = key == "pass" and summary[key] > actual[key]
        hidden_non_pass = key in {"skip", "unavailable"} and summary[key] < actual[key]
        if folded_into_passes or hidden_non_pass:
            faults.append(NEGATIVE_TOKEN)
        else:
            faults.append(CATEGORY_HIDDEN)
    return faults


def _blocked_claim_faults(results: list[dict], asserted: list[str], requirements: dict) -> list[str]:
    by_id = {row["id"]: row for row in results}
    faults: list[str] = []
    for claim in asserted:
        for test_id in requirements.get(claim, []):
            row = by_id.get(test_id)
            if row is None or row["status"] != "pass":
                faults.append(CLAIM_BLOCKED)
                break
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    results = _parse_results(payload["results"])
    summary = _parse_summary(payload["summary"])
    asserted = _parse_claims(payload["assertedClaims"], "assertedClaims")
    requirements = _parse_requirements(payload["claimRequirements"])
    faults = list(bundle["faults"])
    faults.extend(_laundering_faults(results, summary))
    faults.extend(_blocked_claim_faults(results, asserted, requirements))
    extra = [{
        "summary": {key: summary.get(key) for key in _GATE.SUMMARY_KEYS},
        "assertedClaims": asserted,
        "resultIds": [row["id"] for row in results],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            CATEGORY_HIDDEN: CASE["expected"],
            CLAIM_BLOCKED: "claims that require missing or failing evidence stay blocked",
        },
    )
