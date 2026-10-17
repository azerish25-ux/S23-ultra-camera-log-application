"""TC-P155-08 Unreproducible research closure.

Host reference. Favorable outputs alone are not an engineering archive.
Failed experiments and setup details stay preserved so capture, film rendering,
optics, and rejected hypotheses can be reconstructed. A promotional reel does
not substitute for that archive.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P155-08",
    "phase": "P155",
    "workstream": 20,
    "name": "Unreproducible research closure",
    "intervention": "Archive only favorable outputs while omitting failed experiments and essential setup details.",
    "expected": "Preserve enough evidence to reconstruct decisions and reproduce qualified results independently.",
    "negative": "A promotional reel cannot substitute for an engineering archive.",
    "repeat": "Repeat fresh-maintainer reproduction of capture, film rendering, optics, and rejected hypotheses.",
}

NEGATIVE_TOKEN = "promotional-reel-substitutes-for-archive"
DOMAIN_OMITTED = "reproduction-domain-omitted"
REQUIRED_DOMAINS = ("capture", "film-rendering", "optics", "rejected-hypotheses")
ARCHIVE_KEYS = frozenset({
    "favorableOutputs",
    "failedExperiments",
    "setupDetails",
    "promotionalReelOnly",
    "domains",
})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "alternatives",
    "conclusion",
    "archive",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p155_evaluate_reversible_application_level_alternatives.py"
    spec = importlib.util.spec_from_file_location("p155_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_archive(value: object) -> dict:
    _GATE.require(isinstance(value, dict), "archive must be an object")
    _GATE.require(set(value) == ARCHIVE_KEYS, "archive keys are invalid")
    domains_value = value["domains"]
    _GATE.require(isinstance(domains_value, list) and bool(domains_value), "archive.domains must be a non-empty list")
    domains = [_GATE.require_text(item, f"archive.domains[{index}]") for index, item in enumerate(domains_value)]
    _GATE.require(len(domains) == len(set(domains)), "archive.domains must be unique")
    return {
        "favorableOutputs": _GATE.require_bool(value["favorableOutputs"], "archive.favorableOutputs"),
        "failedExperiments": _GATE.require_bool(value["failedExperiments"], "archive.failedExperiments"),
        "setupDetails": _GATE.require_bool(value["setupDetails"], "archive.setupDetails"),
        "promotionalReelOnly": _GATE.require_bool(value["promotionalReelOnly"], "archive.promotionalReelOnly"),
        "domains": domains,
    }


def _archive_faults(archive: dict) -> list[str]:
    faults: list[str] = []
    if archive["promotionalReelOnly"] or not archive["failedExperiments"] or not archive["setupDetails"]:
        faults.append(NEGATIVE_TOKEN)
    missing = [domain for domain in REQUIRED_DOMAINS if domain not in archive["domains"]]
    if missing:
        faults.append(DOMAIN_OMITTED)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    archive = _parse_archive(payload["archive"])
    faults = list(bundle["faults"])
    faults.extend(_archive_faults(archive))
    extra = [{
        "favorableOutputs": archive["favorableOutputs"],
        "failedExperiments": archive["failedExperiments"],
        "setupDetails": archive["setupDetails"],
        "promotionalReelOnly": archive["promotionalReelOnly"],
        "domains": list(archive["domains"]),
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            DOMAIN_OMITTED: CASE["expected"],
        },
    )
