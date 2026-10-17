"""TC-P138-06 Reference edition conflict.

Host fixture. Theatrical, digital, HDR, and unidentified references stay
separate when appearance or equipment disagrees. Averaging them into one
historical stock or lens is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P138-06",
    "phase": "P138",
    "workstream": 18,
    "name": "Reference edition conflict",
    "intervention": "Supply references from different film releases or display assumptions with different appearance.",
    "expected": "Keep separate targets or explicit uncertainty rather than inventing one definitive look.",
    "negative": "Averaging inconsistent editions into a historical fact must fail.",
    "repeat": "Repeat theatrical, digital, HDR, and unidentified reference versions.",
}

NEGATIVE_TOKEN = "averaged-inconsistent-editions"
EDITION_KEYS = {"edition_id", "appearance", "stock", "lens", "traces"}
EDITION_IDS = {"theatrical", "digital", "hdr", "unidentified"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "family",
    "max_entries",
    "editions",
    "averagedStock",
    "averagedLens",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p138_build_the_first_sourced_recipe_family.py"
    spec = importlib.util.spec_from_file_location("p138_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def parse_editions(raw: object) -> list[dict]:
    _GATE.require(isinstance(raw, list) and len(raw) >= 2, "editions must contain at least two references")
    editions: list[dict] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        label = f"editions[{index}]"
        _GATE.require(isinstance(item, dict), label + " must be an object")
        _GATE.require(set(item) == EDITION_KEYS, label + " keys are invalid")
        edition_id = _GATE.require_text(item["edition_id"], label + " edition_id")
        _GATE.require(edition_id in EDITION_IDS, label + " edition_id is not a reference version")
        _GATE.require(edition_id not in seen, "duplicate edition_id")
        seen.add(edition_id)
        _GATE.require(isinstance(item["traces"], list), label + " traces must be a list")
        traces = [
            _GATE.parse_trace(trace_item, f"{label} traces[{trace_index}]")
            for trace_index, trace_item in enumerate(item["traces"])
        ]
        edition = {
            "edition_id": edition_id,
            "appearance": _GATE.require_text(item["appearance"], label + " appearance"),
            "stock": None if item["stock"] is None else _GATE.require_text(item["stock"], label + " stock"),
            "lens": None if item["lens"] is None else _GATE.require_text(item["lens"], label + " lens"),
            "traces": traces,
        }
        for field, token in (("stock", _GATE.UNSOURCED_STOCK), ("lens", _GATE.UNSOURCED_LENS)):
            if edition[field] is not None and not any(trace_item["field"] == field for trace_item in traces):
                edition.setdefault("_faults", []).append(token)
        editions.append(edition)
    return editions


def inconsistent(editions: list[dict]) -> bool:
    return (
        len({item["appearance"] for item in editions}) > 1
        or len({item["stock"] for item in editions}) > 1
        or len({item["lens"] for item in editions}) > 1
    )


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_family_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    editions = parse_editions(payload["editions"])
    for edition in editions:
        faults.extend(edition.get("_faults", []))
    averaged_stock = payload["averagedStock"]
    averaged_lens = payload["averagedLens"]
    if averaged_stock is not None:
        averaged_stock = _GATE.require_text(averaged_stock, "averagedStock")
    if averaged_lens is not None:
        averaged_lens = _GATE.require_text(averaged_lens, "averagedLens")
    conflict = inconsistent(editions)
    if conflict and (averaged_stock is not None or averaged_lens is not None):
        faults.append(NEGATIVE_TOKEN)
    if not conflict and (
        (averaged_stock is not None and len({item["stock"] for item in editions}) == 1 and averaged_stock != editions[0]["stock"])
        or (averaged_lens is not None and len({item["lens"] for item in editions}) == 1 and averaged_lens != editions[0]["lens"])
    ):
        faults.append(NEGATIVE_TOKEN)
    public = []
    for edition in editions:
        public.append({
            "edition_id": edition["edition_id"],
            "appearance": edition["appearance"],
            "stock": edition["stock"],
            "lens": edition["lens"],
            "traces": edition["traces"],
        })
    extra = [{
        "editions": public,
        "inconsistent": conflict,
        "averagedStock": None if conflict else averaged_stock,
        "averagedLens": None if conflict else averaged_lens,
        "definitiveLookInvented": bool(conflict and (payload["averagedStock"] is not None or payload["averagedLens"] is not None)),
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {NEGATIVE_TOKEN: CASE["negative"]},
    )
