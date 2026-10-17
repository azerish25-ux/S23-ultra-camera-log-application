"""TC-P147-02 Critical mutant survives.

Host reference. The critical import mutant trusts an extension whose magic
disagrees and allocates from an unvalidated header. High line coverage does
not replace killing that mutant.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P147-02",
    "phase": "P147",
    "workstream": 19,
    "name": "Critical mutant survives",
    "intervention": "Insert a plausible fault into a production seam and run the intended regression suite.",
    "expected": "Require the relevant test to fail; surviving critical mutants expose insufficient assertions.",
    "negative": "High line coverage without fault detection must not count as adequate protection.",
    "repeat": "Repeat timestamp pairing, source retention, range signalling, and checkpoint identity mutants.",
}

NEGATIVE_TOKEN = "coverage-without-fault-detection"
MUTANT_NOT_DETECTED = "critical-import-mutant-not-detected"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "imports",
    "corpus",
    "lineCoverage",
    "killedIds",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p147_secure_media_and_profile_import_boundaries.py"
    spec = importlib.util.spec_from_file_location("p147_gate_for_tc02", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_killed(value: object) -> list[str]:
    _GATE.require(isinstance(value, list), "killedIds must be a list")
    killed = [_GATE.require_text(item, f"killedIds[{index}]") for index, item in enumerate(value)]
    _GATE.require(len(killed) == len(set(killed)), "killedIds must be unique")
    return killed


def _survivors(corpus_faults: dict, killed: list[str]) -> list[str]:
    survived: list[str] = []
    for corpus_id in _GATE.CRITICAL_CORPUS_IDS:
        faults = corpus_faults.get(corpus_id, [])
        if faults and corpus_id not in killed:
            survived.append(corpus_id)
    return survived


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    coverage = _GATE.require_number(payload["lineCoverage"], "lineCoverage")
    _GATE.require(0 <= coverage <= 1, "lineCoverage must be between 0 and 1")
    killed = _parse_killed(payload["killedIds"])
    survived = _survivors(bundle["snapshot"]["corpusFaults"], killed)
    faults = list(bundle["faults"])
    if survived:
        faults.append(MUTANT_NOT_DETECTED)
        if coverage >= _GATE.HIGH_COVERAGE:
            faults.append(NEGATIVE_TOKEN)
    extra = [{"lineCoverage": coverage, "survivedMutants": survived, "killedIds": killed}]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            MUTANT_NOT_DETECTED: CASE["expected"],
        },
    )
