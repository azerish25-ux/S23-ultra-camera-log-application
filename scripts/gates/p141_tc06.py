"""TC-P141-06 Reference edition conflict.

Host fixture. Theatrical, digital, HDR, and unidentified references stay
separate or explicitly uncertain. Averaging inconsistent editions into one
historical fact is rejected. Rights are still judged per asset.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P141-06",
    "phase": "P141",
    "workstream": 18,
    "name": "Reference edition conflict",
    "intervention": "Supply references from different film releases or display assumptions with different appearance.",
    "expected": "Keep separate targets or explicit uncertainty rather than inventing one definitive look.",
    "negative": "Averaging inconsistent editions into a historical fact must fail.",
    "repeat": "Repeat theatrical, digital, HDR, and unidentified reference versions.",
}

NEGATIVE_TOKEN = "averaged-inconsistent-editions"
INVENTED = "invented-definitive-look"
RELEASES = frozenset({"theatrical", "digital", "hdr", "unidentified"})
EDITION_KEYS = {"edition_id", "release", "appearance"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "assets",
    "editions",
    "averagedIntoFact",
    "separateTargets",
    "explicitUncertainty",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p141_manage_reference_media_rights_and_attribution.py"
    spec = importlib.util.spec_from_file_location("p141_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_editions(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list) and len(value) >= 1, "editions must be a non-empty list")
    parsed = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict) and set(item) == EDITION_KEYS, f"editions[{index}] keys are invalid")
        edition_id = _GATE.require_text(item["edition_id"], f"editions[{index}].edition_id")
        _GATE.require(edition_id not in seen, "duplicate edition_id " + edition_id)
        seen.add(edition_id)
        release = _GATE.require_text(item["release"], f"editions[{index}].release")
        _GATE.require(release in RELEASES, f"editions[{index}].release is not a reference version")
        appearance = _GATE.require_text(item["appearance"], f"editions[{index}].appearance")
        parsed.append({"edition_id": edition_id, "release": release, "appearance": appearance})
    return parsed


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    editions = _parse_editions(payload["editions"])
    averaged = _GATE.require_bool(payload["averagedIntoFact"], "averagedIntoFact")
    separate = _GATE.require_bool(payload["separateTargets"], "separateTargets")
    uncertain = _GATE.require_bool(payload["explicitUncertainty"], "explicitUncertainty")
    appearances = {item["appearance"] for item in editions}
    inconsistent = len(appearances) > 1
    if averaged and len(editions) >= 2:
        faults.append(NEGATIVE_TOKEN)
    if inconsistent and not separate and not uncertain:
        faults.append(INVENTED)
    extra = [{
        "editionIds": [item["edition_id"] for item in editions],
        "releases": [item["release"] for item in editions],
        "inconsistent": inconsistent,
        "averagedIntoFact": averaged,
        "separateTargets": separate,
        "explicitUncertainty": uncertain,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            INVENTED: CASE["expected"],
        },
    )
