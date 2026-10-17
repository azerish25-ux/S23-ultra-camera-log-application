"""TC-P141-01 Missing production fact.

Host fixture. A missing lens or stock fact stays unknown. A clearly labelled
creative reconstruction may be recorded. A plausible equipment guess marked
documented is rejected. Rights are still judged per asset.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P141-01",
    "phase": "P141",
    "workstream": 18,
    "name": "Missing production fact",
    "intervention": "Remove verified lens or scene-specific stock information from an otherwise complete movie record.",
    "expected": "Keep the fact unknown while allowing a clearly labelled creative reconstruction.",
    "negative": "A plausible equipment guess marked documented must fail.",
    "repeat": "Repeat camera, lens, stock, process, and release-version fields.",
}

NEGATIVE_TOKEN = "plausible-equipment-guess-marked-documented"
UNLABELLED = "creative-reconstruction-not-labelled"
FACT_FIELDS = frozenset({"camera", "lens", "stock", "process", "release-version"})
CREATIVE = "creative-reconstruction"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "assets",
    "field",
    "factKnown",
    "factValue",
    "markedDocumented",
    "reconstructionLabel",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p141_manage_reference_media_rights_and_attribution.py"
    spec = importlib.util.spec_from_file_location("p141_gate_for_tc01", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _GATE.require_text(value, label)


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    field = _GATE.require_text(payload["field"], "field")
    _GATE.require(field in FACT_FIELDS, "field is not a production fact")
    fact_known = _GATE.require_bool(payload["factKnown"], "factKnown")
    fact_value = _optional_text(payload["factValue"], "factValue")
    marked = _GATE.require_bool(payload["markedDocumented"], "markedDocumented")
    label = _optional_text(payload["reconstructionLabel"], "reconstructionLabel")
    if fact_known and fact_value is None:
        raise ValueError("known fact requires factValue")
    if not fact_known and (marked or fact_value is not None):
        faults.append(NEGATIVE_TOKEN)
    if not fact_known and label is not None and label != CREATIVE:
        faults.append(UNLABELLED)
    extra = [{
        "field": field,
        "factKnown": fact_known,
        "factValue": fact_value if fact_known else None,
        "markedDocumented": marked,
        "reconstructionLabel": label,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            UNLABELLED: "a creative reconstruction must be clearly labelled",
        },
    )
