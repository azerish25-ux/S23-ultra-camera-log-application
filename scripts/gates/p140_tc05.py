"""TC-P140-05 Publicly accessible but unlicensed asset.

Host reference. Citation metadata can stay. Unapproved bytes stay out of the
release bundle. Public visibility is not a redistribution licence.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P140-05",
    "phase": "P140",
    "workstream": 18,
    "name": "Publicly accessible but unlicensed asset",
    "intervention": "Offer a web-accessible still, LUT, or profile whose redistribution permission is unknown.",
    "expected": "Retain appropriate citation metadata while excluding unapproved bytes from the release bundle.",
    "negative": "Public visibility must not be treated as a redistribution licence.",
    "repeat": "Repeat promotional images, commercial LUTs, and research model weights.",
}
NEGATIVE_TOKEN = "public-visibility-treated-as-redistribution-licence"
CITATION_DROPPED = "citation-metadata-dropped"
ASSET_KINDS = frozenset({
    "still",
    "lut",
    "profile",
    "promotional-image",
    "commercial-lut",
    "research-model-weights",
})
LICENCES = frozenset({"unknown", "granted", "denied"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "assetId",
    "assetKind",
    "publiclyAccessible",
    "redistributionLicence",
    "citation",
    "citationRetained",
    "bytesInReleaseBundle",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p140_implement_offline_search_and_filtering.py"
    spec = importlib.util.spec_from_file_location("p140_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == set(PAYLOAD_KEYS), "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    asset_id = _GATE.require_text(payload["assetId"], "assetId")
    kind = _GATE.require_text(payload["assetKind"], "assetKind")
    _GATE.require(kind in ASSET_KINDS, "assetKind is not recognized")
    public = _GATE.require_bool(payload["publiclyAccessible"], "publiclyAccessible")
    licence = _GATE.require_text(payload["redistributionLicence"], "redistributionLicence")
    _GATE.require(licence in LICENCES, "redistributionLicence is not recognized")
    citation = _GATE.require_text(payload["citation"], "citation")
    retained = _GATE.require_bool(payload["citationRetained"], "citationRetained")
    bundled = _GATE.require_bool(payload["bytesInReleaseBundle"], "bytesInReleaseBundle")
    faults: list[str] = []
    if not retained:
        faults.append(CITATION_DROPPED)
    if bundled and licence != "granted":
        faults.append(NEGATIVE_TOKEN)
    record = {
        "id": asset_id,
        "title": citation,
        "assetKind": kind,
        "evidenceStatus": "citation-only" if not bundled else "bytes-bundled",
        "privateRecipe": False,
    }
    index = _GATE.build_token_index([record] if retained else [])
    found = _GATE.retrieve(index, citation)
    preserved = [
        evidence,
        {
            "assetId": asset_id,
            "assetKind": kind,
            "publiclyAccessible": public,
            "redistributionLicence": licence,
            "citation": citation if retained else None,
            "bytesInReleaseBundle": bundled,
            "bytesExcluded": not bundled,
            "searchIds": found,
        },
    ]
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + _GATE.ORACLE,
        CASE["expected"],
        "repeat " + repeat,
        "licence=" + licence,
        "bytesExcluded=" + ("true" if not bundled else "false"),
    ]
    if NEGATIVE_TOKEN in faults:
        reasons.append(CASE["negative"])
    if not faults:
        reasons.append("citation retained; unapproved bytes excluded from the release bundle")
    return _GATE.finish_result(CASE["id"], evidence, faults, reasons, preserved, [CASE["repeat"], repeat])
