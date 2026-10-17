"""TC-P144-05 Publicly accessible but unlicensed asset.

Citation metadata stays. Bytes whose redistribution permission is unknown
stay out of the release bundle. Public visibility is not a licence.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P144-05",
    "phase": "P144",
    "workstream": 18,
    "name": "Publicly accessible but unlicensed asset",
    "intervention": "Offer a web-accessible still, LUT, or profile whose redistribution permission is unknown.",
    "expected": "Retain appropriate citation metadata while excluding unapproved bytes from the release bundle.",
    "negative": "Public visibility must not be treated as a redistribution licence.",
    "repeat": "Repeat promotional images, commercial LUTs, and research model weights.",
}

ASSET_KINDS = frozenset({
    "still",
    "lut",
    "profile",
    "promotional-image",
    "commercial-lut",
    "research-model-weights",
})
UNLICENSED_BYTES = "unapproved-bytes-in-release-bundle"
VISIBILITY = "public-visibility-treated-as-redistribution-licence"
NO_CITATION = "citation-metadata-not-retained"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "asset_kind",
    "publicly_visible",
    "redistribution_known",
    "citation_retained",
    "bytes_in_release_bundle",
    "visibility_treated_as_licence",
    "recipe",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p144_validate_recipe_fidelity_and_honesty.py"
    spec = importlib.util.spec_from_file_location("p144_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    _GATE.require_keys(payload, set(PAYLOAD_KEYS))
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    kind = _GATE.require_text(payload["asset_kind"], "asset_kind")
    _GATE.require(kind in ASSET_KINDS, "asset_kind is not recognized")
    visible = _GATE.require_bool(payload["publicly_visible"], "publicly_visible")
    known = _GATE.require_bool(payload["redistribution_known"], "redistribution_known")
    citation = _GATE.require_bool(payload["citation_retained"], "citation_retained")
    bundled = _GATE.require_bool(payload["bytes_in_release_bundle"], "bytes_in_release_bundle")
    treated = _GATE.require_bool(payload["visibility_treated_as_licence"], "visibility_treated_as_licence")
    scored = _GATE.score_recipe(payload["recipe"], "recipe")
    faults = list(scored["faults"])
    if not known and bundled:
        faults.append(UNLICENSED_BYTES)
    if treated or (visible and not known and bundled):
        if treated:
            faults.append(VISIBILITY)
    if not citation:
        faults.append(NO_CITATION)
    record = {
        "asset_kind": kind,
        "publicly_visible": visible,
        "redistribution_known": known,
        "citation_retained": citation,
        "bytes_in_release_bundle": bundled,
        "visibility_treated_as_licence": treated,
        "report": scored["report"],
    }
    texts = {
        UNLICENSED_BYTES: "unapproved bytes must stay out of the release bundle",
        VISIBILITY: CASE["negative"],
        NO_CITATION: "citation metadata must be retained",
    }
    return _GATE.case_result(CASE, evidence, repeat, faults, [record], texts)
