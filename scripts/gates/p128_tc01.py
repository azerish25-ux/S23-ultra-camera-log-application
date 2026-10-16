"""TC-P128-01 Ambiguous imported signal.

Host fixture. Filename extension does not assign transfer or dynamic range.
Detected tags, rotation, and timing stay separate from user interpretation.
The long-form frame account still has to be exact.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path


CASE_INDEX = 0
NEGATIVE_TOKEN = "filename-extension-determines-transfer-or-dynamic-range"
SILENT_TOKEN = "silent-source-type-normalization"
ROTATION_TOKEN = "silent-rotation-normalization"
TIMING_TOKEN = "silent-timing-normalization"
EXTENSION_ASSUMPTIONS = {
    "mov": ("rec709", "sdr"),
    "mp4": ("rec709", "sdr"),
    "mxf": ("logc3", "scene-log"),
}
UNTAGGED = {"absent", "contradictory"}
FACT_VALUES = {"unspecified", "contradictory"}
TIMING_VALUES = {"absent", "contradictory", "constant", "variable"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "filename",
    "colorTag",
    "rotationDegrees",
    "reportedRotation",
    "timingMetadata",
    "reportedTiming",
    "detectedTransfer",
    "detectedDynamicRange",
    "userTransfer",
    "userDynamicRange",
    "expected_frames",
    "accounted_frames",
    "checkpoint_frames",
    "audio_duration",
    "video_duration",
    "audio_absent",
    "spot_check_only",
)

_SPEC = importlib.util.spec_from_file_location(
    "p128_validate_long_form_development_end_to_end",
    Path(__file__).resolve().parent / "p128_validate_long_form_development_end_to_end.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)
CASE = _CORE.CASES[CASE_INDEX]
CASE_ID = CASE["id"]
NAME = CASE["name"]
INTERVENTION = CASE["intervention"]
EXPECTED = CASE["expected"]
NEGATIVE = CASE["negative"]
REPEAT = CASE["repeat"]
RESULT_KEYS = _CORE.RESULT_KEYS


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _optional_number(value, label: str):
    if value is None:
        return None
    if type(value) is bool or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number or null")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _same_rotation(left, right) -> bool:
    if left is None or right is None:
        return left is right
    return math.isclose(left, right, rel_tol=0.0, abs_tol=1e-9)


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    filename = _text(payload["filename"], "filename")
    if "." not in filename or not filename.rsplit(".", 1)[1]:
        raise ValueError("filename must include an extension")
    extension = filename.rsplit(".", 1)[1].lower()
    color_tag = _text(payload["colorTag"], "colorTag")
    rotation = _optional_number(payload["rotationDegrees"], "rotationDegrees")
    reported_rotation = _optional_number(payload["reportedRotation"], "reportedRotation")
    timing = _text(payload["timingMetadata"], "timingMetadata")
    reported_timing = _text(payload["reportedTiming"], "reportedTiming")
    if timing not in TIMING_VALUES or reported_timing not in TIMING_VALUES:
        raise ValueError("timing metadata is not a known value")
    detected_transfer = _text(payload["detectedTransfer"], "detectedTransfer")
    detected_range = _text(payload["detectedDynamicRange"], "detectedDynamicRange")
    user_transfer = _text(payload["userTransfer"], "userTransfer")
    user_range = _text(payload["userDynamicRange"], "userDynamicRange")
    account = _CORE.validate_long_form(
        payload["expected_frames"],
        payload["accounted_frames"],
        payload["checkpoint_frames"],
        payload["audio_duration"],
        payload["video_duration"],
        payload["audio_absent"],
        payload["spot_check_only"],
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(account["reasons"])
    reasons.append(f"extension={extension} extension-not-used-as-detected-fact")
    reasons.append(f"detectedTransfer={detected_transfer}")
    reasons.append(f"userTransfer={user_transfer}")
    reasons.append(f"detectedDynamicRange={detected_range}")
    reasons.append(f"userDynamicRange={user_range}")
    rejected = list(account["rejectedClaims"])
    if color_tag in UNTAGGED:
        assumption = EXTENSION_ASSUMPTIONS.get(extension)
        pair = (detected_transfer, detected_range)
        if assumption is not None and pair == assumption:
            _add(rejected, NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
        elif detected_transfer not in FACT_VALUES or detected_range not in FACT_VALUES:
            _add(rejected, SILENT_TOKEN)
            reasons.append("untagged or contradictory signal was normalized to an assumed source type")
        else:
            reasons.append("detected facts stay unspecified or contradictory")
    else:
        reasons.append(f"colorTag={color_tag} kept as a detected fact")
    if not _same_rotation(rotation, reported_rotation):
        _add(rejected, ROTATION_TOKEN)
        reasons.append("reported rotation must keep the detected rotation, including absent")
    else:
        reasons.append("rotation=" + ("absent" if rotation is None else format(rotation, ".12g")))
    if reported_timing != timing:
        _add(rejected, TIMING_TOKEN)
        reasons.append("reported timing must keep the detected timing")
    else:
        reasons.append("timing=" + timing)
    preserved = [evidence, f"detectedTransfer={detected_transfer}", f"userTransfer={user_transfer}"]
    preserved.extend(account["preservedResults"])
    decision = "rejected" if rejected else "recorded"
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
