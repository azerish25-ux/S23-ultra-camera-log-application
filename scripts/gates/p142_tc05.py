"""TC-P142-05 Publicly accessible but unlicensed asset.

Host reference. A public URL can be cited. Unknown redistribution keeps the
bytes out of the release bundle. Public visibility is not a licence.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P142-05",
    "phase": "P142",
    "workstream": 18,
    "name": "Publicly accessible but unlicensed asset",
    "intervention": "Offer a web-accessible still, LUT, or profile whose redistribution permission is unknown.",
    "expected": "Retain appropriate citation metadata while excluding unapproved bytes from the release bundle.",
    "negative": "Public visibility must not be treated as a redistribution licence.",
    "repeat": "Repeat promotional images, commercial LUTs, and research model weights.",
}

NEGATIVE_TOKEN = "public-visibility-treated-as-redistribution-licence"
BUNDLED = "unapproved-bytes-in-release-bundle"
CITATION_MISSING = "citation-not-retained"
KINDS = {"still", "lut", "profile", "promotional-image", "commercial-lut", "research-weights"}
ASSET_KEYS = {
    "kind",
    "publicUrl",
    "publiclyAccessible",
    "redistribution",
    "cited",
    "citation",
    "bundled",
    "treatedAsLicence",
}
PAYLOAD_KEYS = ("evidenceId", "repeat", "source", "reference", "suggestion", "asset")


def _load_gate():
    path = Path(__file__).resolve().parent / "p142_implement_constrained_reference_matching.py"
    spec = importlib.util.spec_from_file_location("p142_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def clean_asset(**overrides):
    asset = {
        "kind": "still",
        "publicUrl": "https://example.test/production-still",
        "publiclyAccessible": True,
        "redistribution": "unknown",
        "cited": True,
        "citation": "production still, public URL, redistribution unknown",
        "bundled": False,
        "treatedAsLicence": False,
    }
    asset.update(overrides)
    return asset


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    raw = payload["asset"]
    _GATE.require(isinstance(raw, dict) and set(raw) == ASSET_KEYS, "asset keys are invalid")
    kind = _GATE.require_text(raw["kind"], "asset.kind")
    _GATE.require(kind in KINDS, "asset.kind is not recognized")
    url = _GATE.require_text(raw["publicUrl"], "asset.publicUrl")
    public = _GATE.require_bool(raw["publiclyAccessible"], "asset.publiclyAccessible")
    redistribution = _GATE.require_text(raw["redistribution"], "asset.redistribution")
    _GATE.require(redistribution in {"unknown", "granted", "denied"}, "asset.redistribution is not recognized")
    cited = _GATE.require_bool(raw["cited"], "asset.cited")
    citation = _GATE.require_text(raw["citation"], "asset.citation")
    bundled = _GATE.require_bool(raw["bundled"], "asset.bundled")
    treated = _GATE.require_bool(raw["treatedAsLicence"], "asset.treatedAsLicence")
    if not cited:
        faults.append(CITATION_MISSING)
    if redistribution != "granted" and bundled:
        faults.append(BUNDLED)
    if public and redistribution != "granted" and treated:
        faults.append(NEGATIVE_TOKEN)
    extra = [{
        "kind": kind,
        "publicUrl": url,
        "citation": citation if cited else None,
        "bundled": bundled,
        "redistribution": redistribution,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            BUNDLED: CASE["expected"],
            CITATION_MISSING: "citation metadata must be retained",
        },
    )
