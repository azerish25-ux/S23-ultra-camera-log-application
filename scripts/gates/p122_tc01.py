"""TC-P122-01 Ambiguous imported signal.

Host fixture. Detected color, rotation, and timing stay separate from the user
interpretation. A filename extension does not assign transfer or dynamic range.
Recipe versions stay immutable and are checked by recomputed version hashes.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P122-01"
NAME = "Ambiguous imported signal"
INTERVENTION = "Import media with absent or contradictory color tags, rotation, or timing metadata."
EXPECTED = "Separate detected facts from user interpretation and avoid silent normalization to an assumed source type."
NEGATIVE = "Filename extension alone must not determine transfer or dynamic range."
REPEAT = "Repeat HDR-looking untagged clips, variable rates, and portrait rotation."
NEGATIVE_TOKEN = "filename-extension-determines-transfer-or-dynamic-range"
SILENT_TOKEN = "silent-source-normalization"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "filename",
    "detectedColorTag",
    "detectedDynamicRange",
    "detectedRotation",
    "detectedTiming",
    "userTransfer",
    "userDynamicRange",
    "interpretationExplicit",
    "extensionTransfer",
    "extensionDynamicRange",
    "silentNormalization",
    "versions",
    "mutatedInPlace",
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
    "p122_create_non_destructive_recipe_versions",
    Path(__file__).resolve().parent / "p122_create_non_destructive_recipe_versions.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def valid_versions():
    return _CORE.sample_versions()


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _optional(value, label: str):
    if value is None:
        return None
    return _text(value, label)


def _extension_alone(payload: dict) -> bool:
    matches = (
        payload["userTransfer"] == payload["extensionTransfer"]
        and payload["userDynamicRange"] == payload["extensionDynamicRange"]
    )
    if not matches or payload["interpretationExplicit"]:
        return False
    color = payload["detectedColorTag"]
    dynamic = payload["detectedDynamicRange"]
    facts_absent = color is None or dynamic is None
    contradicts = (color is not None and color != payload["userTransfer"]) or (
        dynamic is not None and dynamic != payload["userDynamicRange"]
    )
    return facts_absent or contradicts


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    filename = _text(payload["filename"], "filename")
    color = _optional(payload["detectedColorTag"], "detectedColorTag")
    dynamic = _optional(payload["detectedDynamicRange"], "detectedDynamicRange")
    rotation = _optional(payload["detectedRotation"], "detectedRotation")
    timing = _optional(payload["detectedTiming"], "detectedTiming")
    user_transfer = _text(payload["userTransfer"], "userTransfer")
    user_range = _text(payload["userDynamicRange"], "userDynamicRange")
    extension_transfer = _text(payload["extensionTransfer"], "extensionTransfer")
    extension_range = _text(payload["extensionDynamicRange"], "extensionDynamicRange")
    if type(payload["interpretationExplicit"]) is not bool or type(payload["silentNormalization"]) is not bool:
        raise ValueError("interpretation flags must be bools")
    chain = _CORE.review_versions(payload["versions"], mutated_in_place=payload["mutatedInPlace"])
    rejected = list(chain["rejectedClaims"])
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION, f"repeat {repeat}", f"filename {filename}"]
    reasons.extend(chain["reasons"])
    if payload["silentNormalization"] and SILENT_TOKEN not in rejected:
        rejected.append(SILENT_TOKEN)
        reasons.append("silent normalization to an assumed source type")
    elif payload["silentNormalization"]:
        reasons.append("silent normalization to an assumed source type")
    if _extension_alone(payload):
        if NEGATIVE_TOKEN not in rejected:
            rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    preserved = [
        evidence,
        f"detectedColorTag={color if color is not None else 'absent'}",
        f"detectedDynamicRange={dynamic if dynamic is not None else 'absent'}",
        f"detectedRotation={rotation if rotation is not None else 'absent'}",
        f"detectedTiming={timing if timing is not None else 'absent'}",
        f"userTransfer={user_transfer}",
        f"userDynamicRange={user_range}",
        f"extensionTransfer={extension_transfer}",
        f"extensionDynamicRange={extension_range}",
    ]
    preserved.extend(chain["preservedResults"])
    result = _CORE.finish_result(
        CASE_ID,
        reasons,
        rejected,
        preserved,
        ["physical S23 measurement was not run", REPEAT],
    )
    if tuple(result) != RESULT_KEYS or evidence not in result["preservedResults"]:
        raise ValueError("result contract drifted")
    return result
