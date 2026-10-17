"""TC-P143-05 Publicly accessible but unlicensed asset.

Host reference. Citation metadata stays. Bytes without a redistribution grant
stay out of the release bundle. Public visibility is not a licence. Release
looks stay distinct.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P143-05",
    "phase": "P143",
    "workstream": 18,
    "name": "Publicly accessible but unlicensed asset",
    "intervention": "Offer a web-accessible still, LUT, or profile whose redistribution permission is unknown.",
    "expected": "Retain appropriate citation metadata while excluding unapproved bytes from the release bundle.",
    "negative": "Public visibility must not be treated as a redistribution licence.",
    "repeat": "Repeat promotional images, commercial LUTs, and research model weights.",
}

NEGATIVE_TOKEN = "public-visibility-treated-as-licence"
UNAPPROVED_BYTES = "unapproved-bytes-in-release-bundle"
CITATION_DROPPED = "citation-dropped"
KINDS = frozenset({
    "promotional-image",
    "commercial-lut",
    "research-weights",
    "still",
    "lut",
    "profile",
})
PERMISSIONS = frozenset({"unknown", "granted", "denied"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "looks",
    "dropAmbiguous",
    "assetKind",
    "publiclyAccessible",
    "redistributionPermission",
    "citationRetained",
    "bytesInReleaseBundle",
    "treatsPublicAsLicence",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p143_support_release_specific_and_scene_specific_looks.py"
    spec = importlib.util.spec_from_file_location("p143_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    kind = _GATE.require_text(payload["assetKind"], "assetKind")
    _GATE.require(kind in KINDS, "assetKind is not recognized")
    public = _GATE.require_bool(payload["publiclyAccessible"], "publiclyAccessible")
    permission = _GATE.require_text(payload["redistributionPermission"], "redistributionPermission")
    _GATE.require(permission in PERMISSIONS, "redistributionPermission is not recognized")
    citation = _GATE.require_bool(payload["citationRetained"], "citationRetained")
    bundled = _GATE.require_bool(payload["bytesInReleaseBundle"], "bytesInReleaseBundle")
    treats_public = _GATE.require_bool(payload["treatsPublicAsLicence"], "treatsPublicAsLicence")
    if treats_public:
        faults.append(NEGATIVE_TOKEN)
    if permission in {"unknown", "denied"} and bundled:
        faults.append(UNAPPROVED_BYTES)
    if permission == "unknown" and not citation:
        faults.append(CITATION_DROPPED)
    if permission == "granted" and bundled and not citation:
        faults.append(CITATION_DROPPED)
    extra = [{
        "assetKind": kind,
        "publiclyAccessible": public,
        "redistributionPermission": permission,
        "citationRetained": citation,
        "bytesInReleaseBundle": bundled,
        "treatsPublicAsLicence": treats_public,
    }]
    return _GATE.finish_case(CASE, bundle, faults, extra, {
        NEGATIVE_TOKEN: CASE["negative"],
        UNAPPROVED_BYTES: "unapproved bytes are excluded from the release bundle",
        CITATION_DROPPED: "citation metadata must be retained",
    })
