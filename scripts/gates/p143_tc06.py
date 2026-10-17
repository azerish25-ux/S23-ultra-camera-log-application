"""TC-P143-06 Reference edition conflict.

Host reference. Theatrical, digital, HDR, and unidentified references stay
separate targets. Averaging inconsistent editions into one historical fact is
rejected. Ambiguous releases stay listed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P143-06",
    "phase": "P143",
    "workstream": 18,
    "name": "Reference edition conflict",
    "intervention": "Supply references from different film releases or display assumptions with different appearance.",
    "expected": "Keep separate targets or explicit uncertainty rather than inventing one definitive look.",
    "negative": "Averaging inconsistent editions into a historical fact must fail.",
    "repeat": "Repeat theatrical, digital, HDR, and unidentified reference versions.",
}

NEGATIVE_TOKEN = "averaged-inconsistent-editions"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "looks",
    "dropAmbiguous",
    "averagedIntoHistoricalFact",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p143_support_release_specific_and_scene_specific_looks.py"
    spec = importlib.util.spec_from_file_location("p143_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    averaged = _GATE.require_bool(payload["averagedIntoHistoricalFact"], "averagedIntoHistoricalFact")
    if averaged:
        faults.append(NEGATIVE_TOKEN)
    releases = sorted({
        look["release_id"]
        for look in bundle["looks"]
        if look["scene_id"] is None and isinstance(look["release_id"], str)
    })
    extra = [{
        "averagedIntoHistoricalFact": averaged,
        "submittedReleaseIds": releases,
    }]
    return _GATE.finish_case(CASE, bundle, faults, extra, {NEGATIVE_TOKEN: CASE["negative"]})
