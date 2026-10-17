"""TC-P141-05 Publicly accessible but unlicensed asset.

Host fixture. A web-accessible still, LUT, profile, or model weight keeps its
citation and stays out of the release bundle when redistribution permission
is unknown. Public visibility is not a licence. Rights are judged per asset.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P141-05",
    "phase": "P141",
    "workstream": 18,
    "name": "Publicly accessible but unlicensed asset",
    "intervention": "Offer a web-accessible still, LUT, or profile whose redistribution permission is unknown.",
    "expected": "Retain appropriate citation metadata while excluding unapproved bytes from the release bundle.",
    "negative": "Public visibility must not be treated as a redistribution licence.",
    "repeat": "Repeat promotional images, commercial LUTs, and research model weights.",
}

PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "assets",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p141_manage_reference_media_rights_and_attribution.py"
    spec = importlib.util.spec_from_file_location("p141_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    extra = [{
        "excludedAssetIds": [
            item["asset"]["asset_id"]
            for item in bundle["info"]["assets"]
            if not item["packaged"]
        ],
        "citationsRetained": [
            item["asset"]["asset_id"]
            for item in bundle["info"]["assets"]
            if item["asset"]["citation"] is not None and not item["packaged"]
        ],
    }]
    return _GATE.finish_case(CASE, bundle, faults, extra, { _GATE.PUBLIC_WEB_NOT_LICENCE: CASE["negative"] })
