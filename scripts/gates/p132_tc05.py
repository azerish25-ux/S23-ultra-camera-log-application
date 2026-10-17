"""TC-P132-05 Nonvisual interaction.

Host reference. Spoken scope values include domain, freshness, and the
computed clipping count. An unlabeled canvas as the only control is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P132-05",
    "phase": "P132",
    "workstream": 17,
    "name": "Nonvisual interaction",
    "intervention": "Perform the core phase task using accessibility navigation and spoken state information.",
    "expected": "Expose usable names, order, values, and cancellation without relying only on color or precision gestures.",
    "negative": "An unlabeled custom canvas as the only control must fail.",
    "repeat": "Repeat camera operation, ROI selection, focus editing, and recovery export.",
}

NEGATIVE_TOKEN = "unlabeled-canvas-only-control"
CONTROL_KEYS = {"name", "value", "cancellable"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "scopes",
    "source",
    "applyMutant",
    "unlabeledCanvasOnly",
    "controls",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p132_build_scopes_with_declared_signal_domains.py"
    spec = importlib.util.spec_from_file_location("p132_gate_for_tc05", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def spoken_value(record: dict) -> str:
    freshness = "fresh" if record["fresh"] else "stale"
    value = f"domain={record['domain']} label={record['label']} freshness={freshness}"
    if record["kind"] == "clipping":
        value += f" clippingCount={record['clippingCount']}"
    if record["kind"] == "false_color":
        value += f" inputDomain={record['inputDomain']}"
    return value


def _parse_controls(value: object) -> tuple[list[dict], bool]:
    _GATE.require(isinstance(value, list), "controls must be a list")
    parsed: list[dict] = []
    blank = False
    for index, item in enumerate(value):
        _GATE.require(isinstance(item, dict) and set(item) == CONTROL_KEYS, f"controls[{index}] keys are invalid")
        name = item["name"]
        spoken = item["value"]
        _GATE.require(isinstance(name, str), f"controls[{index}].name must be a string")
        _GATE.require(isinstance(spoken, str), f"controls[{index}].value must be a string")
        cancellable = _GATE.require_bool(item["cancellable"], f"controls[{index}].cancellable")
        if not name.strip() or name != name.strip() or not spoken.strip() or spoken != spoken.strip():
            blank = True
        parsed.append({"name": name, "value": spoken, "cancellable": cancellable, "order": index})
    return parsed, blank


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    unlabeled = _GATE.require_bool(payload["unlabeledCanvasOnly"], "unlabeledCanvasOnly")
    controls, blank = _parse_controls(payload["controls"])
    info = bundle["info"]
    missing_speech = False
    for record in info["records"]:
        match = next((item for item in controls if item["name"] == record["id"]), None)
        expected = spoken_value(record)
        if match is None or expected not in match["value"]:
            missing_speech = True
    source_expected = (
        f"domain={info['sourceDomain']} clippingCount={info['sourceClippingCount']}"
    )
    source_spoken = any(item["name"] == "source" and source_expected in item["value"] for item in controls)
    cancellable = any(item["cancellable"] for item in controls)
    if unlabeled or blank or not controls or missing_speech or not source_spoken or not cancellable:
        faults.append(NEGATIVE_TOKEN)
    extra = [{
        "unlabeledCanvasOnly": unlabeled,
        "controlOrder": [item["name"] for item in controls],
        "sourceSpoken": source_spoken,
        "clippingSpoken": not missing_speech,
        "cancellable": cancellable,
        "previewClippingCount": info["previewClippingCount"],
    }]
    return _GATE.finish_case(CASE, bundle, faults, extra, {NEGATIVE_TOKEN: CASE["negative"]})
