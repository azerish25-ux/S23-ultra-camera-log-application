"""TC-P145-04 Unexpected network transmission.

Host fixture. With local assets installed, the offline default transmits no
frames, depth, audio, or private metadata. An analytics thumbnail upload
contradicts the local-processing claim.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P145-04",
    "phase": "P145",
    "workstream": 19,
    "name": "Unexpected network transmission",
    "intervention": "Observe capture and development traffic with local assets already installed.",
    "expected": "Transmit no frames, depth, audio, or private metadata under the offline default.",
    "negative": "An analytics thumbnail upload contradicts the local-processing claim.",
    "repeat": "Repeat startup, errors, crashes, export, and model initialization.",
}

NEGATIVE_TOKEN = "analytics-thumbnail-upload"
OFFLINE_TRANSMISSION = "offline-transmission"
OFFLINE_DISABLED = "offline-default-disabled"
ASSETS_MISSING = "local-assets-not-installed"
MEDIA_KINDS = frozenset({"frames", "depth", "audio", "private-metadata"})
KINDS = MEDIA_KINDS | {"analytics-thumbnail"}
OBSERVATIONS = ("startup", "errors", "crashes", "export", "model-initialization")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "layers",
    "releasePassed",
    "releaseSummary",
    "offlineDefault",
    "localAssetsInstalled",
    "transmissions",
    "observation",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p145_build_the_layered_automated_test_system.py"
    spec = importlib.util.spec_from_file_location("p145_gate_for_tc04", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _transmission(raw: object, index: int) -> dict:
    label = "transmission " + str(index)
    _GATE.require(isinstance(raw, dict), label + " must be an object")
    _GATE.require(set(raw) == {"kind", "bytes", "when"}, label + " keys are invalid")
    kind = _GATE.require_text(raw["kind"], label + " kind")
    _GATE.require(kind in KINDS, label + " kind is not recognized")
    size = _GATE.require_int(raw["bytes"], label + " bytes")
    when = _GATE.require_text(raw["when"], label + " when")
    _GATE.require(when in OBSERVATIONS, label + " when is not recognized")
    return {"kind": kind, "bytes": size, "when": when}


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_layers(
        payload,
        {"offlineDefault", "localAssetsInstalled", "transmissions", "observation"},
    )
    faults = list(bundle["faults"])
    offline = _GATE.require_bool(payload["offlineDefault"], "offlineDefault")
    installed = _GATE.require_bool(payload["localAssetsInstalled"], "localAssetsInstalled")
    observation = _GATE.require_text(payload["observation"], "observation")
    _GATE.require(observation in OBSERVATIONS, "observation is not recognized")
    raw_items = payload["transmissions"]
    _GATE.require(isinstance(raw_items, list), "transmissions must be a list")
    items = [_transmission(item, index) for index, item in enumerate(raw_items)]
    if not installed:
        faults.append(ASSETS_MISSING)
    if not offline:
        faults.append(OFFLINE_DISABLED)
    sent = [item for item in items if item["bytes"] > 0]
    if offline and any(item["kind"] in MEDIA_KINDS for item in sent):
        faults.append(OFFLINE_TRANSMISSION)
    if any(item["kind"] == "analytics-thumbnail" for item in sent):
        faults.append(NEGATIVE_TOKEN)
    extra = [{
        "offlineDefault": offline,
        "localAssetsInstalled": installed,
        "observation": observation,
        "transmitted": sent,
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        OFFLINE_TRANSMISSION: CASE["expected"],
        OFFLINE_DISABLED: "the offline default is required for the local-processing claim",
        ASSETS_MISSING: "local assets must already be installed",
    }
    return _GATE.finish_layers(CASE, bundle, faults, extra, texts)
