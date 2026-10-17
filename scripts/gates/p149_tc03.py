"""TC-P149-03 Hostile imported file.

Host reference. Malformed lengths, excessive dimensions, nonfinite transforms,
and archive traversal paths must be rejected inside resource bounds. Trusting
an extension or accepting an unvalidated header is rejected. Escaping storage
or corrupting retained media is rejected.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

CASE = {
    "id": "TC-P149-03",
    "phase": "P149",
    "workstream": 19,
    "name": "Hostile imported file",
    "intervention": "Submit malformed lengths, excessive dimensions, nonfinite transforms, or archive traversal paths.",
    "expected": "Reject within bounded resource limits without escaping storage or corrupting retained media.",
    "negative": "Trusting extensions or unvalidated headers must fail.",
    "repeat": "Repeat parser truncation, decompression pressure, and repeated invalid imports.",
}

NEGATIVE_TOKEN = "trusted-extension-or-unvalidated-header"
HOSTILE_ACCEPTED = "hostile-import-not-rejected"
STORAGE_DAMAGE = "storage-escape-or-media-corruption"
IMPORT_KEYS = {
    "length",
    "width",
    "height",
    "transform",
    "path",
    "extension",
    "headerValidated",
    "trustedExtension",
    "accepted",
    "escapedStorage",
    "corruptedRetainedMedia",
    "bytesAllocated",
}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "applyMutant",
    "thermalStatus",
    "continueCapture",
    "controlledStop",
    "advertisedFpsClaimed",
    "optionalPreviewReduced",
    "footagePreserved",
    "sampleDurationSeconds",
    "frameRateGuaranteeClaimed",
    "measuredOnDevice",
    "envelopeStatus",
    "configuration",
    "ambientCelsius",
    "deviceState",
    "imported",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p149_establish_thermal_and_endurance_acceptance.py"
    spec = importlib.util.spec_from_file_location("p149_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _hostile_transform(transform: object) -> bool:
    _GATE.require(isinstance(transform, list), "imported.transform must be a list")
    if len(transform) != 9:
        return True
    for item in transform:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            return True
        if not math.isfinite(float(item)):
            return True
    return False


def _hostile_path(path: str) -> bool:
    if path.startswith("/") or path.startswith("\\"):
        return True
    parts = path.replace("\\", "/").split("/")
    return ".." in parts


def _parse_import(value: object) -> dict:
    _GATE.require(isinstance(value, dict), "imported must be an object")
    _GATE.require(set(value) == IMPORT_KEYS, "imported keys are invalid")
    length = _GATE.require_int(value["length"], "imported.length")
    width = _GATE.require_int(value["width"], "imported.width")
    height = _GATE.require_int(value["height"], "imported.height")
    allocated = _GATE.require_int(value["bytesAllocated"], "imported.bytesAllocated")
    path = _GATE.require_text(value["path"], "imported.path")
    extension = _GATE.require_text(value["extension"], "imported.extension")
    return {
        "length": length,
        "width": width,
        "height": height,
        "transform": value["transform"],
        "path": path,
        "extension": extension,
        "headerValidated": _GATE.require_bool(value["headerValidated"], "imported.headerValidated"),
        "trustedExtension": _GATE.require_bool(value["trustedExtension"], "imported.trustedExtension"),
        "accepted": _GATE.require_bool(value["accepted"], "imported.accepted"),
        "escapedStorage": _GATE.require_bool(value["escapedStorage"], "imported.escapedStorage"),
        "corruptedRetainedMedia": _GATE.require_bool(
            value["corruptedRetainedMedia"], "imported.corruptedRetainedMedia"
        ),
        "bytesAllocated": allocated,
        "hostileTransform": _hostile_transform(value["transform"]),
        "hostilePath": _hostile_path(path),
    }


def _import_faults(imported: dict) -> list[str]:
    over_budget = (
        imported["length"] > _GATE.MAX_LENGTH
        or imported["width"] > _GATE.MAX_DIMENSION
        or imported["height"] > _GATE.MAX_DIMENSION
        or imported["bytesAllocated"] > _GATE.MAX_ALLOCATION
    )
    malformed = (
        imported["length"] <= 0
        or imported["width"] <= 0
        or imported["height"] <= 0
        or imported["hostilePath"]
        or imported["hostileTransform"]
    )
    faults: list[str] = []
    if imported["bytesAllocated"] > _GATE.MAX_ALLOCATION or ((malformed or over_budget) and imported["accepted"]):
        faults.append(HOSTILE_ACCEPTED)
    if imported["trustedExtension"] or (imported["accepted"] and not imported["headerValidated"]):
        faults.append(NEGATIVE_TOKEN)
    if imported["escapedStorage"] or imported["corruptedRetainedMedia"]:
        faults.append(STORAGE_DAMAGE)
    return faults


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    imported = _parse_import(payload["imported"])
    faults = list(bundle["faults"])
    faults.extend(_import_faults(imported))
    extra = [{
        "accepted": imported["accepted"],
        "path": imported["path"],
        "extension": imported["extension"],
        "headerValidated": imported["headerValidated"],
        "trustedExtension": imported["trustedExtension"],
        "escapedStorage": imported["escapedStorage"],
        "corruptedRetainedMedia": imported["corruptedRetainedMedia"],
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            HOSTILE_ACCEPTED: CASE["expected"],
            STORAGE_DAMAGE: "escaping storage or corrupting retained media is rejected",
        },
    )
