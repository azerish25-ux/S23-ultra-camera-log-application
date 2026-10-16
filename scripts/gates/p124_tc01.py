"""TC-P124-01 Ambiguous imported signal.

Host fixture. Detected color, rotation, and timing facts stay separate from
user interpretation. A filename extension does not select transfer or dynamic
range.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P124-01"
NAME = "Ambiguous imported signal"
INTERVENTION = "Import media with absent or contradictory color tags, rotation, or timing metadata."
EXPECTED = "Separate detected facts from user interpretation and avoid silent normalization to an assumed source type."
NEGATIVE = "Filename extension alone must not determine transfer or dynamic range."
REPEAT = "Repeat HDR-looking untagged clips, variable rates, and portrait rotation."
EXTENSION_TRANSFER = "extension-determines-transfer"
EXTENSION_RANGE = "extension-determines-dynamic-range"
SILENT_NORMALIZATION = "silent-normalization"
INTERPRETATION_AS_FACT = "interpretation-recorded-as-detected-fact"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "filename",
    "extension",
    "containerColorTag",
    "metadataColorTag",
    "rotationDegrees",
    "timingFrameRate",
    "timingTimebase",
    "detectedFacts",
    "userInterpretation",
    "assumedTransfer",
    "assumedDynamicRange",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_SPEC = importlib.util.spec_from_file_location(
    "p124_checkpoint_temporal_rendering_safely",
    Path(__file__).resolve().parent / "p124_checkpoint_temporal_rendering_safely.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _optional_text(value, label: str):
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be null or a non-empty string")
    return value


def _optional_number(value, label: str):
    if value is None:
        return None
    if type(value) is bool or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be null or a number")
    if value != value:
        raise ValueError(f"{label} must be finite")
    return float(value)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    filename = payload["filename"]
    extension = payload["extension"]
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("filename must be a non-empty string")
    if not isinstance(extension, str) or not extension.strip() or "." in extension:
        raise ValueError("extension must be a non-empty suffix without a dot")
    container = _optional_text(payload["containerColorTag"], "containerColorTag")
    metadata = _optional_text(payload["metadataColorTag"], "metadataColorTag")
    rotation = payload["rotationDegrees"]
    if rotation is not None and (type(rotation) is not int or rotation < 0 or rotation > 359):
        raise ValueError("rotationDegrees must be null or an int in 0..359")
    timing_rate = _optional_number(payload["timingFrameRate"], "timingFrameRate")
    timing_base = _optional_number(payload["timingTimebase"], "timingTimebase")
    facts = payload["detectedFacts"]
    if not isinstance(facts, list) or not facts or not all(isinstance(item, str) and item.strip() for item in facts):
        raise ValueError("detectedFacts must be a non-empty list of strings")
    interpretation = _optional_text(payload["userInterpretation"], "userInterpretation")
    assumed_transfer = _optional_text(payload["assumedTransfer"], "assumedTransfer")
    assumed_range = _optional_text(payload["assumedDynamicRange"], "assumedDynamicRange")

    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION, NEGATIVE]
    rejected: list[str] = []
    tags_absent = container is None and metadata is None
    if tags_absent and assumed_transfer is not None:
        rejected.append(EXTENSION_TRANSFER)
        reasons.append("filename extension " + extension + " does not determine transfer")
    if tags_absent and assumed_range is not None:
        rejected.append(EXTENSION_RANGE)
        reasons.append("filename extension " + extension + " does not determine dynamic range")
    contradictory = container is not None and metadata is not None and container != metadata
    if contradictory:
        reasons.append(f"detected container={container} metadata={metadata}")
        if assumed_transfer is not None:
            rejected.append(SILENT_NORMALIZATION)
            reasons.append("contradictory color tags were silently normalized")
        if not any(container in fact for fact in facts) or not any(metadata in fact for fact in facts):
            rejected.append(SILENT_NORMALIZATION)
            reasons.append("contradictory color tags were not both retained as detected facts")
    if interpretation is not None and interpretation in facts:
        rejected.append(INTERPRETATION_AS_FACT)
        reasons.append("user interpretation was stored as a detected fact")
    if rotation is None and any(fact.startswith("rotation=") for fact in facts):
        rejected.append(SILENT_NORMALIZATION)
        reasons.append("absent rotation was normalized to a detected angle")
    if timing_rate is None and timing_base is None and any("fps=" in fact for fact in facts):
        rejected.append(SILENT_NORMALIZATION)
        reasons.append("absent timing was normalized to a detected frame rate")
    if (
        timing_rate is not None
        and timing_base is not None
        and abs(timing_rate - timing_base) > 1e-6
        and assumed_transfer is not None
        and interpretation is None
    ):
        rejected.append(SILENT_NORMALIZATION)
        reasons.append("contradictory timing was silently normalized")
    if tags_absent and not any("color-tag-absent" == fact for fact in facts):
        rejected.append(SILENT_NORMALIZATION)
        reasons.append("absent color tags were not recorded as a detected fact")
    if not rejected:
        reasons.append("detected facts remain separate from user interpretation")
    preserved = [evidence, "filename=" + filename, "extension=" + extension]
    preserved.extend(facts)
    if interpretation is not None:
        preserved.append("userInterpretation=" + interpretation)
    decision = "rejected" if rejected else "recorded"
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    return _CORE.seal(result)
