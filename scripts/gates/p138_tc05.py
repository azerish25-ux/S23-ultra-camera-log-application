"""TC-P138-05 Publicly accessible but unlicensed asset.

Host fixture. Citation metadata stays with the recipe family. Bytes whose
redistribution permission is unknown are excluded. Public visibility is not
a licence.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P138-05",
    "phase": "P138",
    "workstream": 18,
    "name": "Publicly accessible but unlicensed asset",
    "intervention": "Offer a web-accessible still, LUT, or profile whose redistribution permission is unknown.",
    "expected": "Retain appropriate citation metadata while excluding unapproved bytes from the release bundle.",
    "negative": "Public visibility must not be treated as a redistribution licence.",
    "repeat": "Repeat promotional images, commercial LUTs, and research model weights.",
}

NEGATIVE_TOKEN = "public-visibility-treated-as-redistribution-licence"
ASSET_KEYS = {
    "kind",
    "source_id",
    "citation",
    "publiclyAccessible",
    "redistributionLicensed",
    "includeBytes",
}
KINDS = {"still", "lut", "profile", "promotional-image", "commercial-lut", "research-weights"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "family",
    "max_entries",
    "asset",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p138_build_the_first_sourced_recipe_family.py"
    spec = importlib.util.spec_from_file_location("p138_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def parse_asset(raw: object) -> dict:
    _GATE.require(isinstance(raw, dict), "asset must be an object")
    _GATE.require(set(raw) == ASSET_KEYS, "asset keys are invalid")
    kind = _GATE.require_text(raw["kind"], "kind")
    _GATE.require(kind in KINDS, "asset kind is not recognised")
    licensed = raw["redistributionLicensed"]
    _GATE.require(licensed is None or type(licensed) is bool, "redistributionLicensed must be bool or null")
    return {
        "kind": kind,
        "source_id": _GATE.require_text(raw["source_id"], "asset source_id"),
        "citation": _GATE.require_text(raw["citation"], "citation"),
        "publiclyAccessible": _GATE.require_bool(raw["publiclyAccessible"], "publiclyAccessible"),
        "redistributionLicensed": licensed,
        "includeBytes": _GATE.require_bool(raw["includeBytes"], "includeBytes"),
    }


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_family_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    asset = parse_asset(payload["asset"])
    licensed = asset["redistributionLicensed"] is True
    if asset["includeBytes"] and not licensed:
        faults.append(NEGATIVE_TOKEN)
    record = {
        "kind": asset["kind"],
        "source_id": asset["source_id"],
        "citation": asset["citation"],
        "publiclyAccessible": asset["publiclyAccessible"],
        "redistributionLicensed": asset["redistributionLicensed"],
        "bytesIncluded": bool(asset["includeBytes"] and licensed),
    }
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        [record],
        {NEGATIVE_TOKEN: CASE["negative"]},
    )
