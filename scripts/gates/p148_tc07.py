"""TC-P148-07 Release claim exceeds evidence.

Host reference. Implemented notes may list implemented or physically qualified
features only. Experimental roadmap entries copied into that list are rejected.
Native-resolution or camera-equivalence scopes require physical qualification.
The offline privacy rule still applies.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P148-07",
    "phase": "P148",
    "workstream": 19,
    "name": "Release claim exceeds evidence",
    "intervention": "Generate release notes for features with mixed implemented, experimental, and physically qualified states.",
    "expected": "Describe each scope accurately and exclude unsupported native-resolution or camera-equivalence claims.",
    "negative": "Copying the aspirational roadmap into the implemented list must fail.",
    "repeat": "Repeat source modes, live depth, deferred optics, and calibration status.",
}

NEGATIVE_TOKEN = "roadmap-copied-into-implemented"
UNSUPPORTED_SCOPE = "unsupported-native-or-equivalence-claim"
FEATURE_KEYS = {"id", "state", "scope"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "offline_claim",
    "permissions",
    "network_endpoints",
    "analytics_payload",
    "capture_needs_camera",
    "capture_needs_microphone",
    "visible_warnings",
    "hide_warnings",
    "uploads",
    "diagnostic_export",
    "optional_downloads_explicit",
    "operation_requires_network",
    "features",
    "implementedList",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p148_verify_offline_privacy_and_permissions.py"
    spec = importlib.util.spec_from_file_location("p148_gate_for_tc07", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _parse_features(value: object) -> list[dict]:
    _GATE.require(isinstance(value, list) and bool(value), "features must be a non-empty list")
    features = []
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict), f"features[{index}] must be an object")
        _GATE.require(set(item) == FEATURE_KEYS, f"features[{index}] keys are invalid")
        state = _GATE.require_text(item["state"], f"features[{index}].state")
        _GATE.require(state in _GATE.FEATURE_STATES, f"features[{index}].state is not recognized")
        features.append({
            "id": _GATE.require_text(item["id"], f"features[{index}].id"),
            "state": state,
            "scope": _GATE.require_text(item["scope"], f"features[{index}].scope"),
        })
    ids = [feature["id"] for feature in features]
    _GATE.require(len(ids) == len(set(ids)), "feature ids must be unique")
    return features


def _parse_implemented(value: object) -> list[str]:
    _GATE.require(isinstance(value, list), "implementedList must be a list")
    return [_GATE.require_text(item, f"implementedList[{index}]") for index, item in enumerate(value)]


def _release_faults(features: list[dict], implemented: list[str]) -> list[str]:
    by_id = {feature["id"]: feature for feature in features}
    faults: list[str] = []
    for feature_id in implemented:
        _GATE.require(feature_id in by_id, "implementedList entry is not a feature: " + feature_id)
        if by_id[feature_id]["state"] not in {"implemented", "physically-qualified"}:
            faults.append(NEGATIVE_TOKEN)
    for feature in features:
        if feature["scope"] in _GATE.FORBIDDEN_RELEASE_SCOPES and feature["state"] != "physically-qualified":
            faults.append(UNSUPPORTED_SCOPE)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    features = _parse_features(payload["features"])
    implemented = _parse_implemented(payload["implementedList"])
    faults = list(bundle["faults"])
    faults.extend(_release_faults(features, implemented))
    extra = [{
        "implementedList": implemented,
        "states": {feature["id"]: feature["state"] for feature in features},
        "scopes": {feature["id"]: feature["scope"] for feature in features},
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            UNSUPPORTED_SCOPE: CASE["expected"],
        },
    )
