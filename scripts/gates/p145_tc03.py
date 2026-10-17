"""TC-P145-03 Hostile imported file.

Host fixture. Malformed lengths, excessive dimensions, nonfinite transforms,
and archive traversal are rejected inside resource limits. Retained media is
not rewritten and storage is not escaped. Trusting an extension or an
unvalidated header is rejected.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

CASE = {
    "id": "TC-P145-03",
    "phase": "P145",
    "workstream": 19,
    "name": "Hostile imported file",
    "intervention": "Submit malformed lengths, excessive dimensions, nonfinite transforms, or archive traversal paths.",
    "expected": "Reject within bounded resource limits without escaping storage or corrupting retained media.",
    "negative": "Trusting extensions or unvalidated headers must fail.",
    "repeat": "Repeat parser truncation, decompression pressure, and repeated invalid imports.",
}

NEGATIVE_TOKEN = "trusting-extensions-or-unvalidated-headers"
HOSTILE_ACCEPTED = "hostile-import-accepted"
STORAGE_ESCAPE = "storage-escape"
MEDIA_CORRUPTED = "retained-media-corrupted"
RESOURCE_EXCEEDED = "resource-limit-exceeded"
PRESSURES = ("parser-truncation", "decompression-pressure", "repeated-invalid-imports")
IMPORT_KEYS = {
    "name",
    "extension",
    "declaredLength",
    "actualLength",
    "width",
    "height",
    "transform",
    "path",
    "headerValidated",
    "trustExtensionOnly",
    "accepted",
    "escapedStorage",
    "retainedSha256",
    "retainedSha256After",
}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "layers",
    "releasePassed",
    "releaseSummary",
    "importFile",
    "attempts",
    "pressure",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p145_build_the_layered_automated_test_system.py"
    spec = importlib.util.spec_from_file_location("p145_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _import_facts(spec: object) -> tuple[list[str], dict]:
    _GATE.require(isinstance(spec, dict), "importFile must be an object")
    _GATE.require(set(spec) == IMPORT_KEYS, "importFile keys are invalid")
    name = _GATE.require_text(spec["name"], "name")
    extension = _GATE.require_text(spec["extension"], "extension")
    _GATE.require(extension.startswith(".") and extension == extension.casefold(), "extension must be a dotted lowercase suffix")
    declared = _GATE.require_int(spec["declaredLength"], "declaredLength")
    actual = _GATE.require_int(spec["actualLength"], "actualLength")
    width = _GATE.require_int(spec["width"], "width")
    height = _GATE.require_int(spec["height"], "height")
    transform = spec["transform"]
    _GATE.require(isinstance(transform, list), "transform must be a list")
    nonfinite = False
    numbers: list[float] = []
    for item in transform:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError("transform item must be a number")
        number = float(item)
        if not math.isfinite(number):
            nonfinite = True
            continue
        numbers.append(number)
    path = _GATE.require_text(spec["path"], "path")
    header = _GATE.require_bool(spec["headerValidated"], "headerValidated")
    trust_extension = _GATE.require_bool(spec["trustExtensionOnly"], "trustExtensionOnly")
    accepted = _GATE.require_bool(spec["accepted"], "accepted")
    escaped = _GATE.require_bool(spec["escapedStorage"], "escapedStorage")
    before = _GATE.require_sha256(spec["retainedSha256"], "retainedSha256")
    after = _GATE.require_sha256(spec["retainedSha256After"], "retainedSha256After")
    escapes = _GATE.path_escapes(path)
    over_dimension = width < 1 or height < 1 or width > _GATE.IMPORT_MAX_DIMENSION or height > _GATE.IMPORT_MAX_DIMENSION
    over_bytes = actual > _GATE.IMPORT_MAX_BYTES
    over_expansion = declared > 0 and actual > declared * _GATE.IMPORT_MAX_EXPANSION
    length_mismatch = declared != actual
    hostile = length_mismatch or over_dimension or nonfinite or escapes or over_bytes or over_expansion
    faults: list[str] = []
    if accepted and hostile:
        faults.append(HOSTILE_ACCEPTED)
    if accepted and (not header or trust_extension):
        faults.append(NEGATIVE_TOKEN)
    if escaped:
        faults.append(STORAGE_ESCAPE)
    if before.casefold() != after.casefold():
        faults.append(MEDIA_CORRUPTED)
    if accepted and (over_bytes or over_expansion):
        faults.append(RESOURCE_EXCEEDED)
    observation = {
        "name": name,
        "extension": extension,
        "accepted": accepted,
        "hostile": hostile,
        "escapedStorage": escaped,
        "retainedSha256": before,
        "lengthMismatch": length_mismatch,
        "overDimension": over_dimension,
        "nonfinite": nonfinite,
        "pathEscapes": escapes,
        "overBytes": over_bytes,
        "overExpansion": over_expansion,
        "transform": numbers,
    }
    return faults, observation


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_layers(payload, {"importFile", "attempts", "pressure"})
    faults = list(bundle["faults"])
    attempts = _GATE.require_int(payload["attempts"], "attempts", minimum=1)
    pressure = _GATE.require_text(payload["pressure"], "pressure")
    _GATE.require(pressure in PRESSURES, "pressure is not recognized")
    import_faults, observation = _import_facts(payload["importFile"])
    faults.extend(import_faults)
    observation["attempts"] = attempts
    observation["pressure"] = pressure
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        HOSTILE_ACCEPTED: CASE["expected"],
        STORAGE_ESCAPE: "import must not escape storage",
        MEDIA_CORRUPTED: "retained media must stay unchanged",
        RESOURCE_EXCEEDED: "over-limit imports must be rejected",
    }
    return _GATE.finish_layers(CASE, bundle, faults, [observation], texts)
