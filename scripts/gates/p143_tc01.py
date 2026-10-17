"""TC-P143-01 Missing production fact.

Host reference. A removed camera, lens, stock, process, or release-version fact
stays unknown. A labelled creative reconstruction is allowed. A plausible
equipment guess marked documented is rejected. Release looks stay distinct.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P143-01",
    "phase": "P143",
    "workstream": 18,
    "name": "Missing production fact",
    "intervention": "Remove verified lens or scene-specific stock information from an otherwise complete movie record.",
    "expected": "Keep the fact unknown while allowing a clearly labelled creative reconstruction.",
    "negative": "A plausible equipment guess marked documented must fail.",
    "repeat": "Repeat camera, lens, stock, process, and release-version fields.",
}

NEGATIVE_TOKEN = "plausible-guess-marked-documented"
UNLABELLED = "unlabelled-creative-reconstruction"
NOT_KEPT_UNKNOWN = "removed-fact-was-not-kept-unknown"
FACTS = frozenset({"camera", "lens", "stock", "process", "release-version"})
STATUSES = frozenset({"unknown", "documented", "creative-reconstruction"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "looks",
    "dropAmbiguous",
    "factName",
    "factValue",
    "evidenceStatus",
    "reconstructionLabel",
    "sourced",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p143_support_release_specific_and_scene_specific_looks.py"
    spec = importlib.util.spec_from_file_location("p143_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    fact = _GATE.require_text(payload["factName"], "factName")
    _GATE.require(fact in FACTS, "factName is not a production fact")
    fact_value = payload["factValue"]
    if fact_value is not None:
        fact_value = _GATE.require_text(fact_value, "factValue")
    status = _GATE.require_text(payload["evidenceStatus"], "evidenceStatus")
    _GATE.require(status in STATUSES, "evidenceStatus is not recognized")
    label = payload["reconstructionLabel"]
    if label is not None:
        label = _GATE.require_text(label, "reconstructionLabel")
    sourced = _GATE.require_bool(payload["sourced"], "sourced")
    if status == "documented" and (not sourced or fact_value is None):
        faults.append(NEGATIVE_TOKEN)
    if status == "creative-reconstruction" and label is None:
        faults.append(UNLABELLED)
    if status == "unknown" and fact_value is not None:
        faults.append(NOT_KEPT_UNKNOWN)
    extra = [{
        "factName": fact,
        "factValue": fact_value,
        "evidenceStatus": status,
        "reconstructionLabel": label,
        "sourced": sourced,
        "keptUnknown": fact_value is None and status in {"unknown", "creative-reconstruction"},
    }]
    return _GATE.finish_case(CASE, bundle, faults, extra, {NEGATIVE_TOKEN: CASE["negative"]})
