"""TC-P127-01 Ambiguous imported signal.

Host fixture. Detected color, rotation, and timing stay separate from user
interpretation. A filename extension must not fill transfer or dynamic range.
Bundle manifest rules still apply to the export.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P127-01"
NAME = "Ambiguous imported signal"
INTERVENTION = "Import media with absent or contradictory color tags, rotation, or timing metadata."
EXPECTED = "Separate detected facts from user interpretation and avoid silent normalization to an assumed source type."
NEGATIVE = "Filename extension alone must not determine transfer or dynamic range."
REPEAT = "Repeat HDR-looking untagged clips, variable rates, and portrait rotation."
NEGATIVE_TOKEN = "filename-extension-determined-transfer"
SILENT_TOKEN = "silent-normalization-to-assumed-source"
CONTRADICTION_TOKEN = "contradictory-detected-facts-collapsed"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "filename",
    "labels",
    "manifest",
    "export_allowed",
    "grade_applied",
    "metadataTexts",
    "interpretation",
    "selfDescribing",
    "publishPrivatePaths",
    "personalIdentifiers",
    "detectedColorTags",
    "detectedRotation",
    "detectedFrameRate",
    "timingVariable",
    "userTransfer",
    "userDynamicRange",
    "importerTransfer",
    "importerDynamicRange",
    "userOverride",
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
    "p127_export_interoperable_result_bundles",
    Path(__file__).resolve().parent / "p127_export_interoperable_result_bundles.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _optional(value, label: str):
    if value is None:
        return None
    return _CORE.require_text(value, label, stripped=True)


def _rotation(value):
    if value is None:
        return None
    if type(value) is bool or not isinstance(value, (int, float)):
        raise ValueError("detectedRotation must be a number or null")
    number = float(value)
    if number != number or number in {float("inf"), float("-inf")}:
        raise ValueError("detectedRotation must be finite")
    return number


def _rate(value):
    if value is None:
        return None
    if type(value) is bool or not isinstance(value, (int, float)):
        raise ValueError("detectedFrameRate must be a number or null")
    number = float(value)
    if not number > 0 or number in {float("inf"), float("-inf")}:
        raise ValueError("detectedFrameRate must be positive and finite")
    return number


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _CORE.require_text(payload["evidenceId"], "evidenceId", stripped=True)
    repeat = _CORE.require_text(payload["repeat"], "repeat", stripped=True)
    tags = payload["detectedColorTags"]
    if not isinstance(tags, list) or any(not isinstance(item, str) or not item.strip() for item in tags):
        raise ValueError("detectedColorTags must be a list of non-empty strings")
    rotation = _rotation(payload["detectedRotation"])
    rate = _rate(payload["detectedFrameRate"])
    if type(payload["timingVariable"]) is not bool or type(payload["userOverride"]) is not bool:
        raise ValueError("timing flags must be bools")
    user_transfer = _optional(payload["userTransfer"], "userTransfer")
    user_range = _optional(payload["userDynamicRange"], "userDynamicRange")
    importer_transfer = _optional(payload["importerTransfer"], "importerTransfer")
    importer_range = _optional(payload["importerDynamicRange"], "importerDynamicRange")
    if payload["userOverride"] and user_transfer is None and user_range is None:
        raise ValueError("userOverride requires an explicit user interpretation")
    bundle = _CORE.judge_bundle(payload)
    distinct = list(dict.fromkeys(tags))
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(bundle["reasons"])
    rejected = list(bundle["rejectedClaims"])
    reasons.append("detectedColorTags=" + (",".join(distinct) if distinct else "absent"))
    reasons.append("detectedRotation=" + ("absent" if rotation is None else format(rotation, ".12g")))
    reasons.append("detectedFrameRate=" + ("absent" if rate is None else format(rate, ".12g")))
    reasons.append("timingVariable=" + ("true" if payload["timingVariable"] else "false"))
    reasons.append("userTransfer=" + (user_transfer if user_transfer is not None else "absent"))
    reasons.append("userDynamicRange=" + (user_range if user_range is not None else "absent"))
    extension = payload["filename"].rsplit(".", 1)[-1].lower() if "." in payload["filename"] else ""
    reasons.append("filenameExtension=" + (extension or "absent") + " is not a transfer")
    if len(distinct) > 1:
        if importer_transfer is not None or importer_range is not None:
            rejected.append(CONTRADICTION_TOKEN)
            reasons.append("contradictory detected tags were collapsed into one importer conclusion")
        else:
            reasons.append("contradictory detected facts left unresolved")
    elif len(distinct) == 1:
        if importer_transfer is not None and importer_transfer != distinct[0] and not payload["userOverride"]:
            rejected.append(SILENT_TOKEN)
            reasons.append(EXPECTED)
        elif payload["userOverride"]:
            reasons.append("user interpretation kept separate from the detected tag")
        else:
            reasons.append("detected tag retained without assuming a second source type")
    else:
        filled = importer_transfer is not None or importer_range is not None
        explicit = user_transfer is not None or user_range is not None
        if filled and not explicit and not payload["userOverride"]:
            rejected.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
        elif explicit and (
            (importer_transfer is None or importer_transfer == user_transfer)
            and (importer_range is None or importer_range == user_range)
        ):
            reasons.append("explicit user interpretation was not inferred from the filename extension")
        elif filled and not payload["userOverride"]:
            rejected.append(SILENT_TOKEN)
            reasons.append("untagged media was normalized to an assumed source type")
        else:
            reasons.append("ambiguous import left unresolved; no assumed source type")
    preserved = [evidence, "detected-facts-separated-from-user-interpretation"]
    preserved.extend(bundle["preservedResults"])
    result = _CORE.seal(
        CASE_ID,
        evidence,
        reasons,
        rejected,
        preserved,
        ["physical S23 measurement was not run", REPEAT],
    )
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    return result
