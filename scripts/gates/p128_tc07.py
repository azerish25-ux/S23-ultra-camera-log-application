"""TC-P128-07 Resume boundary duplication.

Host fixture. A playable assembly emits each overlap frame once. Duplicated or
omitted overlap frames fail cadence. The long-form account still has to list
every index from 0 inclusive to expected_frames exclusive exactly once.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path


CASE_INDEX = 6
NEGATIVE_TOKEN = "duplicated-overlap-frames"
OMITTED_TOKEN = "omitted-overlap-frame"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "playable",
    "overlapFrames",
    "frameRate",
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


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def _overlap(value) -> list[int]:
    if not isinstance(value, list) or not value:
        raise ValueError("overlapFrames must be a non-empty list")
    indexes = []
    for index, item in enumerate(value):
        if type(item) is not int:
            raise ValueError(f"overlapFrames[{index}] must be an int")
        indexes.append(item)
    return indexes


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    if type(payload["playable"]) is not bool:
        raise ValueError("playable must be a bool")
    if type(payload["frameRate"]) is bool or not isinstance(payload["frameRate"], (int, float)):
        raise ValueError("frameRate must be a number")
    frame_rate = float(payload["frameRate"])
    if not math.isfinite(frame_rate) or frame_rate <= 0:
        raise ValueError("frameRate must be a positive finite number")
    overlap = _overlap(payload["overlapFrames"])
    account = _CORE.validate_long_form(
        payload["expected_frames"],
        payload["accounted_frames"],
        payload["checkpoint_frames"],
        payload["audio_duration"],
        payload["video_duration"],
        payload["audio_absent"],
        payload["spot_check_only"],
    )
    counts: dict[int, int] = {}
    for index in payload["accounted_frames"]:
        counts[index] = counts.get(index, 0) + 1
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(account["reasons"])
    reasons.append("frameRate=" + format(frame_rate, ".12g"))
    reasons.append("overlapFrames=" + ",".join(str(index) for index in overlap))
    rejected = list(account["rejectedClaims"])
    if payload["playable"]:
        for index in overlap:
            count = counts.get(index, 0)
            if count > 1:
                _add(rejected, NEGATIVE_TOKEN)
                reasons.append(f"overlap frame {index} duplicated in a playable timeline")
                reasons.append(NEGATIVE)
            elif count != 1:
                _add(rejected, OMITTED_TOKEN)
                reasons.append(f"overlap frame {index} omitted from a playable timeline")
        if NEGATIVE_TOKEN not in rejected and OMITTED_TOKEN not in rejected:
            reasons.append("playable timeline emits each overlap frame once")
    else:
        reasons.append("assembly is not presented as playable")
    preserved = [evidence, "frameRate=" + format(frame_rate, ".12g")]
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
