"""TC-P126-07 Resume boundary duplication.

Host fixture. The assembled timeline must equal the intended frame ids once.
A playable movie with duplicated overlap frames fails cadence integrity.
Clip rows still follow the P126 playable rule.
"""

from __future__ import annotations

import importlib.util
import math
from collections import Counter
from pathlib import Path

CASE_INDEX = 6
NEGATIVE_TOKEN = "playable-movie-duplicated-overlap"
DUP_TOKEN = "duplicated-overlap-frames"
TIMELINE_DUP_TOKEN = "duplicated-timeline-frames"
OMITTED_TOKEN = "omitted-boundary-frames"
ORDER_TOKEN = "cadence-order-mismatch"
EXTRA_TOKEN = "unexpected-assembled-frame"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "frameIds",
    "expectedIds",
    "overlapIds",
    "playableMovie",
    "frameRate",
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


def _ids(value, label: str, *, allow_empty: bool) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(f"{label} must be a list of ids")
    parsed = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip() or item != item.strip():
            raise ValueError(f"{label}[{index}] must be a non-empty string")
        parsed.append(item)
    return parsed


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    frame_ids = _ids(payload["frameIds"], "frameIds", allow_empty=False)
    expected_ids = _ids(payload["expectedIds"], "expectedIds", allow_empty=False)
    overlap_ids = _ids(payload["overlapIds"], "overlapIds", allow_empty=True)
    expected_set = set(expected_ids)
    if any(item not in expected_set for item in overlap_ids):
        raise ValueError("overlapIds must be members of expectedIds")
    if type(payload["playableMovie"]) is not bool:
        raise ValueError("playableMovie must be a bool")
    rate = payload["frameRate"]
    if type(rate) is bool or not isinstance(rate, (int, float)):
        raise ValueError("frameRate must be a number")
    frame_rate = float(rate)
    if not math.isfinite(frame_rate) or frame_rate <= 0:
        raise ValueError("frameRate must be positive")
    library = _CORE.evaluate_library(payload["clips"], payload["omitted_ids"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(library["reasons"])
    reasons.append("frameRate=" + format(frame_rate, ".12g"))
    rejected = list(library["rejectedClaims"])
    counts = Counter(frame_ids)
    overlap_duplicated = any(counts[item] > 1 for item in overlap_ids)
    if overlap_duplicated:
        _add(rejected, DUP_TOKEN)
        reasons.append("overlap frames were repeated")
        if payload["playableMovie"]:
            _add(rejected, NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
    if any(count > 1 for count in counts.values()):
        _add(rejected, TIMELINE_DUP_TOKEN)
    missing = [item for item in expected_ids if counts[item] == 0]
    if missing:
        _add(rejected, OMITTED_TOKEN)
        reasons.append("omitted boundary frames: " + ",".join(missing))
    if any(item not in expected_set for item in frame_ids):
        _add(rejected, EXTRA_TOKEN)
        reasons.append("assembled timeline contains frames outside the intended set")
    if frame_ids == expected_ids:
        reasons.append("timeline-emitted-once")
    elif not missing and not any(count > 1 for count in counts.values()):
        _add(rejected, ORDER_TOKEN)
        reasons.append("assembled order does not match the intended timeline")
    preserved = [evidence, "frameRate=" + format(frame_rate, ".12g")]
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
