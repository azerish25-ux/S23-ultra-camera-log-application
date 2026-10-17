"""TC-P145-07 Release claim exceeds evidence.

Host fixture. Implemented, experimental, roadmap, and physically qualified
scopes stay in their own lists. The aspirational roadmap is not the
implemented list. Native-resolution and camera-equivalence claims are excluded.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P145-07",
    "phase": "P145",
    "workstream": 19,
    "name": "Release claim exceeds evidence",
    "intervention": "Generate release notes for features with mixed implemented, experimental, and physically qualified states.",
    "expected": "Describe each scope accurately and exclude unsupported native-resolution or camera-equivalence claims.",
    "negative": "Copying the aspirational roadmap into the implemented list must fail.",
    "repeat": "Repeat source modes, live depth, deferred optics, and calibration status.",
}

NEGATIVE_TOKEN = "aspirational-roadmap-copied-into-implemented"
SCOPE_MISSTATED = "scope-misstated"
NATIVE_RESOLUTION = "native-resolution-claim"
CAMERA_EQUIVALENCE = "camera-equivalence-claim"
STATES = ("implemented", "experimental", "physically-qualified", "roadmap")
NOTE_KEYS = ("implemented", "experimental", "physicallyQualified")
SCOPES = ("source-modes", "live-depth", "deferred-optics", "calibration-status")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "layers",
    "releasePassed",
    "releaseSummary",
    "features",
    "notes",
    "claimsNativeResolution",
    "claimsCameraEquivalence",
    "scope",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p145_build_the_layered_automated_test_system.py"
    spec = importlib.util.spec_from_file_location("p145_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _features(raw: object) -> list[dict[str, str]]:
    _GATE.require(isinstance(raw, list) and raw, "features must be a non-empty list")
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        label = "feature " + str(index)
        _GATE.require(isinstance(item, dict), label + " must be an object")
        _GATE.require(set(item) == {"id", "state"}, label + " keys are invalid")
        feature_id = _GATE.require_text(item["id"], label + " id")
        state = _GATE.require_text(item["state"], label + " state")
        _GATE.require(state in STATES, label + " state is not recognized")
        _GATE.require(feature_id not in seen, "duplicate feature id")
        seen.add(feature_id)
        found.append({"id": feature_id, "state": state})
    return found


def _notes(raw: object, known: set[str]) -> dict[str, list[str]]:
    _GATE.require(isinstance(raw, dict), "notes must be an object")
    _GATE.require(set(raw) == set(NOTE_KEYS), "notes keys are invalid")
    notes: dict[str, list[str]] = {}
    seen: set[str] = set()
    for key in NOTE_KEYS:
        values = raw[key]
        _GATE.require(isinstance(values, list), key + " must be a list")
        bucket: list[str] = []
        for item in values:
            feature_id = _GATE.require_text(item, key + " id")
            _GATE.require(feature_id in known, "notes cite an unknown feature")
            _GATE.require(feature_id not in seen, "feature listed in more than one scope")
            seen.add(feature_id)
            bucket.append(feature_id)
        notes[key] = bucket
    return notes


def _expected_bucket(state: str, physical_status: str) -> str | None:
    if state == "roadmap":
        return None
    if state == "physically-qualified":
        if physical_status == "passed":
            return "physicallyQualified"
        return "experimental"
    if state == "implemented":
        return "implemented"
    return "experimental"


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_layers(
        payload,
        {"features", "notes", "claimsNativeResolution", "claimsCameraEquivalence", "scope"},
    )
    faults = list(bundle["faults"])
    scope = _GATE.require_text(payload["scope"], "scope")
    _GATE.require(scope in SCOPES, "scope is not recognized")
    native = _GATE.require_bool(payload["claimsNativeResolution"], "claimsNativeResolution")
    camera = _GATE.require_bool(payload["claimsCameraEquivalence"], "claimsCameraEquivalence")
    features = _features(payload["features"])
    known = {item["id"] for item in features}
    notes = _notes(payload["notes"], known)
    physical_status = bundle["rows"]["physical"]["status"]
    listed = {feature_id: key for key in NOTE_KEYS for feature_id in notes[key]}
    for feature in features:
        expected = _expected_bucket(feature["state"], physical_status)
        actual = listed.get(feature["id"])
        if feature["state"] == "roadmap" and feature["id"] in notes["implemented"]:
            faults.append(NEGATIVE_TOKEN)
        if actual != expected:
            faults.append(SCOPE_MISSTATED)
    if native:
        faults.append(NATIVE_RESOLUTION)
    if camera:
        faults.append(CAMERA_EQUIVALENCE)
    extra = [{
        "scope": scope,
        "physicalStatus": physical_status,
        "notes": notes,
        "claimsNativeResolution": native,
        "claimsCameraEquivalence": camera,
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        SCOPE_MISSTATED: CASE["expected"],
        NATIVE_RESOLUTION: "native-resolution is not supported by this evidence",
        CAMERA_EQUIVALENCE: "camera equivalence is not supported by this evidence",
    }
    return _GATE.finish_layers(CASE, bundle, faults, extra, texts)
