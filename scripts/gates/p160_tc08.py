"""TC-P160-08 Unreproducible research closure.

Host reference. Closure keeps failed experiments, not_run records, and the
setup a new maintainer needs to reproduce capture, film rendering, and a
virtual-lens evaluation. A promotional reel cannot substitute for that archive.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P160-08",
    "phase": "P160",
    "workstream": 20,
    "name": "Unreproducible research closure",
    "intervention": "Archive only favorable outputs while omitting failed experiments and essential setup details.",
    "expected": "Preserve enough evidence to reconstruct decisions and reproduce qualified results independently.",
    "negative": "A promotional reel cannot substitute for an engineering archive.",
    "repeat": "Repeat fresh-maintainer reproduction of capture, film rendering, optics, and rejected hypotheses.",
}

NEGATIVE_TOKEN = "promotional-reel-substitutes-for-archive"
SETUP_OMITTED = "essential-setup-omitted"
REPRODUCTION_INCOMPLETE = "maintainer-reproduction-incomplete"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "records",
    "maintenanceNote",
    "only_passes",
    "promotionalReelOnly",
    "setupOmitted",
    "reproducesCapture",
    "reproducesFilmRender",
    "reproducesVirtualLens",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p160_close_the_programme_with_a_reproducible_evidence_archive.py"
    spec = importlib.util.spec_from_file_location("p160_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _closure_faults(payload: dict) -> dict:
    reel = _GATE.require_bool(payload["promotionalReelOnly"], "promotionalReelOnly")
    omitted = _GATE.require_bool(payload["setupOmitted"], "setupOmitted")
    capture = _GATE.require_bool(payload["reproducesCapture"], "reproducesCapture")
    film = _GATE.require_bool(payload["reproducesFilmRender"], "reproducesFilmRender")
    lens = _GATE.require_bool(payload["reproducesVirtualLens"], "reproducesVirtualLens")
    faults: list[str] = []
    if reel:
        faults.append(NEGATIVE_TOKEN)
    if omitted:
        faults.append(SETUP_OMITTED)
    if not (capture and film and lens):
        faults.append(REPRODUCTION_INCOMPLETE)
    return {
        "faults": faults,
        "observed": {
            "promotionalReelOnly": reel,
            "setupOmitted": omitted,
            "reproducesCapture": capture,
            "reproducesFilmRender": film,
            "reproducesVirtualLens": lens,
        },
    }


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    judged = _closure_faults(payload)
    faults = list(bundle["faults"])
    faults.extend(judged["faults"])
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [judged["observed"]],
        {
            NEGATIVE_TOKEN: CASE["negative"],
            SETUP_OMITTED: CASE["expected"],
            REPRODUCTION_INCOMPLETE: CASE["expected"],
        },
    )
