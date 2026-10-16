"""TC-P126-01 Ambiguous imported signal.

Host fixture. Filename extension does not assign transfer or dynamic range.
Detected tags stay separate from user interpretation. Clip rows still follow
the P126 playable rule.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

CASE_INDEX = 0
NEGATIVE_TOKEN = "filename-extension-determines-transfer"
CONTRADICTION_TOKEN = "contradictory-color-tags"
SILENT_TOKEN = "silent-source-type-normalization"
TRANSFER_TOKEN = "declared-transfer-contradicts-tag"
RANGE_TOKEN = "declared-dynamic-range-contradicts-tag"
TRANSFER_FOR_TAG = {"rec709": "rec709", "hlg": "hlg", "pq": "pq", "logc3": "logc3"}
RANGE_FOR_TAG = {"rec709": "sdr", "hlg": "hdr", "pq": "hdr", "logc3": "log"}
KNOWN_TAGS = set(TRANSFER_FOR_TAG) | {"unknown"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "filename",
    "colorTag",
    "containerTransfer",
    "rotationDegrees",
    "timingRate",
    "declaredTransfer",
    "declaredDynamicRange",
    "userInterpretation",
    "clips",
    "omitted_ids",
)

_SPEC = importlib.util.spec_from_file_location(
    "p126_build_a_trustworthy_clip_library",
    Path(__file__).resolve().parent / "p126_build_a_trustworthy_clip_library.py",
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


def _optional_text(value, label: str):
    if value is None:
        return None
    return _text(value, label)


def _optional_tag(value, label: str):
    if value is None:
        return None
    if value not in KNOWN_TAGS:
        raise ValueError(f"{label} is not a known color tag")
    return value


def _optional_number(value, label: str, *, positive: bool):
    if value is None:
        return None
    if type(value) is bool or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number or null")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    if positive and number <= 0:
        raise ValueError(f"{label} must be positive")
    return number


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    filename = _text(payload["filename"], "filename")
    color_tag = _optional_tag(payload["colorTag"], "colorTag")
    container = _optional_tag(payload["containerTransfer"], "containerTransfer")
    rotation = _optional_number(payload["rotationDegrees"], "rotationDegrees", positive=False)
    timing = _optional_number(payload["timingRate"], "timingRate", positive=True)
    declared_transfer = _optional_text(payload["declaredTransfer"], "declaredTransfer")
    declared_range = _optional_text(payload["declaredDynamicRange"], "declaredDynamicRange")
    user_interpretation = _optional_text(payload["userInterpretation"], "userInterpretation")
    library = _CORE.evaluate_library(payload["clips"], payload["omitted_ids"])
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "none"
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(library["reasons"])
    reasons.append(f"extension={extension} extension-not-used-for-transfer")
    reasons.append("detected.color_tag=" + (color_tag if color_tag is not None else "absent"))
    reasons.append("detected.container_transfer=" + (container if container is not None else "absent"))
    reasons.append(
        "detected.rotation=" + ("unspecified" if rotation is None else format(rotation, ".12g"))
    )
    reasons.append("detected.timing=" + ("unspecified" if timing is None else format(timing, ".12g")))
    reasons.append("user_interpretation=" + (user_interpretation if user_interpretation is not None else "none"))
    rejected = list(library["rejectedClaims"])
    untagged = color_tag is None or color_tag == "unknown"
    if untagged and (declared_transfer is not None or declared_range is not None):
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if color_tag is not None and container is not None and color_tag != container:
        _add(rejected, CONTRADICTION_TOKEN)
        reasons.append("contradictory color tags kept separate")
        if declared_transfer is not None or declared_range is not None:
            _add(rejected, SILENT_TOKEN)
            reasons.append("contradictory tags were not normalized to one source type")
    if color_tag in TRANSFER_FOR_TAG:
        if declared_transfer not in (None, TRANSFER_FOR_TAG[color_tag]):
            _add(rejected, TRANSFER_TOKEN)
            reasons.append("declared transfer contradicts the detected color tag")
        if declared_range not in (None, RANGE_FOR_TAG[color_tag]):
            _add(rejected, RANGE_TOKEN)
            reasons.append("declared dynamic range contradicts the detected color tag")
    preserved = [evidence, "detected.color_tag=" + (color_tag if color_tag is not None else "absent")]
    preserved.append("user_interpretation=" + (user_interpretation if user_interpretation is not None else "none"))
    preserved.extend(library["preservedResults"])
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
